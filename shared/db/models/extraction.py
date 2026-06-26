# shared/db/models/extraction.py — report_fields table
# LLM structured outputs persisted per-field.
# UNIQUE constraint on (job_id, name) — all writes use upsert.

from __future__ import annotations

from typing import Any, Optional

import re
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, Session, mapped_column

from shared.db.base import Base
from shared.db.upsert import build_upsert


class ReportField(Base):
    """DEPRECATED — replaced by MongoDB case_clinical_fields collection.

    ORM model for the report_fields table.

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
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → cases (cascading delete)",
    )
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → documents (cascading delete)",
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
        UniqueConstraint("case_id", "document_id", "name", "collection_date", name="uq_report_fields_case_doc_name_date"),
    )

    def __repr__(self) -> str:
        return f"<ReportField case_id={self.case_id!r} name={self.name!r}>"


class OCRPage(Base):
    __tablename__ = "ocr_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    extractor: Mapped[str] = mapped_column(String(64), nullable=False, comment="'pymupdf' | 'pdfplumber' | 'gpt4o_vision'")
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<OCRPage doc={self.document_id} page={self.page_no} extractor={self.extractor}>"


# ---------------------------------------------------------------------------
# Upsert helper
# ---------------------------------------------------------------------------


def upsert_fields(
    db: Session,
    case_id: str,
    document_id: str,
    scored_fields: list[Any],
) -> None:
    """Bulk upsert extracted fields into report_fields.

    Uses a database-native upsert so Celery retries never create duplicate rows.

    Args:
        db: SQLAlchemy session.
        case_id: The parent case's unique identifier.
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
        values = {
            "case_id": case_id,
            "document_id": document_id,
            "name": field.name,
            "value": field.value,
            "numeric_value": _parse_numeric_value(field.value),
            "unit": getattr(field, "unit", None),
            "reference_range": getattr(field, "reference_range", None),
            "collection_date": getattr(field, "collection_date", None) or "",
            "ref_low": getattr(field, "ref_low", None),
            "ref_high": getattr(field, "ref_high", None),
        }

        update_values = {
            k: v for k, v in values.items()
            if k not in ("case_id", "document_id", "name", "collection_date")  # don't update the conflict keys
        }

        stmt = build_upsert(
            db,
            ReportField,
            values,
            update_values,
            index_elements=["case_id", "document_id", "name", "collection_date"],
            constraint="uq_report_fields_case_doc_name_date",
        )
        db.execute(stmt)

    db.flush()


def _parse_numeric_value(value: Any) -> float | None:
    if value is None:
        return None

    s = str(value).strip().replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", s)
    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None
