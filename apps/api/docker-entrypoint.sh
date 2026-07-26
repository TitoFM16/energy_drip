#!/bin/sh
set -e

uv run --project /workspace --package medical-api alembic upgrade head
exec uv run --project /workspace --package medical-api fastapi run src/medical_api/main.py --host 0.0.0.0 --port 8000
