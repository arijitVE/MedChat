# shared/db/models/document.py — document_jobs table
# Status, timestamps, observability columns.
# UNIQUE constraint on job_id — all writes use upsert.

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, Session, mapped_column

from shared.db.base import Base
from shared.db.upsert import build_upsert


class DocumentJob(Base):
    """ORM model for the document_jobs table.

    Tracks the lifecycle of a single document processing job from upload
    through Pipeline A completion. Pipeline B reads
    structured_text_for_embedding from this table.
    """

    __tablename__ = "document_jobs"

    # ------ Primary Key ------
    job_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, comment="Unique job ID (UUID4)"
    )

    # ------ Core Fields ------
    patient_id: Mapped[str] = mapped_column(
        String(128), index=True, comment="Patient identifier"
    )
    document_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="DocumentType enum value"
    )
    file_name: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="Original uploaded filename"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending",
        comment="JobStatus enum value",
    )

    # ------ Pipeline B interface ------
    structured_text_for_embedding: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Flattened text for Pipeline B embedding",
    )

    # ------ Timestamps ------
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="When the document was uploaded",
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When processing completed (success or fail)",
    )

    # ------ Error ------
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Error details if status=failed",
    )

    # ------ Observability ------
    llm_latency_ms: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="LLM extraction stage latency in ms"
    )
    total_pipeline_latency_ms: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Total end-to-end pipeline latency in ms"
    )

    # ------ Constraints ------
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_document_jobs_job_id"),
    )

    def __repr__(self) -> str:
        return f"<DocumentJob job_id={self.job_id!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------


def upsert_job(db: Session, job_id: str, **fields: Any) -> None:
    """Insert or update a document_jobs row keyed on job_id.

    patient_id, document_type, and file_name are INSERT-ONLY — they are
    never overwritten on conflict. This allows Pipeline A to call upsert_job
    with only status fields without wiping out patient_id.
    """
    INSERT_ONLY_COLUMNS = {"patient_id", "document_type", "file_name"}

    insert_values: dict[str, Any] = {"job_id": job_id, **fields}

    update_values: dict[str, Any] = {
        k: v for k, v in fields.items()
        if k not in INSERT_ONLY_COLUMNS
    }

    if not update_values:
        stmt = build_upsert(db, DocumentJob, insert_values, {}, index_elements=["job_id"])
    else:
        stmt = build_upsert(
            db,
            DocumentJob,
            insert_values,
            update_values,
            index_elements=["job_id"],
        )

    db.execute(stmt)
    db.flush()
