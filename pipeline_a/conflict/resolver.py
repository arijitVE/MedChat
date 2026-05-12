# pipeline_a/conflict/resolver.py

from sqlalchemy.orm import Session
from shared.schemas.document import IngestedDocument
from shared.schemas.report import (
    OCRResult,
    ScoredField,
    PipelineAOutput,
    JobStatus,
    FieldStatus,
    DocumentType
)
from shared.db.models.document import upsert_job
from shared.db.models.extraction import upsert_fields
from shared.logger import get_logger

logger = get_logger(__name__)

CRITICAL_FIELDS: dict[DocumentType, list[str]] = {
    DocumentType.prescription: ["drug_name"],
}

def resolve(
    doc: IngestedDocument,
    ocr: OCRResult,
    scored_fields: list[ScoredField],
    db: Session
) -> PipelineAOutput:
    """Resolve HITL triggers, format for embedding, and upsert to DB."""
    
    hitl_reasons: list[str] = []
    
    # Trigger 1: Any field.status == HITL
    hitl_field_count = sum(1 for f in scored_fields if f.status == FieldStatus.hitl)
    if hitl_field_count > 0:
        hitl_reasons.append(f"{hitl_field_count} fields have LOW_CONFIDENCE status.")
        
    # Trigger 2: ocr_result.low_confidence == True
    if ocr.low_confidence and len(scored_fields) == 0:
        hitl_reasons.append(f"Document-level OCR confidence is below threshold ({ocr.avg_confidence:.4f}).")
        
    # Trigger 3: len(scored_fields) == 0
    if len(scored_fields) == 0:
        hitl_reasons.append("LLM produced zero fields after all retries and fallback.")
        
    # Trigger 4: Any critical field absent for this DocumentType
    critical_reqs = CRITICAL_FIELDS.get(doc.document_type, [])
    extracted_names = {f.name for f in scored_fields}
    missing_critical = [req for req in critical_reqs if req not in extracted_names]
    if missing_critical:
        hitl_reasons.append(f"Critical fields absent: {', '.join(missing_critical)}.")
        
    hitl_required = len(hitl_reasons) > 0
    job_status = JobStatus.hitl_required if hitl_required else JobStatus.completed
    
    # Assemble structured_text_for_embedding
    lines = [f"Document type: {doc.document_type.value}"]
    for f in scored_fields:
        unit_str = f" {f.unit}" if f.unit else ""
        ref_str = f" (reference: {f.reference_range})" if f.reference_range else ""
        if f.status == FieldStatus.auto:
            lines.append(f"{f.name}: {f.value}{unit_str}{ref_str}")
        else:
            lines.append(f"[LOW_CONFIDENCE] {f.name}: {f.value}{unit_str}")
            
    structured_text_for_embedding = "\n".join(lines)
    
    # DB Writes
    upsert_job(
        db,
        job_id=doc.job_id,
        patient_id=doc.patient_id,
        document_type=doc.document_type.value,
        status=job_status.value,
        hitl_required=hitl_required,
        hitl_reasons=hitl_reasons,
        structured_text_for_embedding=structured_text_for_embedding
    )
    upsert_fields(db, doc.job_id, scored_fields, patient_id=doc.patient_id)
    
    logger.info(
        "conflict_resolution",
        stage="conflict_resolution",
        job_id=doc.job_id,
        hitl_required=hitl_required,
        hitl_field_count=hitl_field_count,
        total_field_count=len(scored_fields),
        job_status=job_status.value,
        hitl_reason_list=hitl_reasons
    )
    
    return PipelineAOutput(
        job_id=doc.job_id,
        patient_id=doc.patient_id,
        document_type=doc.document_type,
        scored_fields=scored_fields,
        hitl_required=hitl_required,
        hitl_reasons=hitl_reasons,
        job_status=job_status,
        structured_text_for_embedding=structured_text_for_embedding
    )
