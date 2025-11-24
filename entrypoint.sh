#!/bin/sh
set -e

# Ensure alembic installed paths are visible
export PATH="$PATH:/home/appuser/.local/bin"

echo "Running Alembic migrations..."
python -m alembic upgrade head

echo "Starting API..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
