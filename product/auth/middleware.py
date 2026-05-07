from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import UUID

from product.auth.jwt_handler import decode_access_token
from product.schemas.user import UserProfile
from shared.db.session import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


_current_payload: dict | None = None


def fetch_user_by_id(user_id: str) -> UserProfile:
    now = datetime.now(timezone.utc)
    try:
        parsed_user_id = UUID(user_id)
    except ValueError:
        parsed_user_id = user_id
    payload = _current_payload or {}
    email = payload.get("email") or ""
    role = payload.get("role") or "patient"
    return UserProfile.model_construct(
        user_id=parsed_user_id,
        email=email,
        role=role,
        full_name=email,
        is_registered=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserProfile:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    global _current_payload
    _current_payload = payload
    user = fetch_user_by_id(user_id)
    _current_payload = None
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user
