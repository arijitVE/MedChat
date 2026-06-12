from __future__ import annotations

from json import dumps
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.auth.password import hash_password
from product.schemas.admin import AdminSettings, AdminStats, SystemHealth, HITLQueueItem
from product.services import assignment_service, notification_service
from shared.config import get_settings


def _count(db: Session, sql: str, params: dict | None = None) -> int:
    return int(db.execute(text(sql), params or {}).scalar_one())


def _pagination(page: int, page_size: int) -> tuple[int, int, int]:
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 1), 100)
    return safe_page, safe_page_size, (safe_page - 1) * safe_page_size


def _paginated_response(items: list[dict], total_count: int, page: int, page_size: int) -> dict:
    total_pages = max((total_count + page_size - 1) // page_size, 1)
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
    }


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
    db.execute(
        text(
            """
            UPDATE users
            SET password_hash = :password_hash,
                updated_at = NOW()
            WHERE user_id = :user_id
            """
        ),
        {
            "user_id": user_id,
            "password_hash": hash_password(new_password),
        },
    )
    row = db.execute(
        text("SELECT user_id, role FROM users WHERE user_id = :user_id"),
        {"user_id": user_id},
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
    page: int = 1,
    page_size: int = 20,
) -> dict:
    page, page_size, offset = _pagination(page, page_size)
    total_count = _count(
        db,
        "SELECT COUNT(*) FROM users WHERE (:role IS NULL OR role = :role)",
        {"role": role},
    )
    sql = """
        SELECT user_id, email, role, full_name, phone, age, gender,
               blood_group, allergies, chronic_conditions, address,
               emergency_contact, last_login, license_number,
               specialization, hospital_name, years_of_experience,
               department, profile_photo, verification_status,
               verification_rejection_reason, patient_uid, date_of_birth, sex,
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
            "limit": page_size,
            "offset": offset,
        },
    ).mappings().all()
    return _paginated_response([dict(row) for row in rows], total_count, page, page_size)


def list_assignments(db: Session, page: int = 1, page_size: int = 20) -> dict:
    page, page_size, offset = _pagination(page, page_size)
    total_count = _count(db, "SELECT COUNT(*) FROM doctor_patient_assignments")
    rows = db.execute(
        text(
            """
            SELECT a.assignment_id, a.doctor_id, d.full_name AS doctor_name,
                   a.patient_id, p.full_name AS patient_name, p.patient_uid,
                   a.assigned_by, a.status, a.created_at, a.updated_at
            FROM doctor_patient_assignments a
            JOIN users d ON d.user_id = a.doctor_id
            JOIN users p ON p.user_id = a.patient_id
            ORDER BY a.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": page_size, "offset": offset},
    ).mappings().all()
    return _paginated_response([dict(row) for row in rows], total_count, page, page_size)


def list_reports(
    db: Session,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    page, page_size, offset = _pagination(page, page_size)
    params = {"status": status, "limit": page_size, "offset": offset}
    total_count = _count(
        db,
        """
        SELECT COUNT(*)
        FROM reports
        WHERE (:status IS NULL OR lifecycle_status = :status)
        """,
        {"status": status},
    )
    rows = db.execute(
        text(
            """
            SELECT r.report_id, r.job_id, r.patient_id, p.full_name AS patient_name,
                   r.doctor_id, d.full_name AS doctor_name, r.uploaded_by,
                   r.file_name, r.upload_document_type, r.inferred_document_type,
                   r.lifecycle_status, r.released_to_patient, r.first_uploaded_at
            FROM reports r
            LEFT JOIN users p ON p.user_id = r.patient_id
            LEFT JOIN users d ON d.user_id = r.doctor_id
            WHERE (:status IS NULL OR r.lifecycle_status = :status)
            ORDER BY r.first_uploaded_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return _paginated_response([dict(row) for row in rows], total_count, page, page_size)


def list_failed_jobs(db: Session, page: int = 1, page_size: int = 20) -> dict:
    page, page_size, offset = _pagination(page, page_size)
    total_count = _count(
        db,
        """
        SELECT COUNT(*)
        FROM document_jobs dj
        LEFT JOIN reports r ON r.job_id = dj.job_id
        WHERE LOWER(dj.status) = 'failed'
           OR dj.error_message IS NOT NULL
           OR r.lifecycle_status = 'failed'
        """,
    )
    rows = db.execute(
        text(
            """
            SELECT dj.job_id, r.report_id, dj.patient_id, dj.file_name,
                   dj.status, r.lifecycle_status, dj.error_message,
                   dj.uploaded_at, dj.processed_at
            FROM document_jobs dj
            LEFT JOIN reports r ON r.job_id = dj.job_id
            WHERE LOWER(dj.status) = 'failed'
               OR dj.error_message IS NOT NULL
               OR r.lifecycle_status = 'failed'
            ORDER BY COALESCE(dj.processed_at, dj.uploaded_at) IS NULL,
                     COALESCE(dj.processed_at, dj.uploaded_at) DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": page_size, "offset": offset},
    ).mappings().all()
    return _paginated_response([dict(row) for row in rows], total_count, page, page_size)


def get_analytics(db: Session) -> dict:
    def grouped(sql: str) -> list[dict]:
        return [dict(row) for row in db.execute(text(sql)).mappings().all()]

    return {
        "total_users": _count(db, "SELECT COUNT(*) FROM users"),
        "total_doctors": _count(db, "SELECT COUNT(*) FROM users WHERE role = 'doctor'"),
        "total_patients": _count(db, "SELECT COUNT(*) FROM users WHERE role = 'patient'"),
        "total_reports": _count(db, "SELECT COUNT(*) FROM reports"),
        "failed_jobs": _count(db, "SELECT COUNT(*) FROM document_jobs WHERE LOWER(status) = 'failed' OR error_message IS NOT NULL"),
        "hitl_required": _count(db, "SELECT COUNT(*) FROM reports WHERE lifecycle_status = 'hitl_required'"),
        "reports_by_status": grouped(
            """
            SELECT lifecycle_status AS label, COUNT(*) AS value
            FROM reports
            GROUP BY lifecycle_status
            ORDER BY lifecycle_status
            """
        ),
        "users_by_role": grouped(
            """
            SELECT role AS label, COUNT(*) AS value
            FROM users
            GROUP BY role
            ORDER BY role
            """
        ),
        "reports_by_document_type": grouped(
            """
            SELECT COALESCE(inferred_document_type, 'unknown') AS label, COUNT(*) AS value
            FROM reports
            GROUP BY COALESCE(inferred_document_type, 'unknown')
            ORDER BY value DESC
            """
        ),
    }


def list_notifications(db: Session, page: int = 1, page_size: int = 20) -> dict:
    page, page_size, offset = _pagination(page, page_size)
    total_count = _count(db, "SELECT COUNT(*) FROM notifications")
    rows = db.execute(
        text(
            """
            SELECT n.notification_id, n.recipient_id, r.full_name AS recipient_name,
                   n.sender_id, s.full_name AS sender_name, n.type, n.title,
                   n.message, n.report_id, n.is_read, n.created_at
            FROM notifications n
            LEFT JOIN users r ON r.user_id = n.recipient_id
            LEFT JOIN users s ON s.user_id = n.sender_id
            ORDER BY n.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": page_size, "offset": offset},
    ).mappings().all()
    return _paginated_response([dict(row) for row in rows], total_count, page, page_size)


def list_audit_logs(db: Session, page: int = 1, page_size: int = 20) -> dict:
    page, page_size, offset = _pagination(page, page_size)
    total_count = _count(db, "SELECT COUNT(*) FROM audit_log")
    rows = db.execute(
        text(
            """
            SELECT log_id, user_id, user_role, action, entity_type, entity_id,
                   report_id, field_name, old_value, new_value, metadata, created_at
            FROM audit_log
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": page_size, "offset": offset},
    ).mappings().all()
    return _paginated_response([dict(row) for row in rows], total_count, page, page_size)


def get_system_health(db: Session) -> SystemHealth:
    db.execute(text("SELECT 1")).scalar_one()
    return SystemHealth(
        api_status="ok",
        database_status="ok",
        total_processing_reports=_count(
            db,
            "SELECT COUNT(*) FROM reports WHERE lifecycle_status IN ('uploaded', 'processing')",
        ),
        total_failed_reports=_count(
            db,
            "SELECT COUNT(*) FROM reports WHERE lifecycle_status = 'failed'",
        ),
        total_failed_jobs=_count(
            db,
            "SELECT COUNT(*) FROM document_jobs WHERE LOWER(status) = 'failed' OR error_message IS NOT NULL",
        ),
    )


def get_admin_settings() -> AdminSettings:
    settings = get_settings()
    return AdminSettings(
        storage_path=settings.STORAGE_PATH,
        max_file_size_mb=settings.MAX_FILE_SIZE_MB,
        jwt_expiry_minutes=settings.JWT_EXPIRY_MINUTES,
        rate_limit_storage=settings.RATE_LIMIT_STORAGE_URI,
        openai_configured=bool(settings.OPENAI_API_KEY),
        google_vision_configured=bool(settings.GOOGLE_APPLICATION_CREDENTIALS),
    )


def get_user(user_id: str | UUID, db: Session) -> dict:
    row = db.execute(
        text(
            """
            SELECT user_id, email, role, full_name, phone, age, gender,
                   blood_group, allergies, chronic_conditions, address,
                   emergency_contact, last_login, license_number,
                   specialization, hospital_name, years_of_experience,
                   department, profile_photo, verification_status,
                   verification_rejection_reason, patient_uid, date_of_birth, sex,
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
    db.execute(
        text(
            """
            UPDATE users
            SET is_active = :is_active,
                updated_at = NOW()
            WHERE user_id = :user_id
            """
        ),
        {
            "user_id": user_id,
            "is_active": is_active,
        },
    )
    row = db.execute(
        text(
            """
            SELECT user_id, email, role, full_name, phone, age, gender,
                   blood_group, allergies, chronic_conditions, address,
                   emergency_contact, last_login, license_number,
                   specialization, hospital_name, years_of_experience,
                   department, profile_photo, verification_status,
                   verification_rejection_reason, patient_uid, date_of_birth, sex,
                   is_registered, is_active, created_at, updated_at
            FROM users
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
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


def set_doctor_verification_status(
    doctor_id: str | UUID,
    verification_status: str,
    admin_id: str | UUID,
    db: Session,
    reason: str | None = None,
) -> dict:
    if verification_status not in {"pending_verification", "approved", "rejected", "suspended"}:
        raise HTTPException(status_code=400, detail="Invalid verification status")

    db.execute(
        text(
            """
            UPDATE users
            SET verification_status = :verification_status,
                verification_rejection_reason = :reason,
                updated_at = NOW()
            WHERE user_id = :doctor_id
              AND role = 'doctor'
            """
        ),
        {
            "doctor_id": doctor_id,
            "verification_status": verification_status,
            "reason": reason,
        },
    )
    row = db.execute(
        text(
            """
            SELECT user_id, email, role, full_name, phone, age, gender,
                   blood_group, allergies, chronic_conditions, address,
                   emergency_contact, last_login, license_number,
                   specialization, hospital_name, years_of_experience,
                   department, profile_photo, verification_status,
                   verification_rejection_reason, patient_uid, date_of_birth, sex,
                   is_registered, is_active, created_at, updated_at
            FROM users
            WHERE user_id = :doctor_id
              AND role = 'doctor'
            """
        ),
        {"doctor_id": doctor_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Doctor not found")

    db.execute(
        text(
            """
            INSERT INTO audit_log (user_id, user_role, action, entity_type, entity_id, metadata)
            VALUES (:user_id, 'admin', :action, 'user', :entity_id, :metadata)
            """
        ),
        {
            "user_id": admin_id,
            "action": f"DOCTOR_{verification_status.upper()}",
            "entity_id": str(doctor_id),
            "metadata": dumps({"verification_status": verification_status, "reason": reason}),
        },
    )
    notification_service.create_notification(
        row["user_id"],
        admin_id,
        "DOCTOR_VERIFICATION",
        "Doctor verification updated",
        f"Your doctor verification status is now {verification_status.replace('_', ' ')}.",
        None,
        db,
    )
    db.commit()
    return dict(row)


def get_hitl_queue(db: Session) -> list[HITLQueueItem]:
    rows = db.execute(
        text(
            """
            SELECT r.report_id, r.job_id, r.patient_id, r.doctor_id,
                   r.file_name, r.lifecycle_status,
                   SUM(CASE WHEN rf.status = 'hitl' THEN 1 ELSE 0 END) AS hitl_count,
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
