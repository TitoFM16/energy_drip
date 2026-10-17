.PHONY: install dev dev-local up down api migrate migrate-new seed test lint format backup-db restore-db generate-api-types e2e

install:
	pnpm install
	uv sync --all-packages
	uv run pre-commit install

# MVP development: API, three frontend apps, and PostgreSQL.
dev up:
	docker compose up --build

down:
	docker compose down

# Local (non-Docker) dev loop: only infra in Docker, apps run on the host via uv/pnpm.
# Faster iteration than rebuilding containers, at the cost of needing host toolchains installed.
dev-local:
	docker compose up -d postgres
	pnpm turbo dev

api:
	uv run --package medical-api fastapi dev src/medical_api/main.py --root-dir apps/api

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

# Regenerates packages/api-client/generated/{openapi.json,schema.d.ts}
# from the FastAPI app's own route/schema definitions — no server needs to
# be running. CI fails if either committed file is stale (see ci.yml).
generate-api-types:
	pnpm run generate:api-types

# Local dev backup/restore verification — see docs/backup-and-recovery.md.
# Not a production backup strategy.
backup-db:
	./scripts/backup_local_db.sh

restore-db:
	./scripts/restore_local_db.sh $(file) $(db)

# Cross-app browser flows against the full `docker compose up` stack — see
# apps/e2e/README.md. Not part of `make test`: needs the whole stack
# running, not just built artifacts, and is meaningfully slower.
e2e:
	pnpm --filter @medical-platform/e2e exec playwright install --with-deps chromium
	pnpm run test:e2e

test:
	pnpm turbo test
	uv run pytest

lint:
	pnpm turbo lint
	uv run ruff check .

format:
	pnpm exec prettier --write .
	uv run ruff format .

# Production uses static frontend assets, one API process, and Postgres.
production:
	docker compose --env-file .env.production -f docker-compose.production.yml up -d --build

bootstrap:
	docker compose exec api uv run --no-sync --package medical-api python scripts/bootstrap_clinic.py
