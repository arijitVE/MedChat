from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from product.auth.rate_limit import check_login_rate_limit
from product.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from product.services import auth_service
from shared.db.session import get_db


router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/signup", response_model=TokenResponse)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    return auth_service.signup(body, db)


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    check_login_rate_limit(request, db)
    return auth_service.login(body, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    return auth_service.refresh_token(token, db)


@router.post("/logout")
def logout(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    return auth_service.logout(token, db)

