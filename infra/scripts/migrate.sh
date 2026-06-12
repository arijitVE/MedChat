#!/usr/bin/env bash
# Apply SQL migrations to the configured MySQL database.

set -euo pipefail

echo "Starting database migrations..."

python - <<'PY'
from pathlib import Path

from sqlalchemy import create_engine, text

from shared.config import get_settings


engine = create_engine(get_settings().DATABASE_URL)
migration_dir = Path("migrations")

with engine.begin() as connection:
    for path in sorted(migration_dir.glob("*.sql")):
        sql = path.read_text(encoding="utf-8").strip()
        if not sql:
            continue
        print(f"Applying {path}")
        for statement in [part.strip() for part in sql.split(";") if part.strip()]:
            if statement.startswith("--"):
                continue
            connection.execute(text(statement))

print("Migrations completed successfully.")
PY
