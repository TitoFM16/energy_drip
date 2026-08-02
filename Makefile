.PHONY: install dev dev-local up down api worker migrate migrate-new seed test lint format

install:
	pnpm install
	uv sync --all-packages
	uv run pre-commit install

# Full stack in Docker: api, worker, worker-queue, all 3 frontend apps, postgres, redis, minio.
dev up:
	docker compose up --build

down:
	docker compose down

# Local (non-Docker) dev loop: only infra in Docker, apps run on the host via uv/pnpm.
# Faster iteration than rebuilding containers, at the cost of needing host toolchains installed.
dev-local:
	docker compose up -d postgres redis minio
	pnpm turbo dev

api:
	uv run --package medical-api fastapi dev src/medical_api/main.py --root-dir apps/api

worker:
	uv run --package medical-worker python -m medical_worker.main

worker-queue:
	uv run --package medical-worker dramatiq medical_worker.tasks

migrate:
	cd apps/api && uv run --package medical-api alembic upgrade head

migrate-new:
	cd apps/api && uv run --package medical-api alembic revision --autogenerate -m "$(name)"

# Demo data for local dev: patients, a practitioner, availability, a
# treatment catalogue entry, and a published consent template with a
# working eligibility rule set. Idempotent. Requires the clinic to already
# be bootstrapped (see apps/api/scripts/bootstrap_clinic.py).
seed:
	cd apps/api && uv run --package medical-api python scripts/seed_reference_data.py

test:
	pnpm turbo test
	uv run pytest

lint:
	pnpm turbo lint
	uv run ruff check .

format:
	pnpm exec prettier --write .
	uv run ruff format .
