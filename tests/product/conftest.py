"""
Shared fixtures for product layer tests.

Uses a REAL MySQL database (same as the dev DB configured via DATABASE_URL).
Each test function gets its own transaction that is rolled back after the test,
so no data leaks between tests.

Fixtures provided:
  db          — SQLAlchemy Session (auto-rolled-back after each test)
  make_user   — factory that INSERTs a user row and returns a dict
  make_report — factory that INSERTs a report (+ document_jobs) row
  make_field  — factory that INSERTs a report_fields row
  pdf_bytes   — minimal valid PDF bytes (magic header)
  png_bytes   — minimal valid PNG bytes (magic header)
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from product.auth.password import hash_password
from shared.config import get_settings

# ---------------------------------------------------------------------------
# Engine / Session — bound to the same DB as the running app
# ---------------------------------------------------------------------------

_engine = create_engine(get_settings().DATABASE_URL, echo=False)
_TestSession: sessionmaker[Session] = sessionmaker(
    bind=_engine, autocommit=False, autoflush=False, expire_on_commit=False
)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Yield a session wrapped in a SAVEPOINT.

    After the test the transaction is rolled back so no data persists.
    """
    connection = _engine.connect()
    transaction = connection.begin()
    session = _TestSession(bind=connection)

    # Nested savepoint so service code can call session.commit()
    # without actually committing — the outer txn is still open.
    nested = connection.begin_nested()

    # Re-open savepoint after each commit() inside the test
    from sqlalchemy import event

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# User factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def make_user(db: Session):
    """Factory fixture: insert a user and return its data as a dict."""

    def _make(
        *,
        role: str = "patient",
        email: str | None = None,
        password: str = "testpass123",
        full_name: str = "Test User",
        patient_uid: str | None = None,
        is_registered: bool = True,
        is_active: bool = True,
        license_number: str | None = None,
        specialization: str | None = None,
    ) -> dict:
        user_id = uuid.uuid4()
        email = email or f"{user_id}@test.local"
        if role == "patient" and patient_uid is None:
            patient_uid = f"PAT-{uuid.uuid4().hex[:5].upper()}"
        pw_hash = hash_password(password) if password else ""
        db.execute(
            text(
                """
                INSERT INTO users (
                    user_id, email, password_hash, role, full_name,
                    patient_uid, is_registered, is_active,
                    license_number, specialization
                )
                VALUES (
                    :user_id, :email, :password_hash, :role, :full_name,
                    :patient_uid, :is_registered, :is_active,
                    :license_number, :specialization
                )
                """
            ),
            {
                "user_id": user_id,
                "email": email,
                "password_hash": pw_hash,
                "role": role,
                "full_name": full_name,
                "patient_uid": patient_uid,
                "is_registered": is_registered,
                "is_active": is_active,
                "license_number": license_number,
                "specialization": specialization,
            },
        )
        db.flush()
        return {
            "user_id": user_id,
            "email": email,
            "password": password,
            "password_hash": pw_hash,
            "role": role,
            "full_name": full_name,
            "patient_uid": patient_uid,
            "is_registered": is_registered,
            "is_active": is_active,
        }

    return _make


# ---------------------------------------------------------------------------
# Report + document_jobs factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def make_report(db: Session):
    """Factory fixture: insert a report (and matching document_jobs row)."""

    def _make(
        *,
        patient_id: uuid.UUID,
        uploaded_by: uuid.UUID,
        file_bytes: bytes | None = None,
        upload_document_type: str = "application/pdf",
        lifecycle_status: str = "processing",
        upload_count: int = 1,
        doctor_id: uuid.UUID | None = None,
    ) -> dict:
        report_id = uuid.uuid4()
        job_id = str(report_id)
        file_bytes = file_bytes or b"%PDF-1.4 minimal"
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file_path = f"storage/{patient_id}/{report_id}/v{upload_count}/original.pdf"

        # Insert document_jobs row (Pipeline A table) so JOINs work
        db.execute(
            text(
                """
                INSERT INTO document_jobs (
                    job_id, patient_id, document_type, file_name, status,
                    uploaded_at, upload_source, collection_date
                )
                VALUES (
                    :job_id, :patient_id, :document_type, :file_name, 'uploaded',
                    NOW(), 'system', CURRENT_DATE
                )
                ON DUPLICATE KEY UPDATE job_id = VALUES(job_id)
                """
            ),
            {
                "job_id": job_id,
                "patient_id": str(patient_id),
                "document_type": upload_document_type,
                "file_name": "original.pdf",
            },
        )

        db.execute(
            text(
                """
                INSERT INTO reports (
                    report_id, job_id, patient_id, uploaded_by, doctor_id,
                    file_path, file_name, file_mime, file_size_bytes,
                    upload_document_type, inferred_document_type,
                    lifecycle_status, released_to_patient,
                    upload_count, file_hash, is_duplicate, duplicate_of
                )
                VALUES (
                    :report_id, :job_id, :patient_id, :uploaded_by, :doctor_id,
                    :file_path, 'original.pdf', :file_mime, :file_size_bytes,
                    :upload_document_type, 'unknown',
                    :lifecycle_status, FALSE,
                    :upload_count, :file_hash, FALSE, NULL
                )
                """
            ),
            {
                "report_id": report_id,
                "job_id": job_id,
                "patient_id": patient_id,
                "uploaded_by": uploaded_by,
                "doctor_id": doctor_id,
                "file_path": file_path,
                "file_mime": upload_document_type,
                "file_size_bytes": len(file_bytes),
                "upload_document_type": upload_document_type,
                "lifecycle_status": lifecycle_status,
                "upload_count": upload_count,
                "file_hash": file_hash,
            },
        )
        db.flush()
        return {
            "report_id": report_id,
            "job_id": job_id,
            "patient_id": patient_id,
            "uploaded_by": uploaded_by,
            "file_hash": file_hash,
            "file_bytes": file_bytes,
            "file_path": file_path,
            "upload_count": upload_count,
            "lifecycle_status": lifecycle_status,
        }

    return _make


# ---------------------------------------------------------------------------
# report_fields factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def make_field(db: Session):
    """Insert a report_fields row (Pipeline A output)."""

    def _make(
        *,
        job_id: str,
        patient_id: uuid.UUID,
        field_name: str = "hemoglobin",
        value: str = "14.5",
        confidence: float = 0.95,
        status: str = "auto",
    ) -> dict:
        result = db.execute(
            text(
                """
                INSERT INTO report_fields (
                    job_id, patient_id, name, value, confidence, status
                )
                VALUES (:job_id, :patient_id, :name, :value, :confidence, :status)
                """
            ),
            {
                "job_id": job_id,
                "patient_id": str(patient_id),
                "name": field_name,
                "value": value,
                "confidence": confidence,
                "status": status,
            },
        )
        db.flush()
        field_id = result.lastrowid  # type: ignore
        return {
            "id": field_id,
            "job_id": job_id,
            "patient_id": patient_id,
            "field_name": field_name,
            "value": value,
            "confidence": confidence,
            "status": status,
        }

    return _make


# ---------------------------------------------------------------------------
# Assignment factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def make_assignment(db: Session):
    """Insert a doctor_patient_assignments row."""

    def _make(
        *,
        doctor_id: uuid.UUID,
        patient_id: uuid.UUID,
        status: str = "active",
        assigned_by: str = "doctor",
    ) -> dict:
        assignment_id = uuid.uuid4()
        db.execute(
            text(
                """
                INSERT INTO doctor_patient_assignments (
                    assignment_id, doctor_id, patient_id, assigned_by, status
                )
                VALUES (:assignment_id, :doctor_id, :patient_id, :assigned_by, :status)
                """
            ),
            {
                "assignment_id": assignment_id,
                "doctor_id": doctor_id,
                "patient_id": patient_id,
                "assigned_by": assigned_by,
                "status": status,
            },
        )
        db.flush()
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
        ).mappings().one()
        return dict(row)

    return _make


# ---------------------------------------------------------------------------
# Binary file fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def pdf_bytes() -> bytes:
    """Minimal bytes that pass the PDF magic-bytes check."""
    return b"%PDF-1.4 test file content " + uuid.uuid4().bytes


@pytest.fixture()
def png_bytes() -> bytes:
    """Minimal bytes that pass the PNG magic-bytes check."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64 + uuid.uuid4().bytes


# ---------------------------------------------------------------------------
# Rate limit reset helper
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the in-memory rate limit buckets between tests."""
    from product.auth.rate_limit import _memory_backend
    _memory_backend._attempts.clear()
    yield
    _memory_backend._attempts.clear()
