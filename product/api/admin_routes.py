from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from product.auth.role_guard import require_role
from product.schemas.admin import AdminStats, HITLQueueItem
from product.schemas.assignment import AssignmentResponse
from product.schemas.user import UserProfile
from product.services import admin_service
from shared.db.session import get_db


router = APIRouter(prefix="/admin", tags=["admin"])


class AdminAssignmentRequest(BaseModel):
    doctor_id: UUID
    patient_id: UUID


class PasswordResetRequest(BaseModel):
    user_id: UUID
    new_password: str


@router.get("/stats", response_model=AdminStats)
def get_stats(
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.get_system_stats(db)


@router.get("/users")
def list_users(
    role: str | None = Query(default=None),
    limit: int = Query(default=100, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.list_users(db, role=role, limit=limit, offset=offset)


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


@router.get("/hitl-queue", response_model=list[HITLQueueItem])
def get_hitl_queue(
    current_user: UserProfile = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return admin_service.get_hitl_queue(db)


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
