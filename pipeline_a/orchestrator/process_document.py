# pipeline_a/orchestrator/process_document.py
import time
from sqlalchemy.orm import Session

from shared.db.models.document import upsert_job
from shared.schemas.report import JobStatus, DocumentType, OCRResult, PipelineAOutput
from shared.schemas.document import IngestedDocument
from shared.config import get_settings
from shared.logger import get_logger

from pipeline_a.ingestion import loader
from pipeline_a.ocr import client as ocr_client
from pipeline_a.ocr import parser as ocr_parser
from pipeline_a.ocr import confidence as ocr_confidence
from pipeline_a.llm_extraction.extractor import extract_fields
from pipeline_a.normalization.normalizer import run_normalization
from pipeline_a.matching.matcher import run_matching
from pipeline_a.confidence.scorer import score_fields
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
    """Run all Pipeline A stages in exact order."""
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
        
        # 2. OCR
        responses, page_count = ocr_client.run_ocr_on_document(doc.file_bytes, doc.mime_type)
        raw_text, words = ocr_parser.parse_all_responses(responses)
        avg_conf, low_conf = ocr_confidence.aggregate_confidence(words, settings.OCR_CONFIDENCE_THRESHOLD)
        ocr_result = OCRResult(
            raw_text=raw_text,
            words=words,
            avg_confidence=avg_conf,
            low_confidence=low_conf
        )

        if doc.document_type == DocumentType.unknown:
            inferred_doc_type = loader.detect_document_type_from_text(ocr_result.raw_text)
            if inferred_doc_type != DocumentType.unknown:
                doc = doc.model_copy(update={"document_type": inferred_doc_type})
                logger.info(
                    "document_type_inferred_from_ocr",
                    stage="ingestion",
                    job_id=job_id,
                    document_type=inferred_doc_type.value,
                )
        
        # 3. LLM Extraction
        llm_result = extract_fields(ocr_result.raw_text, doc.document_type, job_id=job_id)
        
        # 4. Normalization
        norm_result = run_normalization(llm_result, doc.document_type, job_id=job_id)
        
        # 5. Matching
        match_result = run_matching(norm_result, ocr_result, job_id=job_id)
        
        # 6. Confidence Scoring
        scored_fields = score_fields(match_result, norm_result, ocr_result, job_id=job_id, document_type=doc.document_type.value)
        
        # 7. Conflict Resolution & Output Assembly
        # resolver.resolve() internally performs DB upserts according to Step 10 rules.
        output = resolve(doc, ocr_result, scored_fields, db)
        
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
