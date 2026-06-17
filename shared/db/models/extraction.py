# shared/db/models/extraction.py — report_fields table
# LLM structured outputs persisted per-field.
# UNIQUE constraint on (job_id, name) — all writes use upsert.

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, Session, mapped_column

from shared.db.base import Base
from shared.db.upsert import build_upsert


class ReportField(Base):
    """ORM model for the report_fields table.

    Stores individual extracted fields for a document job. Each row
    represents one named field (e.g. "hemoglobin", "drug_name") with its
    normalized value and metadata.

    The UNIQUE constraint on (job_id, name) enables upsert on Celery retry
    so duplicate fields are impossible at the DB level.
    """

    __tablename__ = "report_fields"

    # ------ Primary Key ------
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    # ------ Foreign Key ------
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → document_jobs (cascading delete)",
    )

    # ------ Denormalised for query performance ------
    patient_id: Mapped[str] = mapped_column(
        String(128), index=True,
        comment="Patient identifier (denormalised from document_jobs)",
    )

    # ------ Field Data ------
    name: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="Canonical field name (normalised)",
    )
    value: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Extracted / normalised field value",
    )
    unit: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
        comment="Canonical unit of measurement",
    )
    reference_range: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True,
        comment="Normal reference range",
    )
    collection_date: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True,
        comment="Sample collection or test date",
    )
    numeric_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Parsed numeric value for trend analytics",
    )
    ref_low: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Lower bound of reference range",
    )
    ref_high: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Upper bound of reference range",
    )

    # ------ Constraints ------
    __table_args__ = (
        UniqueConstraint("job_id", "name", name="uq_report_fields_job_id_name"),
    )

    def __repr__(self) -> str:
        return f"<ReportField job_id={self.job_id!r} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------


def upsert_fields(
    db: Session,
    job_id: str,
    scored_fields: list[Any],
    patient_id: str | None = None,
) -> None:
    """Bulk upsert extracted fields into report_fields.

    Uses a database-native upsert so Celery retries never create duplicate rows.

    Args:
        db: SQLAlchemy session.
        job_id: The parent job's unique identifier.
        scored_fields: List of ScoredField Pydantic models with at minimum
                       name, value, unit, reference_range, collection_date.

    Example:
        >>> from shared.schemas.report import ScoredField
        >>> fields = [ScoredField(name="hemoglobin", value="13.5", ...)]
        >>> upsert_fields(db, "abc-123", fields)
    """
    if not scored_fields:
        return

    for field in scored_fields:
        field_patient_id = patient_id or getattr(field, "patient_id", "")

        values = {
            "job_id": job_id,
            "patient_id": field_patient_id,
            "name": field.name,
            "value": field.value,
            "numeric_value": _parse_numeric_value(field.value),
            "unit": getattr(field, "unit", None),
            "reference_range": getattr(field, "reference_range", None),
            "collection_date": getattr(field, "collection_date", None),
            "ref_low": getattr(field, "ref_low", None),
            "ref_high": getattr(field, "ref_high", None),
        }

        update_values = {
            k: v for k, v in values.items()
            if k not in ("job_id", "name")  # don't update the conflict keys
        }

        stmt = build_upsert(
            db,
            ReportField,
            values,
            update_values,
            index_elements=["job_id", "name"],
            constraint="uq_report_fields_job_id_name",
        )
        db.execute(stmt)

    db.flush()


def _parse_numeric_value(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(str(value).strip().replace(",", ""))
    except ValueError:
        return None
