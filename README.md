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

- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- Node 20+, [pnpm](https://pnpm.io/) 9+
- Docker (for postgres/redis/minio locally)

## Getting started

```bash
make install     # uv sync + pnpm install + pre-commit install
make dev          # starts postgres/redis/minio, then all frontend dev servers
make migrate      # apply database migrations
make api          # run the FastAPI dev server
make worker       # run the background worker
```

Copy `.env.example` to `.env` and fill in real values before running services.

## Quality gates

```bash
make lint     # ruff + eslint/typecheck across the workspace
make format   # ruff format + prettier
make test     # pytest + frontend test suites
```

Pre-commit runs ruff (lint + format) and basic hygiene hooks on every commit —
install with `make install` (runs `pre-commit install`) or manually via
`uv run pre-commit install`.
