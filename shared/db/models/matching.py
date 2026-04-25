# shared/db/models/matching.py — Fuzzy + semantic comparison results persistence
# Stores per-field match scores for audit and threshold calibration.

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from shared.db.base import Base


class MatchResult(Base):
    """ORM model for persisted matching results.

    Stores per-field fuzzy and semantic match scores. Used for:
    - Audit trail of how confidence was computed
    - Threshold calibration analysis
    - Debugging false positives / false negatives
    """

    __tablename__ = "match_results"

    # ------ Primary Key ------
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # ------ Job Reference ------
    job_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="Parent job ID",
    )

    # ------ Match Data ------
    field_name: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="Normalised field name",
    )
    llm_value: Mapped[str] = mapped_column(
        String(512), nullable=False,
        comment="Normalised value from LLM extraction",
    )
    ocr_best_phrase: Mapped[str] = mapped_column(
        String(512), nullable=False, default="",
        comment="Best-matching OCR phrase window",
    )
    fuzzy_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="RapidFuzz token_set_ratio (0–100)",
    )
    semantic_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Cosine similarity (0.0–1.0)",
    )
    combined_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Weighted combination (0.0–1.0)",
    )

    # ------ Constraints ------
    __table_args__ = (
        UniqueConstraint(
            "job_id", "field_name",
            name="uq_match_results_job_id_field_name",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MatchResult job_id={self.job_id!r} field={self.field_name!r} "
            f"combined={self.combined_score:.2f}>"
        )


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------


def upsert_match_result(db: Session, job_id: str, **fields: Any) -> None:
    """Upsert a match result row keyed on (job_id, field_name).

    Uses INSERT ... ON CONFLICT (job_id, field_name) DO UPDATE.
    """
    values = {"job_id": job_id, **fields}
    update_values = {
        k: v for k, v in fields.items()
        if k != "field_name"
    }

    stmt = (
        pg_insert(MatchResult)
        .values(**values)
        .on_conflict_do_update(
            constraint="uq_match_results_job_id_field_name",
            set_=update_values,
        )
    )
    db.execute(stmt)
    db.flush()
