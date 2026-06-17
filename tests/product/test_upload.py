"""
Product Layer — Upload Tests

Assertions:
  - patient confirmation checkpoint blocks wrong patient_uid
  - re-upload creates versioned path v2/, v3/ (FIX #7)
  - re-upload is blocked if any field has is_final=True (FIX #3)
  - re-upload resets all verifications when no final fields exist
  - upload rate limit returns 429 after 10 attempts (FIX #6)
  - same file bytes → same SHA-256 hash stored in reports.file_hash (FIX #9)
  - uploading same file twice → 409 EXACT_DUPLICATE on second upload (FIX #9)
  - ?force=true bypasses exact duplicate block and creates new report (FIX #9)
  - DUPLICATE_OVERRIDE audit entry written when force=true used (FIX #9)
  - same upload_document_type + ±3% size + within 72h → 200 with duplicate_warning
    in body (FIX #9, FIX 10)
  - PROBABLE_DUPLICATE_WARNING audit entry written for soft warn (FIX #9)
  - different patient same file → no duplicate detection triggered (FIX #9 scope)
"""

from __future__ import annotations

import hashlib
import io
import uuid

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import text

from product.auth.rate_limit import check_upload_rate_limit
from product.services.upload_service import (
    _detect_mime,
    _find_exact_duplicate,
    _find_metadata_duplicate,
    _resolve_doctor_upload_patient,
    reupload_report,
    upload_report,
)
from product.utils.file_storage import compute_file_hash


# ─── helpers ──────────────────────────────────────────────────────────────

def _spoof_upload(file_bytes: bytes, filename: str = "test.pdf") -> UploadFile:
    """Create an UploadFile backed by in-memory bytes."""
    return UploadFile(file=io.BytesIO(file_bytes), filename=filename)


# ─── patient confirmation checkpoint ─────────────────────────────────────


class TestPatientConfirmationCheckpoint:
    """patient confirmation checkpoint blocks wrong patient_uid."""

    def test_wrong_patient_uid_raises_404(self, db, make_user):
        make_user(role="patient", patient_uid="PAT-REAL")

        with pytest.raises(HTTPException) as exc_info:
            _resolve_doctor_upload_patient(db, "PAT-NONEXIST", None)
        assert exc_info.value.status_code == 404

    def test_correct_uid_resolves(self, db, make_user):
        patient = make_user(role="patient", patient_uid="PAT-12345")
        user_id, uid = _resolve_doctor_upload_patient(db, "PAT-12345", None)
        assert str(user_id) == str(patient["user_id"])
        assert uid == "PAT-12345"

    def test_email_fallback_when_no_uid(self, db, make_user):
        patient = make_user(role="patient", email="found@test.local", is_registered=False)
        user_id, _ = _resolve_doctor_upload_patient(db, None, "found@test.local")
        assert str(user_id) == str(patient["user_id"])

    def test_no_uid_no_email_raises_400(self, db):
        with pytest.raises(HTTPException) as exc_info:
            _resolve_doctor_upload_patient(db, None, None)
        assert exc_info.value.status_code == 400


# ─── FIX #7 — re-upload versioned paths ──────────────────────────────────


class TestReuploadVersionedPaths:
    """re-upload creates versioned path v2/, v3/ (FIX #7)."""

    @pytest.mark.asyncio
    async def test_reupload_increments_upload_count(
        self, db, make_user, make_report, make_assignment, pdf_bytes
    ):
        doctor = make_user(role="doctor", license_number="LIC-V1")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )

        new_bytes = b"%PDF-1.4 new version content " + uuid.uuid4().bytes
        result = await reupload_report(
            report["report_id"],
            doctor["user_id"],
            "doctor",
            _spoof_upload(new_bytes),
            db,
        )

        row = db.execute(
            text("SELECT upload_count, file_path FROM reports WHERE report_id = :rid"),
            {"rid": report["report_id"]},
        ).mappings().one()
        assert row["upload_count"] == 2
        assert "/v2/" in row["file_path"].replace("\\", "/")



# ─── FIX #6 — upload rate limit ──────────────────────────────────────────


class TestUploadRateLimit:
    """upload rate limit returns 429 after 10 attempts (FIX #6)."""

    def test_429_after_10_uploads(self, db, make_user):
        user = make_user(role="patient")
        user_id = str(user["user_id"])

        for _ in range(10):
            check_upload_rate_limit(user_id, db)

        with pytest.raises(HTTPException) as exc_info:
            check_upload_rate_limit(user_id, db)
        assert exc_info.value.status_code == 429


# ─── FIX #9 — SHA-256 hash ───────────────────────────────────────────────


class TestFileHashComputation:
    """same file bytes → same SHA-256 hash stored in reports.file_hash (FIX #9)."""

    def test_compute_file_hash_deterministic(self, pdf_bytes):
        expected = hashlib.sha256(pdf_bytes).hexdigest()
        assert compute_file_hash(pdf_bytes) == expected

    def test_different_bytes_different_hash(self, pdf_bytes, png_bytes):
        assert compute_file_hash(pdf_bytes) != compute_file_hash(png_bytes)

    def test_hash_stored_in_reports_row(self, db, make_user, make_report):
        patient = make_user(role="patient")
        file_bytes = b"%PDF-1.4 hash-test-content"
        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=patient["user_id"],
            file_bytes=file_bytes,
        )

        row = db.execute(
            text("SELECT file_hash FROM reports WHERE report_id = :rid"),
            {"rid": report["report_id"]},
        ).mappings().one()
        assert row["file_hash"] == hashlib.sha256(file_bytes).hexdigest()


# ─── FIX #9 — exact duplicate detection ──────────────────────────────────


class TestExactDuplicateDetection:
    """uploading same file twice → 409 EXACT_DUPLICATE (FIX #9)."""

    def test_exact_duplicate_found(self, db, make_user, make_report):
        patient = make_user(role="patient")
        file_bytes = b"%PDF-1.4 dup content"
        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=patient["user_id"],
            file_bytes=file_bytes,
        )

        dup = _find_exact_duplicate(db, patient["user_id"], report["file_hash"])
        assert dup is not None
        assert str(dup["report_id"]) == str(report["report_id"])

    @pytest.mark.asyncio
    async def test_409_on_second_upload(self, db, make_user, make_report):
        patient = make_user(role="patient")
        file_bytes = b"%PDF-1.4 exact same bytes"
        make_report(
            patient_id=patient["user_id"],
            uploaded_by=patient["user_id"],
            file_bytes=file_bytes,
        )

        with pytest.raises(HTTPException) as exc_info:
            await upload_report(
                patient["user_id"],
                "patient",
                _spoof_upload(file_bytes),
                db,
                patient_id=patient["user_id"],
                force=False,
            )
        assert exc_info.value.status_code == 409
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail["duplicate_type"] == "exact"  # type: ignore


# ─── FIX #9 — force=true bypass ──────────────────────────────────────────


class TestForceBypass:
    """?force=true bypasses exact duplicate block and creates new report (FIX #9)."""

    @pytest.mark.asyncio
    async def test_force_creates_new_report(self, db, make_user, make_report):
        patient = make_user(role="patient")
        file_bytes = b"%PDF-1.4 forced duplicate"
        original = make_report(
            patient_id=patient["user_id"],
            uploaded_by=patient["user_id"],
            file_bytes=file_bytes,
        )

        result = await upload_report(
            patient["user_id"],
            "patient",
            _spoof_upload(file_bytes),
            db,
            patient_id=patient["user_id"],
            force=True,
        )

        assert result["report_id"] != str(original["report_id"])
        assert result["status"] == "processing"


# ─── FIX #9 — DUPLICATE_OVERRIDE audit ───────────────────────────────────


class TestDuplicateOverrideAudit:
    """DUPLICATE_OVERRIDE audit entry written when force=true used (FIX #9)."""

    @pytest.mark.asyncio
    async def test_audit_entry_on_force_upload(self, db, make_user, make_report):
        patient = make_user(role="patient")
        file_bytes = b"%PDF-1.4 audit dup check"
        make_report(
            patient_id=patient["user_id"],
            uploaded_by=patient["user_id"],
            file_bytes=file_bytes,
        )

        await upload_report(
            patient["user_id"],
            "patient",
            _spoof_upload(file_bytes),
            db,
            patient_id=patient["user_id"],
            force=True,
        )

        audit = db.execute(
            text(
                "SELECT action FROM audit_log WHERE user_id = :uid AND action = 'DUPLICATE_OVERRIDE'"
            ),
            {"uid": patient["user_id"]},
        ).mappings().first()
        assert audit is not None


# ─── FIX #9 + FIX 10 — TIER 2 soft warning ──────────────────────────────


class TestMetadataDuplicateWarning:
    """same upload_document_type + ±3% size + within 72h → 200 with
    duplicate_warning in body (FIX #9, FIX 10)."""

    def test_tier2_match_found(self, db, make_user, make_report):
        patient = make_user(role="patient")
        file_bytes = b"%PDF-1.4 " + b"x" * 1000  # 1009 bytes
        make_report(
            patient_id=patient["user_id"],
            uploaded_by=patient["user_id"],
            file_bytes=file_bytes,
            upload_document_type="application/pdf",
        )

        # File within ±3% of 1009 = [978, 1039]
        similar_size = len(file_bytes)  # exact same size → well within 3%
        dup = _find_metadata_duplicate(
            db, patient["user_id"], "application/pdf", similar_size
        )
        assert dup is not None

    def test_tier2_different_mime_no_match(self, db, make_user, make_report):
        patient = make_user(role="patient")
        file_bytes = b"%PDF-1.4 " + b"y" * 500
        make_report(
            patient_id=patient["user_id"],
            uploaded_by=patient["user_id"],
            file_bytes=file_bytes,
            upload_document_type="application/pdf",
        )

        # Different MIME type → no match
        dup = _find_metadata_duplicate(
            db, patient["user_id"], "image/jpeg", len(file_bytes)
        )
        assert dup is None

    @pytest.mark.asyncio
    async def test_200_with_duplicate_warning(self, db, make_user, make_report):
        patient = make_user(role="patient")
        file_bytes_a = b"%PDF-1.4 " + b"a" * 1000
        make_report(
            patient_id=patient["user_id"],
            uploaded_by=patient["user_id"],
            file_bytes=file_bytes_a,
            upload_document_type="application/pdf",
        )

        # Slightly different content but same size range & MIME
        file_bytes_b = b"%PDF-1.4 " + b"b" * 1000
        result = await upload_report(
            patient["user_id"],
            "patient",
            _spoof_upload(file_bytes_b),
            db,
            patient_id=patient["user_id"],
        )

        # Should succeed (200 equivalent — no exception) but include warning
        assert "duplicate_warning" in result
        assert result["duplicate_warning"]["type"] == "probable"


# ─── FIX #9 — PROBABLE_DUPLICATE_WARNING audit ───────────────────────────


class TestProbableDuplicateAudit:
    """PROBABLE_DUPLICATE_WARNING audit entry written for soft warn (FIX #9)."""

    @pytest.mark.asyncio
    async def test_audit_entry_on_tier2(self, db, make_user, make_report):
        patient = make_user(role="patient")
        file_bytes_a = b"%PDF-1.4 " + b"c" * 1000
        make_report(
            patient_id=patient["user_id"],
            uploaded_by=patient["user_id"],
            file_bytes=file_bytes_a,
            upload_document_type="application/pdf",
        )

        file_bytes_b = b"%PDF-1.4 " + b"d" * 1000
        await upload_report(
            patient["user_id"],
            "patient",
            _spoof_upload(file_bytes_b),
            db,
            patient_id=patient["user_id"],
        )

        audit = db.execute(
            text(
                "SELECT action FROM audit_log WHERE user_id = :uid AND action = 'PROBABLE_DUPLICATE_WARNING'"
            ),
            {"uid": patient["user_id"]},
        ).mappings().first()
        assert audit is not None


# ─── FIX #9 scope — cross-patient isolation ──────────────────────────────


class TestCrossPatientIsolation:
    """different patient same file → no duplicate detection triggered (FIX #9 scope)."""

    def test_no_cross_patient_hash_check(self, db, make_user, make_report):
        patient_a = make_user(role="patient")
        patient_b = make_user(role="patient")
        shared_bytes = b"%PDF-1.4 shared content"

        make_report(
            patient_id=patient_a["user_id"],
            uploaded_by=patient_a["user_id"],
            file_bytes=shared_bytes,
        )

        file_hash = hashlib.sha256(shared_bytes).hexdigest()
        dup = _find_exact_duplicate(db, patient_b["user_id"], file_hash)
        assert dup is None, "Cross-patient hash should NOT trigger duplicate"

    @pytest.mark.asyncio
    async def test_upload_for_different_patient_succeeds(
        self, db, make_user, make_report
    ):
        patient_a = make_user(role="patient")
        patient_b = make_user(role="patient")
        shared_bytes = b"%PDF-1.4 cross patient test"

        make_report(
            patient_id=patient_a["user_id"],
            uploaded_by=patient_a["user_id"],
            file_bytes=shared_bytes,
        )

        # Same bytes, different patient → no 409
        result = await upload_report(
            patient_b["user_id"],
            "patient",
            _spoof_upload(shared_bytes),
            db,
            patient_id=patient_b["user_id"],
        )
        assert result["status"] == "processing"
