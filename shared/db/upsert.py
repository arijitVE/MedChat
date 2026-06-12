from __future__ import annotations

from typing import Any

from sqlalchemy import insert
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session


def _dialect_name(db: Session) -> str:
    try:
        return db.get_bind().dialect.name
    except Exception:
        return "mysql"


def build_upsert(
    db: Session,
    model: type,
    values: dict[str, Any],
    update_values: dict[str, Any],
    *,
    index_elements: list[str] | None = None,
    constraint: str | None = None,
):
    """Build a dialect-specific upsert statement for MySQL-first runtime."""
    if _dialect_name(db) in {"mysql", "mariadb"}:
        stmt = mysql_insert(model).values(**values)
        if update_values:
            return stmt.on_duplicate_key_update(**update_values)

        no_op_columns = index_elements or [next(iter(values))]
        return stmt.on_duplicate_key_update(
            **{column: getattr(stmt.inserted, column) for column in no_op_columns}
        )

    return insert(model).values(**values)
