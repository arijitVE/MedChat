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

    The session is committed on success and rolled back + closed on error.
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
    """Create all tables from ORM metadata. Dev / test use only.

    In production, use Alembic migrations instead.

    NOTE: You must import all model modules before calling this so that
    Base.metadata is aware of all tables. Example::

        from shared.db.models import document, extraction  # noqa
        init_db()
    """
    Base.metadata.create_all(bind=_engine)


def get_engine():
    """Return the shared engine instance (for Alembic or test fixtures)."""
    return _engine
