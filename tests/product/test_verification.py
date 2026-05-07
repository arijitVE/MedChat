"""
Product Layer — Verification Tests

Assertions:
  - doctor verification inserts new row, does NOT upsert (FIX #2)
  - patient re-edit inserts additional row — history preserved (FIX #2)
  - latest row reflects current state (FIX #2)
  - doctor verification locks field permanently (is_final=True)
  - locked field raises 403 on further edit
  - all fields doctor_verified → lifecycle_status = 'fully_verified' (FIX #3)
  - is_locked column does NOT exist (FIX #3)
  - HITL field value is None for patient requests (FIX #4)
  - HITL field display_value = "Verification required" for patient (FIX #4)
  - HITL field blocks EDA until doctor_verified (FIX #4)
  - doctor sees HITL field value (FIX #4)
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from product.schemas.user import UserProfile
from product.schemas.verification import FieldVerificationRequest
from product.services.verification_service import (
    get_current_field_verification,
    get_field_verification_history,
    get_field_verification_status,
    verify_field,
)


# ─── helpers ──────────────────────────────────────────────────────────────

def _user_profile(data: dict) -> UserProfile:
    """Build a UserProfile from the make_user factory dict."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return UserProfile(
        user_id=data["user_id"],
        email=data["email"],
        role=data["role"],
        full_name=data["full_name"],
        is_registered=data["is_registered"],
        is_active=data["is_active"],
        created_at=now,
        updated_at=now,
    )


# ─── FIX #2 — insert-only, no upsert ─────────────────────────────────────


class TestInsertOnlyVerification:
    """doctor verification inserts new row, does NOT upsert (FIX #2)."""

    def test_doctor_verify_inserts_new_row(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        doctor = make_user(role="doctor", license_number="LIC-VER1")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
        )

        body = FieldVerificationRequest(verification_type="approved")
        verify_field(
            str(report["report_id"]),
            "hemoglobin",
            body,
            _user_profile(doctor),
            db,
        )

        count = db.execute(
            text(
                """
                SELECT COUNT(*) FROM field_verifications
                WHERE report_id = :rid AND field_name = 'hemoglobin'
                """
            ),
            {"rid": report["report_id"]},
        ).scalar_one()
        assert count == 1  # exactly one row inserted


class TestPatientReEditInsertsAdditionalRow:
    """patient re-edit inserts additional row — history preserved (FIX #2)."""

    def test_two_patient_verifications_produce_two_rows(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        doctor = make_user(role="doctor", license_number="LIC-VER2")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
        )

        # Patient verifies once
        body1 = FieldVerificationRequest(verification_type="approved")
        verify_field(
            str(report["report_id"]),
            "hemoglobin",
            body1,
            _user_profile(patient),
            db,
        )

        # Patient edits the field
        body2 = FieldVerificationRequest(
            verification_type="edited",
            edited_value="14.8",
            edit_reason="Corrected after re-check",
        )
        verify_field(
            str(report["report_id"]),
            "hemoglobin",
            body2,
            _user_profile(patient),
            db,
        )

        count = db.execute(
            text(
                """
                SELECT COUNT(*) FROM field_verifications
                WHERE report_id = :rid AND field_name = 'hemoglobin'
                """
            ),
            {"rid": report["report_id"]},
        ).scalar_one()
        assert count == 2  # two separate rows, history preserved


class TestLatestRowReflectsCurrentState:
    """latest row reflects current state (FIX #2)."""

    def test_get_current_returns_latest(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        doctor = make_user(role="doctor", license_number="LIC-VER3")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
        )

        # Patient verifies
        verify_field(
            str(report["report_id"]),
            "hemoglobin",
            FieldVerificationRequest(verification_type="approved"),
            _user_profile(patient),
            db,
        )

        # Patient edits
        verify_field(
            str(report["report_id"]),
            "hemoglobin",
            FieldVerificationRequest(
                verification_type="edited",
                edited_value="15.0",
                edit_reason="Updated",
            ),
            _user_profile(patient),
            db,
        )

        current = get_current_field_verification(
            str(report["report_id"]), "hemoglobin", db
        )
        assert current is not None
        assert current["verification_type"] == "edited"
        assert current["edited_value"] == "15.0"

    def test_history_returns_all_rows_in_order(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        doctor = make_user(role="doctor", license_number="LIC-VER3b")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="wbc",
            value="7000",
        )

        # Two verifications
        verify_field(
            str(report["report_id"]),
            "wbc",
            FieldVerificationRequest(verification_type="approved"),
            _user_profile(patient),
            db,
        )
        verify_field(
            str(report["report_id"]),
            "wbc",
            FieldVerificationRequest(
                verification_type="edited",
                edited_value="7200",
                edit_reason="Corrected",
            ),
            _user_profile(patient),
            db,
        )

        history = get_field_verification_history(
            str(report["report_id"]), "wbc", db
        )
        assert len(history) == 2
        assert history[0].verification_type == "approved"
        assert history[1].verification_type == "edited"


# ─── doctor verification locks field ─────────────────────────────────────


class TestDoctorVerificationLocksField:
    """doctor verification locks field permanently (is_final=True)."""

    def test_doctor_sets_is_final_true(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        doctor = make_user(role="doctor", license_number="LIC-LOCK1")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
        )

        result = verify_field(
            str(report["report_id"]),
            "hemoglobin",
            FieldVerificationRequest(verification_type="approved"),
            _user_profile(doctor),
            db,
        )
        assert result.is_final is True


class TestLockedFieldRaises403:
    """locked field raises 403 on further edit."""

    def test_patient_edit_after_doctor_lock_raises_403(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        doctor = make_user(role="doctor", license_number="LIC-LOCK2")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
        )

        # Doctor locks the field
        verify_field(
            str(report["report_id"]),
            "hemoglobin",
            FieldVerificationRequest(verification_type="approved"),
            _user_profile(doctor),
            db,
        )

        # Patient tries to edit → 403
        with pytest.raises(HTTPException) as exc_info:
            verify_field(
                str(report["report_id"]),
                "hemoglobin",
                FieldVerificationRequest(
                    verification_type="edited",
                    edited_value="99.0",
                    edit_reason="Attempt",
                ),
                _user_profile(patient),
                db,
            )
        assert exc_info.value.status_code == 403
        assert "locked" in exc_info.value.detail.lower()

    def test_doctor_second_verification_also_raises_403(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        doctor = make_user(role="doctor", license_number="LIC-LOCK3")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
        )

        # Doctor locks
        verify_field(
            str(report["report_id"]),
            "hemoglobin",
            FieldVerificationRequest(verification_type="approved"),
            _user_profile(doctor),
            db,
        )

        # Doctor tries again → 403
        with pytest.raises(HTTPException) as exc_info:
            verify_field(
                str(report["report_id"]),
                "hemoglobin",
                FieldVerificationRequest(verification_type="approved"),
                _user_profile(doctor),
                db,
            )
        assert exc_info.value.status_code == 403


# ─── FIX #3 — fully_verified lifecycle ────────────────────────────────────


class TestFullyVerified:
    """all fields doctor_verified → lifecycle_status = 'fully_verified' (FIX #3)."""

    def test_all_fields_verified_sets_fully_verified(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        doctor = make_user(role="doctor", license_number="LIC-FV1")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        # Two fields
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="wbc",
            value="7000",
        )

        # Doctor verifies both
        for fname in ("hemoglobin", "wbc"):
            verify_field(
                str(report["report_id"]),
                fname,
                FieldVerificationRequest(verification_type="approved"),
                _user_profile(doctor),
                db,
            )

        row = db.execute(
            text(
                "SELECT lifecycle_status FROM reports WHERE report_id = :rid"
            ),
            {"rid": report["report_id"]},
        ).mappings().one()
        assert row["lifecycle_status"] == "fully_verified"

    def test_partial_verification_not_fully_verified(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        doctor = make_user(role="doctor", license_number="LIC-FV2")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="wbc",
            value="7000",
        )

        # Only verify one field
        verify_field(
            str(report["report_id"]),
            "hemoglobin",
            FieldVerificationRequest(verification_type="approved"),
            _user_profile(doctor),
            db,
        )

        row = db.execute(
            text(
                "SELECT lifecycle_status FROM reports WHERE report_id = :rid"
            ),
            {"rid": report["report_id"]},
        ).mappings().one()
        assert row["lifecycle_status"] != "fully_verified"


class TestIsLockedColumnDoesNotExist:
    """is_locked column does NOT exist (FIX #3)."""

    def test_reports_table_has_no_is_locked(self, db):
        cols = db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'reports'
                  AND column_name = 'is_locked'
                """
            )
        ).fetchall()
        assert len(cols) == 0, "is_locked column must NOT exist on reports table"


# ─── FIX #4 — HITL field visibility ──────────────────────────────────────


class TestHITLFieldVisibility:
    """HITL field handling for patient vs doctor views (FIX #4)."""

    def test_hitl_value_none_for_patient(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        """HITL field value is None for patient requests (FIX #4)."""
        doctor = make_user(role="doctor", license_number="LIC-HITL1")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
            status="hitl",
        )

        statuses = get_field_verification_status(
            str(report["report_id"]), db, requesting_user_role="patient"
        )
        assert len(statuses) == 1
        assert statuses[0].value is None

    def test_hitl_display_value_verification_required(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        """HITL field display_value = 'Verification required' for patient (FIX #4)."""
        doctor = make_user(role="doctor", license_number="LIC-HITL2")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
            status="hitl",
        )

        statuses = get_field_verification_status(
            str(report["report_id"]), db, requesting_user_role="patient"
        )
        assert statuses[0].display_value == "Verification required"

    def test_hitl_blocks_eda_until_doctor_verified(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        """HITL field blocks EDA until doctor_verified (FIX #4)."""
        doctor = make_user(role="doctor", license_number="LIC-HITL3")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
            status="hitl",
        )

        # Before doctor verification
        statuses = get_field_verification_status(
            str(report["report_id"]), db, requesting_user_role="patient"
        )
        assert statuses[0].eda_available is False

        # Doctor verifies
        verify_field(
            str(report["report_id"]),
            "hemoglobin",
            FieldVerificationRequest(verification_type="approved"),
            _user_profile(doctor),
            db,
        )

        # After doctor verification
        statuses_after = get_field_verification_status(
            str(report["report_id"]), db, requesting_user_role="patient"
        )
        assert statuses_after[0].eda_available is True

    def test_doctor_sees_hitl_value(
        self, db, make_user, make_report, make_field, make_assignment
    ):
        """doctor sees HITL field value (FIX #4)."""
        doctor = make_user(role="doctor", license_number="LIC-HITL4")
        patient = make_user(role="patient")
        make_assignment(doctor_id=doctor["user_id"], patient_id=patient["user_id"])

        report = make_report(
            patient_id=patient["user_id"],
            uploaded_by=doctor["user_id"],
            doctor_id=doctor["user_id"],
        )
        make_field(
            job_id=report["job_id"],
            patient_id=patient["user_id"],
            field_name="hemoglobin",
            value="14.5",
            status="hitl",
        )

        statuses = get_field_verification_status(
            str(report["report_id"]), db, requesting_user_role="doctor"
        )
        assert len(statuses) == 1
        assert statuses[0].value == "14.5"
        assert statuses[0].display_value == "14.5"
        assert statuses[0].is_value_hidden is False
