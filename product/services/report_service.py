from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.schemas.report import ReportStatusResponse
from product.services import notification_service, verification_service
from product.services.assignment_service import verify_doctor_patient_access


def _parse_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", ""))
    except ValueError:
        return None


def _parse_reference_range(reference_range: str | None) -> tuple[float | None, float | None]:
    if not reference_range:
        return None, None

    import re

    cleaned = reference_range.replace(",", "")
    match = re.search(r"([\d]+\.?\d*)\s*[-–]\s*([\d]+\.?\d*)", cleaned)
    if not match:
        return None, None
    return float(match.group(1)), float(match.group(2))


def _field_status(value: float | None, ref_low: float | None, ref_high: float | None) -> str:
    if value is None or (ref_low is None and ref_high is None):
        return "unknown"
    if ref_low is not None and value < ref_low:
        return "low"
    if ref_high is not None and value > ref_high:
        return "high"
    return "normal"


def _trend_direction(values: list[float]) -> tuple[str, float | None]:
    if len(values) < 2:
        return "insufficient_data", None
    first = values[0]
    latest = values[-1]
    percent_change = ((latest - first) / first * 100) if first != 0 else None
    if percent_change is None:
        return "insufficient_data", None
    if percent_change > 5:
        return "increasing", percent_change
    if percent_change < -5:
        return "decreasing", percent_change
    return "stable", percent_change


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


def _doctor_can_access_report(doctor_id: str | UUID, report, db: Session) -> bool:
    return (
        str(report["doctor_id"]) == str(doctor_id)
        or str(report["uploaded_by"]) == str(doctor_id)
        or verify_doctor_patient_access(doctor_id, report["patient_id"], db)
    )


def release_report_to_patient(
    report_id: str | UUID,
    doctor_id: str | UUID,
    db: Session,
) -> ReportStatusResponse:
    report = _get_report_row(report_id, db)
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
    if not _doctor_can_access_report(doctor_id, report, db):
        raise HTTPException(status_code=403, detail="Doctor does not have access to this report")
    fields = verification_service.get_field_verification_status(
        str(report_id),
        db,
        requesting_user_role="doctor",
    )
    return {
        "report": _report_response(report),
        "fields": fields,
    }


def search_reports_for_doctor(
    doctor_id: str | UUID,
    db: Session,
    lifecycle_status: str | None = None,
    patient_id: str | UUID | None = None,
    query: str | None = None,
) -> list[dict]:
    sql = """
        SELECT DISTINCT r.report_id, r.job_id, r.patient_id, r.uploaded_by, r.doctor_id,
               r.file_path, r.file_name, r.file_mime, r.file_size_bytes,
               r.upload_document_type, r.inferred_document_type,
               r.lifecycle_status, r.released_to_patient, r.first_uploaded_at,
               r.last_edited_at, r.upload_count, r.file_hash, r.is_duplicate,
               r.duplicate_of
        FROM reports r
        LEFT JOIN doctor_patient_assignments a
          ON a.patient_id = r.patient_id
         AND a.doctor_id = :doctor_id
         AND a.status = 'active'
        WHERE (r.doctor_id = :doctor_id OR a.assignment_id IS NOT NULL)
    """
    params: dict[str, object] = {"doctor_id": doctor_id}
    if lifecycle_status is not None:
        sql += " AND r.lifecycle_status = :lifecycle_status"
        params["lifecycle_status"] = lifecycle_status
    if patient_id is not None:
        sql += " AND r.patient_id = :patient_id"
        params["patient_id"] = patient_id
    if query is not None:
        sql += """
            AND (
                r.file_name ILIKE :query
                OR r.inferred_document_type ILIKE :query
                OR r.upload_document_type ILIKE :query
            )
        """
        params["query"] = f"%{query}%"
    sql += " ORDER BY r.first_uploaded_at DESC"
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]


def get_raw_report_file_for_doctor(
    report_id: str | UUID,
    doctor_id: str | UUID,
    db: Session,
) -> dict:
    report = _get_report_row(report_id, db)
    if not _doctor_can_access_report(doctor_id, report, db):
        raise HTTPException(status_code=403, detail="Doctor does not have access to this report")
    _write_audit(db, doctor_id, "doctor", "VIEW_RAW_REPORT", report_id)
    db.commit()
    return {
        "path": report["file_path"],
        "filename": report["file_name"],
        "media_type": report["file_mime"],
    }


def get_patient_sql_analytics(
    patient_id: str | UUID,
    db: Session,
) -> dict:
    # ANALYTICS: SQL engine only — never LLM-generated numbers.
    # Values are sourced from structured report_fields joined to patient reports.
    rows = db.execute(
        text(
            """
            WITH ranked AS (
                SELECT r.patient_id,
                       rf.job_id,
                       rf.name,
                       rf.value,
                       COALESCE(
                           rf.numeric_value,
                           CASE
                               WHEN REPLACE(TRIM(rf.value), ',', '') ~ '^-?[0-9]+([.][0-9]+)?$'
                               THEN CAST(REPLACE(TRIM(rf.value), ',', '') AS FLOAT)
                               ELSE NULL
                           END
                       ) AS numeric_value,
                       rf.unit,
                       rf.reference_range,
                       rf.collection_date,
                       rf.confidence,
                       rf.status,
                       r.report_id,
                       r.file_name,
                       r.lifecycle_status,
                       r.first_uploaded_at,
                       r.last_edited_at,
                       r.is_duplicate,
                       ROW_NUMBER() OVER (
                           PARTITION BY r.patient_id,
                                        COALESCE(NULLIF(rf.collection_date, ''), r.first_uploaded_at::date::text),
                                        rf.name,
                                        r.report_id
                           ORDER BY r.is_duplicate ASC,
                                    r.last_edited_at DESC NULLS LAST,
                                    r.first_uploaded_at DESC
                       ) AS rn
                FROM report_fields rf
                JOIN reports r ON r.job_id = rf.job_id
                WHERE r.patient_id = :patient_id
                  AND COALESCE(
                      rf.numeric_value,
                      CASE
                          WHEN REPLACE(TRIM(rf.value), ',', '') ~ '^-?[0-9]+([.][0-9]+)?$'
                          THEN CAST(REPLACE(TRIM(rf.value), ',', '') AS FLOAT)
                          ELSE NULL
                      END
                  ) IS NOT NULL
                  AND r.lifecycle_status != 'failed'
            )
            SELECT patient_id, job_id, name, value, numeric_value, unit,
                   reference_range, collection_date, confidence, status,
                   report_id, file_name, lifecycle_status, first_uploaded_at,
                   last_edited_at
            FROM ranked
            WHERE rn = 1
            ORDER BY name ASC,
                     COALESCE(NULLIF(collection_date, ''), first_uploaded_at::date::text) ASC,
                     first_uploaded_at ASC
            """
        ),
        {"patient_id": str(patient_id)},
    ).mappings().all()
    rows_by_field: dict[str, list[dict]] = {}
    for row in rows:
        item = dict(row)
        value = _parse_float(item["numeric_value"])
        ref_low, ref_high = _parse_reference_range(item["reference_range"])
        status = _field_status(value, ref_low, ref_high)
        report_date = item["collection_date"] or (
            item["first_uploaded_at"].date().isoformat() if item["first_uploaded_at"] else ""
        )
        item.update(
            {
                "numeric_value": value,
                "report_date": report_date,
                "reference_min": ref_low,
                "reference_max": ref_high,
                "analytics_status": status,
                "is_abnormal": status in {"low", "high"},
            }
        )
        rows_by_field.setdefault(str(item["name"]), []).append(item)

    trends = []
    abnormal_fields = []
    normal_fields = []
    critical_changes = []
    stable_parameters = []
    insufficient_data = []

    for field_name, field_rows in rows_by_field.items():
        numeric_values = [row["numeric_value"] for row in field_rows if row["numeric_value"] is not None]
        direction, percent_change = _trend_direction(numeric_values)
        latest = field_rows[-1]
        latest_ref_low = latest["reference_min"]
        latest_ref_high = latest["reference_max"]
        latest_status = latest["analytics_status"]
        values = [
            {
                "value": row["numeric_value"],
                "display_value": row["value"],
                "unit": row["unit"],
                "report_date": row["report_date"],
                "reference_min": row["reference_min"],
                "reference_max": row["reference_max"],
                "reference_range": row["reference_range"],
                "status": row["analytics_status"],
                "is_abnormal": row["is_abnormal"],
                "report_id": str(row["report_id"]),
                "report_name": row["file_name"],
                "confidence": row["confidence"],
            }
            for row in field_rows
        ]
        trend = {
            "field_name": field_name,
            "unit": latest["unit"],
            "sample_size": len(field_rows),
            "trend_direction": direction,
            "percent_change": percent_change,
            "latest_value": latest["numeric_value"],
            "latest_display_value": latest["value"],
            "latest_status": latest_status,
            "latest_report_date": latest["report_date"],
            "latest_reference_min": latest_ref_low,
            "latest_reference_max": latest_ref_high,
            "values": values,
        }
        trends.append(trend)

        clinical_field = {
            "field_id": f"{latest['job_id']}_{field_name}",
            "job_id": latest["job_id"],
            "patient_id": str(patient_id),
            "name": field_name,
            "raw_name": field_name,
            "value": latest["value"],
            "numeric_value": latest["numeric_value"],
            "unit": latest["unit"],
            "reference_range": latest["reference_range"],
            "ref_low": latest_ref_low,
            "ref_high": latest_ref_high,
            "confidence": latest["confidence"],
            "status": latest_status,
            "is_abnormal": latest_status in {"low", "high"},
        }
        if clinical_field["is_abnormal"]:
            abnormal_fields.append(clinical_field)
        elif latest_status == "normal":
            normal_fields.append(clinical_field)

        if direction == "stable":
            stable_parameters.append(trend)
        if len(field_rows) < 2:
            insufficient_data.append(trend)
        if latest_status in {"low", "high"} or (
            percent_change is not None and abs(percent_change) >= 20
        ):
            critical_changes.append(trend)

    trends.sort(key=lambda item: (item["sample_size"] < 2, item["field_name"]))
    total_values = sum(trend["sample_size"] for trend in trends)
    trend_ready_count = sum(1 for trend in trends if trend["sample_size"] >= 2)

    return {
        "patient_id": str(patient_id),
        "analytics_engine": "sql",
        "overview": {
            "tracked_fields": len(trends),
            "trend_ready_fields": trend_ready_count,
            "total_values": total_values,
            "abnormal_latest_count": len(abnormal_fields),
            "critical_change_count": len(critical_changes),
            "insufficient_data_count": len(insufficient_data),
        },
        "fields": [
            {
                "field_name": trend["field_name"],
                "sample_size": trend["sample_size"],
                "latest_value": trend["latest_value"],
                "unit": trend["unit"],
                "trend_direction": trend["trend_direction"],
            }
            for trend in trends
        ],
        "trends": trends,
        "critical_changes": critical_changes,
        "stable_parameters": stable_parameters,
        "insufficient_data": insufficient_data,
        "abnormal_fields": abnormal_fields,
        "normal_fields": normal_fields,
        "abnormal_count": len(abnormal_fields),
        "normal_count": len(normal_fields),
        "chart_json": {
            "type": "bar_chart",
            "data": {
                "fields": [trend["field_name"] for trend in trends],
                "values": [trend["latest_value"] for trend in trends],
                "ref_low": [trend["latest_reference_min"] for trend in trends],
                "ref_high": [trend["latest_reference_max"] for trend in trends],
            },
            "meta": {"patient_id": str(patient_id), "date": "aggregate"},
        },
        "ai_insight": "Analytics are calculated from structured report fields stored in the database. Numeric chart values are not LLM-generated.",
        "cached": False,
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
