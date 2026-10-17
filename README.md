# Energy Drip MVP

A healthcare professional's service catalogue and appointment booking app. The owner manages
services, prices, photos, workers, their weekly availability and appointments. Patients book an
available time from the public site. Staff can create a consent template, share a private consent
link manually, and download the signed PDF after the patient submits it.

The production stack is **one VPS: PostgreSQL + one API process + Caddy serving static frontends**.
No Redis, queue worker, messaging provider, managed database or storage subscription is required.
Private consents use a persistent local volume by default; an existing private S3-compatible bucket
is optional. Service photos always stay on the VPS. The UI uses Colombia time (America/Bogota).

## Start locally

```sh
make up
# In another terminal, create your clinic and owner account interactively:
make bootstrap
```

Open the public site at http://localhost:5175, the admin app at http://localhost:5173,
and consent links at http://localhost:5174. The API is http://localhost:8000.
The API applies database migrations on startup. Docker volumes retain the database, signed
consents and uploaded service photos across restarts. `make down` stops the stack without deleting
volumes. Do not use `down -v` on a clinic with real data.

In the admin app, add a service with its price and duration, add a worker,
then configure the worker's weekly hours. Those slots become bookable from the public site.
Archived services and workers disappear from new bookings while existing appointments remain.

For a host development loop, install Node 22+, pnpm 9, Python 3.12+ and uv, plus WeasyPrint's native
Pango/font libraries (`brew install pango` on macOS; `apt install libpango-1.0-0 libpangoft2-1.0-0
fonts-dejavu-core` on Debian). Then copy `.env.example` to `.env`, run `make install`, `make dev-local`,
`make migrate`, and `make api` in a separate terminal. On Homebrew macOS, set
`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` if the PDF library cannot find Pango.

## Deploy

Follow [the single-VPS runbook](docs/deploy-vps.md). It includes DNS/TLS, the first owner account,
private storage, backups and upgrades. Production owner creation is an operator command; public
registration stays disabled. No payment integration is included; the clinic collects payment itself.

## Project layout

- `apps/api`: FastAPI app, migrations and synchronous consent PDFs.
- `apps/staff-web`: owner/admin app.
- `apps/landing`: services, prices and appointment booking.
- `apps/patient-web`: consent questionnaire and signature flow.
- `deploy`: production static build and Caddy reverse proxy.
- `packages`: shared UI, forms, authentication and API types.
- `apps/worker`: retained legacy automation code; not started or required by the MVP.

```sh
make test
make lint
pnpm turbo typecheck build
make generate-api-types
```

The database-backed API tests need a migrated PostgreSQL database. `make e2e` runs Playwright
against a running development stack. Legacy feature notes in `docs/missing_features.md` describe
the previous broader product and are not MVP acceptance requirements.
