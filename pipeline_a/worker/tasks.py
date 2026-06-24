# pipeline_a/worker/tasks.py
import time
from datetime import datetime
from celery import chord, group
from infra.queue.celery_config import celery_app
from shared.db.session import SessionLocal
from shared.db.models.case import Job, Document
from shared.schemas.report import JobStatus
from shared.logger import get_logger
from pipeline_a.orchestrator import process_document
from pipeline_a.orchestrator.insights import generate_insights_for_case
from storage.backend import get_storage

logger = get_logger(__name__)

@celery_app.task(bind=True, max_retries=2)
def process_case_task(self, job_id: str, case_id: str):
    logger.info(f"Starting process_case_task for case_id {case_id}")
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job:
            job.status = "PROCESSING"
            db.commit()
            
        docs = db.query(Document).filter(Document.case_id == case_id).all()
        
        if not docs:
            if job:
                job.status = "COMPLETED"
                job.completed_at = datetime.utcnow()
                db.commit()
            return {"job_id": job_id, "status": "COMPLETED"}

        # Build a parallel group — one task per document
        parallel_tasks = group(
            process_single_document.s(job_id, case_id, doc.id, doc.storage_path)
            for doc in docs
        )

        # chord: run aggregation ONLY after ALL parallel tasks finish
        chord(parallel_tasks)(generate_insights_for_case_task.s(job_id, case_id))

        return {"job_id": job_id, "status": "PROCESSING_STARTED"}

    except Exception as exc:
        if job:
            job.status = "FAILED"
            job.error_message = str(exc)
            db.commit()
        logger.error(f"process_case_task failed: {exc}")
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def process_single_document(self, job_id: str, case_id: str, doc_id: str, storage_key: str):
    logger.info(f"Processing document {doc_id}")
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if not doc:
            logger.warning(f"Document {doc_id} not found.")
            return None

        # Idempotency: skip if already processed
        if doc.status == "PROCESSED":
            return doc_id

        doc.status = "IN_PROGRESS"
        db.commit()

        if not storage_key:
            logger.warning(f"Document {doc_id} has no storage_key. Skipping.")
            doc.status = "FAILED"
            db.commit()
            return None

        storage = get_storage()
        file_bytes = storage.download_file(storage_key)
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

        doc.status = "PROCESSED"
        db.commit()
        return doc_id

    except Exception as exc:
        db.rollback()
        db.close()
        
        try:
            with SessionLocal() as retry_db:
                doc = retry_db.get(Document, doc_id)
                if doc:
                    doc.status = "FAILED"
                    retry_db.commit()
        except Exception as retry_exc:
            logger.error(f"Failed to update document status on failure: {retry_exc}")
            
        logger.error(f"process_single_document failed for {doc_id}: {exc}")
        retries = self.request.retries
        raise self.retry(exc=exc, countdown=30 * (2 ** retries))
    finally:
        try:
            db.close()
        except Exception:
            pass


@celery_app.task(bind=True)
def generate_insights_for_case_task(self, doc_ids: list, job_id: str, case_id: str):
    logger.info(f"Generating insights for case_id {case_id}")
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        
        # Filter out None results from failed tasks
        successful = [d for d in doc_ids if d is not None]
        if not successful:
            if job:
                job.status = "FAILED"
                job.error_message = "All documents failed processing."
                db.commit()
            return

        generate_insights_for_case(case_id, db)

        if job:
            job.status = "COMPLETED"
            job.completed_at = datetime.utcnow()
            db.commit()
            
    except Exception as exc:
        job = db.get(Job, job_id)
        if job:
            job.status = "FAILED"
            job.error_message = str(exc)
            db.commit()
        logger.error(f"generate_insights_for_case_task failed: {exc}")
    finally:
        db.close()
