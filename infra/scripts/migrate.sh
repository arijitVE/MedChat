#!/usr/bin/env bash
# migrate.sh — Database migration script

set -e

echo "Starting database migrations..."
# Assuming alembic is configured correctly in the project root
alembic upgrade head
echo "Migrations completed successfully."
