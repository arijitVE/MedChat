from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.schemas.report import ReportStatusResponse
from product.services import notification_service, verification_service
from product.services.assignment_service import verify_doctor_patient_access


def _get_report_row(report_id: str | UUID, db: Session):
    row = db.execute(
        text(
            """
            SELECT report_id, job_id, patient_id, uploaded_by, doctor_id,
                   file_path, file_name, file_mime, file_size_bytes,
                   upload_document_type, inferred_document_type,
                   lifecycle_status, released_to_patient, first_uploaded_at,
                   last_edited_at, upload_count, file_hash, is_duplicate,
                   duplicate_of
            FROM reports
            WHERE report_id = :report_id
            """
        ),
        {"report_id": report_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return row


def _report_response(row) -> ReportStatusResponse:
    return ReportStatusResponse(**row)


def _write_audit(
    db: Session,
    user_id,
    user_role: str,
    action: str,
    report_id,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO audit_log (user_id, user_role, action, entity_type, entity_id, report_id)
            VALUES (:user_id, :user_role, :action, 'report', :entity_id, :report_id)
            """
        ),
        {
            "user_id": user_id,
            "user_role": user_role,
            "action": action,
            "entity_id": str(report_id),
            "report_id": report_id,
        },
    )


def ensure_doctor_patient_access(doctor_id: str | UUID, patient_id: str | UUID, db: Session) -> None:
    if not verify_doctor_patient_access(doctor_id, patient_id, db):
        raise HTTPException(status_code=403, detail="Doctor does not have access to this patient")


def release_report_to_patient(
    report_id: str | UUID,
    doctor_id: str | UUID,
    db: Session,
) -> ReportStatusResponse:
    report = _get_report_row(report_id, db)
    ensure_doctor_patient_access(doctor_id, report["patient_id"], db)
    if str(report["uploaded_by"]) != str(doctor_id):
        raise HTTPException(status_code=403, detail="Only the uploading doctor can release this report")

    row = db.execute(
        text(
            """
            UPDATE reports
            SET released_to_patient = TRUE,
                last_edited_at = NOW()
            WHERE report_id = :report_id
            RETURNING report_id, job_id, patient_id, uploaded_by, doctor_id,
                      file_path, file_name, file_mime, file_size_bytes,
                      upload_document_type, inferred_document_type,
                      lifecycle_status, released_to_patient, first_uploaded_at,
                      last_edited_at, upload_count, file_hash, is_duplicate,
                      duplicate_of
            """
        ),
        {"report_id": report_id},
    ).mappings().one()

    _write_audit(db, doctor_id, "doctor", "RELEASE_REPORT", report_id)
    notification_service.notify_report_released(row["patient_id"], row["report_id"], db)
    db.commit()
    return _report_response(row)


def get_report_for_patient(
    report_id: str | UUID,
    patient_id: str | UUID,
    db: Session,
) -> dict:
    report = _get_report_row(report_id, db)
    if str(report["patient_id"]) != str(patient_id):
        raise HTTPException(status_code=403, detail="Patient does not own this report")
    if not report["released_to_patient"]:
        raise HTTPException(status_code=404, detail="Report not found")

    fields = verification_service.get_field_verification_status(
        str(report_id),
        db,
        requesting_user_role="patient",
    )
    return {
        "report": _report_response(report),
        "fields": fields,
    }


def get_report_for_doctor(
    report_id: str | UUID,
    doctor_id: str | UUID,
    db: Session,
) -> dict:
    report = _get_report_row(report_id, db)
    ensure_doctor_patient_access(doctor_id, report["patient_id"], db)
    fields = verification_service.get_field_verification_status(
        str(report_id),
        db,
        requesting_user_role="doctor",
    )
    return {
        "report": _report_response(report),
        "fields": fields,
    }


def get_patient_sql_analytics(
    patient_id: str | UUID,
    db: Session,
) -> dict:
    # ANALYTICS: SQL engine only — never LLM
    # ANALYTICS: deduplicated on (patient_id, collection_date, field_name) — FIX 9c
    rows = db.execute(
        text(
            """
            WITH ranked AS (
                SELECT rf.patient_id, rf.collection_date, rf.name, rf.numeric_value,
                       r.is_duplicate, r.last_edited_at, r.first_uploaded_at,
                       ROW_NUMBER() OVER (
                           PARTITION BY rf.patient_id, rf.collection_date, rf.name
                           ORDER BY r.is_duplicate ASC,
                                    r.last_edited_at DESC NULLS LAST,
                                    r.first_uploaded_at DESC
                       ) AS rn
                FROM report_fields rf
                JOIN reports r ON r.job_id = rf.job_id
                WHERE rf.patient_id = :patient_id
                  AND rf.numeric_value IS NOT NULL
            )
            SELECT name AS field_name,
                   COUNT(*) AS sample_size,
                   AVG(numeric_value) AS mean,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY numeric_value) AS median,
                   MIN(numeric_value) AS min_value,
                   MAX(numeric_value) AS max_value
            FROM ranked
            WHERE rn = 1
            GROUP BY name
            ORDER BY name ASC
            """
        ),
        {"patient_id": str(patient_id)},
    ).mappings().all()
    return {
        "patient_id": str(patient_id),
        "analytics_engine": "sql",
        "fields": [dict(row) for row in rows],
    }


def get_report_eda(
    report_id: str | UUID,
    patient_id: str | UUID,
    db: Session,
) -> dict:
    report = _get_report_row(report_id, db)
    if str(report["patient_id"]) != str(patient_id):
        raise HTTPException(status_code=403, detail="Patient does not own this report")
    if not report["released_to_patient"]:
        raise HTTPException(status_code=404, detail="Report not found")

    fields = verification_service.get_field_verification_status(
        str(report_id),
        db,
        requesting_user_role="patient",
    )
    visible_fields = [field for field in fields if field.eda_available and field.value is not None]
    return {
        "report_id": str(report_id),
        "chart_json": {
            "type": "bar_chart",
            "data": {
                "fields": [field.field_name for field in visible_fields],
                "values": [field.value for field in visible_fields],
            },
            "meta": {
                "patient_id": str(patient_id),
                "hidden_fields": [field.field_name for field in fields if field.is_value_hidden],
            },
        },
    }
