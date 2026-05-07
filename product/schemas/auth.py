from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class SignupRequest(BaseModel):
    email: str
    password: str
    role: Literal["doctor", "patient", "admin"]
    full_name: str
    phone: str | None = None
    license_number: str | None = None
    specialization: str | None = None
    date_of_birth: date | None = None
    sex: Literal["male", "female", "other"] | None = None
    claim_patient_uid: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    role: Literal["doctor", "patient", "admin"]

