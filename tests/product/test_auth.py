"""
Product Layer — Auth Tests

Assertions:
  - signup creates user with correct role
  - login returns valid JWT
  - wrong password returns 401
  - pre-registered patient activates via patient_uid claim (FIX #5)
  - pre-registered patient activates via email fallback (FIX #5)
  - login rate limit returns 429 after 5 attempts (FIX #6)
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from starlette.datastructures import Address
from starlette.requests import Request
from starlette.types import Scope

from product.auth.jwt_handler import decode_access_token
from product.auth.rate_limit import check_login_rate_limit
from product.schemas.auth import LoginRequest, SignupRequest
from product.services.auth_service import login, signup


# ─── helpers ──────────────────────────────────────────────────────────────

def _fake_request(client_ip: str = "127.0.0.1") -> Request:
    """Build a minimal Starlette Request with a client IP."""
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/auth/login",
        "headers": [],
        "client": (client_ip, 0),
    }
    return Request(scope)


# ─── signup ───────────────────────────────────────────────────────────────


class TestSignupCreatesUser:
    """signup creates user with correct role."""

    def test_doctor_signup_returns_doctor_role(self, db):
        body = SignupRequest(
            email="doc@test.local",
            password="strongPass1",
            role="doctor",
            full_name="Dr. Test",
            license_number="LIC-001",
            specialization="General",
            phone="1234567890",
        )
        token_resp = signup(body, db)

        assert token_resp.role == "doctor"
        assert token_resp.user_id is not None

        row = db.execute(
            text("SELECT role, full_name, is_registered FROM users WHERE user_id = :uid"),
            {"uid": token_resp.user_id},
        ).mappings().one()
        assert row["role"] == "doctor"
        assert row["full_name"] == "Dr. Test"
        assert bool(row["is_registered"]) is True

    def test_patient_signup_generates_patient_uid(self, db):
        body = SignupRequest(
            email="pat@test.local",
            password="strongPass1",
            role="patient",
            full_name="Patient One",
        )
        token_resp = signup(body, db)

        assert token_resp.role == "patient"
        row = db.execute(
            text("SELECT patient_uid FROM users WHERE user_id = :uid"),
            {"uid": token_resp.user_id},
        ).mappings().one()
        assert row["patient_uid"] is not None
        assert row["patient_uid"].startswith("PAT-")

    def test_duplicate_email_raises_409(self, db):
        body = SignupRequest(
            email="dup@test.local",
            password="pass1",
            role="doctor",
            full_name="Doc",
            license_number="LIC-002",
            specialization="Cardiology",
            phone="1234567890",
        )
        signup(body, db)

        with pytest.raises(HTTPException) as exc_info:
            signup(body, db)
        assert exc_info.value.status_code == 409


# ─── login ────────────────────────────────────────────────────────────────


class TestLogin:
    """login returns valid JWT / wrong password returns 401."""

    def test_login_returns_valid_jwt(self, db):
        signup(
            SignupRequest(
                email="login@test.local", password="myPass", role="patient", full_name="P"
            ),
            db,
        )
        token_resp = login(LoginRequest(email="login@test.local", password="myPass"), db)

        assert token_resp.access_token
        payload = decode_access_token(token_resp.access_token)
        assert payload["role"] == "patient"
        assert payload["email"] == "login@test.local"

    def test_wrong_password_returns_401(self, db):
        signup(
            SignupRequest(
                email="wp@test.local",
                password="correct",
                role="doctor",
                full_name="D",
                license_number="LIC-003",
                specialization="Pediatrics",
                phone="1234567890",
            ),
            db,
        )
        with pytest.raises(HTTPException) as exc_info:
            login(LoginRequest(email="wp@test.local", password="wrong"), db)
        assert exc_info.value.status_code == 401

    def test_nonexistent_email_returns_401(self, db):
        with pytest.raises(HTTPException) as exc_info:
            login(LoginRequest(email="nobody@test.local", password="x"), db)
        assert exc_info.value.status_code == 401


# ─── FIX #5 — pre-registered patient activation ──────────────────────────


class TestPreRegisteredPatientActivation:
    """Pre-registered patient activates via patient_uid claim or email fallback (FIX #5)."""

    def test_activate_via_patient_uid_claim(self, db, make_user):
        """patient_uid claim flow — FIX #5 Priority 1."""
        pre_reg = make_user(
            role="patient",
            email="pre@test.local",
            password="",
            is_registered=False,
            patient_uid="PAT-CLAIM",
        )

        body = SignupRequest(
            email="pre@test.local",
            password="newPassword",
            role="patient",
            full_name="Activated Patient",
            claim_patient_uid="PAT-CLAIM",
        )
        token_resp = signup(body, db)

        assert token_resp.role == "patient"
        assert token_resp.user_id == pre_reg["user_id"]

        row = db.execute(
            text("SELECT is_registered, full_name FROM users WHERE user_id = :uid"),
            {"uid": pre_reg["user_id"]},
        ).mappings().one()
        assert bool(row["is_registered"]) is True
        assert row["full_name"] == "Activated Patient"

        # Audit entries written
        audits = db.execute(
            text(
                "SELECT action FROM audit_log WHERE entity_id = :eid ORDER BY created_at"
            ),
            {"eid": str(pre_reg["user_id"])},
        ).mappings().all()
        actions = [a["action"] for a in audits]
        assert "SIGNUP" in actions
        assert "ACCOUNT_ACTIVATED" in actions

    def test_activate_via_email_fallback(self, db, make_user):
        """Email match fallback — FIX #5 Priority 2."""
        pre_reg = make_user(
            role="patient",
            email="fallback@test.local",
            password="",
            is_registered=False,
        )

        body = SignupRequest(
            email="fallback@test.local",
            password="newPass",
            role="patient",
            full_name="Fallback Patient",
        )
        token_resp = signup(body, db)

        assert token_resp.role == "patient"
        assert token_resp.user_id == pre_reg["user_id"]

        row = db.execute(
            text("SELECT is_registered FROM users WHERE user_id = :uid"),
            {"uid": pre_reg["user_id"]},
        ).mappings().one()
        assert bool(row["is_registered"]) is True

    def test_claim_wrong_email_raises_400(self, db, make_user):
        """patient_uid claim rejects email mismatch."""
        make_user(
            role="patient",
            email="real@test.local",
            password="",
            is_registered=False,
            patient_uid="PAT-WRONG",
        )

        body = SignupRequest(
            email="imposter@test.local",
            password="pass",
            role="patient",
            full_name="Bad",
            claim_patient_uid="PAT-WRONG",
        )
        with pytest.raises(HTTPException) as exc_info:
            signup(body, db)
        assert exc_info.value.status_code == 400

    def test_claim_nonexistent_uid_raises_404(self, db):
        body = SignupRequest(
            email="x@test.local",
            password="p",
            role="patient",
            full_name="X",
            claim_patient_uid="PAT-NOPE",
        )
        with pytest.raises(HTTPException) as exc_info:
            signup(body, db)
        assert exc_info.value.status_code == 404


# ─── FIX #6 — login rate limit ───────────────────────────────────────────


class TestLoginRateLimit:
    """login rate limit returns 429 after 5 attempts (FIX #6)."""

    def test_rate_limit_429_after_5_attempts(self, db):
        """After 5 calls to check_login_rate_limit from the same IP → 429."""
        req = _fake_request("10.0.0.99")

        # First 5 should pass
        for _ in range(5):
            check_login_rate_limit(req, db)

        # 6th should raise 429
        with pytest.raises(HTTPException) as exc_info:
            check_login_rate_limit(req, db)
        assert exc_info.value.status_code == 429

    def test_different_ips_have_separate_limits(self, db):
        req_a = _fake_request("10.0.0.1")
        req_b = _fake_request("10.0.0.2")

        for _ in range(5):
            check_login_rate_limit(req_a, db)

        # IP B should still work
        check_login_rate_limit(req_b, db)

        # IP A should be blocked
        with pytest.raises(HTTPException) as exc_info:
            check_login_rate_limit(req_a, db)
        assert exc_info.value.status_code == 429
