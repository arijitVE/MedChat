from fastapi import Depends, HTTPException

from product.auth.middleware import get_current_user
from product.schemas.user import UserProfile


def require_role(*roles: str):
    async def guard(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return guard


async def require_approved_doctor(
    current_user: UserProfile = Depends(require_role("doctor")),
) -> UserProfile:
    if current_user.verification_status != "approved":
        raise HTTPException(
            status_code=403,
            detail="Doctor account verification is pending",
        )
    return current_user
