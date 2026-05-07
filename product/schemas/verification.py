from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FieldVerificationRequest(BaseModel):
    verification_type: Literal["approved", "edited", "rejected"]
    edited_value: str | None = None
    edit_reason: str | None = None


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
    confidence: float
    pipeline_status: Literal["auto", "hitl"]
    patient_verified: bool = False
    doctor_verified: bool = False
    is_final: bool = False
    eda_available: bool = False
