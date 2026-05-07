from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportUploadRequest(BaseModel):
    patient_id: UUID | None = None
    patient_uid: str | None = None
    patient_email: str | None = None
    force: bool = False


class ReportStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: UUID
    job_id: str
    patient_id: UUID
    uploaded_by: UUID
    doctor_id: UUID | None = None
    file_path: str
    file_name: str
    file_mime: str
    file_size_bytes: int | None = None
    upload_document_type: str = "unknown"
    inferred_document_type: str = "unknown"
    lifecycle_status: Literal[
        "uploaded",
        "processing",
        "auto_approved",
        "hitl_required",
        "patient_verified",
        "doctor_verified",
        "fully_verified",
    ]
    released_to_patient: bool = False
    first_uploaded_at: datetime
    last_edited_at: datetime | None = None
    upload_count: int = 1
    file_hash: str | None = None
    is_duplicate: bool = False
    duplicate_of: UUID | None = None
