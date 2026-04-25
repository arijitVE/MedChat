# pipeline_a/hitl/service.py
from sqlalchemy.orm import Session
from shared.db.models.document import DocumentJob, upsert_job
from shared.db.models.extraction import ReportField, upsert_single_field
from shared.schemas.report import ScoredField, JobStatus, FieldStatus, PipelineAOutput, DocumentType

def get_hitl_queue(db: Session) -> list[DocumentJob]:
    """Retrieve all jobs requiring Human-in-the-Loop review."""
    return db.query(DocumentJob).filter(DocumentJob.status == JobStatus.hitl_required.value).all()

def apply_hitl_review(job_id: str, field_overrides: list[ScoredField], db: Session) -> PipelineAOutput:
    """Apply human review to fields and mark the job as completed."""
    
    # 1. Fetch the job
    job = db.query(DocumentJob).filter(DocumentJob.job_id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found.")
        
    # 2. Update overridden fields
    for field in field_overrides:
        field.status = FieldStatus.auto  # Manually reviewed, so it's auto now
        upsert_single_field(
            db, 
            job_id, 
            job.patient_id, 
            name=field.name, 
            value=field.value, 
            unit=field.unit, 
            reference_range=field.reference_range, 
            collection_date=field.collection_date, 
            confidence=1.0,  # Human review means 100% confidence
            status=FieldStatus.auto.value, 
            hitl_reason=None
        )
    
    # 3. Read ALL fields from DB to reconstruct `structured_text_for_embedding`
    all_fields_rows = db.query(ReportField).filter(ReportField.job_id == job_id).all()
    all_scored_fields = []
    
    lines = [f"Document type: {job.document_type}"]
    for row in all_fields_rows:
        unit_str = f" {row.unit}" if row.unit else ""
        ref_str = f" (reference: {row.reference_range})" if row.reference_range else ""
        
        if row.status == FieldStatus.auto.value:
            lines.append(f"{row.name}: {row.value}{unit_str}{ref_str}")
        else:
            lines.append(f"[LOW_CONFIDENCE] {row.name}: {row.value}{unit_str}")
            
        # Reconstruct ScoredField
        all_scored_fields.append(ScoredField(
            name=row.name,
            value=row.value,
            unit=row.unit,
            reference_range=row.reference_range,
            collection_date=row.collection_date,
            confidence=row.confidence,
            status=FieldStatus(row.status),
            hitl_reason=row.hitl_reason
        ))
        
    structured_text_for_embedding = "\n".join(lines)
    
    # 4. Upsert Job 
    upsert_job(
        db, 
        job_id, 
        status=JobStatus.completed.value,
        structured_text_for_embedding=structured_text_for_embedding,
        hitl_required=False
    )
    
    return PipelineAOutput(
        job_id=job.job_id,
        patient_id=job.patient_id,
        document_type=DocumentType(job.document_type),
        scored_fields=all_scored_fields,
        hitl_required=False,
        hitl_reasons=job.hitl_reasons or [],
        job_status=JobStatus.completed,
        structured_text_for_embedding=structured_text_for_embedding,
        ocr_latency_ms=job.ocr_latency_ms,
        llm_latency_ms=job.llm_latency_ms
    )
