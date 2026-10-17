# Deploy the MVP on one VPS

The runtime is three containers: PostgreSQL 16, a single FastAPI process, and Caddy with three
compiled React sites. A small Linux VPS with 2 GB RAM and persistent disk is a reasonable starting
point; image builds may need more memory or swap. No application worker, Redis, MinIO or notification
provider is required. Configure the clinic's real service and consent content before accepting patients.

## DNS and configuration

Install Docker Engine with Compose. Point three DNS names at the VPS (for example
`clinic.example.com`, `admin.clinic.example.com`, `consent.clinic.example.com`). Permit inbound
80/443 and your restricted SSH access; PostgreSQL and the API publish no host ports.
Caddy obtains and renews HTTPS certificates automatically. Three names can share the same domain
and VPS; the separate sites do not require separate servers.

```sh
cp .env.production.example .env.production
chmod 600 .env.production
openssl rand -hex 32
openssl rand -hex 32
```

Set `POSTGRES_PASSWORD` and `SECRET_KEY` to those two independently generated values, then set
the three domain names and `TLS_EMAIL`. Keep the password hexadecimal so it is safe in the DB URL.
Do not commit `.env.production`. Keep `CLINIC_TIMEZONE=America/Bogota`: the MVP's customer and
admin interfaces display Colombia time. Changing the backend timezone alone does not translate
the UI into another timezone.

```sh
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
docker compose --env-file .env.production -f docker-compose.production.yml exec api \
  uv run --no-sync --package medical-api python scripts/bootstrap_clinic.py
```

The bootstrap prompts for clinic name, owner name/email and a password without echoing it.
It refuses to create a second clinic. It prints `PUBLIC_ORGANIZATION_ID`; copy this ID into
`.env.production` and run the `up` command again. If omitted, public booking selects the sole active
clinic and fails closed if there are multiple clinics. Production HTTP registration remains disabled.
Open the admin domain and log in with the new owner account. Add services, upload their images,
add workers and configure weekly hours before sharing the public site.

## Consents and storage

Create and publish consent text in the admin app, then request consent from a patient's record.
Copy the returned link and share it yourself (in person or using your normal communication tools).
The app does not send paid messages. A link expires after 48 hours and can be used once. Resending
creates a new link and invalidates the prior pending one. Submission immediately creates the
signed PDF, its hash and an audit record in the same database transaction; no queue needs to run.

`app_data` persists private signature/PDF files under `/data/private` and public service images
under `/data/media`. Private files are never mounted as static assets. Only authorized staff can
issue five-minute download links; those links are bearer capabilities and should not be shared
publicly. Original PDF versions remain immutable when regenerated. Protect the VPS and backups,
and set a retention policy appropriate for your clinic.

To use S3-compatible private storage, pre-create a private bucket, set `STORAGE_BACKEND=s3`,
`S3_BUCKET`, access credentials and the provider's `S3_ENDPOINT_URL`. AWS S3 can omit the endpoint.
Set `S3_PUBLIC_ENDPOINT_URL` only when browser downloads use a different endpoint. Bucket access
must remain private and credentials need only list/head bucket plus object read/write rights.
Changing backend does not migrate existing documents: copy existing keys byte-for-byte first and
verify old downloads before switching. Service images remain on the VPS in either mode.

## Recover a forgotten staff or owner password

The MVP does not send password-reset email. An operator with SSH access can reset an existing
active account using the same scoped recovery command for owner and staff accounts:

```sh
docker compose --env-file .env.production -f docker-compose.production.yml exec api \
  uv run --no-sync --package medical-api python scripts/reset_staff_password.py
```

It displays the configured clinic UUID (or asks for it if unset), then asks for the exact account
email and a new password twice without echo. Use at least 12 characters. It updates only that
clinic/account, records an audit event, revokes existing refresh sessions and invalidates unused
reset links. Existing short-lived access tokens remain valid until their normal expiry (30 minutes
by default). Give the new password to the account owner through your normal private channel;
no password is placed in a shell command or email provider.

## Backups and recovery

Back up BOTH the database and `app_data`; the database alone cannot restore consents or photos.
The following consistent backup briefly stops writes while Postgres stays up. Run from the project
directory. Backup files contain private patient data; store a protected copy off the VPS.

```sh
mkdir -p backups
chmod 700 backups
docker compose --env-file .env.production -f docker-compose.production.yml stop api
docker compose --env-file .env.production -f docker-compose.production.yml exec -T postgres \
  pg_dump -U medical -d medical_platform -Fc > backups/clinic.dump
docker compose --env-file .env.production -f docker-compose.production.yml run --rm -T --no-deps \
  --entrypoint tar api -C /data -czf - . > backups/files.tar.gz
docker compose --env-file .env.production -f docker-compose.production.yml start api
chmod 600 backups/clinic.dump backups/files.tar.gz
```

Use timestamped directories so the next backup does not overwrite the only good copy. Schedule
this process with the VPS's cron and monitor its result. If using S3, enable bucket versioning and
back up the bucket independently; the local archive still includes public service photos.
Keep `.env.production` and the repository revision with the backup in protected storage.

Practice restore on a separate empty VPS/database before relying on a backup:

```sh
# Restore into an empty database and empty data volume, not a running clinic.
docker compose --env-file .env.production -f docker-compose.production.yml up -d postgres
docker compose --env-file .env.production -f docker-compose.production.yml exec -T postgres \
  pg_restore -U medical -d medical_platform --exit-on-error < backups/clinic.dump
docker compose --env-file .env.production -f docker-compose.production.yml run --rm -T --no-deps \
  --entrypoint tar api -C /data -xzf - < backups/files.tar.gz
docker compose --env-file .env.production -f docker-compose.production.yml up -d
```

Verify owner login, services/photos, appointment history and a consent download/hash after restore.
Never use `docker compose down -v` on production: it deletes the database and local documents.

## Upgrade an existing development installation

The development Compose project keeps its original `medical-platform` name so its existing
PostgreSQL volume is reused. Production uses the separate `energy-drip` project name on a new VPS.
Moving a clinic between those projects requires the explicit database and files backup/restore
above; the application does not select another Docker project's volume automatically.

The previous stack stored signatures and PDFs in MinIO. **Existing MinIO objects are not migrated
automatically to local storage.** Back up the old database and bucket before upgrading. Either keep
the existing private bucket reachable and configure `STORAGE_BACKEND=s3` with its endpoint and
credentials, or export every object, preserving its full key (including `organizations/...`), into
`/data/private` in the new `app_data` volume. Do not flatten filenames or change object bytes.
Verify old consent downloads and stored hashes before removing the old MinIO service or volume.

After migration, stop the old `worker`, `worker-queue` and Redis containers belonging to this
Compose project; they are no longer required. Use `docker compose up -d --remove-orphans` only
after confirming the old object storage has been preserved. Never delete old volumes as part of
that cleanup. Review previously configured weekly hours: they are now interpreted as Colombia
local time; older versions interpreted them as UTC. Adjust those rules before reopening public
bookings if the original values represented UTC hours.

## Updates and operating limits

Take and verify a backup first, deploy the reviewed repository revision, then run `up -d --build`.
The API applies migrations before becoming ready. Inspect `docker compose ... logs api` on failure.
Rolling application code back does not roll back the schema; use the verified matching backup if
a migration must be reversed. An upgrade has brief downtime on this single-server MVP.

The API must run **one process and one replica**. Its in-memory rate limits reset on restart.
Do not add workers/replicas without introducing shared rate-limit state. Caddy is the only public
entry point and forwards the client address; the internal API trusts proxy headers only because
its port is not published. The app needs no external messaging delivery or automatic reminders.
