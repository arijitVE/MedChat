# shared/db/models/confidence.py — Per-field confidence breakdown persistence
# Stores the component scores that fed into the final weighted confidence.

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, Session, mapped_column

from shared.db.base import Base
from shared.db.upsert import build_upsert


class ConfidenceBreakdown(Base):
    """ORM model for per-field confidence score breakdowns.

    Stores the individual components (match combined_score, ocr_word_conf)
    alongside the final weighted score. Used for:
    - Threshold calibration (should we adjust 0.85?)
    - Per-stage quality monitoring
    - Debugging why specific fields were flagged for HITL
    """

    __tablename__ = "confidence_breakdowns"

    # ------ Primary Key ------
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # ------ Job Reference ------
    job_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="Parent job ID",
    )

    # ------ Field Reference ------
    field_name: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="Normalised field name",
    )

    # ------ Score Components ------
    combined_match_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="0.6 * (fuzzy/100) + 0.4 * semantic",
    )
    ocr_word_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
        comment="Mean OCR word confidence for matched words",
    )
    final_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="0.7 * combined_match + 0.3 * ocr_word_conf",
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="auto",
        comment="FieldStatus: auto | hitl | missing",
    )
    hitl_reason: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True,
        comment="Descriptive reason if status=hitl",
    )

    # ------ Constraints ------
    __table_args__ = (
        UniqueConstraint(
            "job_id", "field_name",
            name="uq_confidence_breakdowns_job_id_field_name",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ConfidenceBreakdown job_id={self.job_id!r} field={self.field_name!r} "
            f"final={self.final_score:.2f} status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------


def upsert_confidence_breakdown(db: Session, job_id: str, **fields: Any) -> None:
    """Upsert a confidence breakdown row keyed on (job_id, field_name).

    Uses a database-native upsert keyed on (job_id, field_name).
    """
    values = {"job_id": job_id, **fields}
    update_values = {
        k: v for k, v in fields.items()
        if k != "field_name"
    }

    stmt = build_upsert(
        db,
        ConfidenceBreakdown,
        values,
        update_values,
        index_elements=["job_id", "field_name"],
        constraint="uq_confidence_breakdowns_job_id_field_name",
    )
    db.execute(stmt)
    db.flush()
