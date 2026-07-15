from __future__ import annotations

from typing import Any

from sqlalchemy import insert
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session


def _dialect_name(db: Session) -> str:
    try:
        return db.get_bind().dialect.name
    except Exception:
        return "postgresql"


def build_upsert(
    db: Session,
    model: type,
    values: dict[str, Any],
    update_values: dict[str, Any],
    *,
    index_elements: list[str] | None = None,
    constraint: str | None = None,
):
    """Build a dialect-specific upsert statement for PostgreSQL/MySQL runtimes."""
    dialect = _dialect_name(db)
    if dialect in {"postgresql", "postgres"}:
        stmt = pg_insert(model).values(**values)
        if update_values:
            return stmt.on_conflict_do_update(
                index_elements=index_elements,
                constraint=constraint,
                set_=update_values,
            )

        no_op_columns = index_elements or [next(iter(values))]
        return stmt.on_conflict_do_update(
            index_elements=index_elements,
            constraint=constraint,
            set_={col: getattr(stmt.excluded, col) for col in no_op_columns},
        )

    if dialect in {"mysql", "mariadb"}:
        stmt = mysql_insert(model).values(**values)
        if update_values:
            return stmt.on_duplicate_key_update(**update_values)

        no_op_columns = index_elements or [next(iter(values))]
        return stmt.on_duplicate_key_update(
            **{column: getattr(stmt.inserted, column) for column in no_op_columns}
        )

    return insert(model).values(**values)

