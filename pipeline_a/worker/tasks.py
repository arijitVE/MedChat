# pipeline_a/worker/tasks.py
import time
from datetime import datetime
from infra.queue.celery_config import celery_app
from shared.db.session import SessionLocal
from shared.db.models.case import Job, Document
from shared.schemas.report import JobStatus
from shared.logger import get_logger
from pipeline_a.orchestrator import process_document
from pipeline_a.orchestrator.insights import generate_insights_for_case

logger = get_logger(__name__)

@celery_app.task(bind=True, max_retries=2)
def process_case_task(self, job_id: str, case_id: str):
    start_time = time.time()
    db = SessionLocal()
    retry_count = self.request.retries
    
    job = None
    try:
        job = db.get(Job, job_id)
        if job:
            job.status = JobStatus.processing.value
            db.commit()
            
        docs = db.query(Document).filter(Document.case_id == case_id).all()
        
        for doc in docs:
            logger.info(f"Processing document {doc.id}")
            if not doc.storage_path:
                logger.warning(f"Document {doc.id} has no storage_path. Skipping.")
                continue
                
            with open(doc.storage_path, "rb") as f:
                file_bytes = f.read()
                
            file_bytes_hex = file_bytes.hex()
            
            # process document
            process_document.run(
                job_id=job_id,
                case_id=case_id,
                document_id=doc.id,
                file_bytes_hex=file_bytes_hex,
                document_type=doc.doc_type,
                db=db,
                file_name=doc.file_name
            )
            
            # update doc status
            doc.status = "PROCESSED"
            db.commit()
            
        # generate insights
        generate_insights_for_case(case_id, db)
            
        if job:
            job.status = JobStatus.completed.value
            job.completed_at = datetime.utcnow()
            db.commit()
            
        return {"job_id": job_id, "status": JobStatus.completed.value}
        
    except Exception as exc:
        if job:
            job.status = JobStatus.failed.value
            job.error_message = str(exc)
            db.commit()
        logger.error(f"process_case_task failed: {exc}")
        raise self.retry(exc=exc, countdown=30 * 2**retry_count)
    finally:
        db.close()
