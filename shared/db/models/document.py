# shared/db/models/document.py — document_jobs table
# Status, pipeline version, timestamps, observability columns.
# UNIQUE constraint on job_id — all writes use upsert.

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from shared.db.base import Base


class DocumentJob(Base):
    """ORM model for the document_jobs table.

    Tracks the lifecycle of a single document processing job from upload
    through Pipeline A completion. Pipeline B reads
    structured_text_for_embedding from this table — it never imports
    Pipeline A code directly.
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

    # ------ HITL ------
    hitl_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True if any HITL trigger condition fired",
    )
    hitl_reasons: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="JSON list of HITL trigger reasons",
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
        comment="Error details if status=FAILED",
    )

    # ------ Observability ------
    ocr_latency_ms: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="OCR stage latency in ms"
    )
    llm_latency_ms: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="LLM extraction stage latency in ms"
    )

    # ------ Constraints ------
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_document_jobs_job_id"),
    )

    def __repr__(self) -> str:
        return f"<DocumentJob job_id={self.job_id!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Upsert helper — INSERT ... ON CONFLICT (job_id) DO UPDATE
# ---------------------------------------------------------------------------


def upsert_job(db: Session, job_id: str, **fields: Any) -> None:
    """Insert or update a document_jobs row keyed on job_id.

    patient_id, document_type, and file_name are INSERT-ONLY — they are
    never overwritten on conflict. This allows Pipeline A to call upsert_job
    with only status fields without wiping out patient_id.
    """
    INSERT_ONLY_COLUMNS = {"patient_id", "document_type", "file_name"}

    # Always include job_id in insert
    insert_values: dict[str, Any] = {"job_id": job_id, **fields}

    # UPDATE clause: only columns explicitly passed AND not insert-only
    update_values: dict[str, Any] = {
        k: v for k, v in fields.items()
        if k not in INSERT_ONLY_COLUMNS
    }

    if not update_values:
        # Nothing to update — use DO NOTHING to avoid constraint violation
        stmt = (
            pg_insert(DocumentJob)
            .values(**insert_values)
            .on_conflict_do_nothing(index_elements=["job_id"])
        )
    else:
        stmt = (
            pg_insert(DocumentJob)
            .values(**insert_values)
            .on_conflict_do_update(
                index_elements=["job_id"],
                set_=update_values,
            )
        )

    db.execute(stmt)
    db.flush()
