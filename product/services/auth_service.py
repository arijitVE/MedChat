from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from product.auth.jwt_handler import create_access_token, decode_access_token
from product.auth.password import hash_password, verify_password
from product.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from shared.config import get_settings
from shared.db.models.user import User


def _token_response(user_id: UUID | str, role: str, email: str) -> TokenResponse:
    from typing import Literal, cast
    uuid_user_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
    role_lit = cast(Literal["admin", "user"], role)
    return TokenResponse(
        access_token=create_access_token(str(uuid_user_id), role_lit, email),
        user_id=uuid_user_id,
        role=role_lit,
    )


def signup(body: SignupRequest, db: Session) -> TokenResponse:
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid4())
    new_user = User(
        user_id=user_id,
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(new_user)
    db.commit()
    
    return _token_response(user_id, body.role, body.email)


def login(body: LoginRequest, db: Session) -> TokenResponse:
    # 1. Try DB user
    db_user = db.query(User).filter(User.email == body.email).first()
    if db_user:
        if verify_password(body.password, db_user.password_hash):
            return _token_response(db_user.user_id, db_user.role, db_user.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Fallback to hardcoded admin in .env
    settings = get_settings()
    if body.email == settings.ADMIN_USERNAME and body.password == settings.ADMIN_PASSWORD:
        admin_uuid = UUID("00000000-0000-0000-0000-000000000001")
        return _token_response(admin_uuid, "admin", body.email)
    
    raise HTTPException(status_code=401, detail="Invalid credentials")


def refresh_token(token: str, db: Session) -> TokenResponse:
    payload = decode_access_token(token)
    user_id = payload["sub"]
    role = payload["role"]
    email = payload["email"]
    return _token_response(user_id, role, email)


def logout(token: str, db: Session) -> dict:
    return {"status": "logged_out"}
