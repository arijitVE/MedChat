from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from product.auth.middleware import get_current_user
from product.schemas.user import UserProfile
from shared.db.session import get_db


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
def get_me(
    current_user: UserProfile = Depends(get_current_user),
):
    """Return the currently authenticated user's profile."""
    return current_user

