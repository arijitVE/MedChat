# pipeline_a/worker/tasks.py
import time
from infra.queue.celery_config import celery_app
from shared.db.session import SessionLocal
from shared.db.models.document import upsert_job
from shared.db.models.extraction import upsert_fields
from shared.schemas.report import JobStatus
from shared.logger import get_logger
from pipeline_a.orchestrator import process_document

logger = get_logger(__name__)

@celery_app.task(bind=True, max_retries=2)
def process_document_task(self, job_id: str, patient_id: str, file_bytes_hex: str, document_type: str):
    start_time = time.time()
    db = SessionLocal()
    retry_count = self.request.retries
    
    try:
        # Mark job as PROCESSING
        upsert_job(db, job_id, status=JobStatus.processing.value)
        
        # Call orchestrator.run() ONLY
        output = process_document.run(job_id, patient_id, file_bytes_hex, document_type, db)
        
        # Upsert the result (safe on retry)
        upsert_job(
            db, 
            output.job_id, 
            status=output.job_status.value,
            hitl_required=output.hitl_required,
            hitl_reasons=output.hitl_reasons,
            structured_text_for_embedding=output.structured_text_for_embedding,
            ocr_latency_ms=output.ocr_latency_ms,
            llm_latency_ms=output.llm_latency_ms
        )
        upsert_fields(db, output.job_id, output.scored_fields)
        
        total_latency_ms = (time.time() - start_time) * 1000
        upsert_job(db, job_id, total_pipeline_latency_ms=total_latency_ms)

        logger.info(
            "worker_completed",
            stage="worker",
            job_id=job_id,
            retry_count=retry_count,
            total_pipeline_latency_ms=total_latency_ms,
            final_status=output.job_status.value
        )
        
        return {"job_id": job_id, "status": output.job_status.value}
        
    except Exception as exc:
        total_latency_ms = (time.time() - start_time) * 1000
        upsert_job(
            db, 
            job_id, 
            status=JobStatus.failed.value, 
            error_message=str(exc),
            total_pipeline_latency_ms=total_latency_ms
        )
        
        logger.error(
            "worker_failed",
            stage="worker",
            job_id=job_id,
            retry_count=retry_count,
            total_pipeline_latency_ms=total_latency_ms,
            final_status=JobStatus.failed.value,
            error=str(exc)
        )
        
        # Exponential backoff
        raise self.retry(exc=exc, countdown=30 * 2**retry_count)
        
    finally:
        db.close()
