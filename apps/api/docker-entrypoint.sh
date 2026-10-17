#!/bin/sh
set -e

uv run --no-sync --project /workspace --package medical-api alembic upgrade head
exec uv run --no-sync --project /workspace --package medical-api fastapi run src/medical_api/main.py --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
