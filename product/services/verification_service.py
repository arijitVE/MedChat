from uuid import UUID

from fastapi import HTTPException
from pipeline_b.cache.response_cache import invalidate_patient
from pipeline_b.ingestion.ingest import ingest_patient_record
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.schemas.user import UserProfile
from product.schemas.verification import (
    FieldStatus,
    FieldVerificationRequest,
    VerificationResponse,
)
from product.services.assignment_service import verify_doctor_patient_access
from shared.schemas.report import DocumentType
from shared.utils.validators import validate_field


def _get_report(db: Session, report_id: str | UUID):
    report = db.execute(
        text(
            """
            SELECT report_id, job_id, patient_id, doctor_id, lifecycle_status
            FROM reports
            WHERE report_id = :report_id
            """
        ),
        {"report_id": report_id},
    ).mappings().first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _get_field(db: Session, job_id: str, field_name: str):
    field = db.execute(
        text(
            """
            SELECT id, job_id, patient_id, name, value, confidence, status
            FROM report_fields
            WHERE job_id = :job_id
              AND name = :field_name
            """
        ),
        {"job_id": job_id, "field_name": field_name},
    ).mappings().first()
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


def _parse_numeric(value: str) -> float | None:
    cleaned = value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _write_audit(
    db: Session,
    user_id,
    user_role: str,
    action: str,
    report_id,
    field_name: str,
    old_value: str | None,
    new_value: str | None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO audit_log (
                user_id, user_role, action, entity_type, entity_id,
                report_id, field_name, old_value, new_value
            )
            VALUES (
                :user_id, :user_role, :action, 'field', :entity_id,
                :report_id, :field_name, :old_value, :new_value
            )
            """
        ),
        {
            "user_id": user_id,
            "user_role": user_role,
            "action": action,
            "entity_id": field_name,
            "report_id": report_id,
            "field_name": field_name,
            "old_value": old_value,
            "new_value": new_value,
        },
    )


def _send_notification(
    db: Session,
    recipient_id,
    sender_id,
    notif_type: str,
    field_name: str,
    report_id,
) -> None:
    if recipient_id is None:
        return
    db.execute(
        text(
            """
            INSERT INTO notifications (
                recipient_id, sender_id, type, title, message, report_id
            )
            VALUES (
                :recipient_id, :sender_id, :type, :title, :message, :report_id
            )
            """
        ),
        {
            "recipient_id": recipient_id,
            "sender_id": sender_id,
            "type": notif_type,
            "title": "Field verified",
            "message": f"{field_name} was verified.",
            "report_id": report_id,
        },
    )


def _response_from_row(row) -> VerificationResponse:
    return VerificationResponse(
        verification_id=row["verification_id"],
        report_id=row["report_id"],
        job_id=row["job_id"],
        field_name=row["field_name"],
        field_value=row["field_value"],
        verified_by=row["verified_by"],
        verifier_role=row["verifier_role"],
        verification_type=row["verification_type"],
        edited_value=row["edited_value"],
        edit_reason=row["edit_reason"],
        is_final=row["is_final"],
        verified_at=row["verified_at"],
    )


def get_current_field_verification(report_id: str, field_name: str, db: Session):
    return db.execute(
        text(
            """
            SELECT verification_id, report_id, job_id, field_name, field_value,
                   verified_by, verifier_role, verification_type, edited_value,
                   edit_reason, is_final, verified_at
            FROM field_verifications
            WHERE report_id = :report_id
              AND field_name = :field_name
            ORDER BY verified_at DESC
            LIMIT 1
            """
        ),
        {"report_id": report_id, "field_name": field_name},
    ).mappings().first()


def get_field_verification_history(
    report_id: str,
    field_name: str,
    db: Session,
) -> list[VerificationResponse]:
    rows = db.execute(
        text(
            """
            SELECT verification_id, report_id, job_id, field_name, field_value,
                   verified_by, verifier_role, verification_type, edited_value,
                   edit_reason, is_final, verified_at
            FROM field_verifications
            WHERE report_id = :report_id
              AND field_name = :field_name
            ORDER BY verified_at ASC
            """
        ),
        {"report_id": report_id, "field_name": field_name},
    ).mappings().all()
    return [_response_from_row(row) for row in rows]


def _check_fully_verified(db: Session, report_id, job_id: str) -> None:
    total_fields = db.execute(
        text("SELECT COUNT(*) FROM report_fields WHERE job_id = :job_id"),
        {"job_id": job_id},
    ).scalar_one()
    final_fields = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT field_name)
            FROM field_verifications
            WHERE report_id = :report_id
              AND is_final = TRUE
            """
        ),
        {"report_id": report_id},
    ).scalar_one()
    if total_fields > 0 and total_fields == final_fields:
        db.execute(
            text(
                """
                UPDATE reports
                SET lifecycle_status = 'fully_verified'
                WHERE report_id = :report_id
                """
            ),
            {"report_id": report_id},
        )


def verify_field(
    report_id: str,
    field_name: str,
    body: FieldVerificationRequest,
    verifying_user: UserProfile,
    db: Session,
) -> VerificationResponse:
    report = _get_report(db, report_id)
    field = _get_field(db, report["job_id"], field_name)

    locked = db.execute(
        text(
            """
            SELECT 1
            FROM field_verifications
            WHERE report_id = :report_id
              AND field_name = :field_name
              AND is_final = TRUE
            LIMIT 1
            """
        ),
        {"report_id": report_id, "field_name": field_name},
    ).first()
    if locked is not None:
        raise HTTPException(status_code=403, detail="Field is locked by doctor verification")

    if verifying_user.role == "patient":
        if str(verifying_user.user_id) != str(report["patient_id"]):
            raise HTTPException(status_code=403, detail="Patient does not own this report")
        if report["doctor_id"] is not None and not verify_doctor_patient_access(
            report["doctor_id"],
            report["patient_id"],
            db,
        ):
            raise HTTPException(status_code=403, detail="No active doctor assignment")
        is_final = False
    elif verifying_user.role == "doctor":
        if not verify_doctor_patient_access(
            verifying_user.user_id,
            report["patient_id"],
            db,
        ):
            raise HTTPException(status_code=403, detail="Doctor does not have access to this patient")
        is_final = True
    else:
        raise HTTPException(status_code=403, detail="Unsupported verifier role")

    field_value = field["value"]
    new_value = body.edited_value if body.verification_type == "edited" else None
    if body.verification_type == "edited":
        if new_value is None or not validate_field(field_name, new_value, DocumentType.unknown):
            raise HTTPException(status_code=400, detail="Invalid edited value")
        db.execute(
            text(
                """
                UPDATE report_fields
                SET value = :value,
                    numeric_value = :numeric_value
                WHERE job_id = :job_id
                  AND name = :field_name
                """
            ),
            {
                "value": new_value,
                "numeric_value": _parse_numeric(new_value),
                "job_id": report["job_id"],
                "field_name": field_name,
            },
        )
        field_value = new_value

    row = db.execute(
        text(
            """
            INSERT INTO field_verifications (
                report_id, job_id, field_name, field_value,
                verified_by, verifier_role, verification_type,
                edited_value, edit_reason, is_final, verified_at
            )
            VALUES (
                :report_id, :job_id, :field_name, :field_value,
                :verified_by, :verifier_role, :verification_type,
                :edited_value, :edit_reason, :is_final, clock_timestamp()
            )
            RETURNING verification_id, report_id, job_id, field_name, field_value,
                      verified_by, verifier_role, verification_type, edited_value,
                      edit_reason, is_final, verified_at
            """
        ),
        {
            "report_id": report_id,
            "job_id": report["job_id"],
            "field_name": field_name,
            "field_value": field_value,
            "verified_by": verifying_user.user_id,
            "verifier_role": verifying_user.role,
            "verification_type": body.verification_type,
            "edited_value": body.edited_value,
            "edit_reason": body.edit_reason,
            "is_final": is_final,
        },
    ).mappings().one()

    action = "EDIT_FIELD" if body.verification_type == "edited" else "VERIFY_FIELD"
    _write_audit(
        db,
        verifying_user.user_id,
        verifying_user.role,
        action,
        report_id,
        field_name,
        field["value"],
        field_value,
    )
    if is_final:
        _send_notification(
            db,
            report["patient_id"],
            verifying_user.user_id,
            "DOCTOR_VERIFIED",
            field_name,
            report_id,
        )
    else:
        _send_notification(
            db,
            report["doctor_id"],
            verifying_user.user_id,
            "PATIENT_VERIFIED",
            field_name,
            report_id,
        )

    _check_fully_verified(db, report_id, report["job_id"])
    if body.verification_type == "edited":
        ingest_patient_record(str(report["patient_id"]), report["job_id"], db)
    invalidate_patient(str(report["patient_id"]))
    db.commit()
    return _response_from_row(row)


def get_field_verification_status(
    report_id: str,
    db: Session,
    requesting_user_role: str,
) -> list[FieldStatus]:
    report = _get_report(db, report_id)
    fields = db.execute(
        text(
            """
            SELECT name, value, confidence, status
            FROM report_fields
            WHERE job_id = :job_id
            ORDER BY id ASC
            """
        ),
        {"job_id": report["job_id"]},
    ).mappings().all()

    statuses: list[FieldStatus] = []
    for field in fields:
        current = get_current_field_verification(report_id, field["name"], db)
        patient_verified = current is not None and current["verifier_role"] == "patient"
        doctor_verified = current is not None and current["is_final"] is True
        pipeline_status = field["status"]
        is_hitl_hidden = (
            requesting_user_role == "patient"
            and pipeline_status == "hitl"
            and not doctor_verified
        )
        if is_hitl_hidden:
            value = None
            display_value = "Verification required"
            eda_available = False
        else:
            value = field["value"]
            display_value = field["value"]
            eda_available = pipeline_status == "auto" or patient_verified or doctor_verified

        statuses.append(
            FieldStatus(
                field_name=field["name"],
                value=value,
                display_value=display_value,
                is_value_hidden=is_hitl_hidden,
                confidence=field["confidence"],
                pipeline_status=pipeline_status,
                patient_verified=patient_verified,
                doctor_verified=doctor_verified,
                is_final=doctor_verified,
                eda_available=eda_available,
            )
        )
    return statuses
