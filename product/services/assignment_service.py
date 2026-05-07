from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.schemas.assignment import AssignmentResponse
from product.schemas.user import DoctorProfile, PatientProfile


def _get_user(db: Session, user_id: str | UUID):
    return db.execute(
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


def _write_audit(
    db: Session,
    user_id: str | UUID,
    user_role: str,
    action: str,
    assignment_id: str | UUID,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO audit_log (user_id, user_role, action, entity_type, entity_id)
            VALUES (:user_id, :user_role, :action, 'assignment', :entity_id)
            """
        ),
        {
            "user_id": user_id,
            "user_role": user_role,
            "action": action,
            "entity_id": str(assignment_id),
        },
    )


def _send_notification(
    db: Session,
    recipient_id: str | UUID,
    sender_id: str | UUID | None,
    notif_type: str,
    title: str,
    message: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO notifications (recipient_id, sender_id, type, title, message)
            VALUES (:recipient_id, :sender_id, :type, :title, :message)
            """
        ),
        {
            "recipient_id": recipient_id,
            "sender_id": sender_id,
            "type": notif_type,
            "title": title,
            "message": message,
        },
    )


def _assignment_response(row) -> AssignmentResponse:
    return AssignmentResponse(
        assignment_id=row["assignment_id"],
        doctor_id=row["doctor_id"],
        patient_id=row["patient_id"],
        assigned_by=row["assigned_by"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_assignment(
    doctor_id,
    patient_id,
    initiated_by,
    db: Session,
    initiator_id=None,
) -> AssignmentResponse:
    doctor = _get_user(db, doctor_id)
    patient = _get_user(db, patient_id)
    if doctor is None or doctor["role"] != "doctor":
        raise HTTPException(status_code=400, detail="doctor_id must belong to a doctor")
    if patient is None or patient["role"] != "patient":
        raise HTTPException(status_code=400, detail="patient_id must belong to a patient")

    existing = db.execute(
        text(
            """
            SELECT 1
            FROM doctor_patient_assignments
            WHERE doctor_id = :doctor_id
              AND patient_id = :patient_id
              AND status IN ('pending', 'active')
            """
        ),
        {"doctor_id": doctor_id, "patient_id": patient_id},
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Assignment already exists")

    status = "active" if initiated_by == "admin" else "pending"
    row = db.execute(
        text(
            """
            INSERT INTO doctor_patient_assignments (
                doctor_id, patient_id, assigned_by, status
            )
            VALUES (:doctor_id, :patient_id, :assigned_by, :status)
            RETURNING assignment_id, doctor_id, patient_id, assigned_by,
                      status, created_at, updated_at
            """
        ),
        {
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "assigned_by": initiated_by,
            "status": status,
        },
    ).mappings().one()

    if initiated_by == "admin":
        if initiator_id is None:
            raise HTTPException(status_code=400, detail="admin initiator_id is required")
    else:
        initiator_id = initiator_id or (doctor_id if initiated_by == "doctor" else patient_id)
    target_id = patient_id if initiated_by in ("admin", "doctor") else doctor_id
    _write_audit(db, initiator_id, initiated_by, "ASSIGN_DOCTOR", row["assignment_id"])
    _send_notification(
        db,
        target_id,
        initiator_id,
        "ASSIGNMENT_REQUEST",
        "Assignment request",
        "A doctor-patient assignment changed state.",
    )
    db.commit()
    return _assignment_response(row)


def _get_assignment(db: Session, assignment_id: str | UUID):
    row = db.execute(
        text(
            """
            SELECT assignment_id, doctor_id, patient_id, assigned_by,
                   status, created_at, updated_at
            FROM doctor_patient_assignments
            WHERE assignment_id = :assignment_id
            """
        ),
        {"assignment_id": assignment_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return row


def approve_assignment(assignment_id, approving_user_id, db: Session) -> AssignmentResponse:
    assignment = _get_assignment(db, assignment_id)
    if str(approving_user_id) not in (str(assignment["doctor_id"]), str(assignment["patient_id"])):
        raise HTTPException(status_code=403, detail="User is not part of this assignment")
    if assignment["status"] != "pending":
        raise HTTPException(status_code=400, detail="Assignment is not pending")

    assigned_by = assignment["assigned_by"]
    pending_party = assignment["patient_id"] if assigned_by == "doctor" else assignment["doctor_id"]
    if str(approving_user_id) != str(pending_party):
        raise HTTPException(status_code=403, detail="Only the pending party can approve")

    row = db.execute(
        text(
            """
            UPDATE doctor_patient_assignments
            SET status = 'active', updated_at = NOW()
            WHERE assignment_id = :assignment_id
            RETURNING assignment_id, doctor_id, patient_id, assigned_by,
                      status, created_at, updated_at
            """
        ),
        {"assignment_id": assignment_id},
    ).mappings().one()

    _write_audit(db, approving_user_id, "patient" if assigned_by == "doctor" else "doctor", "APPROVE_ASSIGNMENT", assignment_id)
    other_party = row["patient_id"] if str(approving_user_id) == str(row["doctor_id"]) else row["doctor_id"]
    _send_notification(db, other_party, approving_user_id, "ASSIGNMENT_APPROVED", "Assignment approved", "A doctor-patient assignment was approved.")
    db.commit()
    return _assignment_response(row)


def reject_assignment(assignment_id, rejecting_user_id, db: Session) -> AssignmentResponse:
    assignment = _get_assignment(db, assignment_id)
    if assignment["status"] != "pending":
        raise HTTPException(status_code=400, detail="Assignment is not pending")
    if str(rejecting_user_id) not in (str(assignment["doctor_id"]), str(assignment["patient_id"])):
        raise HTTPException(status_code=403, detail="User is not part of this assignment")
    row = db.execute(
        text(
            """
            UPDATE doctor_patient_assignments
            SET status = 'rejected', updated_at = NOW()
            WHERE assignment_id = :assignment_id
            RETURNING assignment_id, doctor_id, patient_id, assigned_by,
                      status, created_at, updated_at
            """
        ),
        {"assignment_id": assignment_id},
    ).mappings().one()

    rejecting_role = "patient" if str(rejecting_user_id) == str(row["patient_id"]) else "doctor"
    target_id = row["doctor_id"] if rejecting_role == "patient" else row["patient_id"]
    _write_audit(db, rejecting_user_id, rejecting_role, "REJECT_ASSIGNMENT", assignment_id)
    _send_notification(db, target_id, rejecting_user_id, "ASSIGNMENT_REJECTED", "Assignment rejected", "A doctor-patient assignment was rejected.")
    db.commit()
    return _assignment_response(row)


def get_doctor_patients(doctor_id, db: Session) -> list[PatientProfile]:
    rows = db.execute(
        text(
            """
            SELECT u.user_id, u.email, u.role, u.full_name, u.phone,
                   u.patient_uid, u.date_of_birth, u.sex,
                   u.is_registered, u.is_active, u.created_at, u.updated_at
            FROM users u
            JOIN doctor_patient_assignments a ON a.patient_id = u.user_id
            WHERE a.doctor_id = :doctor_id
              AND a.status = 'active'
            """
        ),
        {"doctor_id": doctor_id},
    ).mappings().all()
    return [PatientProfile(**row) for row in rows]


def get_patient_doctors(patient_id, db: Session) -> list[DoctorProfile]:
    rows = db.execute(
        text(
            """
            SELECT u.user_id, u.email, u.role, u.full_name, u.phone,
                   u.license_number, u.specialization,
                   u.is_registered, u.is_active, u.created_at, u.updated_at
            FROM users u
            JOIN doctor_patient_assignments a ON a.doctor_id = u.user_id
            WHERE a.patient_id = :patient_id
              AND a.status = 'active'
            """
        ),
        {"patient_id": patient_id},
    ).mappings().all()
    return [DoctorProfile(**row) for row in rows]


def verify_doctor_patient_access(doctor_id, patient_id, db: Session) -> bool:
    row = db.execute(
        text(
            """
            SELECT 1
            FROM doctor_patient_assignments
            WHERE doctor_id = :doctor_id
              AND patient_id = :patient_id
              AND status = 'active'
            """
        ),
        {"doctor_id": doctor_id, "patient_id": patient_id},
    ).first()
    return row is not None


def list_doctor_assignments(doctor_id, db: Session) -> list[AssignmentResponse]:
    rows = db.execute(
        text(
            """
            SELECT assignment_id, doctor_id, patient_id, assigned_by,
                   status, created_at, updated_at
            FROM doctor_patient_assignments
            WHERE doctor_id = :doctor_id
              AND status IN ('pending', 'active')
            ORDER BY created_at DESC
            """
        ),
        {"doctor_id": doctor_id},
    ).mappings().all()
    return [_assignment_response(row) for row in rows]


def list_patient_assignments(patient_id, db: Session) -> list[AssignmentResponse]:
    rows = db.execute(
        text(
            """
            SELECT assignment_id, doctor_id, patient_id, assigned_by,
                   status, created_at, updated_at
            FROM doctor_patient_assignments
            WHERE patient_id = :patient_id
              AND status IN ('pending', 'active')
            ORDER BY created_at DESC
            """
        ),
        {"patient_id": patient_id},
    ).mappings().all()
    return [_assignment_response(row) for row in rows]
