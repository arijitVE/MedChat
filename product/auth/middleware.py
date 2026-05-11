from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from uuid import UUID

from product.auth.jwt_handler import decode_access_token
from product.schemas.user import UserProfile
from shared.db.session import get_db
from sqlalchemy import text


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def fetch_user_by_id(user_id: str, db: Session) -> UserProfile | None:
    try:
        parsed_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    row = db.execute(
        text(
            """
            SELECT user_id, email, role, full_name, phone, age, gender,
                   blood_group, allergies, chronic_conditions, address,
                   emergency_contact, last_login, is_registered, is_active,
                   created_at, updated_at
            FROM users
            WHERE user_id = :user_id
            """
        ),
        {"user_id": parsed_user_id},
    ).mappings().first()
    if row is None:
        return None
    return UserProfile(**row)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserProfile:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = fetch_user_by_id(user_id, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user
