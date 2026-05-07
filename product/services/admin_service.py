from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.auth.password import hash_password
from product.schemas.admin import AdminStats, HITLQueueItem
from product.services import assignment_service, notification_service


def _count(db: Session, sql: str, params: dict | None = None) -> int:
    return int(db.execute(text(sql), params or {}).scalar_one())


def get_system_stats(db: Session) -> AdminStats:
    return AdminStats(
        total_doctors=_count(db, "SELECT COUNT(*) FROM users WHERE role = 'doctor'"),
        total_patients=_count(db, "SELECT COUNT(*) FROM users WHERE role = 'patient'"),
        total_reports=_count(db, "SELECT COUNT(*) FROM reports"),
        reports_processing=_count(
            db,
            "SELECT COUNT(*) FROM reports WHERE lifecycle_status = 'processing'",
        ),
        reports_hitl_required=_count(
            db,
            "SELECT COUNT(*) FROM reports WHERE lifecycle_status = 'hitl_required'",
        ),
        reports_fully_verified=_count(
            db,
            "SELECT COUNT(*) FROM reports WHERE lifecycle_status = 'fully_verified'",
        ),
        assignments_active=_count(
            db,
            "SELECT COUNT(*) FROM doctor_patient_assignments WHERE status = 'active'",
        ),
        assignments_pending=_count(
            db,
            "SELECT COUNT(*) FROM doctor_patient_assignments WHERE status = 'pending'",
        ),
    )


def reset_user_password(
    user_id: str | UUID,
    new_password: str,
    admin_id: str | UUID,
    db: Session,
) -> None:
    row = db.execute(
        text(
            """
            UPDATE users
            SET password_hash = :password_hash,
                updated_at = NOW()
            WHERE user_id = :user_id
            RETURNING user_id, role
            """
        ),
        {
            "user_id": user_id,
            "password_hash": hash_password(new_password),
        },
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.execute(
        text(
            """
            INSERT INTO audit_log (user_id, user_role, action, entity_type, entity_id)
            VALUES (:user_id, 'admin', 'PASSWORD_RESET', 'user', :entity_id)
            """
        ),
        {
            "user_id": admin_id,
            "entity_id": str(user_id),
        },
    )
    notification_service.create_notification(
        row["user_id"],
        admin_id,
        "PASSWORD_RESET",
        "Password reset",
        "Your password was reset by an administrator.",
        None,
        db,
    )
    db.commit()


def list_users(
    db: Session,
    role: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    sql = """
        SELECT user_id, email, role, full_name, phone, license_number,
               specialization, patient_uid, date_of_birth, sex,
               is_registered, is_active, created_at, updated_at
        FROM users
        WHERE (:role IS NULL OR role = :role)
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(
        text(sql),
        {
            "role": role,
            "limit": limit,
            "offset": offset,
        },
    ).mappings().all()
    return [dict(row) for row in rows]


def get_user(user_id: str | UUID, db: Session) -> dict:
    row = db.execute(
        text(
            """
            SELECT user_id, email, role, full_name, phone, license_number,
                   specialization, patient_uid, date_of_birth, sex,
                   is_registered, is_active, created_at, updated_at
            FROM users
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


def set_user_active(
    user_id: str | UUID,
    is_active: bool,
    admin_id: str | UUID,
    db: Session,
) -> dict:
    row = db.execute(
        text(
            """
            UPDATE users
            SET is_active = :is_active,
                updated_at = NOW()
            WHERE user_id = :user_id
            RETURNING user_id, email, role, full_name, phone, license_number,
                      specialization, patient_uid, date_of_birth, sex,
                      is_registered, is_active, created_at, updated_at
            """
        ),
        {
            "user_id": user_id,
            "is_active": is_active,
        },
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    action = "ACTIVATE_USER" if is_active else "DEACTIVATE_USER"
    db.execute(
        text(
            """
            INSERT INTO audit_log (user_id, user_role, action, entity_type, entity_id)
            VALUES (:user_id, 'admin', :action, 'user', :entity_id)
            """
        ),
        {
            "user_id": admin_id,
            "action": action,
            "entity_id": str(user_id),
        },
    )
    db.commit()
    return dict(row)


def get_hitl_queue(db: Session) -> list[HITLQueueItem]:
    rows = db.execute(
        text(
            """
            SELECT r.report_id, r.job_id, r.patient_id, r.doctor_id,
                   r.file_name, r.lifecycle_status,
                   COUNT(rf.id) FILTER (WHERE rf.status = 'hitl') AS hitl_count,
                   r.first_uploaded_at
            FROM reports r
            LEFT JOIN report_fields rf ON rf.job_id = r.job_id
            WHERE r.lifecycle_status = 'hitl_required'
            GROUP BY r.report_id, r.job_id, r.patient_id, r.doctor_id,
                     r.file_name, r.lifecycle_status, r.first_uploaded_at
            ORDER BY r.first_uploaded_at ASC
            """
        )
    ).mappings().all()
    return [HITLQueueItem(**row) for row in rows]


def create_admin_assignment(
    doctor_id: str | UUID,
    patient_id: str | UUID,
    admin_id: str | UUID,
    db: Session,
):
    return assignment_service.create_assignment(
        doctor_id,
        patient_id,
        "admin",
        db,
        initiator_id=admin_id,
    )
