from datetime import datetime

from pydantic import BaseModel


class ClinicalField(BaseModel):
    # Identity
    field_id: str
    job_id: str
    patient_id: str
    document_type: str
    collection_date: str | None
    processed_at: datetime

    # Canonical field data
    name: str
    raw_name: str
    value: str
    numeric_value: float | None
    unit: str | None
    reference_range: str | None
    ref_low: float | None
    ref_high: float | None

    is_abnormal: bool | None

    # Source
    source_type: str = "patient"


class PatientRecord(BaseModel):
    patient_id: str
    job_id: str
    document_type: str
    processed_at: datetime
    structured_text: str
    fields: list[ClinicalField]
