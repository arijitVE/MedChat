"""
Product Layer — Admin Tests

Assertions:
  - admin can reset any user's password
  - admin assignment is immediately active
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from product.auth.password import verify_password
from product.services.admin_service import (
    create_admin_assignment,
    reset_user_password,
)


# ─── admin password reset ────────────────────────────────────────────────


class TestAdminPasswordReset:
    """admin can reset any user's password."""

    def test_reset_doctor_password(self, db, make_user):
        admin = make_user(role="admin", email="admin@test.local")
        doctor = make_user(
            role="doctor",
            email="doc-reset@test.local",
            password="oldPass",
            license_number="LIC-ADMIN1",
        )

        reset_user_password(doctor["user_id"], "newPass123", admin["user_id"], db)

        row = db.execute(
            text("SELECT password_hash FROM users WHERE user_id = :uid"),
            {"uid": doctor["user_id"]},
        ).mappings().one()
        assert verify_password("newPass123", row["password_hash"]) is True
        assert verify_password("oldPass", row["password_hash"]) is False

    def test_reset_patient_password(self, db, make_user):
        admin = make_user(role="admin", email="admin2@test.local")
        patient = make_user(
            role="patient",
            email="pat-reset@test.local",
            password="oldPatPass",
        )

        reset_user_password(patient["user_id"], "secureNew1", admin["user_id"], db)

        row = db.execute(
            text("SELECT password_hash FROM users WHERE user_id = :uid"),
            {"uid": patient["user_id"]},
        ).mappings().one()
        assert verify_password("secureNew1", row["password_hash"]) is True

    def test_audit_log_written_on_reset(self, db, make_user):
        admin = make_user(role="admin", email="admin3@test.local")
        doctor = make_user(
            role="doctor",
            email="doc-audit@test.local",
            license_number="LIC-ADMIN2",
        )

        reset_user_password(doctor["user_id"], "auditPass", admin["user_id"], db)

        audit = db.execute(
            text(
                """
                SELECT action, entity_id
                FROM audit_log
                WHERE user_id = :admin_id
                  AND action = 'PASSWORD_RESET'
                """
            ),
            {"admin_id": admin["user_id"]},
        ).mappings().first()
        assert audit is not None
        assert audit["entity_id"] == str(doctor["user_id"])

    def test_notification_sent_to_user(self, db, make_user):
        admin = make_user(role="admin", email="admin4@test.local")
        patient = make_user(
            role="patient",
            email="pat-notif@test.local",
        )

        reset_user_password(patient["user_id"], "notifPass", admin["user_id"], db)

        notif = db.execute(
            text(
                """
                SELECT type, title
                FROM notifications
                WHERE recipient_id = :uid
                  AND type = 'PASSWORD_RESET'
                """
            ),
            {"uid": patient["user_id"]},
        ).mappings().first()
        assert notif is not None
        assert notif["type"] == "PASSWORD_RESET"


# ─── admin assignment ────────────────────────────────────────────────────


class TestAdminAssignment:
    """admin assignment is immediately active."""

    def test_admin_assignment_creates_active_status(self, db, make_user):
        admin = make_user(role="admin", email="admin5@test.local")
        doctor = make_user(
            role="doctor",
            email="doc-assign@test.local",
            license_number="LIC-ADMIN3",
        )
        patient = make_user(
            role="patient",
            email="pat-assign@test.local",
        )

        result = create_admin_assignment(
            doctor["user_id"],
            patient["user_id"],
            admin["user_id"],
            db,
        )

        assert result.status == "active"
        assert result.assigned_by == "admin"
        assert result.doctor_id == doctor["user_id"]
        assert result.patient_id == patient["user_id"]

    def test_admin_assignment_no_pending_state(self, db, make_user):
        """Admin assignments skip the pending state entirely."""
        admin = make_user(role="admin", email="admin6@test.local")
        doctor = make_user(
            role="doctor",
            email="doc-skip@test.local",
            license_number="LIC-ADMIN4",
        )
        patient = make_user(
            role="patient",
            email="pat-skip@test.local",
        )

        result = create_admin_assignment(
            doctor["user_id"],
            patient["user_id"],
            admin["user_id"],
            db,
        )

        # Verify in DB directly
        row = db.execute(
            text(
                """
                SELECT status
                FROM doctor_patient_assignments
                WHERE assignment_id = :aid
                """
            ),
            {"aid": result.assignment_id},
        ).mappings().one()
        assert row["status"] == "active"

    def test_admin_assignment_writes_audit(self, db, make_user):
        admin = make_user(role="admin", email="admin7@test.local")
        doctor = make_user(
            role="doctor",
            email="doc-aaud@test.local",
            license_number="LIC-ADMIN5",
        )
        patient = make_user(role="patient", email="pat-aaud@test.local")

        create_admin_assignment(
            doctor["user_id"],
            patient["user_id"],
            admin["user_id"],
            db,
        )

        audit = db.execute(
            text(
                """
                SELECT action FROM audit_log
                WHERE user_id = :admin_id AND action = 'ASSIGN_DOCTOR'
                """
            ),
            {"admin_id": admin["user_id"]},
        ).mappings().first()
        assert audit is not None
