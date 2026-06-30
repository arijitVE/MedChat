# pipeline_a/orchestrator/process_document.py
import time
from datetime import datetime
from sqlalchemy.orm import Session

from shared.schemas.report import JobStatus, DocumentType, PipelineAOutput
from shared.schemas.document import IngestedDocument
from shared.config import get_settings
from shared.logger import get_logger
from shared.db.mongo import get_collection


logger = get_logger(__name__)

def run(
    job_id: str,
    case_id: str,
    document_id: str,
    file_bytes_hex: str,
    document_type: str,
    db: Session,
    file_name: str = "",
) -> PipelineAOutput:
    """Run simplified Pipeline A stages with unified string join and MongoDB persistence."""
    t_start = time.perf_counter()
    settings = get_settings()

    try:
        # 0. Prep
        file_bytes = bytes.fromhex(file_bytes_hex)
        doc_type_enum = DocumentType(document_type)
        
        # 1. Ingestion
        mime_type = "application/pdf" if file_bytes.startswith(b"%PDF") else "image/jpeg"
        doc = IngestedDocument(
            case_id=case_id,
            document_id=document_id,
            file_bytes=file_bytes,
            mime_type=mime_type,
            document_type=doc_type_enum,
            file_name=file_name,
        )
        
        from pipeline_a.ingestion.ocr import extract_text_from_document
        from shared.db.models.extraction import OCRPage
        
        extracted_pages = extract_text_from_document(doc.file_bytes, doc.mime_type)
        
        pages_for_chunking = []
        for page_no, extractor, text in extracted_pages:
            ocr_page = OCRPage(
                document_id=doc.document_id,
                page_no=page_no,
                extractor=extractor,
                extracted_text=text
            )
            db.add(ocr_page)
            pages_for_chunking.append({"page_no": page_no, "text": text})
            
        db.commit()
        
        # Ensure Document Type via Classifier if unknown
        if doc.document_type == DocumentType.unknown and pages_for_chunking:
            from shared.llm import get_llm_client, get_text_model
            client = get_llm_client()
            first_page_text = pages_for_chunking[0]["text"]
            
            prompt = f"""Classify this medical document into exactly ONE of the following categories: lab_report, prescription, discharge_summary, radiology. 
            If it does not fit any, return unknown. Return ONLY the category name.
            
            TEXT:
            {first_page_text[:3000]}"""
            
            try:
                resp = client.chat.completions.create(
                    model=get_text_model(),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                pred = (resp.choices[0].message.content or "").strip().lower()
                if pred in ["lab_report", "prescription", "discharge_summary", "radiology"]:
                    doc.document_type = DocumentType(pred)
                    doc_type_enum = doc.document_type
                    db.commit()
            except Exception as e:
                logger.error(f"LLM Classification failed: {e}")
        
        # Stage 2: Build unified document text
        pages_for_chunking.sort(key=lambda x: x["page_no"])
        unified_document_text = ""
        for p in pages_for_chunking:
            unified_document_text += f"\n--- PAGE {p['page_no']} ---\n{p['text']}\n\n"
        
        # Stage 3: Chunking
        from pipeline_a.orchestrator.chunking import chunk_text
        chunks = chunk_text(unified_document_text)
        
        # Stage 4: Unified LLM Extraction
        from pipeline_a.llm_extraction.chunk_extractor import extract_from_chunk
        all_extracted_fields = []
        all_metadata_dicts = []
        for chunk in chunks:
            fields, metadata = extract_from_chunk(chunk["chunk_text"], case_id, chunk["chunk_id"])
            all_extracted_fields.extend(fields)
            if metadata:
                all_metadata_dicts.append(metadata)
        
        # Stage 5: Merge & Normalize
        from pipeline_a.orchestrator.merger import merge_and_normalize, merge_metadata_dicts
        scored_fields = merge_and_normalize(all_extracted_fields)
        merged_metadata = merge_metadata_dicts(all_metadata_dicts)
        
        # Format text for embedding
        lines = [f"Document type: {doc.document_type.value}"]
        for f in scored_fields:
            unit_str = f" {f.unit}" if f.unit else ""
            ref_str = f" (reference: {f.reference_range})" if f.reference_range else ""
            lines.append(f"{f.name}: {f.value}{unit_str}{ref_str}")
        structured_text_for_embedding = "\n".join(lines)
        
        # Persist to MongoDB
        now = datetime.utcnow()
        col_fields = get_collection("case_clinical_fields")
        existing_doc = col_fields.find_one({"case_id": case_id})
        existing_fields = existing_doc.get("fields", []) if existing_doc else []
        
        # Keep fields that do not belong to the current document_id (idempotency)
        preserved_fields = [
            f for f in existing_fields 
            if f.get("document_id") != document_id
        ]
        
        new_fields = [
            {
                "document_id": document_id,
                "name": f.name,
                "value": f.value,
                "numeric_value": getattr(f, "numeric_value", None),
                "unit": getattr(f, "unit", None),
                "ref_low": getattr(f, "ref_low", None),
                "ref_high": getattr(f, "ref_high", None),
                "is_abnormal": getattr(f, "is_abnormal", None),
                "collection_date": getattr(f, "collection_date", None)
            }
            for f in scored_fields
        ]
        
        clinical_doc = {
            "case_id": case_id,
            "fields": preserved_fields + new_fields,
            "updated_at": now
        }
        col_fields.update_one(
            {"case_id": case_id},
            {"$set": clinical_doc},
            upsert=True
        )
        
        meta_update = {
            k: v for k, v in merged_metadata.items() if v is not None
        }
        meta_update["case_id"] = case_id
        meta_update["updated_at"] = now
        get_collection("case_metadata").update_one(
            {"case_id": case_id},
            {"$set": meta_update},
            upsert=True
        )
        
        # --- Stage 7: Embeddings & Qdrant RAG ---
        import sys
        from pathlib import Path
        root_dir = str(Path(__file__).resolve().parent.parent.parent)
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            
        from pipeline_b.vector_db.qdrant_client import ensure_collections_exist, upsert_vectors
        from pipeline_b.embedding.embedder import embed
        from qdrant_client.models import PointStruct
        import uuid
        
        ensure_collections_exist()
        
        if chunks:
            chunk_texts = [c["chunk_text"] for c in chunks]
            chunk_vectors = embed(chunk_texts)
            chunk_points = []
            for i, c in enumerate(chunks):
                chunk_points.append(
                    PointStruct(
                        id=uuid.UUID(c["chunk_id"]), 
                        vector=chunk_vectors[i], 
                        payload={
                            "case_id": case_id, 
                            "document_id": document_id, 
                            "page_start": c["page_start"], 
                            "page_end": c["page_end"], 
                            "text": c["chunk_text"]
                        }
                    )
                )
            upsert_vectors("raw_chunks", chunk_points)

        return PipelineAOutput(
            case_id=case_id,
            document_id=document_id,
            document_type=doc_type_enum,
            scored_fields=scored_fields,
            job_status=JobStatus.completed,
            structured_text_for_embedding=structured_text_for_embedding,
        )

    except Exception as exc:
        total_latency_ms = (time.perf_counter() - t_start) * 1000
        logger.error(
            "pipeline_a_failed",
            stage="orchestrator",
            job_id=job_id,
            total_pipeline_latency_ms=total_latency_ms,
            status="error",
            error=str(exc)
        )
        raise
