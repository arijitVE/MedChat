from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: str
    role: Literal["doctor", "patient", "admin"]
    full_name: str
    phone: str | None = None
    age: int | None = None
    gender: str | None = None
    blood_group: str | None = None
    allergies: str | None = None
    chronic_conditions: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    last_login: datetime | None = None
    is_registered: bool = True
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class DoctorProfile(UserProfile):
    role: Literal["doctor"] = "doctor"
    license_number: str | None = None
    specialization: str | None = None


class PatientProfile(UserProfile):
    role: Literal["patient"] = "patient"
    patient_uid: str | None = None
    date_of_birth: date | None = None
    sex: Literal["male", "female", "other"] | None = None
    account_status: str | None = None
