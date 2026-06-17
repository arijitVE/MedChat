from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.auth.jwt_handler import create_access_token, decode_access_token
from product.auth.password import hash_password, verify_password
from product.schemas.auth import LoginRequest, SignupRequest, TokenResponse


def _write_audit(
    db: Session,
    user_id: UUID | str | None,
    user_role: str | None,
    action: str,
    entity_type: str = "user",
    entity_id: str | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO audit_log (user_id, user_role, action, entity_type, entity_id)
            VALUES (:user_id, :user_role, :action, :entity_type, :entity_id)
            """
        ),
        {
            "user_id": user_id,
            "user_role": user_role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
        },
    )


def _token_response(user_id: UUID | str, role: str, email: str) -> TokenResponse:
    from typing import Literal, cast
    uuid_user_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
    role_lit = cast(Literal["doctor", "patient", "admin"], role)
    return TokenResponse(
        access_token=create_access_token(str(uuid_user_id), role_lit, email),
        user_id=uuid_user_id,
        role=role_lit,
    )


def _safe_user_id(value: str) -> UUID | str:
    try:
        return UUID(value)
    except ValueError:
        return value


def _get_user_by_email(db: Session, email: str):
    return db.execute(
        text(
            """
            SELECT user_id, email, password_hash, role, is_registered, is_active
            FROM users
            WHERE email = :email
            """
        ),
        {"email": email},
    ).mappings().first()


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


def _phone_value(body: SignupRequest) -> str | None:
    return body.phone_number or body.phone


def _gender_value(body: SignupRequest) -> str | None:
    return body.gender or body.sex


def _activate_existing_patient(db: Session, user_id: UUID, body: SignupRequest) -> TokenResponse:
    password_hash = hash_password(body.password)
    db.execute(
        text(
            """
            UPDATE users
            SET email = :email,
                password_hash = :password_hash,
                full_name = :full_name,
                phone = :phone,
                age = :age,
                gender = :gender,
                blood_group = :blood_group,
                allergies = :allergies,
                chronic_conditions = :chronic_conditions,
                address = :address,
                emergency_contact = :emergency_contact,
                date_of_birth = :date_of_birth,
                sex = :sex,
                is_registered = TRUE,
                is_active = TRUE,
                updated_at = NOW()
            WHERE user_id = :user_id
            """
        ),
        {
            "user_id": user_id,
            "email": body.email,
            "password_hash": password_hash,
            "full_name": body.full_name,
            "phone": _phone_value(body),
            "age": body.age,
            "gender": _gender_value(body),
            "blood_group": body.blood_group,
            "allergies": body.allergies,
            "chronic_conditions": body.chronic_conditions,
            "address": body.address,
            "emergency_contact": body.emergency_contact,
            "date_of_birth": body.date_of_birth,
            "sex": _gender_value(body),
        },
    )
    _write_audit(db, user_id, "patient", "SIGNUP", entity_id=str(user_id))
    _write_audit(db, user_id, "patient", "ACCOUNT_ACTIVATED", entity_id=str(user_id))
    db.commit()
    return _token_response(user_id, "patient", body.email)


def signup(body: SignupRequest, db: Session) -> TokenResponse:
    if body.role == "doctor":
        if not body.license_number:
            raise HTTPException(status_code=400, detail="License number is required")
        if not body.specialization:
            raise HTTPException(status_code=400, detail="Specialization is required")
        if not _phone_value(body):
            raise HTTPException(status_code=400, detail="Phone number is required")

    if body.claim_patient_uid:
        row = db.execute(
            text(
                """
                SELECT user_id, email, is_registered
                FROM users
                WHERE patient_uid = :patient_uid
                """
            ),
            {"patient_uid": body.claim_patient_uid},
        ).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Patient UID not found")
        if row["email"] is not None and row["email"] != body.email:
            raise HTTPException(status_code=400, detail="Patient UID email mismatch")
        if row["is_registered"]:
            raise HTTPException(status_code=409, detail="Patient already registered")
        return _activate_existing_patient(db, row["user_id"], body)

    existing = _get_user_by_email(db, body.email)
    if existing is not None:
        if existing["role"] == "patient" and not existing["is_registered"]:
            return _activate_existing_patient(db, existing["user_id"], body)
        raise HTTPException(status_code=409, detail="Email already registered")

    patient_uid = _generate_patient_uid(db) if body.role == "patient" else None
    verification_status = "pending_verification" if body.role == "doctor" else "approved"
    user_id = str(uuid4())
    db.execute(
        text(
            """
            INSERT INTO users (
                user_id, email, password_hash, role, full_name, phone, license_number,
                specialization, hospital_name, years_of_experience, department,
                profile_photo, verification_status,
                patient_uid, age, gender, date_of_birth, sex,
                blood_group, allergies, chronic_conditions, address, emergency_contact,
                is_registered, is_active
            )
            VALUES (
                :user_id, :email, :password_hash, :role, :full_name, :phone, :license_number,
                :specialization, :hospital_name, :years_of_experience, :department,
                :profile_photo, :verification_status,
                :patient_uid, :age, :gender, :date_of_birth, :sex,
                :blood_group, :allergies, :chronic_conditions, :address, :emergency_contact,
                TRUE, TRUE
            )
            """
        ),
        {
            "user_id": user_id,
            "email": body.email,
            "password_hash": hash_password(body.password),
            "role": body.role,
            "full_name": body.full_name,
            "phone": _phone_value(body),
            "license_number": body.license_number,
            "specialization": body.specialization,
            "hospital_name": body.hospital_name,
            "years_of_experience": body.years_of_experience,
            "department": body.department,
            "profile_photo": body.profile_photo,
            "verification_status": verification_status,
            "patient_uid": patient_uid,
            "age": body.age,
            "gender": _gender_value(body),
            "date_of_birth": body.date_of_birth,
            "sex": _gender_value(body),
            "blood_group": body.blood_group,
            "allergies": body.allergies,
            "chronic_conditions": body.chronic_conditions,
            "address": body.address,
            "emergency_contact": body.emergency_contact,
        },
    )
    _write_audit(db, user_id, body.role, "SIGNUP", entity_id=str(user_id))
    db.commit()
    return _token_response(user_id, body.role, body.email)


def login(body: LoginRequest, db: Session) -> TokenResponse:
    row = _get_user_by_email(db, body.email)
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Inactive user")

    db.execute(
        text("UPDATE users SET last_login = NOW(), updated_at = NOW() WHERE user_id = :user_id"),
        {"user_id": row["user_id"]},
    )
    _write_audit(db, row["user_id"], row["role"], "LOGIN", entity_id=str(row["user_id"]))
    db.commit()
    return _token_response(row["user_id"], row["role"], row["email"])


def refresh_token(token: str, db: Session) -> TokenResponse:
    payload = decode_access_token(token)
    user_id = _safe_user_id(payload["sub"])
    role = payload["role"]
    email = payload["email"]
    _write_audit(db, user_id, role, "REFRESH", entity_id=str(user_id))
    db.commit()
    return _token_response(user_id, role, email)


def logout(token: str, db: Session) -> dict:
    payload = decode_access_token(token)
    user_id = _safe_user_id(payload["sub"])
    _write_audit(db, user_id, payload.get("role"), "LOGOUT", entity_id=str(user_id))
    db.commit()
    return {"status": "logged_out"}
