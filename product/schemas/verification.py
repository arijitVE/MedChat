from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FieldVerificationRequest(BaseModel):
    verification_type: Literal["approved", "edited", "rejected"]
    edited_value: str | None = None
    edit_reason: str | None = None


class FieldEditRequest(BaseModel):
    edited_value: str
    edit_reason: str | None = None


class ReportVerificationResponse(BaseModel):
    report_id: UUID
    status: str
    verified_fields: int = 0


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    verification_id: UUID
    report_id: UUID
    job_id: str
    field_name: str
    field_value: str | None = None
    verified_by: UUID
    verifier_role: Literal["patient", "doctor"]
    verification_type: Literal["approved", "edited", "rejected"]
    edited_value: str | None = None
    edit_reason: str | None = None
    is_final: bool = False
    verified_at: datetime


class FieldStatus(BaseModel):
    field_name: str
    value: str | None
    display_value: str
    is_value_hidden: bool
    unit: str | None = None
    reference_range: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    numeric_value: float | None = None
    confidence: float
    pipeline_status: Literal["auto", "hitl", "missing"]
    patient_verified: bool = False
    doctor_verified: bool = False
    is_final: bool = False
    eda_available: bool = False
