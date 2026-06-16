from datetime import datetime
from typing import Any
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


class AdminReportItem(BaseModel):
    report_id: UUID
    job_id: str
    patient_id: UUID
    patient_name: str | None = None
    doctor_id: UUID | None = None
    doctor_name: str | None = None
    uploaded_by: UUID
    file_name: str
    upload_document_type: str
    inferred_document_type: str | None = None
    lifecycle_status: str
    released_to_patient: bool
    first_uploaded_at: datetime


class FailedJobItem(BaseModel):
    job_id: str
    report_id: UUID | None = None
    patient_id: str | None = None
    file_name: str | None = None
    status: str
    lifecycle_status: str | None = None
    error_message: str | None = None
    uploaded_at: datetime | None = None
    processed_at: datetime | None = None


class AdminAnalytics(BaseModel):
    total_users: int
    total_doctors: int
    total_patients: int
    total_reports: int
    failed_jobs: int
    hitl_required: int
    reports_by_status: list[dict[str, Any]]
    users_by_role: list[dict[str, Any]]
    reports_by_document_type: list[dict[str, Any]]


class AuditLogItem(BaseModel):
    log_id: UUID
    user_id: UUID | None = None
    user_role: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    report_id: UUID | None = None
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime


class SystemHealth(BaseModel):
    api_status: str
    database_status: str
    total_processing_reports: int
    total_failed_reports: int
    total_failed_jobs: int


class AdminSettings(BaseModel):
    storage_path: str
    max_file_size_mb: int
    jwt_expiry_minutes: int
    rate_limit_storage: str
    openai_configured: bool
