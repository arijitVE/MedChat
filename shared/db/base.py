# shared/db/base.py — SQLAlchemy Base + metadata registry
# All ORM models inherit from this Base. Import Base in every model file.

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase):
    """SQLAlchemy 2.x declarative base for all HDMIS ORM models.

    All models should inherit from this class. The metadata registry is
    shared across all models so that Base.metadata.create_all() creates
    all tables in one call.
    """
    pass
