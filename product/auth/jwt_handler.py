from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from shared.config import get_settings


TOKEN_EXPIRY_MINUTES = 60 * 24
REFRESH_EXPIRY_DAYS = 7


def create_access_token(user_id: str, role: str, email: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_EXPIRY_MINUTES or TOKEN_EXPIRY_MINUTES
    )
    payload = {
        "sub": user_id,
        "role": role,
        "email": email,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
