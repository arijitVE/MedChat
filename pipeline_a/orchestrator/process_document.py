# pipeline_a/orchestrator/process_document.py
import time
from sqlalchemy.orm import Session

from shared.schemas.report import JobStatus, DocumentType, PipelineAOutput
from shared.schemas.document import IngestedDocument
from shared.config import get_settings
from shared.logger import get_logger


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
    """Run simplified Pipeline A stages."""
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
        
        # --- Task 2/3/4 extraction logic will go here ---
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
        
        # --- Task 4: Chunking ---
        from pipeline_a.orchestrator.chunking import chunk_text
        chunks = chunk_text(pages_for_chunking)
        
        # --- Task 5: Medical Extraction ---
        from pipeline_a.llm_extraction.chunk_extractor import extract_from_chunk
        all_extracted_fields = []
        for chunk in chunks:
            fields = extract_from_chunk(chunk["chunk_text"], case_id, chunk["chunk_id"])
            all_extracted_fields.extend(fields)
        
        # --- Task 6 & 7: Merge & Normalize ---
        from pipeline_a.orchestrator.merger import merge_and_normalize
        scored_fields = merge_and_normalize(all_extracted_fields)
        
        # Format text for embedding
        lines = [f"Document type: {doc.document_type.value}"]
        for f in scored_fields:
            unit_str = f" {f.unit}" if f.unit else ""
            ref_str = f" (reference: {f.reference_range})" if f.reference_range else ""
            lines.append(f"{f.name}: {f.value}{unit_str}{ref_str}")
        structured_text_for_embedding = "\n".join(lines)
        
        # Persist extracted fields
        from shared.db.models.extraction import upsert_fields
        upsert_fields(db, case_id, scored_fields)
        
        # --- Task 12 & 13: Embeddings & Qdrant RAG ---
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
                        id=c["chunk_id"], 
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
