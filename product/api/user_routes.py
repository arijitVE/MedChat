from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from product.auth.middleware import get_current_user
from product.schemas.user import UserProfile
from shared.db.session import get_db


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_me(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.execute(
        text(
            """
            SELECT user_id, email, role, full_name, phone, age, gender,
                   blood_group, allergies, chronic_conditions, address,
                   emergency_contact, patient_uid, date_of_birth, sex,
                   license_number, specialization, is_registered, is_active,
                   created_at, updated_at, last_login,
                   CASE WHEN is_active THEN 'active' ELSE 'inactive' END AS account_status
            FROM users
            WHERE user_id = :user_id
            """
        ),
        {"user_id": current_user.user_id},
    ).mappings().one()
    return dict(row)
