# Backup and recovery (operator runbook)

This documents what needs backing up, a starting-point strategy, and a
**verified** local restore drill. It does not — and cannot — stand in for a
production backup strategy: that needs a real hosting/managed-database
decision first (see "Production deployment infrastructure" in
[`missing_features.md`](missing_features.md)), plus legal input on retention
(see below). Nothing here should be read as "backups are handled" — it's the
foundation to build the real thing on.

## What needs backing up

1. **PostgreSQL** — everything: patients, appointments, treatments, consent
   submissions/eligibility results, the audit trail, booking requests. This
   is the primary system of record; losing it is losing the clinic's data.
2. **Object storage (MinIO locally / S3-compatible in production)** —
   consent signature SVGs and generated consent PDFs
   (`apps/api/src/medical_api/integrations/object_storage/client.py`). These
   are the actual signed legal records; a Postgres-only backup does not
   preserve them. Nothing in this codebase versions or backs up this bucket
   yet — see `apps/worker/src/medical_worker/workflows/consent_document_generation.py`
   for where PDFs get written.
3. **Redis** — deliberately _not_ a backup target. It's used as a message
   broker (dramatiq) and a rate-limit counter store
   (`apps/api/src/medical_api/core/rate_limit.py`), both fine to lose:
   in-flight jobs would need re-triggering (the outbox table is the
   source of truth for what still needs processing, not the broker), and
   rate-limit counters resetting is harmless.

## Recommended strategy (once a hosting provider is chosen)

- **PostgreSQL**: automated daily snapshots plus WAL archiving for
  point-in-time recovery (PITR) — every major managed provider (RDS, Cloud
  SQL, Supabase, Neon, etc.) supports this natively; prefer the provider's
  built-in mechanism over a custom cron job. Enable it as part of initial
  provisioning, not as a follow-up.
- **Object storage**: enable bucket versioning at minimum (protects against
  accidental overwrite/delete — consent PDFs/signatures should never be
  silently replaced) and cross-region replication if the compliance review
  requires it.
- **Recovery objectives**: RPO (how much data loss is acceptable) and RTO
  (how long restoration is allowed to take) need an actual business
  decision — this is clinic-operations input, not an engineering default.
  Until that's set, treat "automated daily snapshot + WAL archiving" as the
  floor, not the target.
- **Retention**: how long patient records, audit data, messages, and
  generated documents must be _kept_ (and when they must be _deleted_) is a
  legal question specific to the jurisdiction(s) this clinic operates in —
  same category of "needs qualified counsel, not engineering" as the
  legal/privacy content review in `missing_features.md`. Don't guess at
  retention periods for medical records.

## Local backup/restore drill (verified working)

`scripts/backup_local_db.sh` and `scripts/restore_local_db.sh` (also
`make backup-db` / `make restore-db file=... db=...`) back up and restore
the **local Docker Compose Postgres only** — a tool for practicing the
restore path and for a manual safety net before a risky local
migration/data experiment, not a production mechanism.

```sh
make backup-db
# -> backups/medical_platform-<timestamp>.dump (gitignored, never commit this)

./scripts/restore_local_db.sh backups/medical_platform-<timestamp>.dump
# restores into medical_platform_restore_test — a *separate* database, so
# this never touches your real local dev data even if something goes wrong
```

Verified end to end this session: dumped the real local dev database
(`pg_dump --format=custom`), restored it into a fresh
`medical_platform_restore_test` database, and confirmed row counts matched
exactly across `patients`, `organizations`, `booking_requests`, and
`audit_events` before dropping the test database.

## Still open

- No production backup automation exists yet — blocked on choosing a
  hosting/managed-Postgres provider.
- No object-storage backup/versioning configured (MinIO locally has none;
  production S3-compatible storage needs it configured at provisioning
  time).
- RPO/RTO are undefined — needs a business decision.
- Retention and deletion schedules are undefined — needs qualified legal
  review per jurisdiction.
- No _regular, automated_ restoration test exists — the drill above is
  manual and was run once, by hand, this session. A real strategy needs
  this to run on a schedule against a real backup, not just the local dev
  database.
