from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from product.auth.role_guard import require_role
from product.schemas.admin import AdminStats, HITLQueueItem
from product.schemas.assignment import AssignmentResponse
from product.schemas.user import UserProfile
from product.schemas.verification import (
    FieldStatus,
)
from product.services import admin_service
from product.services import notification_service
from product.services import report_service
from shared.db.session import get_db


router = APIRouter(prefix="/admin", tags=["admin"])


class AdminAssignmentRequest(BaseModel):
    doctor_id: UUID
    patient_id: UUID


class PasswordResetRequest(BaseModel):
    user_id: UUID
    new_password: str


class DoctorVerificationRequest(BaseModel):
    reason: str | None = None


@router.get("/stats", response_model=AdminStats)
def get_stats(
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.get_system_stats(db)


@router.get("/dashboard", response_model=AdminStats)
def get_dashboard(
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.get_system_stats(db)


@router.get("/users")
def list_users(
    role: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.list_users(db, role=role, page=page, page_size=page_size)


@router.get("/doctors")
def list_doctors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.list_users(db, role="doctor", page=page, page_size=page_size)


@router.get("/patients")
def list_patients(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.list_users(db, role="patient", page=page, page_size=page_size)


@router.get("/users/{user_id}")
def get_user(
    user_id: UUID,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.get_user(user_id, db)


@router.post("/assignments", response_model=AssignmentResponse)
def create_assignment(
    body: AdminAssignmentRequest,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.create_admin_assignment(
        body.doctor_id,
        body.patient_id,
        current_user.user_id,
        db,
    )


@router.get("/assignments")
def list_assignments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.list_assignments(db, page=page, page_size=page_size)


@router.get("/reports")
def list_reports(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.list_reports(db, status=status, page=page, page_size=page_size)


@router.get("/reports/{report_id}")
def get_report(
    report_id: UUID,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return report_service.get_report_for_admin(report_id, db)


@router.get("/reports/{report_id}/raw-file")
def get_raw_report(
    report_id: UUID,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    file_info = report_service.get_raw_report_file_for_admin(report_id, current_user.user_id, db)
    path = file_info["path"]
    if not path:
        raise HTTPException(status_code=404, detail="Raw report file not found")
    return FileResponse(
        path,
        media_type=file_info["media_type"],
        filename=file_info["filename"],
    )


@router.get("/reports/{report_id}/fields", response_model=list[FieldStatus])
def get_report_fields(
    report_id: UUID,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return report_service.get_field_status(
        str(report_id),
        db,
        requesting_user_role=current_user.role,
    )


@router.get("/failed-jobs")
def list_failed_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.list_failed_jobs(db, page=page, page_size=page_size)


@router.get("/hitl-queue", response_model=list[HITLQueueItem])
def get_hitl_queue(
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.get_hitl_queue(db)


@router.get("/analytics")
def get_analytics(
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.get_analytics(db)


@router.get("/notifications")
def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.list_notifications(db, page=page, page_size=page_size)


@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: UUID,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return notification_service.mark_notification_read(
        notification_id,
        current_user.user_id,
        db,
    )


@router.get("/audit-logs")
def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.list_audit_logs(db, page=page, page_size=page_size)


@router.get("/system-health")
def get_system_health(
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.get_system_health(db)


@router.get("/settings")
def get_settings(
    current_user: UserProfile = Depends(require_role("admin")),
):
    return admin_service.get_admin_settings()


@router.post("/password-reset")
def reset_password(
    body: PasswordResetRequest,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    admin_service.reset_user_password(
        body.user_id,
        body.new_password,
        current_user.user_id,
        db,
    )
    return {"status": "password_reset"}


@router.put("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: UUID,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.set_user_active(user_id, False, current_user.user_id, db)


@router.put("/users/{user_id}/activate")
def activate_user(
    user_id: UUID,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.set_user_active(user_id, True, current_user.user_id, db)


@router.put("/doctors/{doctor_id}/approve")
def approve_doctor(
    doctor_id: UUID,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.set_doctor_verification_status(
        doctor_id,
        "approved",
        current_user.user_id,
        db,
    )


@router.put("/doctors/{doctor_id}/reject")
def reject_doctor(
    doctor_id: UUID,
    body: DoctorVerificationRequest | None = None,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.set_doctor_verification_status(
        doctor_id,
        "rejected",
        current_user.user_id,
        db,
        reason=body.reason if body else None,
    )


@router.put("/doctors/{doctor_id}/suspend")
def suspend_doctor(
    doctor_id: UUID,
    body: DoctorVerificationRequest | None = None,
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.set_doctor_verification_status(
        doctor_id,
        "suspended",
        current_user.user_id,
        db,
        reason=body.reason if body else None,
    )
