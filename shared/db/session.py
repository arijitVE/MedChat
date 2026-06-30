# shared/db/session.py — DB session factory + FastAPI dependency (get_db)

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.config import get_settings
from shared.db.base import Base

# ---------------------------------------------------------------------------
# Engine & Session factory
# ---------------------------------------------------------------------------

_engine = create_engine(
    get_settings().DATABASE_URL,
    pool_pre_ping=True,            # detect stale connections
    pool_size=10,
    max_overflow=20,
    echo=False,                    # set True for SQL debug logging
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Usage in a route::

        @router.post("/upload")
        def upload(db: Session = Depends(get_db)):
            ...

    The session is NOT committed automatically. You must call db.commit() explicitly.
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


# ---------------------------------------------------------------------------
# Dev-only initialisation
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create all tables from ORM metadata and seed super admin user if not present."""
    Base.metadata.create_all(bind=_engine)
    try:
        db = SessionLocal()
        from shared.db.models.user import User
        from product.auth.password import hash_password
        from uuid import uuid4
        
        admin_user = db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            settings = get_settings()
            admin_email = settings.ADMIN_USERNAME if "@" in settings.ADMIN_USERNAME else "admin@documed.ai"
            new_admin = User(
                user_id=str(uuid4()),
                email=admin_email,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                full_name="System Super Administrator",
                role="admin",
            )
            db.add(new_admin)
            db.commit()
            print(f"[Seed] Created super admin user in DB: {admin_email}")
        db.close()
    except Exception as e:
        print(f"[Seed] Note: could not check/seed admin user: {e}")


def get_engine():
    """Return the shared engine instance (for Alembic or test fixtures)."""
    return _engine
