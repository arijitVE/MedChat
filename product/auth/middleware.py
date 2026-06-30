from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from product.auth.jwt_handler import decode_access_token
from product.schemas.user import UserProfile
from shared.db.session import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserProfile:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    role = payload.get("role")
    email = payload.get("email")

    if not user_id or not role or not email:
        raise HTTPException(status_code=401, detail="Invalid token")

    # DB user
    from shared.db.models.user import User
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=401, detail="User not found")

    from typing import Literal, cast
    return UserProfile(
        user_id=UUID(db_user.user_id),
        email=db_user.email,
        role=cast(Literal["admin", "user"], db_user.role),
        full_name=db_user.full_name,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at,
    )
