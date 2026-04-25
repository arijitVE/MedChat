# pipeline_a/hitl/queue.py
from sqlalchemy.orm import Session
from shared.db.models.document import upsert_job
from shared.schemas.report import JobStatus

def push_to_hitl_queue(job_id: str, hitl_reasons: list[str], db: Session) -> None:
    """Mark a document job as requiring HITL review."""
    upsert_job(
        db,
        job_id=job_id,
        status=JobStatus.hitl_required.value,
        hitl_reasons=hitl_reasons,
        hitl_required=True
    )
