"""
Product Layer — Assignment Tests

Assertions:
  - doctor-initiated assignment creates pending status
  - patient approval makes it active
  - doctor cannot see unassigned patient
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from product.services.assignment_service import (
    approve_assignment,
    create_assignment,
    get_doctor_patients,
    verify_doctor_patient_access,
)


# ─── doctor-initiated assignment ─────────────────────────────────────────


class TestDoctorInitiatedAssignment:
    """doctor-initiated assignment creates pending status."""

    def test_creates_pending_status(self, db, make_user):
        doctor = make_user(role="doctor", license_number="LIC-A1")
        patient = make_user(role="patient")

        result = create_assignment(
            doctor["user_id"],
            patient["user_id"],
            "doctor",
            db,
            initiator_id=doctor["user_id"],
        )

        assert result.status == "pending"
        assert result.doctor_id == doctor["user_id"]
        assert result.patient_id == patient["user_id"]
        assert result.assigned_by == "doctor"

    def test_duplicate_assignment_raises_409(self, db, make_user):
        doctor = make_user(role="doctor", license_number="LIC-B1")
        patient = make_user(role="patient")

        create_assignment(
            doctor["user_id"], patient["user_id"], "doctor", db,
            initiator_id=doctor["user_id"],
        )

        with pytest.raises(HTTPException) as exc_info:
            create_assignment(
                doctor["user_id"], patient["user_id"], "doctor", db,
                initiator_id=doctor["user_id"],
            )
        assert exc_info.value.status_code == 409

    def test_wrong_role_raises_400(self, db, make_user):
        patient_a = make_user(role="patient")
        patient_b = make_user(role="patient")

        with pytest.raises(HTTPException) as exc_info:
            create_assignment(
                patient_a["user_id"],  # not a doctor
                patient_b["user_id"],
                "doctor",
                db,
                initiator_id=patient_a["user_id"],
            )
        assert exc_info.value.status_code == 400


# ─── patient approval ────────────────────────────────────────────────────


class TestPatientApproval:
    """patient approval makes it active."""

    def test_patient_approves_pending_assignment(self, db, make_user):
        doctor = make_user(role="doctor", license_number="LIC-C1")
        patient = make_user(role="patient")

        assignment = create_assignment(
            doctor["user_id"], patient["user_id"], "doctor", db,
            initiator_id=doctor["user_id"],
        )
        assert assignment.status == "pending"

        approved = approve_assignment(
            assignment.assignment_id, patient["user_id"], db
        )

        assert approved.status == "active"
        assert approved.assignment_id == assignment.assignment_id

    def test_doctor_cannot_self_approve(self, db, make_user):
        """Only the pending party (patient for doctor-initiated) can approve."""
        doctor = make_user(role="doctor", license_number="LIC-D1")
        patient = make_user(role="patient")

        assignment = create_assignment(
            doctor["user_id"], patient["user_id"], "doctor", db,
            initiator_id=doctor["user_id"],
        )

        with pytest.raises(HTTPException) as exc_info:
            approve_assignment(assignment.assignment_id, doctor["user_id"], db)
        assert exc_info.value.status_code == 403


# ─── doctor cannot see unassigned patient ─────────────────────────────────


class TestDoctorCannotSeeUnassigned:
    """doctor cannot see unassigned patient."""

    def test_no_active_assignment_returns_empty(self, db, make_user):
        doctor = make_user(role="doctor", license_number="LIC-E1")
        unassigned_patient = make_user(role="patient")

        patients = get_doctor_patients(doctor["user_id"], db)
        patient_ids = [p.user_id for p in patients]
        assert unassigned_patient["user_id"] not in patient_ids

    def test_pending_assignment_not_visible(self, db, make_user):
        """Pending assignments do NOT grant access."""
        doctor = make_user(role="doctor", license_number="LIC-F1")
        patient = make_user(role="patient")

        create_assignment(
            doctor["user_id"], patient["user_id"], "doctor", db,
            initiator_id=doctor["user_id"],
        )
        # Still pending — patient should NOT appear in doctor's list
        patients = get_doctor_patients(doctor["user_id"], db)
        patient_ids = [p.user_id for p in patients]
        assert patient["user_id"] not in patient_ids

    def test_verify_access_returns_false_without_active(self, db, make_user):
        doctor = make_user(role="doctor", license_number="LIC-G1")
        patient = make_user(role="patient")

        assert verify_doctor_patient_access(
            doctor["user_id"], patient["user_id"], db
        ) is False

    def test_verify_access_returns_true_with_active(self, db, make_user):
        doctor = make_user(role="doctor", license_number="LIC-H1")
        patient = make_user(role="patient")

        assignment = create_assignment(
            doctor["user_id"], patient["user_id"], "doctor", db,
            initiator_id=doctor["user_id"],
        )
        approve_assignment(assignment.assignment_id, patient["user_id"], db)

        assert verify_doctor_patient_access(
            doctor["user_id"], patient["user_id"], db
        ) is True
