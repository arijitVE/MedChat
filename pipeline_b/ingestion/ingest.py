import time

from sqlalchemy import text

from pipeline_b.adapters.pipeline_a_adapter import get_patient_record
from pipeline_b.cache.response_cache import invalidate_patient
from pipeline_b.chunking.chunker import chunk_record
from pipeline_b.embedding.embedder import embed
from pipeline_b.vector_db.qdrant_client import ensure_collections_exist, upsert_chunks
from shared.logger import get_logger


logger = get_logger(__name__)


def ingest_patient_record(patient_id: str, job_id: str, db):
    t_start = time.time()
    ensure_collections_exist()

    record = get_patient_record(patient_id, job_id, db)
    if record is None:
        logger.warning("record_not_found", job_id=job_id, patient_id=patient_id)
        return

    chunks = chunk_record(record)
    vectors = embed([c.chunk_text for c in chunks])

    field_chunks = [c for c in chunks if c.payload["chunk_type"] == "field"]
    doc_chunks = [c for c in chunks if c.payload["chunk_type"] == "document"]
    field_vecs = vectors[: len(field_chunks)]
    doc_vecs = vectors[len(field_chunks) :]

    upsert_chunks(field_chunks, field_vecs, "fields")
    upsert_chunks(doc_chunks, doc_vecs, "documents")

    invalidate_patient(patient_id)

    logger.info(
        "ingestion_complete",
        job_id=job_id,
        patient_id=patient_id,
        field_chunks=len(field_chunks),
        duration_ms=round((time.time() - t_start) * 1000, 2),
    )


def ingest_all_existing(db):
    rows = db.execute(
        text(
            "SELECT job_id, patient_id FROM document_jobs "
            "WHERE status = 'completed'"
        )
    ).fetchall()

    for row in rows:
        ingest_patient_record(row.patient_id, row.job_id, db)
