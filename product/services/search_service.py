from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from product.schemas.user import PatientProfile


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
        SELECT report_id, job_id, patient_id, uploaded_by, doctor_id,
               file_name, file_mime, file_size_bytes, upload_document_type,
               inferred_document_type, lifecycle_status, released_to_patient,
               first_uploaded_at, last_edited_at, upload_count, is_duplicate,
               duplicate_of
        FROM reports
        WHERE patient_id = :patient_id
          AND released_to_patient = TRUE
    """
    params: dict[str, object] = {"patient_id": patient_id}

    if date_from is not None:
        sql += " AND first_uploaded_at::date >= CAST(:date_from AS DATE)"
        params["date_from"] = date_from
    if date_to is not None:
        sql += " AND first_uploaded_at::date <= CAST(:date_to AS DATE)"
        params["date_to"] = date_to
    if document_type is not None:
        sql += """
            AND (
                inferred_document_type = :document_type
                OR upload_document_type = :document_type
            )
        """
        params["document_type"] = document_type
    if status is not None:
        sql += " AND lifecycle_status = :status"
        params["status"] = status
    if query is not None:
        sql += """
            AND (
                file_name ILIKE :query
                OR inferred_document_type ILIKE :query
                OR upload_document_type ILIKE :query
            )
        """
        params["query"] = f"%{query}%"

    sql += " ORDER BY first_uploaded_at DESC"
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]
