# pipeline_a/conflict/resolver.py

from sqlalchemy.orm import Session
from shared.schemas.document import IngestedDocument
from shared.schemas.report import (
    NormalizedField,
    ScoredField,
    PipelineAOutput,
    JobStatus,
)
from shared.db.models.document import upsert_job
from shared.db.models.extraction import upsert_fields
from shared.logger import get_logger

logger = get_logger(__name__)

def resolve(
    doc: IngestedDocument,
    normalized_fields: list[NormalizedField],
    db: Session
) -> PipelineAOutput:
    """Format normalized LLM fields for embedding and persistence."""
    
    # Map NormalizedField to ScoredField (defaulting to 1.0 confidence)
    scored_fields: list[ScoredField] = []
    for f in normalized_fields:
        scored = ScoredField(
            name=f.normalized_name,
            value=f.normalized_value,
            unit=f.unit,
            reference_range=f.reference_range,
            collection_date=f.collection_date,
        )
        scored_fields.append(scored)

    job_status = JobStatus.completed
    
    # Assemble structured_text_for_embedding
    lines = [f"Document type: {doc.document_type.value}"]
    for f in scored_fields:
        unit_str = f" {f.unit}" if f.unit else ""
        ref_str = f" (reference: {f.reference_range})" if f.reference_range else ""
        lines.append(f"{f.name}: {f.value}{unit_str}{ref_str}")
            
    structured_text_for_embedding = "\n".join(lines)
    
    # DB Writes
    upsert_job(
        db,
        job_id=doc.job_id,
        patient_id=doc.patient_id,
        document_type=doc.document_type.value,
        status=job_status.value,
        structured_text_for_embedding=structured_text_for_embedding
    )
    upsert_fields(db, doc.job_id, scored_fields, patient_id=doc.patient_id)
    
    logger.info(
        "conflict_resolution",
        stage="conflict_resolution",
        job_id=doc.job_id,
        total_field_count=len(scored_fields),
        job_status=job_status.value,
    )
    
    return PipelineAOutput(
        job_id=doc.job_id,
        patient_id=doc.patient_id,
        document_type=doc.document_type,
        scored_fields=scored_fields,
        job_status=job_status,
        structured_text_for_embedding=structured_text_for_embedding
    )
