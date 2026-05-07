from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdminStats(BaseModel):
    total_doctors: int
    total_patients: int
    total_reports: int
    reports_processing: int
    reports_hitl_required: int
    reports_fully_verified: int
    assignments_active: int
    assignments_pending: int


class HITLQueueItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: UUID
    job_id: str
    patient_id: UUID
    doctor_id: UUID | None = None
    file_name: str
    lifecycle_status: str
    hitl_count: int
    first_uploaded_at: datetime

