# pipeline_a/orchestrator/process_document.py
import time
from sqlalchemy.orm import Session

from shared.db.models.document import upsert_job
from shared.schemas.report import JobStatus, DocumentType, PipelineAOutput
from shared.schemas.document import IngestedDocument
from shared.config import get_settings
from shared.logger import get_logger

from pipeline_a.ingestion import loader
from pipeline_a.llm_extraction.extractor import extract_fields
from pipeline_a.normalization.normalizer import run_normalization
from pipeline_a.conflict.resolver import resolve

logger = get_logger(__name__)

def run(
    job_id: str,
    patient_id: str,
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
        if doc_type_enum == DocumentType.unknown:
            doc_type_enum = loader.detect_document_type(file_name)
        
        # 1. Ingestion
        mime_type = loader.detect_mime_type(file_bytes)
        doc = IngestedDocument(
            job_id=job_id,
            patient_id=patient_id,
            file_bytes=file_bytes,
            mime_type=mime_type,
            document_type=doc_type_enum,
            file_name=file_name,
        )
        
        # 2. Image Preparation (No OCR text generation)
        if doc.mime_type == "application/pdf":
            page_images = loader.pdf_to_images(doc.file_bytes, dpi=200)
        else:
            page_images = [doc.file_bytes]
        
        # 3. LLM Extraction (Directly from images)
        llm_result = extract_fields(page_images, doc.document_type, job_id=job_id)
        
        # 4. Normalization
        norm_result = run_normalization(llm_result, doc.document_type, job_id=job_id)
        
        # 5. Output Assembly (Bypassing HITL, Scoring, Matching)
        output = resolve(doc, norm_result.fields, db)
        
        total_latency_ms = (time.perf_counter() - t_start) * 1000
        
        logger.info(
            "pipeline_a_completed",
            stage="orchestrator",
            job_id=job_id,
            total_pipeline_latency_ms=total_latency_ms,
            status="success"
        )
        
        return output

    except Exception as exc:
        total_latency_ms = (time.perf_counter() - t_start) * 1000
        upsert_job(db, job_id, patient_id=patient_id, status=JobStatus.failed.value, error_message=str(exc))
        logger.error(
            "pipeline_a_failed",
            stage="orchestrator",
            job_id=job_id,
            total_pipeline_latency_ms=total_latency_ms,
            status="error",
            error=str(exc)
        )
        raise
