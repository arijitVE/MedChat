from uuid import UUID, uuid4

from fastapi import HTTPException
from pipeline_b.cache.response_cache import invalidate_patient
from pipeline_b.ingestion.ingest import ingest_patient_record
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.schemas.user import UserProfile
from product.schemas.verification import (
    FieldEditRequest,
    FieldStatus,
    FieldVerificationRequest,
    ReportVerificationResponse,
    VerificationResponse,
)
from product.services.assignment_service import verify_doctor_patient_access
from shared.schemas.report import DocumentType
from shared.utils.validators import validate_field


def _get_report(db: Session, report_id: str | UUID):
    report = db.execute(
        text(
            """
            SELECT report_id, job_id, patient_id, uploaded_by, doctor_id, lifecycle_status
            FROM reports
            WHERE report_id = :report_id
            """
        ),
        {"report_id": report_id},
    ).mappings().first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _ensure_doctor_report_access(report, doctor_id, db: Session) -> None:
    has_access = (
        str(report["doctor_id"]) == str(doctor_id)
        or str(report["uploaded_by"]) == str(doctor_id)
        or verify_doctor_patient_access(doctor_id, report["patient_id"], db)
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Doctor does not have access to this report")


def _ensure_clinical_verifier_access(report, verifying_user: UserProfile, db: Session) -> None:
    if verifying_user.role == "admin":
        return
    if verifying_user.role == "doctor":
        _ensure_doctor_report_access(report, verifying_user.user_id, db)
        return
    raise HTTPException(status_code=403, detail="Unsupported verifier role")


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


def _write_report_audit(
    db: Session,
    user_id,
    user_role: str,
    action: str,
    report_id,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO audit_log (
                user_id, user_role, action, entity_type, entity_id,
                report_id, old_value, new_value
            )
            VALUES (
                :user_id, :user_role, :action, 'report', :entity_id,
                :report_id, :old_value, :new_value
            )
            """
        ),
        {
            "user_id": user_id,
            "user_role": user_role,
            "action": action,
            "entity_id": str(report_id),
            "report_id": report_id,
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


def _get_verification_by_id(db: Session, verification_id: str):
    return db.execute(
        text(
            """
            SELECT verification_id, report_id, job_id, field_name, field_value,
                   verified_by, verifier_role, verification_type, edited_value,
                   edit_reason, is_final, verified_at
            FROM field_verifications
            WHERE verification_id = :verification_id
            """
        ),
        {"verification_id": verification_id},
    ).mappings().one()


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
        raise HTTPException(status_code=403, detail="Field is locked by final verification")

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
    elif verifying_user.role == "admin":
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

    verification_id = str(uuid4())
    db.execute(
        text(
            """
            INSERT INTO field_verifications (
                verification_id, report_id, job_id, field_name, field_value,
                verified_by, verifier_role, verification_type,
                edited_value, edit_reason, is_final, verified_at
            )
            VALUES (
                :verification_id, :report_id, :job_id, :field_name, :field_value,
                :verified_by, :verifier_role, :verification_type,
                :edited_value, :edit_reason, :is_final, CURRENT_TIMESTAMP(6)
            )
            """
        ),
        {
            "verification_id": verification_id,
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
    )
    row = _get_verification_by_id(db, verification_id)

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


def edit_field_value(
    report_id: str,
    field_name: str,
    body: FieldEditRequest,
    verifying_user: UserProfile,
    db: Session,
) -> VerificationResponse:
    if verifying_user.role not in ("doctor", "admin"):
        raise HTTPException(status_code=403, detail="Only doctors or admins can edit report fields")
    report = _get_report(db, report_id)
    _ensure_clinical_verifier_access(report, verifying_user, db)

    locked = db.execute(
        text(
            """
            SELECT 1
            FROM field_verifications
            WHERE report_id = :report_id
              AND is_final = TRUE
            LIMIT 1
            """
        ),
        {"report_id": report_id},
    ).first()
    if locked is not None:
        raise HTTPException(status_code=403, detail="Unlock report before editing fields")

    field = _get_field(db, report["job_id"], field_name)
    new_value = body.edited_value.strip()
    if not new_value or not validate_field(field_name, new_value, DocumentType.unknown):
        raise HTTPException(status_code=400, detail="Invalid edited value")

    db.execute(
        text(
            """
            UPDATE report_fields
            SET value = :value,
                numeric_value = :numeric_value,
                status = 'hitl'
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

    verification_id = str(uuid4())
    db.execute(
        text(
            """
            INSERT INTO field_verifications (
                verification_id, report_id, job_id, field_name, field_value,
                verified_by, verifier_role, verification_type,
                edited_value, edit_reason, is_final, verified_at
            )
            VALUES (
                :verification_id, :report_id, :job_id, :field_name, :field_value,
                :verified_by, :verifier_role, 'edited',
                :edited_value, :edit_reason, FALSE, CURRENT_TIMESTAMP(6)
            )
            """
        ),
        {
            "verification_id": verification_id,
            "report_id": report_id,
            "job_id": report["job_id"],
            "field_name": field_name,
            "field_value": new_value,
            "verified_by": verifying_user.user_id,
            "verifier_role": verifying_user.role,
            "edited_value": new_value,
            "edit_reason": body.edit_reason,
        },
    )
    row = _get_verification_by_id(db, verification_id)

    db.execute(
        text(
            """
            UPDATE reports
            SET lifecycle_status = 'hitl_required',
                released_to_patient = FALSE,
                last_edited_at = NOW()
            WHERE report_id = :report_id
            """
        ),
        {"report_id": report_id},
    )
    _write_audit(
        db,
        verifying_user.user_id,
        verifying_user.role,
        "EDIT_FIELD",
        report_id,
        field_name,
        field["value"],
        new_value,
    )
    ingest_patient_record(str(report["patient_id"]), report["job_id"], db)
    invalidate_patient(str(report["patient_id"]))
    db.commit()
    return _response_from_row(row)


def verify_report(
    report_id: str,
    verifying_user: UserProfile,
    db: Session,
) -> ReportVerificationResponse:
    if verifying_user.role not in ("doctor", "admin"):
        raise HTTPException(status_code=403, detail="Only doctors or admins can verify reports")
    report = _get_report(db, report_id)
    _ensure_clinical_verifier_access(report, verifying_user, db)

    fields = db.execute(
        text(
            """
            SELECT name, value
            FROM report_fields
            WHERE job_id = :job_id
            ORDER BY id ASC
            """
        ),
        {"job_id": report["job_id"]},
    ).mappings().all()
    if not fields:
        raise HTTPException(status_code=400, detail="No extracted fields found for this report")

    db.execute(
        text(
            """
            UPDATE field_verifications
            SET is_final = FALSE
            WHERE report_id = :report_id
              AND is_final = TRUE
            """
        ),
        {"report_id": report_id},
    )

    for field in fields:
        db.execute(
            text(
                """
                INSERT INTO field_verifications (
                    report_id, job_id, field_name, field_value,
                    verified_by, verifier_role, verification_type,
                    edited_value, edit_reason, is_final, verified_at
                )
                VALUES (
                    :report_id, :job_id, :field_name, :field_value,
                    :verified_by, :verifier_role, 'approved',
                    NULL, 'Report-level verification', TRUE, CURRENT_TIMESTAMP(6)
                )
                """
            ),
            {
                "report_id": report_id,
                "job_id": report["job_id"],
                "field_name": field["name"],
                "field_value": field["value"],
                "verified_by": verifying_user.user_id,
                "verifier_role": verifying_user.role,
            },
        )

    db.execute(
        text(
            """
            UPDATE reports
            SET lifecycle_status = 'doctor_verified',
                released_to_patient = TRUE,
                last_edited_at = NOW()
            WHERE report_id = :report_id
            """
        ),
        {"report_id": report_id},
    )
    _write_report_audit(
        db,
        verifying_user.user_id,
        verifying_user.role,
        "VERIFY_REPORT",
        report_id,
        old_value=report["lifecycle_status"],
        new_value="doctor_verified",
    )
    _send_notification(
        db,
        report["patient_id"],
        verifying_user.user_id,
        "REPORT_VERIFIED",
        "report",
        report_id,
    )
    ingest_patient_record(str(report["patient_id"]), report["job_id"], db)
    invalidate_patient(str(report["patient_id"]))
    db.commit()
    return ReportVerificationResponse(
        report_id=report["report_id"],
        status="doctor_verified",
        verified_fields=len(fields),
    )


def unlock_report(
    report_id: str,
    verifying_user: UserProfile,
    db: Session,
) -> ReportVerificationResponse:
    if verifying_user.role not in ("doctor", "admin"):
        raise HTTPException(status_code=403, detail="Only doctors or admins can unlock reports")
    report = _get_report(db, report_id)
    _ensure_clinical_verifier_access(report, verifying_user, db)

    updated = db.execute(
        text(
            """
            UPDATE field_verifications
            SET is_final = FALSE
            WHERE report_id = :report_id
              AND is_final = TRUE
            """
        ),
        {"report_id": report_id},
    )
    db.execute(
        text(
            """
            UPDATE reports
            SET lifecycle_status = 'hitl_required',
                released_to_patient = FALSE,
                last_edited_at = NOW()
            WHERE report_id = :report_id
            """
        ),
        {"report_id": report_id},
    )
    _write_report_audit(
        db,
        verifying_user.user_id,
        verifying_user.role,
        "UNLOCK_REPORT",
        report_id,
        old_value=report["lifecycle_status"],
        new_value="hitl_required",
    )
    invalidate_patient(str(report["patient_id"]))
    db.commit()
    return ReportVerificationResponse(
        report_id=report["report_id"],
        status="hitl_required",
        verified_fields=updated.rowcount or 0,
    )


def get_field_verification_status(
    report_id: str,
    db: Session,
    requesting_user_role: str,
) -> list[FieldStatus]:
    report = _get_report(db, report_id)
    fields = db.execute(
        text(
            """
            SELECT name, value, unit, reference_range, numeric_value, confidence, status
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
                unit=field["unit"],
                reference_range=field["reference_range"],
                numeric_value=field["numeric_value"],
                confidence=field["confidence"],
                pipeline_status=pipeline_status,
                patient_verified=patient_verified,
                doctor_verified=doctor_verified,
                is_final=doctor_verified,
                eda_available=eda_available,
            )
        )
    return statuses
