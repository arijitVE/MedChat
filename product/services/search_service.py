from __future__ import annotations

from uuid import UUID
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from product.schemas.user import PatientProfile


def _name_token(value: str | None, fallback: str) -> str:
    raw = (value or fallback).strip()
    token = re.sub(r"[^A-Za-z0-9-]+", "_", raw).strip("_")
    return token or fallback


def _document_type_token(inferred_document_type: str | None, upload_document_type: str | None) -> str:
    raw_type = inferred_document_type if inferred_document_type and inferred_document_type != "unknown" else upload_document_type
    token = _name_token(raw_type, "Medical")
    words = [word for word in token.split("_") if word]
    title_words = [word[:1].upper() + word[1:].lower() for word in words]
    if not title_words:
        title_words = ["Medical"]
    if "report" not in {word.lower() for word in title_words}:
        title_words.append("Report")
    return "_".join(title_words)


def _with_display_report_name(row: dict) -> dict:
    row["display_report_name"] = (
        f"{_name_token(row.get('patient_name'), 'Patient')}_"
        f"{_document_type_token(row.get('inferred_document_type'), row.get('upload_document_type'))}_"
        f"{_name_token(row.get('patient_uid') or str(row.get('patient_id') or ''), 'PatientID')}"
    )
    return row


def search_patients_for_doctor(
    doctor_id: str | UUID,
    query: str,
    db: Session,
) -> list[PatientProfile]:
    rows = db.execute(
        text(
            """
            SELECT u.user_id, u.email, u.role, u.full_name, u.phone,
                   u.patient_uid, u.date_of_birth, u.sex,
                   u.age, u.gender, u.blood_group, u.allergies,
                   u.chronic_conditions, u.address, u.emergency_contact,
                   u.last_login, u.is_registered, u.is_active, u.created_at, u.updated_at
            FROM users u
            JOIN doctor_patient_assignments a ON a.patient_id = u.user_id
            WHERE a.doctor_id = :doctor_id
              AND a.status = 'active'
              AND u.role = 'patient'
              AND (
                  u.full_name ILIKE :query
                  OR u.patient_uid ILIKE :query
                  OR u.email ILIKE :query
              )
            ORDER BY u.full_name ASC
            LIMIT 20
            """
        ),
        {
            "doctor_id": doctor_id,
            "query": f"%{query}%",
        },
    ).mappings().all()
    return [PatientProfile(**row) for row in rows]


def search_reports_for_patient(
    patient_id: str | UUID,
    date_from: str | None,
    date_to: str | None,
    document_type: str | None,
    db: Session,
    status: str | None = None,
    query: str | None = None,
) -> list[dict]:
    sql = """
        SELECT r.report_id, r.job_id, r.patient_id, r.uploaded_by, r.doctor_id,
               r.file_name, r.file_mime, r.file_size_bytes, r.upload_document_type,
               r.inferred_document_type, r.lifecycle_status, r.released_to_patient,
               r.first_uploaded_at, r.last_edited_at, r.upload_count, r.is_duplicate,
               r.duplicate_of,
               u.full_name AS patient_name,
               u.patient_uid AS patient_uid
        FROM reports r
        LEFT JOIN users u ON u.user_id = r.patient_id
        WHERE r.patient_id = :patient_id
          AND r.released_to_patient = TRUE
    """
    params: dict[str, object] = {"patient_id": patient_id}

    if date_from is not None:
        sql += " AND r.first_uploaded_at::date >= CAST(:date_from AS DATE)"
        params["date_from"] = date_from
    if date_to is not None:
        sql += " AND r.first_uploaded_at::date <= CAST(:date_to AS DATE)"
        params["date_to"] = date_to
    if document_type is not None:
        sql += """
            AND (
                r.inferred_document_type = :document_type
                OR r.upload_document_type = :document_type
            )
        """
        params["document_type"] = document_type
    if status is not None:
        sql += " AND r.lifecycle_status = :status"
        params["status"] = status
    if query is not None:
        sql += """
            AND (
                r.file_name ILIKE :query
                OR r.inferred_document_type ILIKE :query
                OR r.upload_document_type ILIKE :query
                OR u.full_name ILIKE :query
                OR u.patient_uid ILIKE :query
            )
        """
        params["query"] = f"%{query}%"

    sql += " ORDER BY r.first_uploaded_at DESC"
    rows = db.execute(text(sql), params).mappings().all()
    return [_with_display_report_name(dict(row)) for row in rows]
