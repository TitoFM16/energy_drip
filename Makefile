.PHONY: install dev api worker migrate migrate-new test lint format

install:
	pnpm install
	uv sync --all-packages
	uv run pre-commit install

dev:
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

test:
	pnpm turbo test
	uv run pytest

lint:
	pnpm turbo lint
	uv run ruff check .

format:
	pnpm exec prettier --write .
	uv run ruff format .
