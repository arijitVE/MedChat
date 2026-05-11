from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AssignmentRequest(BaseModel):
    patient_id: UUID | None = None
    patient_uid: str | None = None
    assigned_by: Literal["admin", "doctor", "patient"] = "doctor"


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assignment_id: UUID
    doctor_id: UUID
    patient_id: UUID
    assigned_by: Literal["admin", "doctor", "patient"]
    status: Literal["pending", "active", "rejected"]
    created_at: datetime
    updated_at: datetime
