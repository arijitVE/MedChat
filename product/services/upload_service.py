from __future__ import annotations

from json import dumps
from pathlib import Path
from traceback import format_exc
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException, UploadFile
from pipeline_b.cache.response_cache import invalidate_patient
from pipeline_b.ingestion.ingest import ingest_patient_record
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.services.assignment_service import verify_doctor_patient_access
from product.utils.file_storage import compute_file_hash, save_file
from shared.config import get_settings
from shared.db.session import SessionLocal
from shared.schemas.report import DocumentType


ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
}

VALID_PIPELINE_DOCUMENT_TYPES = {document_type.value for document_type in DocumentType}


def _detect_mime(file_bytes: bytes) -> str:
    if file_bytes.startswith(b"%PDF"):
        return "application/pdf"
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if file_bytes.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    raise HTTPException(status_code=400, detail="Unsupported file type")


def _extension_for_mime(mime: str) -> str:
    return {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/tiff": ".tiff",
    }[mime]


def _pipeline_document_type(inferred_document_type: str | None = None) -> str:
    if inferred_document_type in VALID_PIPELINE_DOCUMENT_TYPES:
        return inferred_document_type
    return DocumentType.unknown.value


def _write_audit(
    db: Session,
    user_id,
    user_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    report_id=None,
    metadata: dict | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO audit_log (
                user_id, user_role, action, entity_type, entity_id, report_id, metadata
            )
            VALUES (
                :user_id, :user_role, :action, :entity_type, :entity_id,
                :report_id, CAST(:metadata AS JSONB)
            )
            """
        ),
        {
            "user_id": user_id,
            "user_role": user_role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "report_id": report_id,
            "metadata": dumps(metadata or {}),
        },
    )


def _send_notification(
    db: Session,
    recipient_id,
    sender_id,
    notif_type: str,
    title: str,
    message: str,
    report_id=None,
) -> None:
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
            "title": title,
            "message": message,
            "report_id": report_id,
        },
    )


def _enforce_file_size(file_bytes: bytes) -> None:
    max_bytes = get_settings().MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail="File exceeds maximum allowed size")


def _insert_file_storage_ref(
    db: Session,
    report_id,
    patient_id,
    file_path: str,
    file_name: str,
    file_mime: str,
    file_size_bytes: int,
    upload_count: int,
    file_hash: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO file_storage_refs (
                report_id, patient_id, file_path, file_name, file_mime,
                file_size_bytes, upload_count, version, file_hash
            )
            VALUES (
                :report_id, :patient_id, :file_path, :file_name, :file_mime,
                :file_size_bytes, :upload_count, :version, :file_hash
            )
            """
        ),
        {
            "report_id": report_id,
            "patient_id": patient_id,
            "file_path": str(Path(file_path).resolve()),
            "file_name": file_name,
            "file_mime": file_mime,
            "file_size_bytes": file_size_bytes,
            "upload_count": upload_count,
            "version": upload_count,
            "file_hash": file_hash,
        },
    )


def _generate_patient_uid(db: Session) -> str:
    count = db.execute(
        text("SELECT COUNT(*) FROM users WHERE role = 'patient'")
    ).scalar_one()
    candidate_number = int(count) + 1
    while True:
        candidate = f"PAT-{candidate_number:05d}"
        exists = db.execute(
            text("SELECT 1 FROM users WHERE patient_uid = :patient_uid"),
            {"patient_uid": candidate},
        ).first()
        if exists is None:
            return candidate
        candidate_number += 1


def _resolve_doctor_upload_patient(
    db: Session,
    patient_uid: str | None,
    patient_email: str | None,
) -> tuple[UUID, str]:
    if patient_uid:
        row = db.execute(
            text(
                """
                SELECT user_id, patient_uid
                FROM users
                WHERE patient_uid = :patient_uid
                  AND role = 'patient'
                """
            ),
            {"patient_uid": patient_uid},
        ).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Patient UID not found")
        return row["user_id"], row["patient_uid"]

    if not patient_email:
        raise HTTPException(status_code=400, detail="patient_uid or patient_email is required")

    row = db.execute(
        text(
            """
            SELECT user_id, patient_uid, is_registered
            FROM users
            WHERE email = :email
              AND role = 'patient'
            """
        ),
        {"email": patient_email},
    ).mappings().first()
    if row is not None:
        if row["is_registered"]:
            raise HTTPException(status_code=409, detail="Email already registered. Use Patient-ID instead.")
        return row["user_id"], row["patient_uid"]

    generated_uid = _generate_patient_uid(db)
    created = db.execute(
        text(
            """
            INSERT INTO users (
                email, password_hash, role, full_name, patient_uid,
                is_registered, is_active
            )
            VALUES (
                :email, '', 'patient', :full_name, :patient_uid,
                FALSE, TRUE
            )
            RETURNING user_id, patient_uid
            """
        ),
        {
            "email": patient_email,
            "full_name": patient_email,
            "patient_uid": generated_uid,
        },
    ).mappings().one()
    return created["user_id"], created["patient_uid"]


def _ensure_doctor_upload_assignment(db: Session, doctor_id, patient_id) -> None:
    db.execute(
        text(
            """
            INSERT INTO doctor_patient_assignments (
                doctor_id, patient_id, assigned_by, status
            )
            VALUES (:doctor_id, :patient_id, 'doctor', 'active')
            ON CONFLICT (doctor_id, patient_id)
            DO UPDATE SET status = 'active', updated_at = NOW()
            """
        ),
        {"doctor_id": doctor_id, "patient_id": patient_id},
    )


def _find_exact_duplicate(
    db: Session,
    patient_id,
    file_hash: str,
    current_report_id=None,
):
    query = """
        SELECT r.report_id, r.first_uploaded_at, r.uploaded_by,
               u.role AS uploaded_by_role
        FROM reports r
        JOIN users u ON u.user_id = r.uploaded_by
        WHERE r.patient_id = :patient_id
          AND r.file_hash = :file_hash
    """
    params = {"patient_id": patient_id, "file_hash": file_hash}
    if current_report_id is not None:
        query += " AND r.report_id != :current_report_id"
        params["current_report_id"] = current_report_id
    query += " ORDER BY r.first_uploaded_at DESC LIMIT 1"
    return db.execute(text(query), params).mappings().first()


def _find_metadata_duplicate(
    db: Session,
    patient_id,
    upload_document_type: str,
    file_size_bytes: int,
    current_report_id=None,
):
    query = """
        SELECT r.report_id, r.first_uploaded_at, r.uploaded_by,
               u.role AS uploaded_by_role
        FROM reports r
        JOIN users u ON u.user_id = r.uploaded_by
        WHERE r.patient_id = :patient_id
          AND r.upload_document_type = :upload_document_type
          AND r.file_size_bytes BETWEEN :low_size AND :high_size
          AND r.first_uploaded_at >= NOW() - INTERVAL '72 hours'
    """
    params = {
        "patient_id": patient_id,
        "upload_document_type": upload_document_type,
        "low_size": int(file_size_bytes * 0.97),
        "high_size": int(file_size_bytes * 1.03),
    }
    if current_report_id is not None:
        query += " AND r.report_id != :current_report_id"
        params["current_report_id"] = current_report_id
    query += " ORDER BY r.first_uploaded_at DESC LIMIT 1"
    return db.execute(text(query), params).mappings().first()


def _duplicate_warning(row) -> dict:
    return {
        "type": "probable",
        "existing_report_id": str(row["report_id"]),
        "existing_uploaded_at": row["first_uploaded_at"].isoformat(),
        "uploaded_by_role": row["uploaded_by_role"],
        "message": "A similar report was uploaded recently. Please verify this is not a duplicate.",
    }


def _raise_exact_duplicate(db: Session, row, file_hash: str, user_id) -> None:
    payload = {
        "duplicate_type": "exact",
        "existing_report_id": str(row["report_id"]),
        "existing_uploaded_at": row["first_uploaded_at"].isoformat(),
        "uploaded_by_role": row["uploaded_by_role"],
        "uploaded_by_user_id": str(row["uploaded_by"]),
        "actions": {
            "use_existing": f"GET /reports/{row['report_id']}",
            "force_upload": "POST /upload?force=true",
        },
        "message": "This exact file has already been uploaded for this patient.",
    }
    _write_audit(
        db,
        user_id,
        row["uploaded_by_role"],
        "EXACT_DUPLICATE_BLOCKED",
        "report",
        str(row["report_id"]),
        row["report_id"],
        {
            "existing_report_id": str(row["report_id"]),
            "file_hash": file_hash,
            "tier": 1,
            "triggered_by": str(user_id),
        },
    )
    raise HTTPException(status_code=409, detail=payload)


def _upsert_document_job(
    db: Session,
    job_id: str,
    patient_id,
    document_type: str,
    file_name: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO document_jobs (
                job_id, patient_id, document_type, file_name, status,
                hitl_required, uploaded_at, upload_source, collection_date
            )
            VALUES (
                :job_id, :patient_id, :document_type, :file_name, 'uploaded',
                FALSE, NOW(), 'system', CURRENT_DATE
            )
            ON CONFLICT (job_id) DO UPDATE
            SET document_type = EXCLUDED.document_type,
                file_name = EXCLUDED.file_name,
                status = EXCLUDED.status,
                uploaded_at = NOW()
            """
        ),
        {
            "job_id": job_id,
            "patient_id": str(patient_id),
            "document_type": document_type,
            "file_name": file_name,
        },
    )


def _mark_pipeline_a_failed(db: Session, job_id: str, traceback_text: str) -> None:
    db.execute(
        text(
            """
            UPDATE document_jobs
            SET status = 'failed',
                error_message = :error_message,
                processed_at = NOW()
            WHERE job_id = :job_id
            """
        ),
        {"job_id": job_id, "error_message": traceback_text},
    )
    db.execute(
        text(
            """
            UPDATE reports
            SET lifecycle_status = 'failed',
                last_edited_at = NOW()
            WHERE job_id = :job_id
            """
        ),
        {"job_id": job_id},
    )


def on_pipeline_a_complete(
    job_id: str,
    patient_id: str,
    output,
    db: Session,
) -> None:
    """Post-Pipeline-A hook — updates report metadata, notifies, re-checks dups.

    Called from ``run_pipeline_a_task`` with the background-thread DB session.
    Never call from a request handler.

    Steps executed (in order):
        1. Update ``reports.inferred_document_type`` from Pipeline A output.
        2. Set ``lifecycle_status`` based on ``output.hitl_required``.
        3. Trigger Qdrant ingestion (Pipeline B).
        4. Send role-appropriate notification (doctor for HITL, patient otherwise).
        5. Re-evaluate TIER 2 duplicate using ``inferred_document_type`` (FIX 13).
        6. Log completion.
    """
    from product.services import notification_service
    from shared.logger import get_logger

    logger = get_logger(__name__)

    # ------------------------------------------------------------------
    # Determine inferred_document_type from output
    # ------------------------------------------------------------------
    inferred_type = "unknown"
    if hasattr(output, "document_type") and output.document_type is not None:
        inferred_type = (
            output.document_type.value
            if hasattr(output.document_type, "value")
            else str(output.document_type)
        )

    hitl_required = bool(getattr(output, "hitl_required", False))
    lifecycle_status = "hitl_required" if hitl_required else "auto_approved"

    # ------------------------------------------------------------------
    # STEP 1 + STEP 2 — Update inferred_document_type & lifecycle_status
    # ------------------------------------------------------------------
    db.execute(
        text(
            """
            UPDATE reports
            SET inferred_document_type = :inferred_document_type,
                lifecycle_status = :lifecycle_status
            WHERE job_id = :job_id
            """
        ),
        {
            "job_id": job_id,
            "inferred_document_type": inferred_type,
            "lifecycle_status": lifecycle_status,
        },
    )

    # Fetch the report row for downstream steps
    report = db.execute(
        text(
            """
            SELECT report_id, patient_id, doctor_id, released_to_patient
            FROM reports
            WHERE job_id = :job_id
            """
        ),
        {"job_id": job_id},
    ).mappings().first()

    if report is None:
        logger.warning("on_pipeline_a_complete_report_missing", job_id=job_id)
        return

    report_id = report["report_id"]
    report_patient_id = str(report["patient_id"])

    # ------------------------------------------------------------------
    # STEP 3 — Trigger Qdrant ingestion (Pipeline B)
    # ------------------------------------------------------------------
    ingest_patient_record(report_patient_id, job_id, db)

    # ------------------------------------------------------------------
    # STEP 4 — Send notification to correct party
    # ------------------------------------------------------------------
    if hitl_required:
        # Notify the assigned doctor (if any)
        doctor_row = db.execute(
            text(
                """
                SELECT doctor_id
                FROM doctor_patient_assignments
                WHERE patient_id = :patient_id
                  AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"patient_id": report["patient_id"]},
        ).mappings().first()
        doctor_id = doctor_row["doctor_id"] if doctor_row else report.get("doctor_id")
        if doctor_id is not None:
            notification_service.create_notification(
                recipient_id=doctor_id,
                sender_id=None,
                notif_type="HITL_REQUIRED",
                title="Verification Required",
                message=f"Report needs manual verification for patient {report_patient_id}",
                report_id=report_id,
                db=db,
            )
    else:
        # Notify patient only if report is already released
        if report["released_to_patient"]:
            notification_service.create_notification(
                recipient_id=report["patient_id"],
                sender_id=None,
                notif_type="REPORT_PROCESSED",
                title="Your report is ready",
                message="Your report has been processed and is available to view.",
                report_id=report_id,
                db=db,
            )

    # Audit entry
    _write_audit(
        db,
        None,
        "system",
        "REPORT_PROCESSED",
        "report",
        str(report_id),
        report_id,
        {
            "job_id": job_id,
            "lifecycle_status": lifecycle_status,
            "inferred_document_type": inferred_type,
        },
    )

    # ------------------------------------------------------------------
    # STEP 5 — Re-evaluate TIER 2 duplicate with inferred type (FIX 13)
    # ------------------------------------------------------------------
    try:
        if inferred_type != "unknown":
            file_size = db.execute(
                text(
                    "SELECT file_size_bytes FROM reports WHERE report_id = :rid"
                ),
                {"rid": report_id},
            ).scalar_one_or_none()
            if file_size is not None:
                tier2_match = _find_metadata_duplicate(
                    db,
                    report["patient_id"],
                    inferred_type,
                    file_size,
                    current_report_id=report_id,
                )
                if tier2_match is not None:
                    db.execute(
                        text(
                            """
                            UPDATE reports
                            SET is_duplicate = TRUE,
                                duplicate_of = :dup_of
                            WHERE report_id = :rid
                              AND is_duplicate = FALSE
                            """
                        ),
                        {
                            "rid": report_id,
                            "dup_of": tier2_match["report_id"],
                        },
                    )
                    _write_audit(
                        db,
                        None,
                        "system",
                        "TIER2_DEFERRED_DUPLICATE",
                        "report",
                        str(report_id),
                        report_id,
                        {
                            "existing_report_id": str(tier2_match["report_id"]),
                            "inferred_document_type": inferred_type,
                            "tier": 2,
                        },
                    )
    except Exception:
        logger.warning(
            "tier2_deferred_duplicate_check_failed",
            job_id=job_id,
            report_id=str(report_id),
            exc_info=True,
        )

    # ------------------------------------------------------------------
    # STEP 6 — Log completion
    # ------------------------------------------------------------------
    logger.info(
        "pipeline_a_complete_hook_done",
        job_id=job_id,
        patient_id=patient_id,
        lifecycle_status=lifecycle_status,
        hitl_required=hitl_required,
        inferred_document_type=inferred_type,
    )


def run_pipeline_a_task(
    job_id: str,
    patient_id: str,
    file_bytes_hex: str,
    document_type: str,
    db_url: str,
    file_name: str = "",
    raise_on_error: bool = False,
) -> None:
    """Runs in background thread after upload response is returned.

    Creates its OWN database session — never reuses the request session.

    Args:
        raise_on_error: When True, re-raise exceptions instead of swallowing
            them.  Use ``True`` in tests so failures are visible.
    """
    import datetime as _dt

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from pipeline_a.orchestrator.process_document import run
    from shared.db.models.document import upsert_job
    from shared.db.models.extraction import upsert_fields
    from shared.logger import get_logger
    from shared.schemas.report import JobStatus

    logger = get_logger(__name__)
    engine = create_engine(db_url)
    _LocalSession = sessionmaker(bind=engine)
    db = _LocalSession()
    document_type = _pipeline_document_type(document_type)
    try:
        # Pre-create document_jobs row with all NOT NULL columns so that
        # Pipeline A's internal upsert_job(status='processing') hits the
        # ON CONFLICT DO UPDATE path instead of a bare INSERT that would
        # fail with "null value in column patient_id".
        upsert_job(
            db,
            job_id,
            patient_id=patient_id,
            document_type=document_type,
            file_name="",
            status=JobStatus.processing.value,
            hitl_required=False,
            uploaded_at=_dt.datetime.now(_dt.timezone.utc),
        )
        db.commit()

        output = run(
            job_id=job_id,
            patient_id=patient_id,
            file_bytes_hex=file_bytes_hex,
            document_type=document_type,
            db=db,
            file_name=file_name,
        )
        upsert_job(
            db,
            output.job_id,
            status=output.job_status.value,
            hitl_required=output.hitl_required,
            hitl_reasons=output.hitl_reasons,
            structured_text_for_embedding=output.structured_text_for_embedding,
            ocr_latency_ms=output.ocr_latency_ms,
            llm_latency_ms=output.llm_latency_ms,
        )
        upsert_fields(db, output.job_id, output.scored_fields, patient_id=output.patient_id)
        db.commit()
        on_pipeline_a_complete(
            job_id=job_id,
            patient_id=patient_id,
            output=output,
            db=db,
        )
        db.commit()
    except Exception as e:
        traceback_text = format_exc()
        db.rollback()
        try:
            _mark_pipeline_a_failed(db, job_id, traceback_text)
            db.commit()
        except Exception as failure_update_error:
            db.rollback()
            logger.error(
                "pipeline_a_failure_persist_failed",
                job_id=job_id,
                error=str(failure_update_error),
                exc_info=True,
            )
        logger.error(
            "pipeline_a_background_task_failed",
            job_id=job_id,
            error=str(e),
            exc_info=True,
        )
        if raise_on_error:
            raise
    finally:
        db.close()
        engine.dispose()


async def upload_report(
    uploaded_by,
    uploader_role: str,
    file: UploadFile,
    db: Session,
    patient_id=None,
    patient_uid: str | None = None,
    patient_email: str | None = None,
    force: bool = False,
    background_tasks: BackgroundTasks | None = None,
) -> dict:
    file_bytes = await file.read()
    _enforce_file_size(file_bytes)
    file_hash = compute_file_hash(file_bytes)
    upload_document_type = _detect_mime(file_bytes)
    if upload_document_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    resolved_patient_uid = None
    if uploader_role == "doctor":
        patient_id, resolved_patient_uid = _resolve_doctor_upload_patient(db, patient_uid, patient_email)
        _ensure_doctor_upload_assignment(db, uploaded_by, patient_id)
    elif patient_id is None:
        patient_id = uploaded_by

    exact_duplicate = _find_exact_duplicate(db, patient_id, file_hash)
    duplicate_of = None
    is_duplicate = False
    if exact_duplicate is not None:
        if not force:
            _raise_exact_duplicate(db, exact_duplicate, file_hash, uploaded_by)
        duplicate_of = exact_duplicate["report_id"]
        is_duplicate = True
        _write_audit(
            db,
            uploaded_by,
            uploader_role,
            "DUPLICATE_OVERRIDE",
            "report",
            str(duplicate_of),
            duplicate_of,
            {
                "existing_report_id": str(duplicate_of),
                "file_hash": file_hash,
                "tier": 1,
                "triggered_by": str(uploaded_by),
                "forced_by": str(uploaded_by),
            },
        )

    metadata_duplicate = None
    metadata_duplicate = _find_metadata_duplicate(
        db,
        patient_id,
        upload_document_type,
        len(file_bytes),
    )
    if metadata_duplicate is not None:
        if duplicate_of is None:
            duplicate_of = metadata_duplicate["report_id"]
            is_duplicate = True
        _write_audit(
            db,
            uploaded_by,
            uploader_role,
            "PROBABLE_DUPLICATE_WARNING",
            "report",
            str(metadata_duplicate["report_id"]),
            metadata_duplicate["report_id"],
            {
                "existing_report_id": str(metadata_duplicate["report_id"]),
                "file_hash": file_hash,
                "tier": 2,
                "triggered_by": str(uploaded_by),
            },
        )

    report_id = uuid4()
    job_id = str(report_id)
    upload_count = 1
    original_name = f"original{_extension_for_mime(upload_document_type)}"
    file_path = save_file(str(patient_id), str(report_id), upload_count, original_name, file_bytes)
    pipeline_document_type = _pipeline_document_type()
    _upsert_document_job(db, job_id, patient_id, pipeline_document_type, file.filename or original_name)

    db.execute(
        text(
            """
            INSERT INTO reports (
                report_id, job_id, patient_id, uploaded_by, doctor_id,
                file_path, file_name, file_mime, file_size_bytes,
                upload_document_type, inferred_document_type, lifecycle_status,
                released_to_patient, upload_count, file_hash, is_duplicate, duplicate_of
            )
            VALUES (
                :report_id, :job_id, :patient_id, :uploaded_by, :doctor_id,
                :file_path, :file_name, :file_mime, :file_size_bytes,
                :upload_document_type, 'unknown', 'uploaded',
                :released_to_patient, :upload_count, :file_hash, :is_duplicate, :duplicate_of
            )
            """
        ),
        {
            "report_id": report_id,
            "job_id": job_id,
            "patient_id": patient_id,
            "uploaded_by": uploaded_by,
            "doctor_id": uploaded_by if uploader_role == "doctor" else None,
            "file_path": file_path,
            "file_name": file.filename or Path(file_path).name,
            "file_mime": upload_document_type,
            "file_size_bytes": len(file_bytes),
            "upload_document_type": upload_document_type,
            "released_to_patient": uploader_role == "patient",
            "upload_count": upload_count,
            "file_hash": file_hash,
            "is_duplicate": is_duplicate,
            "duplicate_of": duplicate_of,
        },
    )
    _insert_file_storage_ref(
        db,
        report_id,
        patient_id,
        file_path,
        file.filename or Path(file_path).name,
        upload_document_type,
        len(file_bytes),
        upload_count,
        file_hash,
    )
    db.execute(
        text("UPDATE reports SET lifecycle_status = 'processing' WHERE report_id = :report_id"),
        {"report_id": report_id},
    )
    _write_audit(
        db,
        uploaded_by,
        uploader_role,
        "UPLOAD",
        "report",
        str(report_id),
        report_id,
        {"file_hash": file_hash},
    )
    if uploader_role == "doctor":
        _send_notification(
            db,
            patient_id,
            uploaded_by,
            "REPORT_UPLOADED",
            "Report uploaded",
            "A doctor uploaded a report for you.",
            report_id,
        )
    db.commit()
    settings = get_settings()
    if background_tasks is not None:
        background_tasks.add_task(
            run_pipeline_a_task,
            job_id=job_id,
            patient_id=str(patient_id),
            file_bytes_hex=file_bytes.hex(),
            document_type=pipeline_document_type,
            db_url=settings.DATABASE_URL,
            file_name=file.filename or original_name,
        )

    response = {
        "report_id": str(report_id),
        "status": "processing",
        "patient_uid": resolved_patient_uid,
    }
    if metadata_duplicate is not None:
        response["duplicate_warning"] = _duplicate_warning(metadata_duplicate)
    return response


async def reupload_report(
    report_id,
    uploaded_by,
    uploader_role: str,
    file: UploadFile,
    db: Session,
    force: bool = False,
    background_tasks: BackgroundTasks | None = None,
) -> dict:
    report = db.execute(
        text(
            """
            SELECT report_id, job_id, patient_id, uploaded_by, doctor_id,
                   upload_count, lifecycle_status, inferred_document_type
            FROM reports
            WHERE report_id = :report_id
            """
        ),
        {"report_id": report_id},
    ).mappings().first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if (
        uploader_role == "doctor"
        and str(report["doctor_id"]) != str(uploaded_by)
        and str(report["uploaded_by"]) != str(uploaded_by)
        and not verify_doctor_patient_access(uploaded_by, report["patient_id"], db)
    ):
        raise HTTPException(status_code=403, detail="Doctor does not have access to this patient")
    if uploader_role == "patient" and str(uploaded_by) != str(report["patient_id"]):
        raise HTTPException(status_code=403, detail="Patient does not own this report")
    if report["lifecycle_status"] == "fully_verified":
        raise HTTPException(status_code=403, detail="Report has finalized fields — cannot re-upload")

    finalized = db.execute(
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
    if finalized is not None:
        raise HTTPException(status_code=403, detail="Report has finalized fields — cannot re-upload")

    file_bytes = await file.read()
    _enforce_file_size(file_bytes)
    file_hash = compute_file_hash(file_bytes)
    upload_document_type = _detect_mime(file_bytes)
    exact_duplicate = _find_exact_duplicate(db, report["patient_id"], file_hash, report_id)
    duplicate_of = None
    is_duplicate = False
    if exact_duplicate is not None:
        if not force:
            _raise_exact_duplicate(db, exact_duplicate, file_hash, uploaded_by)
        duplicate_of = exact_duplicate["report_id"]
        is_duplicate = True
        _write_audit(
            db,
            uploaded_by,
            uploader_role,
            "DUPLICATE_OVERRIDE",
            "report",
            str(duplicate_of),
            duplicate_of,
            {
                "existing_report_id": str(duplicate_of),
                "file_hash": file_hash,
                "tier": 1,
                "triggered_by": str(uploaded_by),
                "forced_by": str(uploaded_by),
            },
        )

    metadata_duplicate = _find_metadata_duplicate(
        db,
        report["patient_id"],
        upload_document_type,
        len(file_bytes),
        report_id,
    )
    if metadata_duplicate is not None:
        if duplicate_of is None:
            duplicate_of = metadata_duplicate["report_id"]
            is_duplicate = True
        _write_audit(
            db,
            uploaded_by,
            uploader_role,
            "PROBABLE_DUPLICATE_WARNING",
            "report",
            str(metadata_duplicate["report_id"]),
            metadata_duplicate["report_id"],
            {
                "existing_report_id": str(metadata_duplicate["report_id"]),
                "file_hash": file_hash,
                "tier": 2,
                "triggered_by": str(uploaded_by),
            },
        )

    new_count = int(report["upload_count"]) + 1
    original_name = f"original{_extension_for_mime(upload_document_type)}"
    file_path = save_file(str(report["patient_id"]), str(report_id), new_count, original_name, file_bytes)
    pipeline_document_type = _pipeline_document_type(report["inferred_document_type"])
    _upsert_document_job(db, report["job_id"], report["patient_id"], pipeline_document_type, file.filename or original_name)
    db.execute(text("DELETE FROM field_verifications WHERE report_id = :report_id"), {"report_id": report_id})
    db.execute(text("DELETE FROM report_fields WHERE job_id = :job_id"), {"job_id": report["job_id"]})
    db.execute(
        text(
            """
            UPDATE reports
            SET lifecycle_status = 'uploaded',
                last_edited_at = NOW(),
                upload_count = :upload_count,
                file_path = :file_path,
                file_name = :file_name,
                file_mime = :file_mime,
                file_size_bytes = :file_size_bytes,
                file_hash = :file_hash,
                upload_document_type = :upload_document_type,
                inferred_document_type = 'unknown',
                is_duplicate = :is_duplicate,
                duplicate_of = :duplicate_of,
                released_to_patient = FALSE
            WHERE report_id = :report_id
            """
        ),
        {
            "report_id": report_id,
            "upload_count": new_count,
            "file_path": file_path,
            "file_name": file.filename or Path(file_path).name,
            "file_mime": upload_document_type,
            "file_size_bytes": len(file_bytes),
            "file_hash": file_hash,
            "upload_document_type": upload_document_type,
            "is_duplicate": is_duplicate,
            "duplicate_of": duplicate_of,
        },
    )
    _insert_file_storage_ref(
        db,
        report_id,
        report["patient_id"],
        file_path,
        file.filename or Path(file_path).name,
        upload_document_type,
        len(file_bytes),
        new_count,
        file_hash,
    )
    db.execute(
        text("UPDATE reports SET lifecycle_status = 'processing' WHERE report_id = :report_id"),
        {"report_id": report_id},
    )
    _write_audit(db, uploaded_by, uploader_role, "RE_UPLOAD", "report", str(report_id), report_id, {"file_hash": file_hash})
    _write_audit(db, uploaded_by, uploader_role, "VERIFICATION_RESET", "report", str(report_id), report_id, {})
    _send_notification(
        db,
        report["patient_id"],
        uploaded_by,
        "RE_UPLOAD_DONE",
        "Report re-uploaded",
        "A report was re-uploaded.",
        report_id,
    )
    db.commit()
    invalidate_patient(str(report["patient_id"]))
    settings = get_settings()
    if background_tasks is not None:
        background_tasks.add_task(
            run_pipeline_a_task,
            job_id=report["job_id"],
            patient_id=str(report["patient_id"]),
            file_bytes_hex=file_bytes.hex(),
            document_type=pipeline_document_type,
            db_url=settings.DATABASE_URL,
            file_name=file.filename or original_name,
        )
    response = {"report_id": str(report_id), "status": "processing"}
    if metadata_duplicate is not None:
        response["duplicate_warning"] = _duplicate_warning(metadata_duplicate)
    return response
