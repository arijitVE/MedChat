# shared/db/models/ocr.py — Raw OCR output persistence
# Stores the raw OCR text and per-word data for a document job.
# Enables audit trail and re-processing without re-calling Vision API.

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Boolean, Float, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from shared.db.base import Base


class OCROutput(Base):
    """ORM model for persisted OCR results.

    Stores the full OCR text, per-word data (as JSON), and aggregate
    confidence. Keyed on job_id (one OCR result per job).
    """

    __tablename__ = "ocr_outputs"

    # ------ Primary Key ------
    job_id: Mapped[str] = mapped_column(
        String(64), primary_key=True,
        comment="Job ID — one OCR result per job",
    )

    # ------ OCR Data ------
    raw_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
        comment="Full concatenated OCR text",
    )
    words_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="Per-word OCR data: [{text, confidence, bounding_box}, ...]",
    )
    page_count: Mapped[int] = mapped_column(
        nullable=False, default=1,
        comment="Number of pages processed",
    )

    # ------ Confidence ------
    avg_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Mean word-level confidence (0.0–1.0)",
    )
    low_confidence: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True if avg_confidence < OCR_CONFIDENCE_THRESHOLD",
    )

    # ------ Observability ------
    ocr_latency_ms: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="OCR stage latency in ms",
    )

    # ------ Constraints ------
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_ocr_outputs_job_id"),
    )

    def __repr__(self) -> str:
        return f"<OCROutput job_id={self.job_id!r} avg_confidence={self.avg_confidence:.2f}>"


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------


def upsert_ocr_output(db: Session, job_id: str, **fields: Any) -> None:
    """Upsert an OCR output row keyed on job_id.

    Uses INSERT ... ON CONFLICT (job_id) DO UPDATE.
    """
    values = {"job_id": job_id, **fields}
    update_values = {k: v for k, v in fields.items()}

    stmt = (
        pg_insert(OCROutput)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["job_id"],
            set_=update_values,
        )
    )
    db.execute(stmt)
    db.flush()
