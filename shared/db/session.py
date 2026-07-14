# shared/db/session.py
# PostgreSQL Database Session Factory + FastAPI Dependency

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.config import get_settings
from shared.db.base import Base

# ============================================================================
# Settings
# ============================================================================

settings = get_settings()

# ============================================================================
# PostgreSQL Engine
# ============================================================================

_engine = create_engine(
    settings.DATABASE_URL,           # Example:
                                     # postgresql+psycopg://user:password@host:5432/database
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    echo=False,
    future=True,
)

# ============================================================================
# Session Factory
# ============================================================================

SessionLocal = sessionmaker(
    bind=_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)

# ============================================================================
# FastAPI Dependency
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a PostgreSQL database session.

    Example:

        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            ...

    The session commits automatically if no exception occurs.
    """
    db = SessionLocal()

    try:
        yield db
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ============================================================================
# Database Initialization
# ============================================================================

def init_db() -> None:
    """
    Creates all tables (development only) and seeds the default admin user
    if one does not already exist.

    NOTE:
    In production, use Alembic migrations instead of Base.metadata.create_all().
    """

    Base.metadata.create_all(bind=_engine)

    try:
        db = SessionLocal()

        from uuid import uuid4

        from product.auth.password import hash_password
        from shared.db.models.user import User

        admin_user = (
            db.query(User)
            .filter(User.role == "admin")
            .first()
        )

        if admin_user is None:

            admin_email = (
                settings.ADMIN_USERNAME
                if "@" in settings.ADMIN_USERNAME
                else "admin@documed.ai"
            )

            new_admin = User(
                user_id=str(uuid4()),
                email=admin_email,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                full_name="System Super Administrator",
                role="admin",
            )

            db.add(new_admin)
            db.commit()

            print(f"[Seed] Created super admin user: {admin_email}")

        db.close()

    except Exception as e:
        print(f"[Seed] Unable to seed admin user: {e}")


# ============================================================================
# Engine Accessor
# ============================================================================

def get_engine():
    """
    Returns the shared SQLAlchemy engine.

    Used by:
    - Alembic
    - Test fixtures
    - Scripts
    """
    return _engine