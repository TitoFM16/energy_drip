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

## Auth

Every user belongs to an `Organization`; there's no cross-tenant login. The first
account for a new clinic is created via registration, and every account after
that comes from an invite sent by an existing admin — there's no open sign-up.

```
POST /api/v1/auth/register-organization   Creates the organization + its first
                                           organization_admin user. Public.
POST /api/v1/auth/login                   { email, password } + ?organization_id=
                                           query param. Returns access + refresh tokens.
POST /api/v1/auth/refresh                 { refresh_token } -> new access + refresh
                                           token pair. The old refresh token is
                                           revoked immediately (rotation).
POST /api/v1/auth/logout                  { refresh_token } -> revokes it.
GET  /api/v1/auth/me                      Current user + roles. Requires Authorization: Bearer.

POST /api/v1/auth/invites                 { email, role } -> invite token.
                                           Requires organization_admin/platform_admin.
POST /api/v1/auth/invites/{token}/accept  { full_name, password } -> creates the
                                           user with the invited role, returns tokens.

POST /api/v1/auth/password-reset/request  { organization_id, email } -> always 200,
                                           regardless of whether the account exists.
POST /api/v1/auth/password-reset/confirm  { token, new_password }
```

Access tokens are short-lived JWTs (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 30 min);
refresh tokens are opaque, hashed at rest, and rotated on every use so a stolen
refresh token stops working the moment the legitimate client refreshes.

**Dev-mode note:** invite and password-reset tokens are returned directly in the
API response (`token` field) since no email/WhatsApp delivery is wired up yet.
Before production, those must be delivered out-of-band instead and never
included in the response — see the `token`/`InviteCreateResponse` docstrings in
`apps/api/src/medical_api/modules/identity/schemas.py`.

## Scheduling & availability

Practitioners have recurring weekly `AvailabilityRule`s (weekday + start/end
time); the API computes actual open slots from those rules minus existing
appointments — nothing needs to be precomputed or cached.

```
POST   /api/v1/appointments/availability-rules              Create a recurring rule.
GET    /api/v1/appointments/availability-rules?practitioner_id=
DELETE /api/v1/appointments/availability-rules/{rule_id}

GET /api/v1/appointments/availability
    ?practitioner_id=&date_from=&date_to=&duration_minutes=30
    -> [{ starts_at, ends_at }, ...]
```

Known simplification: rule times are interpreted as UTC directly rather than
converted from a location's local timezone — fine for a single-timezone clinic;
multi-location deployments spanning timezones will need that conversion added
in `AvailabilityService.compute_slots` (`apps/api/src/medical_api/modules/scheduling/service.py`).

## Quality gates

```bash
make lint     # ruff + eslint/typecheck across the workspace
make format   # ruff format + prettier
make test     # pytest + frontend test suites
```

Pre-commit runs ruff (lint + format) and basic hygiene hooks on every commit —
install with `make install` (runs `pre-commit install`) or manually via
`uv run pre-commit install`.
