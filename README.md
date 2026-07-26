# Medical Platform

FastAPI + React monorepo for on-demand medical appointments: agenda/patients/treatments,
mobile consent with biometric signature, and WhatsApp/SMS notification automation.

## Layout

- `apps/api` — FastAPI backend (modular monolith, see `docs/architecture`)
- `apps/worker` — background jobs: outbox consumer, notification workflows, PDF generation
- `apps/staff-web` — React app for clinic staff (agenda, patients, treatments, consent review)
- `apps/patient-web` — mobile-first consent + medical filter flow
- `apps/landing` — public marketing site and booking entry point
- `packages/*` — shared TS packages (ui, api-client, forms, config, design-tokens)
- `services/*` — local dev service configuration (postgres, redis, storage)
- `infrastructure/*` — docker/terraform/k8s/scripts for deployment

## Requirements

- Docker, for the all-in-Docker workflow below (recommended — no local Python/Node/Postgres needed)
- Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+, [pnpm](https://pnpm.io/) 9+ — only if you want the faster host-based dev loop instead

## Getting started

The whole stack runs in Docker — Postgres, Redis, MinIO, the API, the worker
(both the outbox poller and the dramatiq queue), and all three frontend apps:

```bash
make up      # docker compose up --build — everything, migrations run automatically
make down    # stop and remove containers
```

Once up: API on `:8000`, staff-web on `:5173`, patient-web on `:5174`, landing on `:5175`,
MinIO console on `:9001`. Source directories are bind-mounted, so most edits are picked
up without a rebuild — rebuild (`make up` again) after changing dependencies.

If you'd rather run the apps directly on the host (faster reload, needs the
Python/Node toolchain installed locally) and only put infra in Docker:

```bash
make install      # uv sync + pnpm install + pre-commit install
make dev-local     # starts postgres/redis/minio in Docker, then all frontend dev servers
make migrate       # apply database migrations
make api           # run the FastAPI dev server
make worker        # run the background worker (outbox poller)
make worker-queue  # run the dramatiq queue worker
```

Copy `.env.example` to `.env` and fill in real values for the host-based workflow
(the Docker workflow sets container-network env vars directly in `docker-compose.yml`).

## Quality gates

```bash
make lint     # ruff + eslint/typecheck across the workspace
make format   # ruff format + prettier
make test     # pytest + frontend test suites
```

Pre-commit runs ruff (lint + format) and basic hygiene hooks on every commit —
install with `make install` (runs `pre-commit install`) or manually via
`uv run pre-commit install`.
