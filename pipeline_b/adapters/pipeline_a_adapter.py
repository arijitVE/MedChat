import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from pipeline_b.schemas.input import ClinicalField, PatientRecord
from shared.db.models.document import DocumentJob
from shared.db.models.extraction import ReportField
from shared.utils.medical_dict import MEDICAL_SYNONYMS


def parse_reference_range(ref_str: str | None) -> tuple[float | None, float | None]:
    """
    Handles all formats seen in Indian lab reports:
      "11.5 - 16.4 gm/dl"       -> (11.5, 16.4)
      "FEMALE: 11.5 - 16.4"     -> (11.5, 16.4)
      "4000-11,000"             -> (4000.0, 11000.0)
      "50-70"                   -> (50.0, 70.0)
      "Male 42 52%"             -> (42.0, 52.0)
      "Not Found" | None        -> (None, None)
    """
    if ref_str is None:
        return None, None

    cleaned = ref_str.strip()
    if not cleaned or cleaned.lower() == "not found":
        return None, None

    cleaned = cleaned.replace(",", "")
    match = re.search(r"([\d]+\.?\d*)\s*[-–\s]\s*([\d]+\.?\d*)", cleaned)
    if not match:
        return None, None

    return float(match.group(1)), float(match.group(2))


def normalize_field_name(raw_name: str) -> str:
    cleaned = raw_name.strip().lower()
    return MEDICAL_SYNONYMS.get(cleaned, cleaned)


def compute_is_abnormal(
    numeric_value: float | None,
    ref_low: float | None,
    ref_high: float | None,
) -> bool | None:
    if numeric_value is None or (ref_low is None and ref_high is None):
        return None

    if ref_low is not None and numeric_value < ref_low:
        return True
    if ref_high is not None and numeric_value > ref_high:
        return True

    return False


def _get_value(row: Any, attr: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(attr, default)
    return getattr(row, attr, default)


def _parse_numeric_value(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(str(value).strip().replace(",", ""))
    except ValueError:
        return None


def _build_clinical_field(row: Any, job_row: Any) -> ClinicalField:
    raw_name = _get_value(row, "name", "")
    normalized_name = normalize_field_name(raw_name)
    numeric_value = _parse_numeric_value(_get_value(row, "value"))
    ref_low, ref_high = parse_reference_range(_get_value(row, "reference_range"))

    return ClinicalField(
        field_id=f"{_get_value(job_row, 'job_id')}_{normalized_name}",
        job_id=_get_value(row, "job_id"),
        patient_id=_get_value(job_row, "patient_id"),
        document_type=_get_value(job_row, "document_type"),
        collection_date=_get_value(row, "collection_date"),
        processed_at=_get_value(job_row, "processed_at") or datetime.now(timezone.utc),
        name=normalized_name,
        raw_name=raw_name,
        value=_get_value(row, "value"),
        numeric_value=numeric_value,
        unit=_get_value(row, "unit"),
        reference_range=_get_value(row, "reference_range"),
        ref_low=ref_low,
        ref_high=ref_high,
        confidence=_get_value(row, "confidence"),
        status=_get_value(row, "status"),
        is_abnormal=compute_is_abnormal(numeric_value, ref_low, ref_high),
        source_type="patient",
    )


def get_patient_record(
    patient_id: str,
    job_id: str,
    db: Session,
) -> PatientRecord | None:
    job_row = (
        db.query(DocumentJob)
        .filter(DocumentJob.job_id == job_id, DocumentJob.patient_id == patient_id)
        .first()
    )
    if job_row is None:
        return None

    field_rows = (
        db.query(ReportField)
        .filter(ReportField.job_id == job_id)
        .order_by(ReportField.name)
        .all()
    )

    return PatientRecord(
        patient_id=job_row.patient_id,
        job_id=job_row.job_id,
        document_type=job_row.document_type,
        processed_at=job_row.processed_at or datetime.now(timezone.utc),
        hitl_required=job_row.hitl_required,
        structured_text=job_row.structured_text_for_embedding or "",
        fields=[_build_clinical_field(row, job_row) for row in field_rows],
    )


def get_all_records_for_patient(patient_id: str, db: Session) -> list[PatientRecord]:
    job_rows = (
        db.query(DocumentJob)
        .filter(
            DocumentJob.patient_id == patient_id,
            DocumentJob.status.in_(("completed", "hitl_required")),
        )
        .order_by(DocumentJob.processed_at.asc())
        .all()
    )

    records: list[PatientRecord] = []
    for job_row in job_rows:
        record = get_patient_record(patient_id, job_row.job_id, db)
        if record is not None:
            records.append(record)

    return records
