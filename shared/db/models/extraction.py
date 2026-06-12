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
    value, confidence score, and review status.

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
        comment="Parsed numeric value for trend analytics when the extracted value is numeric",
    )

    # ------ Confidence & Status ------
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Final weighted confidence (0.0–1.0)",
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="auto",
        comment="FieldStatus enum value: auto | hitl | missing",
    )
    hitl_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Descriptive reason if status=hitl",
    )

    # ------ Constraints ------
    __table_args__ = (
        UniqueConstraint("job_id", "name", name="uq_report_fields_job_id_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReportField job_id={self.job_id!r} name={self.name!r} "
            f"confidence={self.confidence:.2f} status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------


def upsert_fields(
    db: Session,
    job_id: str,
    scored_fields: list[Any],
    patient_id: str | None = None,
) -> None:
    """Bulk upsert scored fields into report_fields.

    Uses a database-native upsert so Celery retries never create duplicate rows.

    Args:
        db: SQLAlchemy session.
        job_id: The parent job's unique identifier.
        scored_fields: List of ScoredField Pydantic models (or any object
                       with name, value, unit, reference_range,
                       collection_date, confidence, status, hitl_reason
                       attributes).

    Example:
        >>> from shared.schemas.report import ScoredField, FieldStatus
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
            "confidence": field.confidence,
            "status": field.status.value if hasattr(field.status, "value") else str(field.status),
            "hitl_reason": getattr(field, "hitl_reason", None),
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


def upsert_single_field(db: Session, job_id: str, patient_id: str, **field_data: Any) -> None:
    """Upsert a single report_fields row.

    Convenience wrapper for HITL review updates where individual fields
    are overridden by a human reviewer.

    Args:
        db: SQLAlchemy session.
        job_id: Parent job ID.
        patient_id: Patient ID.
        **field_data: Column values including at minimum 'name' and 'value'.
    """
    if "numeric_value" not in field_data and "value" in field_data:
        field_data["numeric_value"] = _parse_numeric_value(field_data["value"])

    values = {"job_id": job_id, "patient_id": patient_id, **field_data}
    update_values = {
        k: v for k, v in field_data.items()
        if k != "name"
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
