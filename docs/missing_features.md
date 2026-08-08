# Missing Features

This document tracks the work still required to turn the current architectural
foundation into a usable, secure, and production-ready medical platform.

Last reviewed: 2026-08-01, after the single-clinic scope correction below
(session following commit `c77858f`).

See [`blocked-on-owner-input.md`](blocked-on-owner-input.md) for the
checklist of everything below that needs a decision, an account, or a
review from the clinic owner rather than more engineering time.

## Product scope correction (2026-08-01) — resolved

**This is a single-clinic product, not multi-tenant SaaS.** There is exactly
one clinic ("we are the only one"); patients are individual end users booking
appointments with that one clinic — they are never staff and never see or
choose an organization. The backend's multi-tenant data model
(`organization_id` on every table) is kept as-is — it costs nothing and is
good practice regardless — but the _product surface_ built during the
auth-wiring session assumed a multi-tenant SaaS UX. That has now been
corrected:

- `POST /api/v1/auth/register-organization` now returns `403` whenever
  `ENVIRONMENT=production` (see `identity/router.py`), so it can no longer be
  used to spin up additional "clinics" in a live deployment. It stays
  reachable in development/test so local dev and the test suite can still
  create disposable clinics on demand. Production bootstrap is instead a
  one-time operator step: `apps/api/scripts/bootstrap_clinic.py`, which
  creates the organization + first `organization_admin` directly against the
  database and refuses to run a second time once a clinic already exists.
- staff-web's `/register` screen and its "¿Primera vez aquí?" link on
  `/login` are removed entirely (`apps/staff-web/src/routes/register/` no
  longer exists; `router.tsx` has no `/register` route). Verified live:
  navigating to `/register` now 404s.
- The login screen no longer asks for an "ID de organización" — it's just
  email + password. `POST /api/v1/auth/login` dropped its `organization_id`
  query param; the backend resolves the user by email alone
  (`UserRepository.get_by_email_any_org`), which is correct because there is
  only ever one tenant to search. `POST /api/v1/auth/password-reset/request`
  was changed the same way. Verified live in a browser: login with only
  email/password → dashboard → logout → back to the (org-ID-free) login
  screen.
- `packages/auth/src/token-storage.ts`'s `StoredSession` no longer carries an
  `organizationId` — there's nothing for it to disambiguate.
- Everything else built in the auth-wiring session (login/refresh/logout
  mechanics, `apiFetch` auth header + retry-on-401, invite-based staff
  onboarding, practitioner CRUD, availability engine) was already
  tenant-count-agnostic and needed no rework.

The repository already contains the FastAPI modular monolith, background worker,
staff application, mobile consent application, landing page, initial database
schema, Docker development stack, and basic CI configuration. The items below
are intentionally limited to missing or incomplete capabilities.

## Recently implemented

The following capabilities were completed after the initial gap review and are
therefore no longer tracked as wholly missing:

- Public organization registration creates the organization, its first
  `organization_admin`, and an initial access/refresh token pair atomically.
- Authentication now supports hashed rotating refresh tokens, logout,
  invite-based staff onboarding, and password-reset tokens.
- Staff invites and password-reset tokens are expiring and single-use.
- Password hashing uses `bcrypt` directly and request schemas constrain password
  length.
- Scheduling now supports availability-rule creation, listing, and deletion.
- The API can compute future practitioner slots from weekly rules while
  excluding existing practitioner appointments.
- Appointment creation rejects overlapping appointments for the selected
  practitioner.
- Backend tests were added for authentication flows and availability
  computation. Database-backed authentication tests skip when PostgreSQL is not
  available.
- staff-web now has a working login screen (email + password only, no
  organization picker), session restore on page load, transparent
  refresh-token rotation with single-flight deduping on `401`, and a logout
  button. The shared `apiFetch` helper attaches `Authorization: Bearer` to
  every staff-web request and redirects to `/login` on unrecoverable auth
  failure; the patient-web consent app was left untouched (no session to
  attach). Verified live in a browser: login → dashboard → logout → back to
  login.
- Added `POST/GET /api/v1/practitioners` and `PATCH /api/v1/practitioners/{id}`
  so a practitioner profile (linking an existing user to a specialty) can be
  created without a direct database insert; `PractitionerRead` now also
  includes `full_name`/`email` (joined from the linked user) so callers don't
  need a separate user lookup. The Agenda screen consumes this now — see
  below — but there's still no Settings UI to create/manage practitioners
  themselves (see "Settings administration").
- Public organization self-registration is closed in production (`403` when
  `ENVIRONMENT=production`); the single clinic is bootstrapped once via
  `apps/api/scripts/bootstrap_clinic.py` instead. staff-web's `/register`
  screen and login's "ID de organización" field are removed — see "Product
  scope correction" above.
- staff-web now has invite-acceptance (`/accept-invite/:token`), password-reset
  request (`/forgot-password`), and password-reset confirm
  (`/reset-password/:token`) screens, all wired to the backend endpoints that
  already existed. Verified live in a browser: create an invite as an admin →
  accept it → land logged-in on the dashboard; and separately, request a
  reset → follow the (dev-only) link → set a new password → log in with it.
- The Agenda screen is now a real day-view scheduler instead of a static
  today-only list — see "Appointment management" above for what's done and
  what's still open.
- Settings now has a working Practitioners section (list, create, edit
  specialty, toggle active/inactive) — see "Settings administration" above.
- The Patients screen now has live search, patient creation, and a detail
  page for editing name/phone/email and toggling active status — see
  "Patient management" above for what's done and what's still open.
- The Treatments screen now manages the treatment catalogue, and the patient
  detail page manages that patient's treatment plans and sessions — see
  "Treatment catalogue, plans, and session workflow" above for what's done
  and what's still open.
- The Consents screen now authors and publishes consent templates and shows
  a review queue with per-submission detail, and the patient detail page can
  request a consent against a published template. See "Consent-template
  administration and publishing" and "Consent review workspace" above for
  what's done and what's still open.
- The Dashboard is now an organization-scoped operational workspace showing
  upcoming appointments, cancellations/no-shows, pending and expired consent
  requests, submissions requiring medical review, and recent WhatsApp
  delivery/failure status. See "Operational dashboard" below.
- `uv run pytest` now works from the repository root — see "Repair the root
  Python test command" above.
- `pnpm test` and `make test` both pass now — see "Add frontend tests and
  repair `make test`" above.
- The local MinIO dev bucket is now created automatically on API startup
  (non-production only) — see "Verify and harden the Docker development
  stack" above. A fresh `docker compose up` no longer 500s on the first
  consent submission.
- `make seed` / `apps/api/scripts/seed_reference_data.py` provides
  idempotent demo data including a working consent eligibility rule set —
  see "Reference and demonstration data" above.
- `test_auth_flows.py` no longer leaves permanent rows in the database —
  every test now runs inside a rolled-back transaction — see "Backend
  integration tests" above.
- SMS is out of scope by product decision — WhatsApp is the only outbound
  channel. The now-dead `integrations/sms/` code is removed, and the
  WhatsApp client fails fast (no HTTP call at all) when credentials aren't
  configured instead of burning through 5 retries against Meta's API with
  an empty token — see "Notification automation" above.
- The WhatsApp delivery-status webhook is built and verified live end to
  end (signature verification, challenge-response handshake, idempotent
  out-of-order-safe status updates) — see "Delivery callbacks and
  message-state reconciliation" above. Also fixed a latent bug in every
  worker actor (not just this one): dramatiq's thread pool plus a shared
  pooled DB engine meant to be sized for one long-lived event loop caused
  intermittent asyncpg "different loop" crashes — worker actors now use a
  separate NullPool-backed engine (`apps/worker/src/medical_worker/database.py`).
- Added [`docs/whatsapp-setup.md`](whatsapp-setup.md): a step-by-step
  operator runbook for the Meta account/template/webhook setup that only
  the clinic owner can do — see "Notification automation" above.
- Reminders and missed-appointment checks now run on a schedule instead of
  requiring a manual trigger — see "Automated reminder scheduling" above.
  Verified live: it correctly auto-marked a real stale appointment as
  `no_show` on its very first tick.
- Fixed a real cross-tenant IDOR: clinical notes and treatment sessions
  had no organization-boundary check at all (only reachable through a
  parent record's org, which nothing ever joined through), and clinical
  notes had no role gate either. Also wired `AuditService` into every
  staff-mutating endpoint (it existed but was never called), added a
  request-context middleware so audit events capture request
  ID/IP/user agent without threading `Request` through every service, and
  fixed a hash-chain ordering bug plus a naive-vs-aware datetime bug that
  a new authorization/audit test suite caught. All fixes verified live
  against the running Docker stack with real cross-org tokens — see
  "Authorization, audit, and security" above for the full list of what's
  fixed and what's still open.
- Observability: requests are now correlated end-to-end through structured
  logs via a `request_id` bound into structlog contextvars; the worker
  processes now emit the same JSON log format as the API instead of a
  different console format (they never called `configure_logging()`
  before); the outbox consumer and scheduler now log periodic
  heartbeats/ticks instead of only logging once at startup; and the API
  has a real `/health/ready` dependency check (Postgres + Redis) alongside
  the existing pure-liveness `/health`. See "Observability" above for what
  still needs a monitoring-backend decision (metrics, tracing, alerts).
- Added a startup schema-version guard (`core/schema_check.py`, called
  from the API's lifespan and both worker entry points) that refuses to
  start a process whose database schema doesn't match what its own
  bundled migrations expect, rather than failing confusingly on the first
  query that touches a missing/changed column. Finding and fixing this
  surfaced a real, unrelated bug: dramatiq's multi-process worker startup
  had a latent bytecode-cache race (`EOFError: marshal data too short`)
  that the schema check's extra imports made likely enough to actually hit
  — fixed by precompiling bytecode at Docker image build time. See
  "Migration and release discipline" above.
- Added a verified local Postgres backup/restore drill
  (`scripts/backup_local_db.sh` / `restore_local_db.sh`,
  `make backup-db`/`restore-db`) and
  [`docs/backup-and-recovery.md`](backup-and-recovery.md) documenting what
  needs backing up and what's still blocked on choosing a hosting/managed-
  Postgres provider. See "Backup, recovery, and retention" above.
- CI was silently not testing most of what this project already has tests
  for: the backend job had no database (every DB-backed integration test
  skipped on every push) and the frontend job's turbo command didn't
  include `test` at all. Both fixed — see "CI completeness" above. Also
  added `alembic check` as a CI step and `.github/dependabot.yml`.
- `/reservar` is now a real public booking-request form end to end
  (public treatment listing, rate-limited and honeypot-protected booking
  submission, org-scoped staff review endpoints, audit logging) instead of
  a placeholder — see "Connected public booking experience" above.
  Verified live with a real browser submission landing correctly in
  Postgres, plus curl-driven rate-limit and honeypot checks. Production
  landing content/SEO and the legal-content review (both in the same
  numbered section) are untouched — they need real brand/business content
  and qualified-counsel review respectively, not engineering work.
- `packages/api-client`'s generated TypeScript types are now real —
  `generate:schema`/`generate:types` produce
  `generated/{openapi.json,schema.d.ts}` from the FastAPI app directly (no
  server needs to be running), CI fails on drift in either file, and every
  practical hand-typed response/request interface across staff-web and
  patient-web now aliases a generated type instead of duplicating it — see
  "Generated TypeScript API contract" above for the full list and the one
  small backend-schema follow-up it surfaced.
- Added [`blocked-on-owner-input.md`](blocked-on-owner-input.md): a
  standalone checklist of everything in this document that needs a
  decision, account, or review from the clinic owner rather than more
  engineering time (WhatsApp/Meta setup, hosting/managed-database choice,
  legal review, landing content, monitoring-backend choice, branch
  protection).
- `packages/ui` now has real, adopted components (`Button`, `Badge`,
  `Callout`, `TextField`/`TextAreaField`, `ErrorText`) instead of one
  unused `Button`. Scoped to staff-web and patient-web only — both already
  shared a de facto plain-Tailwind/slate visual language that matches
  these components; `landing`'s separate, actively-developed brand
  identity was deliberately left untouched. Replaced 14 hand-rolled
  primary buttons, 5 duplicated status pills, 16+ duplicated error
  messages, and every plain-text-input form field across both apps — see
  "Shared UI, forms, and design system" above for what's still open
  (dialogs/tables/date-pickers — no existing duplication to extract yet;
  design-tokens CSS files remain unused since neither app reads CSS custom
  properties).
- Added `apps/e2e`: Playwright end-to-end tests against the real
  `docker compose up` stack, wired into CI as a third job. 8 flows covered
  (staff login → appointment booking, the full cross-app patient consent
  flow, the public booking form, patient creation as its own
  assertion-bearing test, treatment-plan creation + session recording
  under the `practitioner` role, the medical-record flows, Settings
  availability-rules management, and consent-request revoke/resend) —
  verified these actually catch regressions, not just that they pass, by
  deliberately breaking a button and watching the suite fail before
  reverting, for the appointment-booking, treatment-plan/session,
  medical-record, availability-rules, and consent-lifecycle tests. See
  "End-to-end tests" above for the full list of what's covered vs. still
  open, and two real environment gotchas (slot-grid alignment near
  day-end, the booking rate-limiter applying to repeated local test runs)
  worth knowing about before extending this suite.
- Closed most of "Settings administration"'s availability-rules gap:
  added a Settings UI for the practitioner availability-rule API (create,
  list, delete), which previously only existed as a raw API — see
  "Settings administration" below.
- Closed "Consent request lifecycle": added revoke (with a required
  reason) and resend for consent requests, and replaced the
  patient-facing "invalid or expired" catch-all with a distinct message
  per state (not-found/expired/invalidated/completed) — see "Consent
  request lifecycle" below.
- Closed "Complete medical-record API": built org-scoped, role-gated,
  audited APIs for medical history (append-only with finalize/amend, like
  `ClinicalNote`), allergies, conditions, and medications (update +
  deactivate/reactivate, like the treatment catalogue's active/inactive
  toggle), plus a `MedicalRecordSection` on the patient detail page in
  staff-web and an E2E test. See "Complete medical-record API" below for
  the full writeup.

## Priority levels

- **P0 — Foundation:** Blocks normal end-to-end use or creates a significant
  security, integrity, or deployment risk.
- **P1 — Core product:** Required for the first operational release.
- **P2 — Production readiness:** Required before handling real medical data at
  scale.
- **P3 — Later enhancement:** Valuable after the core workflow is stable.

## 1. Authentication and platform bootstrap

### P0: Staff authentication experience — resolved

Login, session restore, refresh, logout, invite-acceptance, and
password-reset request/confirm all have working staff-web screens and are
verified in a real browser session:
`apps/staff-web/src/routes/{login,accept-invite,forgot-password,reset-password}/`.
Login shows a generic "Credenciales inválidas." message and the password-reset
request screen shows the same "if that account exists..." message regardless
of outcome, so neither leaks account existence.

Remaining acceptance criteria:

- Deliver invite and password-reset tokens out of band (WhatsApp/email)
  rather than returning them directly in the API response — see the
  dev-mode note in `identity/schemas.py`. The forgot-password screen only
  surfaces the dev-mode token behind `import.meta.env.DEV` (stripped from
  production builds), but the backend itself still needs to stop returning
  it outside development before this is fully closed.

### P0: Authenticated frontend API client — resolved

`apiFetch` (`apps/staff-web/src/shared/utilities/api.ts`) attaches
`Authorization: Bearer` to every request, retries exactly once after a
single-flight-deduped silent refresh on `401`, and clears storage plus
redirects to `/login` when refresh also fails. The patient-web consent app
was intentionally left unchanged — it has no staff session to attach.

### P0: Single-clinic bootstrap — mostly resolved

**Decision (2026-08-01): this product has exactly one clinic, operator-
controlled, no public self-service registration.** Implemented: the public
registration route is disabled in production, the `/register` screen and the
login screen's "ID de organización" field are gone, and
`apps/api/scripts/bootstrap_clinic.py` is the one-time operator bootstrap
path — see "Product scope correction" at the top of this document.

Remaining acceptance criteria:

- Seed or otherwise guarantee the complete standard role catalogue rather than
  creating only roles encountered by registration and invites.
- Never expose invite or password-reset tokens in production responses.
- Send invite and reset links using an approved out-of-band channel.
- Never commit real bootstrap credentials to the repository (the bootstrap
  script reads them from env vars or an interactive, non-echoed prompt —
  never hardcode them in a deploy manifest).
- Document credential rotation and administrator recovery for the one
  organization (no "organization suspension" concept needed at single-tenant
  scale).

### P1: Reference and demonstration data — seed command done

`apps/api/scripts/seed_reference_data.py` (`make seed`) creates: a demo
practitioner user + `Practitioner` profile, Monday–Friday 09:00–17:00
availability rules for them, two demo patients, a treatment catalogue
entry, and a **published** consent template version with a real,
working eligibility rule set (`pregnant == true` → `not_eligible`,
`pregnant == false` → `eligible`, unanswered → `requires_manual_review`) —
this is currently the only way to see the eligibility engine actually
produce `eligible`/`not_eligible` results, since the template-authoring UI
has no rule builder yet (see "Consent-template administration and
publishing"). Every entity is looked up by a fixed identifier before being
created, so re-running is a no-op — verified by running it twice and
diffing the output. It refuses to run when `ENVIRONMENT=production` (same
gate as `register-organization`) and requires the clinic to already be
bootstrapped, clearly separating it from `bootstrap_clinic.py`'s one-time
production path. Also added `OrganizationRepository.get_first()`, since
this product has exactly one organization and several call sites (this
script included) need to resolve "the" organization without an ID.

Verifying this surfaced (and led directly to fixing) a real bug: the shared
local dev Postgres had accumulated **hundreds** of throwaway
`organization`/`user` rows named "Test Clinic {uuid}" from running the
`pytest` auth-integration suite repeatedly, because those tests hit a real
database and never rolled back or cleaned up — see "Backend integration
tests" below for the fix. The existing hundreds of rows from before the fix
are still sitting in this local dev database (harmless — see below — but
not retroactively cleaned up by this change); a fresh database won't
accumulate any more.

Remaining acceptance criteria:

- Seed data for appointments and notification workflows (patients,
  practitioners, treatments, and a consent template are covered; no seeded
  appointment or notification/reminder example yet).
- Seed the complete standard role catalogue (only the roles exercised by
  invites/register-organization/this script exist today — see "Single-clinic
  bootstrap").

## 2. Staff application and clinical workflows

### P1: Appointment management — day view resolved, rest still open

The Agenda screen (`apps/staff-web/src/routes/agenda/`) now picks a
practitioner, navigates by single day, shows that day's appointments with
status-change actions (Confirmar/Marcar atendida/No asistió/Cancelar), lists
the practitioner's open slots for the day from the real availability API, and
books a new appointment against a selected slot with a patient search picker.
`PractitionerRead` (`scheduling/schemas.py`) now includes `full_name`/`email`
(joined from the linked user in `PractitionerService`) so the UI has a name to
show instead of a bare `user_id`. Verified live in a browser: pick
practitioner → see open slots → book a slot with a searched patient → new
appointment appears and the slot disappears from availability → Confirmar
updates its status live.

Remaining acceptance criteria:

- Week view (day view only for now).
- Edit/reschedule an existing appointment (only status changes and creation
  exist; no way to move a booked appointment to a different slot).
- Select location, room, and treatment when booking (only patient +
  practitioner + slot today).
- Use the availability endpoint in the public booking interface too (staff-web
  is done; landing page's `/reservar` still doesn't use it — see "Connected
  public booking experience").
- Validate that newly created and rescheduled appointments fall inside allowed
  availability, not merely that they avoid practitioner conflicts (today
  nothing stops booking outside a practitioner's availability rules via the
  raw `POST /appointments` call — the UI only ever offers computed slots, but
  the API itself doesn't enforce it).
- Reject room conflicts as well as practitioner conflicts (no room selection
  yet at all — see above).
- Validate organization ownership of patient, practitioner, room, and related
  records.
- Display appointment status history (the backend records it in
  `AppointmentStatusHistory`; nothing surfaces it in the UI).
- Trigger the appropriate outbox events after state changes (only
  `appointment.scheduled` and `appointment.cancelled` currently enqueue
  events; confirm/checked_in/completed/no_show don't).
- Convert location-local availability rules to UTC correctly; the current
  implementation interprets rule times directly as UTC, and the Agenda UI
  intentionally displays everything in UTC to match that (see
  `apps/staff-web/src/routes/agenda/date-utils.ts`) rather than papering over
  the gap with local-time formatting.
- Support exceptions such as holidays, leave, blocked periods, and one-off
  availability.
- Validate `duration_minutes` with safe positive bounds and prevent invalid or
  excessive slot generation.

### P1: Patient management — search/create/edit done, records still open

The Patients screen (`apps/staff-web/src/routes/patients/`) now has live
search (name or document ID, `GET /api/v1/patients?q=`), an inline creation
form, and a detail page (`/patients/:id`) that edits name/phone/email and
toggles active/inactive. Verified live in a browser: create a patient →
search finds it → open its detail page → edit phone number → save → change
persists back in the list.

Remaining acceptance criteria:

- Pagination (the search endpoint caps at 25 results server-side; the UI has
  no way to page past that yet).
- Edit document ID and date of birth — the backend's `PatientUpdate` schema
  doesn't accept either field today, so they're shown read-only on the detail
  page rather than silently failing to save.
- Contact details and emergency contacts — `PatientContact` and
  `EmergencyContact` already exist as database models
  (`modules/patients/models.py`) but have no API or UI at all.
- Medical history, allergies, conditions, and medications (see "Complete
  medical-record API" below).
- Duplicate-patient detection and a controlled merge process.
- Server-side authorization for every record and action.
- Audit patient views and modifications.

### P1: Complete medical-record API — done

The four remaining medical-history models (`PatientMedicalHistory`,
`PatientAllergy`, `PatientCondition`, `PatientMedication` —
`apps/api/src/medical_api/modules/medical_records/models.py`) already had
migrations from the initial schema but no API layer at all. Built
following the same org-scoped, join-through-`Patient` pattern the
"Complete server-side authorization review" pass established for
`ClinicalNote` and `TreatmentSession`:

- **Medical history** behaves like `ClinicalNote`: append-only, with
  `author_user_id`/`is_finalized`/`finalized_at`/`amends_entry_id` added
  via migration `12431a907aea`. `POST /patients/medical-history` creates
  a draft entry; `POST /patients/medical-history/{id}/finalize` is
  one-way (a second finalize 409s); correcting a finalized entry never
  edits it in place — a new entry is created referencing the original via
  `amends_entry_id`, and the amended entry must belong to the same
  patient/org or the request 404s.
- **Allergies and conditions** are simple structured facts, not clinical
  notes — they support in-place `PATCH` updates and an `is_active`
  deactivate/reactivate toggle (same migration), rather than
  append-only/amendment semantics. **Medications** already had
  `is_current` from the initial schema, toggled the same way.
- Every mutating endpoint is role-gated the same as clinical notes
  (`practitioner`/`medical_director` to write, `organization_admin` added
  for read) and calls `AuditService.record(...)` — verified live against
  the real API that `allergy.created`, `medical_history_entry.finalized`,
  etc. all show up in `GET /api/v1/audit`.
- `apps/api/tests/test_medical_records.py` (8 tests) covers org-scoping
  and role-gating for all four resources (parametrized), the
  allergy update/deactivate flow, the medication current/discontinued
  toggle, the medical-history finalize-is-one-way behavior, the full
  amendment flow (including rejecting an `amends_entry_id` that belongs
  to a different patient), and audit-trail coverage.
- staff-web: new `apps/staff-web/src/features/patient-record/` hooks and
  a `MedicalRecordSection` on the patient detail page
  (`apps/staff-web/src/routes/patients/medical-record-section.tsx`) with
  inline forms for all four resources, wired into
  `apps/staff-web/src/routes/patients/detail.tsx`. Manually verified in a
  real browser end to end (create/finalize/correct a history entry,
  create/deactivate an allergy, create a condition, create/suspend a
  medication) — all four sections persist correctly across a full page
  reload, confirming real backend persistence rather than optimistic-only
  UI state.
- `apps/e2e/tests/medical-record.spec.ts` exercises the same flow through
  the real UI as the practitioner role (organization_admin alone can't
  write these either, same boundary as treatment plans) — verified it
  actually catches regressions by disabling the "Finalizar" button and
  watching the test fail with a precise timeout before reverting.

Sensitive medical content (note bodies, allergy/condition/medication
details) is still excluded from application logs only by convention, same
as `ClinicalNote` — no field-level redaction is enforced structurally
anywhere in the codebase yet.

### P1: Treatment catalogue, plans, and session workflow — core loop done

The Treatments screen (`apps/staff-web/src/routes/treatments/`) now manages
the treatment catalogue: list, create, and toggle active/inactive, same
list/create/toggle pattern as the Practitioners Settings section (including
an `include_inactive` query param on `GET /api/v1/treatments/definitions` so
deactivated entries stay reachable). The patient detail page
(`apps/staff-web/src/routes/patients/treatment-plans-section.tsx`) now shows
a patient's treatment plans, creates a new plan against a catalogue entry,
records sessions against an active plan (practitioner + clinical evolution
note), and completes/cancels a plan. This required three backend additions
that didn't exist before: `TreatmentDefinition` CRUD entirely (there was no
way to create a catalogue entry at all), `GET /api/v1/treatments/plans?patient_id=`
to list a patient's plans (the repository method existed but was never
wired to a route), and `PATCH /api/v1/treatments/plans/{id}` to change
status/notes. Verified live in a browser as a `practitioner`-role user:
create a plan for a patient → record a session with clinical evolution →
complete the plan → recording form and status buttons correctly disappear
for a non-active plan.

Remaining acceptance criteria:

- Record formulas, dosages or parameters — `TreatmentFormula` exists as a
  database model with no API or UI.
- Attachments — `Attachment` exists as a database model with no API or UI.
- Personalized follow-ups — `Followup` exists as a database model with no
  API or UI.
- Link appointments to sessions (`TreatmentSessionCreate` already accepts an
  optional `appointment_id`, but nothing in the UI sets it — sessions are
  currently only recordable from the patient detail page, disconnected from
  the Agenda).
- Finalize sessions and preserve their history (sessions can be created but
  not edited or finalized/locked).
- Provide a dedicated patient-level treatment history view beyond the
  expandable list on the detail page (e.g. progress against planned session
  count, session date timeline).

### P1: Consent review workspace — list/detail view done, rest still open

The Consents screen (`apps/staff-web/src/routes/consents/review-section.tsx`)
now lists every consent request for the organization (patient name, status,
created date) and, on selection, shows the submission detail: eligibility
result badge, submitted-at timestamp, whether a signature was captured, and
every answer matched back to its original question prompt (via the new
staff-side `GET /api/v1/consents/templates/versions/{version_id}` endpoint,
which works for completed requests too — unlike the public form endpoint,
it isn't gated on the request still being pending). The patient detail page
also got a "Solicitar consentimiento" action
(`apps/staff-web/src/routes/patients/consent-requests-section.tsx`) that
creates a request against a published template and surfaces the dev-mode
link. Verified live end to end in two browsers: author a template → publish
→ request it for a patient → open the real link
(`http://localhost:5174/c/:token`) in patient-web → submit → see the
eligibility result and answers in the staff review panel.

Remaining acceptance criteria:

- Filter the review list by appointment, treatment, eligibility result, or
  date (today it's an unfiltered list of every request for the org).
- Distinguish expired/invalidated requests visually with the same care as
  pending/completed (the status badge exists but nothing drives those two
  statuses yet — see the request-lifecycle gap below).
- Allow authorized professionals to record a review decision and rationale
  (today the workspace is read-only — there's no way to act on
  `requires_manual_review`).
- Display signed-document metadata and a link to the generated PDF (only
  "firma capturada: sí/no" is shown; no document viewer).
- Prevent the eligibility engine from being presented as an autonomous
  medical diagnosis — the UI already labels `requires_manual_review` as
  "Requiere revisión médica" rather than a pass/fail verdict, but this needs
  a real design/content review, not just a first pass.

### P1: Settings administration — practitioners and availability rules done, rest still a placeholder

The Settings screen (`apps/staff-web/src/routes/settings/`) now has a working
Practitioners section: list every practitioner (including inactive ones),
create one from an existing user, edit specialty inline, and
toggle active/inactive. Required a new backend endpoint,
`GET /api/v1/auth/users` (organization-scoped, admin/medical_director only),
since there was previously no way for the frontend to know which users exist
to attach a practitioner profile to. `GET /api/v1/practitioners` also gained
an `include_inactive` query param — the default (`false`) preserves the
Agenda's practitioner picker only offering bookable practitioners, while
Settings passes `true` so a deactivated practitioner can still be found and
reactivated instead of disappearing forever. Verified live in a browser: add
a practitioner from an existing user → appears in Agenda's picker → toggle
inactive → disappears from Agenda's picker but stays visible in Settings
tagged "Inactivo — reactivar" → reactivate → reappears in Agenda.

Also added a **Horarios de disponibilidad** section right below it
(`apps/staff-web/src/routes/settings/availability-rules-section.tsx`):
pick a practitioner, see their existing rules sorted by weekday, add a new
one (day + start/end time), or delete one — all against the
`POST`/`GET`/`DELETE /api/v1/appointments/availability-rules` endpoints,
which already existed and were previously only reachable via a raw API
call (e.g. from `apps/e2e/tests/support/api-setup.ts`'s test fixtures).
This is the first `DELETE` mutation in staff-web, so a small new
`useDeleteAvailabilityRule` hook pattern was added to
`apps/staff-web/src/features/scheduling/`. Verified live in a browser
(add a rule → appears sorted correctly among existing rules → delete it
→ disappears) and with an E2E test
(`apps/e2e/tests/settings-availability-rules.spec.ts`) — verified the
test actually catches regressions by disabling the "Agregar horario"
button and watching it fail before reverting.

Remaining acceptance criteria:

- Manage user role assignments (users can be listed now; nothing lets an
  admin change or add a role after invite time).
- ~~Manage locations, rooms, and~~ availability rules. Availability rules
  now have a Settings UI — see above. Locations/rooms don't exist as a
  concept anywhere in the data model yet (not just missing UI — there's
  no backend model to manage).
- Manage treatment catalogue entries.
- Manage consent templates and notification configuration.
- Restrict each section using server-enforced permissions (practitioners
  section already does — create/update require organization_admin or
  medical_director — but this needs to hold for every future section too).
- Audit permission and configuration changes.

### P2: Operational dashboard — done

`apps/staff-web/src/routes/dashboard/index.tsx` is now a read-only operational
workspace in the same Badge/Callout/list-card visual language as Agenda and
Consentimientos. It shows upcoming appointments for the next seven days,
recent/upcoming cancellations and no-shows, pending and expired consent
requests, completed submissions whose eligibility result requires manual
medical review, and the latest WhatsApp delivery states. Failed notifications
include the normalized provider failure reason. Dates are rendered with
Spanish-Colombia formatting in `America/Bogota`, and every card links to the
existing Agenda, Consentimientos, or Notificaciones workspace for action.

The consent list endpoint now accepts the organization-scoped `status` and
`needs_review` filters. `needs_review=true` joins submissions in one bulk SQL
query instead of issuing one detail request per consent. The notification read
schema now exposes `failure_reason` and `created_at`; the generated OpenAPI and
TypeScript client contracts were regenerated accordingly. Appointments retain
their existing organization-scoped range query and are split by status in the
client because that endpoint intentionally has no status filter.

Verified against an isolated real Docker Compose stack with two organizations:
the first organization returned confirmed/cancelled appointments, pending and
expired consents, a manual-review submission, and failed/delivered
notifications; the second organization returned no rows from any of those
same queries. `test_operational_dashboard.py` keeps that HTTP-to-PostgreSQL
boundary and filter coverage repeatable.

## 3. Consent, medical filter, and signed documents

### P0: Consent-template administration and publishing — authoring/publishing done

There was previously no way to create a `ConsentTemplate` at all — the data
model existed but every field had to be inserted directly into the
database. `apps/staff-web/src/routes/consents/templates-section.tsx` now
authors a template (name, consent text, and a dynamic question builder
supporting all five question types, with an options editor for
single/multiple-choice) and publishes it, calling three new backend pieces:
`POST /api/v1/consents/templates` (creates the template + its first draft
version + questions + options in one call), `GET /api/v1/consents/templates`
(list with each template's latest version and publish status), and
`POST /api/v1/consents/templates/{id}/versions/{version_id}/publish` (sets
`published_at`; a second publish attempt on the same version correctly
409s). Publishing is enforced as one-way — there's no unpublish or edit
endpoint, so a published version's content is already immutable by
construction, not just convention.

Remaining acceptance criteria:

- Author eligibility rules. The authoring form has no rule builder at all —
  every template currently publishes with zero rules, which is safe (every
  submission falls through to `requires_manual_review`, never
  auto-`eligible`/auto-`not_eligible`) but means the eligibility engine is
  effectively unused until this exists.
- Validate field keys, required questions, and rule references beyond
  Pydantic's basic type checking (e.g. no server-side check that
  `field_key`s are unique within a version, or that a `single_choice`
  question actually has options).
- Preview the exact mobile experience before publishing (no preview; staff
  has to actually create a request and open the patient-web link to see it).
- Create a new version of an _existing_ template after its first version is
  published — right now, once published, a template has no way to be
  revised; the only option is authoring an entirely new template. Given
  immutability is enforced by never exposing an edit endpoint, this is the
  next thing to add: `POST /templates/{id}/versions` for a new draft.
- Retire a template (`is_active` exists on the model but nothing in the API
  or UI sets it to `false`).

### P0: Strict submission validation

The API must not trust question identifiers, field keys, or values supplied by
the browser.

Acceptance criteria:

- Confirm every submitted question belongs to the request's template version.
- Reject unknown, duplicated, or mismatched question IDs and field keys.
- Enforce required questions and validate values by question type.
- Evaluate rules only from server-validated answers.
- Limit payload and signature sizes.
- Sanitize or safely transform signature input before PDF rendering.
- Make concurrent submissions of the same single-use token safe and idempotent.

### P1: Consent request lifecycle — done

Added `POST /api/v1/consents/requests/{id}/invalidate` (revoke, with a
required `reason`) and `POST /api/v1/consents/requests/{id}/resend`
(`apps/api/src/medical_api/modules/consents/{router,service}.py`):

- **Invalidate**: only a `pending` request can be invalidated (409
  otherwise) — role-gated the same as request creation
  (`receptionist`/`assistant`/`practitioner`/`organization_admin`).
  Records a `ConsentEvent(event_type="consent.invalidated")` with the
  reason in `event_metadata` (this model already existed for
  `consent.submitted` but was otherwise unused) and an
  `AuditService.record(...)` call with the reason in `metadata` — the
  reason is staff-internal audit/event data, **not** returned to the
  patient-facing endpoint (see below).
- **Resend**: only a `pending` or `expired` request can be resent (409
  otherwise, so a completed or already-invalidated request can't be
  resent). Creates a fresh `ConsentRequest` via the same `create_request`
  path (new token, new 48h TTL); if the original was still `pending` it's
  invalidated as superseded so only one live link exists per purpose; an
  already-`expired` original is left as `expired` rather than relabeled.
  A `ConsentEvent(event_type="consent.resent")` links the two.
- **Clear per-state patient errors**: `ConsentService._resolve_active_request`
  now raises a structured `{"reason": "not_found"|"expired"|"invalidated"|
"completed"}` detail instead of one generic string, covering all four
  `ConsentRequestStatus` values plus a true 404. `patient-web`'s
  `apiFetch` (`apps/patient-web/src/shared/api.ts`) gained an `ApiError`
  class carrying the parsed `reason`, and `ConsentStartPage` renders a
  distinct Spanish message per reason (a catch-all "unavailable" message
  covers anything else — network failure, an unrecognized reason, a plain
  500). Verified the staff-entered revoke reason is never present in the
  patient-facing response body.
- **Staff UI**: `apps/staff-web/src/routes/patients/consent-requests-section.tsx`
  gained "Revocar" (prompts for a reason inline, like the medical-history
  correction flow) and "Reenviar" actions per request row, shown only for
  the statuses each action is valid for. The already-existing dev-mode
  "here's the link" `Callout` pattern was reused for the freshly resent
  link.
- Already true before this pass, confirmed unchanged: links are
  short-lived (48h TTL) and single-use (status transitions out of
  `pending` on submit); only the SHA-256 token hash is ever persisted
  (see `ConsentRequest`'s docstring); no `logger.*` calls exist anywhere
  in the consents module, so raw tokens were never at risk of being
  logged.
- `apps/api/tests/test_consent_lifecycle.py` (7 tests) covers: invalidate
  status-transition guards, org-scoping on invalidate, the structured
  per-reason patient error (including that the revoke reason isn't
  leaked), resend superseding a pending request vs. leaving an expired
  one alone, resend rejecting completed/invalidated requests, and audit
  coverage. `apps/e2e/tests/consent-lifecycle.spec.ts` exercises revoke
  and resend through the real staff-web UI and confirms patient-web shows
  the right message for each — verified it actually catches regressions
  by disabling the "Reenviar" button and watching it fail before
  reverting.

### P1: Document access, verification, and invalidation

PDF generation exists, but staff-facing document operations are incomplete.

Acceptance criteria:

- Authorize document metadata and download requests.
- Return short-lived signed download URLs.
- Recalculate or verify the stored SHA-256 hash when required.
- Provide a document verification view.
- Allow only designated roles to invalidate a document.
- Never delete or overwrite an invalidated historical document.
- Record document creation, access, download, verification, regeneration, and
  invalidation in the audit trail.

### P1: Document version history and regeneration

Acceptance criteria:

- Treat every generated PDF as a distinct document version.
- Never replace an existing object-storage key.
- Record which document version is current and why a later version was created.
- Preserve the original submission and every generated version.
- Make retries idempotent so a worker retry does not create unintended duplicate
  versions.

### P1: Durable object-storage configuration

The application uses unique object keys, but local and production storage still
need lifecycle and immutability configuration.

Acceptance criteria:

- Automatically create required development buckets.
- Use private buckets.
- Enable object versioning in supported production storage.
- Restrict delete and overwrite permissions.
- Configure encryption, retention, backup, and recovery policies.
- Test signed URL expiration and tenant isolation.
- Define what operationally “inalterable” means for the selected provider.

### P2: Reliable signing metadata and client IP

Directly reading `request.client.host` is insufficient behind a load balancer or
reverse proxy.

Acceptance criteria:

- Configure trusted proxy handling.
- Accept forwarded IP headers only from trusted infrastructure.
- Preserve UTC timestamp, local timezone, IP address, user agent, patient,
  organization, appointment, treatment, and template version.
- Document which metadata is evidentiary and how it is retained.

### P2: Consent accessibility and device testing

Acceptance criteria:

- Keyboard and screen-reader accessible form controls.
- Responsive signature capture on supported phones and tablets.
- Handle rotation, canvas scaling, touch cancellation, and accidental
  navigation.
- Prevent submission until required answers and signature are present.
- Test slow networks, refreshes, retries, and expired links.

## 4. Notification automation

### Product decision (2026-08-02): WhatsApp only, no SMS

The clinic decided to use Meta's WhatsApp Business Cloud API exclusively —
no SMS provider. `integrations/sms/` (client + worker activity) has been
removed; `sms_provider_api_key`/`SMS_PROVIDER_API_KEY` are gone from
`Settings`, `.env.example`, and `docker-compose.yml`. `send_sms_message` was
never actually wired into any workflow (`appointment_confirmation`,
`appointment_reminders`, `consent_request` all only ever called
`send_whatsapp_message`), so removing it was pure dead-code cleanup with no
behavior change. `NotificationChannel.SMS` remains in the model/DB enum
(dropping a Postgres enum value cleanly isn't worth the migration risk for
zero functional benefit) but nothing in the app can produce a message with
that channel anymore. User-facing copy that mentioned "WhatsApp/SMS"
(landing FAQ, the patient-detail consent-request dev-mode banner) now says
WhatsApp only.

### P0: WhatsApp production configuration — safe failure handling done

`integrations/whatsapp/client.py` calls Meta's Cloud API directly (no BSP
middleman — this is already the cheapest way to do it, since there's no BSP
markup on top of Meta's per-conversation pricing). Two of the five
acceptance criteria are now handled in code:

- **Safe development behavior when credentials are absent**: previously,
  empty `WHATSAPP_API_TOKEN`/`WHATSAPP_PHONE_NUMBER_ID` (the local dev
  default) meant every send attempt actually POSTed to Meta's API with a
  blank bearer token and an empty phone-number-id path segment, then let
  dramatiq retry that guaranteed-permanent failure 5 times with growing
  backoff. `WhatsAppClient.send_template_message` now checks for this
  up front and raises `WhatsAppNotConfiguredError` immediately — verified
  live: calling it locally now fails instantly with a clear message and
  makes zero HTTP requests, instead of hammering Meta's servers.
- **Handle provider rate limits and retryable errors**: the client now
  raises one of three typed exceptions —
  `WhatsAppTransientError` (429, 5xx, or a network-level failure — meant to
  be retried), `WhatsAppRejectedError` (any other 4xx: bad/unapproved
  template name, invalid recipient, revoked token — retrying produces the
  same failure every time), or `WhatsAppNotConfiguredError` (see above).
  The worker's `send_whatsapp_message` actor catches the two permanent-failure
  types, logs, and returns without re-raising — so dramatiq's retry policy
  only ever kicks in for the transient case, matching what
  `max_retries=5, min_backoff=5_000, max_backoff=300_000` was actually meant
  for. Verified live: unconfigured credentials now log
  `whatsapp.send_failed_permanently` once and stop, rather than retrying 5
  times.

Remaining acceptance criteria:

- Configure the actual WhatsApp Business account and get message templates
  approved through Meta — this is an operator task (Meta Business Manager
  account, phone number verification, template submission/review) that
  can't be done from this codebase; nothing here is blocked on it, but no
  message can actually be _sent_ until it happens. Full step-by-step
  runbook: [`docs/whatsapp-setup.md`](whatsapp-setup.md) — credentials →
  env var mapping, the exact four templates this codebase sends (names,
  param order, language), webhook registration, and an end-to-end
  verification checklist.
- Validate template names, locales, and parameter ordering before sending
  (today the client trusts whatever `template_name`/`params` a caller
  passes — no check that the param count matches what the approved
  template expects, or that `language.code` is right for a given
  template).
- Store tokens securely and support rotation (still a plain env var, same
  as every other secret in this codebase — no rotation mechanism).

### P1: Delivery callbacks and message-state reconciliation — done

`GET/POST /api/v1/webhooks/whatsapp`
(`apps/api/src/medical_api/modules/notifications/webhook_router.py`) now
exists. `GET` handles Meta's challenge-response handshake (validates
`hub.verify_token` against `WHATSAPP_WEBHOOK_VERIFY_TOKEN`, echoes back
`hub.challenge`). `POST` verifies `X-Hub-Signature-256` over the raw body
using `WHATSAPP_APP_SECRET` (HMAC-SHA256,
`integrations/whatsapp/webhook.py::verify_signature`) before touching the
payload — an unsigned or wrongly-signed request never reaches parsing.
That pure signature/parsing logic — the actual security
boundary — has 14 unit tests
(`apps/api/tests/test_whatsapp_webhook.py`) covering correct/tampered/
wrong-secret/missing-header/missing-prefix/unconfigured-secret signatures
and multi-entry/multi-status/malformed-entry payload parsing.

Rather than processing inline, the webhook enqueues one outbox event per
status update (event type `whatsapp.delivery_status`), matching this app's
existing rule that the API layer only ever enqueues work. The worker's
`update_delivery_status` actor (now `payload: dict`-shaped, matching every
other outbox handler) applies it with basic out-of-order protection: a
`sent` arriving after `delivered` is ignored rather than regressing the
status, and a `failed` is ignored if the message is already `delivered`.
Failure reasons from Meta's `errors[]` are stored in a new
`NotificationMessage.failure_reason` column (migration `8d569bbaea97`).

Two upstream gaps were fixed to make this actually work rather than just
exist: `send_whatsapp_message` never threaded a `NotificationMessage.id`
through to the send attempt, so `provider_message_id` was never written
back onto a row — nothing a webhook callback could ever match against. All
three call sites (`appointment_confirmation`, `appointment_reminders`,
`consent_request`) now pass their message's id, and the actor updates
`status`/`provider_message_id`/`sent_at` on success or `status`/
`failure_reason` on a permanent failure. Separately, `consent_request.py`
had a hardcoded fake link domain (`consent.example.com`) and never created
a `NotificationMessage` row at all for the consent-link send; both fixed
(new `patient_web_base_url` setting, default `http://localhost:5174`,
matching the real link staff-web already shows in dev mode).

Verified live end to end against the real Docker stack, not just unit
tests: `GET` handshake accepts the correct token and rejects a wrong one;
`POST` rejects an unsigned payload (403) and accepts a correctly-signed one
(200); a signed `sent` callback for an unknown `provider_message_id` is
logged and dropped without erroring; after manually creating a
`NotificationMessage` row with a known `provider_message_id`, a `delivered`
callback correctly updates its status and `delivered_at`; a subsequent
stale `sent` callback for the same message is correctly ignored
(`notification.status_update.ignored_out_of_order`) rather than regressing
the status.

**Bug found and fixed while doing that live verification, unrelated to this
feature's own code but blocking it**: every worker actor
(`generate_pdf`, `send_whatsapp`, `update_delivery_status`, and all four
workflow actors) shares one module-level `engine`/`async_session_factory`
from `medical_api.core.database`, sized for a single long-lived event loop
(the API's uvicorn process). dramatiq runs actors across a thread pool,
and each actor wraps its work in its own `asyncio.run(...)` — a fresh
event loop per call, per thread. Two sequential webhook-triggered actor
calls were enough to hit asyncpg's "got Future attached to a different
loop" (the same root cause fixed earlier this session in
`test_auth_flows.py`, but here in the actual worker process, not a test).
Fixed with a separate NullPool-backed engine for worker actors
(`apps/worker/src/medical_worker/database.py`) — never reuses a
connection across checkouts, so there's nothing to hand across loops.
`consumers/outbox.py` didn't need this (one continuous loop for the
process's whole life) and still uses the pooled engine. This was a latent
bug in every actor, discovered only now because nothing before this
session had actually driven two live dramatiq actor calls through the
real worker process in the same debugging session — worth being aware of
if delivery seems to intermittently fail in ways that don't reproduce via
direct script invocation.

Remaining acceptance criteria:

- "Undeliverable" isn't a status this tracks separately from `failed`
  (Meta's webhook doesn't distinguish them either, in practice).
- Audit meaningful delivery events without logging medical content — no
  audit-log integration yet (see "Audit coverage and integrity").

### P1: Automated reminder scheduling — cron trigger done

`check_due_reminders` and `check_missed_appointments` previously existed
but nothing ever called them outside a manual invocation. A new
`apps/worker/src/medical_worker/consumers/scheduler.py` runs two interval
loops (5 minutes each — the reminder windows already tolerate ±5 minutes,
so consecutive checks' windows overlap with no gap) as a second concurrent
task in the same `worker` process as the outbox consumer (`main.py` now
`asyncio.gather`s both) — no new service or dependency, matching the
"simple first version" scheduling note already in
`appointment_reminders.py`'s docstring. Verified live against the real
Docker stack, not synthetically: restarted the `worker` container, both
`outbox_consumer.started` and `scheduler.started` logged, and on the very
first tick `check_missed_appointments` found and correctly marked `no_show`
a real appointment left over from this session's earlier Agenda testing
(confirmed by querying the row directly afterward) — not a contrived test
fixture, an actual appointment that had genuinely gone stale.

Remaining acceptance criteria:

- Send confirmation, consent link, 24-hour reminder, and 2-hour reminder
  according to clinic policy (the actors exist and now run on a schedule;
  "according to clinic policy" implies configurable timing/content this
  doesn't have yet — see the organization-configurable item below).
- Re-check appointment and consent state immediately before sending (today
  a reminder fires for any appointment in an active status at check time;
  no explicit re-check of consent state specifically).
- Avoid duplicate reminders across retries and multiple workers (the
  existing `already_sent_ids` check in `appointment_reminders.py` guards
  against re-sending the _same_ window's reminder on a later tick, but
  there's no lock/dedup if two `worker` processes ever ran concurrently —
  fine at this app's current single-worker deployment, worth revisiting
  before running more than one).
- Respect appointment rescheduling and cancellation (a cancelled/rescheduled
  appointment falls out of `_ACTIVE_STATUSES`'s query on the next tick, so
  it stops getting _new_ reminders, but there's no explicit
  cancel-in-flight signal — acceptable for a 5-minute-interval poll, not
  for anything needing faster reaction).
- Make reminder windows and templates organization-configurable (still
  hardcoded constants — reasonable for a single-clinic product with no
  per-organization variation to configure, but worth noting as a real gap
  if that ever changes).

### P1: Consent delivery automation

Acceptance criteria:

- Generate a consent request when required by the appointment or treatment.
- Send the short-lived link through the configured channel.
- Record notification and consent-request relationships.
- Resend or escalate when delivery fails.
- Stop reminders when consent is completed, invalidated, or replaced.

### P1: Patient communication preferences and opt-out

Acceptance criteria:

- Record channel preferences and legally required opt-in evidence.
- Process WhatsApp opt-out signals.
- Prevent nonessential sends after opt-out.
- Distinguish transactional/clinical messages from marketing messages.
- Record preference changes in the audit trail.

### P2: Outbox reliability and idempotency

The transactional outbox exists, but production failure handling needs stronger
guarantees.

Acceptance criteria:

- Use stable idempotency keys for dispatched work.
- Prevent duplicate provider messages after consumer or worker crashes.
- Retry failed outbox dispatches with backoff.
- Expose permanently failed events for operator intervention.
- Add dead-letter or replay tooling.
- Monitor queue depth, age, failure rate, and worker health.
- Define safe recovery procedures.

### P3: Durable workflow evaluation

Reassess Temporal or another durable workflow engine after the simple
Dramatiq-based workflow is operational.

Consider migration when:

- Workflows must wait for long periods while reacting immediately to
  reschedules, cancellations, completion, or opt-out signals.
- Manual replay and workflow inspection become operational requirements.
- Timer durability becomes difficult to guarantee with periodic scans.

## 5. Landing page and public booking

### P1: Connected public booking experience — done

`/reservar` is now a working, unauthenticated booking-request form backed by
a new `booking` module, rather than a "coming soon" placeholder.

What's built:

- `GET /api/v1/public/treatments`: lists only active treatment
  name/description for the clinic — no pricing, session counts, or other
  internal fields (see `PublicTreatmentRead`).
- `POST /api/v1/public/booking-requests`: creates a `BookingRequest` row
  (not an `Appointment` directly — deliberately a request for staff to
  confirm and act on through the existing internal patient/appointment
  flows, so an anonymous caller never gets to see or claim real
  availability). Validates the submitted `treatment_definition_id` belongs
  to the org and is active. Response is a single fixed confirmation
  message — never echoes back schedule, patient, or internal state.
- Rate limiting: a Redis fixed-window counter
  (`core/rate_limit.py`), 5 requests/hour per IP, returns `429` past the
  limit. Verified live: 5 requests succeed, the 6th is rejected.
- Bot protection: a honeypot field (`website`) hidden off-screen in the
  real form (visually hidden, `tabIndex={-1}`, `aria-hidden`) — a
  non-empty value silently drops the submission without persisting
  anything, but returns the identical success response so an automated
  submitter can't learn it was filtered. Verified live: a honeypot-filled
  submission returns 201 but nothing lands in `booking_requests`.
- Staff side: `GET /api/v1/booking-requests` and
  `PATCH /api/v1/booking-requests/{id}/status` (roles:
  `receptionist`/`assistant`/`practitioner`/`organization_admin`, matching
  who can already create patients/appointments), org-scoped, and status
  updates are recorded in the audit trail
  (`booking_request.status_updated`).
- The `/reservar` page itself: a real form (name, last name, WhatsApp
  phone, optional email, treatment dropdown populated live from the API,
  optional preferred date, optional message), matching the site's existing
  visual design. Verified live end-to-end in a real browser: filled out
  and submitted the form, confirmed the success screen, and confirmed the
  submission landed in Postgres with the right data.
- Landing gained its first real logic and test coverage: payload-shaping
  (empty-optional-fields → `null`) is a pure function with unit tests; see
  the updated comment in `apps/landing/vite.config.ts` for why the rest of
  the app still has no tests (no DOM stack, mostly static content).

Still open from the original acceptance criteria:

- No staff-web UI to review incoming booking requests — only the API (and
  the audit trail) surfaces them today; a staff member would need to call
  the API directly or a future screen would need to be built.
- No WhatsApp/email notification to staff when a request comes in (no
  consumer exists for that yet — matches this project's "don't build a
  notification path with no consumer" pattern from the WhatsApp work).
- No automatic consent-workflow triggering — that only makes sense once
  staff have converted a request into a real appointment, which is a
  manual step through the existing internal flows.
- The rate limiter is a simple fixed IP-keyed window (can be bypassed by
  rotating IPs, and doesn't cover the public consent endpoints, which have
  the same exposure but weren't in scope here).

### P2: Production landing-page content and SEO — technical SEO complete; final content still owner-blocked

Technical SEO completed:

- Added one centralized metadata registry for all ten public routes: home,
  services, treatments, professionals, security/privacy, FAQ, contact,
  booking, terms, and privacy policy. Client-side navigation now updates the
  title, description, canonical URL, robots directive, Open Graph tags, and
  Twitter Card tags without duplicating metadata in each page component.
- The Vite production build now writes a route-specific HTML entry point for
  every public route. Titles and metadata therefore exist in the initial HTML
  returned to crawlers; they do not depend on React executing first.
- The existing Energy Drip home-care image is reused for Open Graph and
  Twitter previews. The home page includes JSON-LD using
  `MedicalBusiness`/`LocalBusiness`, limited to facts already present in the
  site: Energy Drip Medellín, Medellín/Colombia, mobile IV therapy,
  at-home service, professional assessment, and Spanish/English service.
- `sitemap.xml` and `robots.txt` are generated into the Vite output with all
  canonical routes. The build validates every generated HTML file, the social
  image, sitemap route coverage/XML envelope, and robots directives before it
  can succeed.
- Canonical, social, sitemap, and robots URLs use `VITE_SITE_URL`. Production
  must set it to the real public HTTPS origin; the checked-in landing
  `.env.example` documents this without inventing an unconfirmed domain.
- Responsive layout review is complete for the landing routes, including the
  uncropped hero fix across mobile, tablet, desktop, short-laptop, and
  ultrawide viewports. Navigation remains semantic and keyboard-accessible.

Still open (owner input; also tracked in `docs/blocked-on-owner-input.md`):

- Final Spanish-language brand and service content.
- Accurate professional and treatment information, practitioner bios, and
  approved photos/assets.
- Final search positioning and keyword priorities (what the clinic wants to
  rank for); the current metadata intentionally reflects only existing copy.
- Content ownership and update process.

### P0: Legal and privacy content review

Existing legal routes are placeholders until reviewed for the actual countries,
providers, and clinic operation.

Acceptance criteria:

- Approved terms of service and privacy policy.
- Cookie and analytics policy where applicable.
- Patient data processing, retention, and rights language.
- Electronic-signature and consent language reviewed by qualified counsel.
- Display document versions and effective dates.
- Preserve acceptance evidence when required.

## 6. Shared packages and API contract

### P1: Generated TypeScript API contract — generation done and enforced in CI, adoption across apps still incremental

`packages/api-client` already had a `generate` script and `openapi-typescript`
as a dependency, but nothing had ever actually run it — `generated/` held
only a `.gitkeep`. Also, the script as written needed a live server
(`openapi-typescript http://localhost:8000/openapi.json`), which meant
generating types locally required `docker compose up` first, and running it
in CI would have meant standing up the whole app just to read its own route
table.

Fixed:

- Added `apps/api/scripts/dump_openapi_schema.py`, which imports the FastAPI
  `app` object and calls `.openapi()` directly — building the schema is pure
  route/Pydantic-model introspection, no database or Redis involved, so this
  needs no running server at all. Writes
  `packages/api-client/generated/openapi.json`.
- Split the package's `generate` script into `generate:schema` (runs the
  Python dump) and `generate:types` (runs `openapi-typescript` against that
  now-static file) so each half only needs the toolchain it actually
  requires — useful for CI, where the backend job has `uv`/Python but not
  `pnpm`, and the frontend job has `pnpm`/node but not `uv`.
- `make generate-api-types` / `pnpm run generate:api-types` at the repo root
  for a one-command regeneration.
- CI now fails on drift in both directions: the backend job regenerates
  `openapi.json` from the live route table and diffs it against the
  committed version (catches "changed a response model, forgot to
  regenerate"); the frontend job regenerates `schema.d.ts` from the
  committed `openapi.json` and diffs that (catches "openapi.json changed, or
  the codegen tool's output format changed, but the TypeScript wasn't
  regenerated"). Verified locally by running both regeneration steps twice
  in a row and confirming no diff either time.
- `hooks/index.ts` now exports the generated `paths`/`operations`/
  `components` types plus a `Schemas` convenience alias
  (`Schemas['PatientRead']` instead of the more awkward
  `components['schemas']['PatientRead']`).
- Replaced the manually-duplicated response interfaces across every
  staff-web and patient-web `types.ts`-style file with generated types:
  staff-web's `Patient`, `Practitioner`, `AvailableSlot`, `AppointmentStatus`,
  `Appointment`, `ConsentQuestionOptionInput`, `ConsentQuestionInput`,
  `ConsentTemplateVersion`, `ConsentTemplate`, `ConsentRequestStatus`,
  `EligibilityResult`, `ConsentRequest`, `ConsentAnswer`,
  `ConsentSubmission`, `ConsentRequestDetail`, `TokenResponse`,
  `CurrentUser`, `TreatmentDefinition`, `TreatmentPlanStatus`,
  `TreatmentPlan`, `TreatmentSession`, `StaffUser`; patient-web's
  `ConsentSubmissionResult` and `ConsentSubmissionPayload`. Each is now
  `type X = Schemas['XRead']` instead of a parallel hand-maintained
  interface — done one at a time, comparing the generated shape against
  the hand-typed one field-by-field first (not a blind bulk swap), and
  checking for literal object construction of each type that could break
  on a newly-required field. Two types were deliberately left hand-typed
  rather than replaced: staff-web's `ConsentQuestionPublic` and
  `ConsentTemplateVersionDetail`, and patient-web's `ConsentQuestion` (all
  ultimately from the same backend response model) — the backend's
  `options` field is typed as a loose `dict[str, str]` rather than a
  structured `{value, label}` model, so the generated type for it is only
  `{[key: string]: string}[]`, less precise than the existing hand-typed
  version. Fixing that needs a real Pydantic sub-model on the backend
  first, noted inline in both files as a follow-up.

  Verified: `pnpm turbo lint typecheck test build` passes clean across all
  three apps with zero errors, and live in a real browser — logged into
  staff-web and clicked through Agenda, Pacientes, Tratamientos, and
  Consentimientos, all rendering real data correctly with no new console
  errors (this is a pure type-level change with no runtime logic touched,
  so the type-check passing was the primary signal; the browser walk was
  confirmation, not the main verification).

Acceptance criteria:

- ~~Generate TypeScript definitions from FastAPI OpenAPI.~~ Done.
- ~~Provide a repeatable generation command.~~ Done (`make
generate-api-types`).
- ~~Fail CI when committed generated output is stale.~~ Done, see above.
- ~~Replace manually duplicated response interfaces where practical.~~ Done
  across staff-web and patient-web (see above). Two related types stay
  hand-typed pending a backend schema fix (see above) — not a gap in this
  item so much as a small follow-up it surfaced.
- ~~Preserve public-consent and authenticated-staff client separation.~~
  Preserved by construction: this only generates _types_, not a runtime
  client. Each app still owns its own `apiFetch`/auth-handling wrapper
  (`shared/api.ts` in each app) — the generated types just describe request/
  response shapes for whichever wrapper calls them, so the public
  (patient-web, landing) and authenticated-staff (staff-web) call paths
  never share a runtime client or auth assumptions.

### P2: Shared UI, forms, and design system — core primitives built and adopted in staff-web/patient-web; landing deliberately excluded

**Scope decision**: this only covers staff-web and patient-web. Both were
already using the same de facto visual language — plain Tailwind utility
classes on a `slate` gray palette, no custom theme — which happens to match
`packages/ui`'s pre-existing (but previously unused) `Button` component and
`packages/design-tokens`' color palette almost exactly. `landing` has its
own bespoke brand identity (forest green, gold, serif headings, hand-rolled
CSS classes) that's under active, separate development — pulling it into a
shared internal-tool design system would mean either forcing marketing
pages into a gray dashboard aesthetic or diluting the component library
with two incompatible visual languages. Not touched.

Before building anything, audited both apps for actual duplicated markup
(not speculative components) — found the exact same hand-rolled patterns
copy-pasted across essentially every route: a primary button
(`rounded-lg bg-slate-900 ... text-white`) in 14 files, a status pill
(`rounded-full bg-slate-100 ... text-xs`) in 5 files, a label+input wrapper
in 12+ files, and a standalone error paragraph in 16+ files, each with
small inconsistencies (different padding/sizing) that had crept in over
time from copy-pasting rather than sharing.

Built in `packages/ui` (`Button`, `Badge`, `Callout`, `TextField`/
`TextAreaField`, `ErrorText`), each matching the _exact_ classes already in
majority use rather than inventing a new look — verified field-by-field
against real call sites before writing each component. Then actually
adopted them:

- **staff-web**: all 14 primary-button call sites, all 5 status pills
  (including consent eligibility results — `eligible`/
  `requires_manual_review`/`not_eligible` now map to
  `success`/`warning`/`danger` Badge variants, consolidating three
  slightly-different existing amber/red shades into one), every standalone
  error paragraph, and every plain-text-input form field across patients,
  treatments, consents, agenda, settings, and all four auth screens
  (login, forgot/reset-password, accept-invite). `<select>`-based fields
  and a few genuinely different bespoke patterns (pill-shaped toggle
  chips, inline text-link "quitar" buttons, a dense inline-edit input with
  no visible label) were deliberately left alone — they don't match what
  these components implement, and forcing them in would just be a
  different kind of inconsistency.
- **patient-web**: all 5 full-width mobile CTA buttons (added a `size="lg"`
  Button variant matching patient-web's larger touch-target sizing,
  distinct from staff-web's compact desktop default) and the
  signature-pad's clear/confirm buttons.
- Also opportunistically replaced two more hand-typed interfaces with
  generated `Schemas[...]` types while in these files (staff-web's
  `NotificationMessage`), continuing the "Generated TypeScript API
  contract" cleanup.

Verified: full `pnpm turbo lint typecheck test build` passes clean across
all three apps (only pre-existing, unrelated warnings remain). Live in a
real browser: logged into staff-web and clicked through Dashboard,
Pacientes (list, new-patient form, detail — including the secondary
"Marcar como inactivo" button), Agenda (status badges, booking panel's
textarea), Tratamientos, and Consentimientos (template authoring, the
"Publicada" success badge, and the eligibility warning badge on a real
submission), confirming pixel-for-pixel visual parity with the pre-refactor
screenshots and zero new console errors on a fresh page load.
patient-web's changes are lower-risk, mechanical `size="lg"` Button swaps
with no layout changes — verified via the passing automated pipeline; a
live click-through of the mobile consent flow wasn't completed this pass
(session constraints), worth a quick manual check before considering this
fully closed.

Acceptance criteria:

- ~~Shared accessible form controls and validation presentation.~~ Done for
  staff-web (`TextField`/`TextAreaField` support an `error` prop, though no
  current call site actually populates one — form-level errors via
  `ErrorText` are what's actually used today).
- ~~Shared dialogs, data tables, status badges, date/time controls, and
  error states.~~ Status badges and error states are done (`Badge`,
  `ErrorText`, `Callout`). Dialogs, data tables, and date/time controls are
  still open — neither app has a single dialog or `<table>` element today,
  so there was no real duplication to extract; building these speculatively
  ahead of an actual need was skipped rather than guessed at.
- ~~Shared design tokens used consistently by all applications.~~
  Reinterpreted rather than done as originally written: the pre-existing
  `packages/design-tokens` CSS-custom-property files remain unused (neither
  app reads CSS custom properties — both are pure Tailwind-utility-class
  codebases), and wiring them in as a Tailwind v4 `@theme` would be a
  bigger, riskier change than this pass's scope. The _components_ are the
  practical consistency mechanism instead — each one is now the single
  source of truth for what "primary button" or "status badge" means,
  which is what actually eliminates the drift that existed before.
- ~~Keep application-specific clinical workflows outside generic UI
  packages.~~ Held: every component in `packages/ui` is domain-agnostic
  (no patient/appointment/consent-specific logic or copy) — call sites
  pass in their own labels/content.

## 7. Authorization, audit, and security

### P0: Complete server-side authorization review — org-scoping and role-gate gaps fixed, permission matrix still informal

Found and fixed two real IDOR-class gaps while reviewing every module's
mutating and listing endpoints against organization scoping:

- `medical_records` (clinical notes) had **no organization scoping at
  all** — `ClinicalNote` has no `organization_id` column of its own (it's
  reachable only through the `Patient` it belongs to), and the repository
  never joined through `Patient` to check it. Any authenticated user from
  any organization could read, and — worse — finalize (mutate) another
  organization's clinical notes by patient/note UUID, since role checks
  don't imply org checks. The list endpoint additionally had **no role
  dependency at all**, so any authenticated staff member (including
  reception) could read clinical content. Fixed: repository methods now
  join `ClinicalNote`/`Patient` and filter on `Patient.organization_id`;
  `list_clinical_notes` is now gated to
  `organization_admin`/`medical_director`/`practitioner` (reception
  barred, per this section's own acceptance criteria); `add_note` verifies
  the caller-supplied `patient_id` belongs to the caller's org before
  creating a note.
- `treatments`: `list_sessions_for_plan` had the same shape of bug
  (`TreatmentSession` has no `organization_id`, scoped only through its
  `TreatmentPlan`) — fixed with the same join-through-parent pattern, now
  also 404s (via `get_plan`) instead of silently returning another org's
  session list. Additionally, `create_plan` never verified the
  caller-supplied `patient_id` belonged to the org — fixed so a plan can
  no longer be created that references a patient outside the org.
- Live-verified against the real Docker stack with two separate
  organizations and cross-org tokens: cross-org clinical-note read returns
  an empty list (not another org's data), cross-org finalize/create both
  404, reception gets 403 on clinical-note read even for its own org's
  patient, and the same pattern holds for treatment plans/sessions.
- Added `apps/api/tests/test_authorization_and_audit.py` with automated
  cross-tenant isolation tests covering both of the above, plus the
  audit-trail coverage below.

Still open from the original acceptance criteria:

- No formal, centralized permission matrix document/table — role checks
  are still declared ad hoc per-route via `require_roles(...)`, just
  audited for correctness this pass rather than replaced with a matrix.
- No record-level rules beyond organization boundary (e.g.
  assigned-practitioner-only access to a specific patient's notes) — every
  staff role in an org can still see every patient/note/plan in that org.
- Consent invalidation and eligibility-override endpoints don't exist yet
  at all (no code path to restrict).
- React route guards were not audited this pass (server-side checks are
  now correct; the frontend was already known to not be relied on for
  security, but wasn't specifically re-verified here).

### P0: Audit coverage and integrity — now recording, still needs export/retention policy

The audit model and listing route existed but nothing ever called
`AuditService.record(...)` — verified via a full grep across every module
before this pass; it was dead code. Fixed:

- Added `AuditService.record(...)` calls to every staff-mutating endpoint:
  organization registration, invite creation/acceptance, password-reset
  request/confirm, patient create/update, appointment create/status-change,
  availability-rule create/delete, practitioner create/update, consent
  template create/publish, consent request create, consent-form submission
  (patient-token flow — `actor_user_id` is `None` there since patients
  don't authenticate as staff), clinical note create/finalize, treatment
  definition create/update, treatment plan create/update, and treatment
  session recording.
- Added `RequestContextMiddleware`
  (`apps/api/src/medical_api/core/middleware.py` +
  `core/request_context.py`) so `AuditService.record(...)` picks up
  `request_id`/`ip_address`/`user_agent` from contextvars automatically
  instead of every route/service having to thread a `Request` parameter
  through its whole call chain. Also echoes `X-Request-Id` back on every
  response (generates one if the caller didn't send one) — verified live
  that a caller-supplied request ID round-trips into both the response
  header and the resulting audit row.
- Found and fixed a real hash-chain integrity bug the new tests caught:
  `AuditService._last_hash` picked the "previous" event by
  `ORDER BY occurred_at DESC LIMIT 1`, but Postgres's `now()` is frozen to
  transaction-start time, not per-statement — any two audit events written
  in the same transaction got an identical `occurred_at`, making "last"
  ambiguous. Added a monotonic `sequence` column (`BigInteger`,
  `Identity(always=True)`) to `AuditEvent` and switched both the chain
  lookup and the listing route's ordering to it (migration
  `fbae6f06d123`). This wasn't reachable through today's call sites (each
  records at most once per request) but would have silently produced an
  invalid/inconsistent chain the moment two audit events landed in one
  transaction.
- Also found and fixed, incidentally, that `ClinicalNote.finalized_at` was
  mapped as a naive `TIMESTAMP` while the service wrote an aware
  `datetime.now(UTC)` into it — `finalize_clinical_note` had apparently
  never been exercised against real Postgres before (it 500s with
  `asyncpg.exceptions.DataError`, "can't subtract offset-naive and
  offset-aware datetimes"). Fixed the column to `DateTime(timezone=True)`
  in the same migration.
- Live-verified end to end: registered two real organizations through the
  running API, drove a full patient → clinical-note → finalize sequence,
  and confirmed via a direct Postgres query that `sequence` is monotonic,
  every row's `previous_hash` equals the prior row's `event_hash`, and
  `request_id`/`ip_address` are populated correctly (including the
  caller-supplied `X-Request-Id` on the last event).
- Added `apps/api/tests/test_authorization_and_audit.py` tests asserting
  mutations show up in `GET /api/v1/audit`, that a role without audit
  access is rejected with 403, and that the hash chain is verifiable
  end-to-end (calls `AuditService` directly against the same DB
  transaction the test uses).

Still open from the original acceptance criteria:

- Documents module has no router yet (nothing to audit there until it's
  built).
- Notification-preference changes aren't audited — there's no
  preference-change endpoint yet either (only a read-only notifications
  list exists).
- No audit export tooling, and access is still just role-gated
  (`auditor`/`organization_admin`/`platform_admin`) rather than having a
  separate restricted export path.
- No retention or integrity-monitoring policy defined (e.g. periodic
  full-chain verification, alerting on a broken link).

### P1: API and application security hardening

Acceptance criteria:

- Production secret management and rotation.
- Strong password policy and administrator recovery.
- Rate limiting for login, consent links, webhooks, and public booking.
- Secure CORS and trusted-host configuration per environment.
- Security headers and HTTPS-only production cookies or tokens.
- Input-size limits and upload validation.
- Dependency and container vulnerability scanning.
- Protection against sensitive-data leakage in logs and error responses.
- Documented security incident and credential-revocation procedures.

### P2: Session-security enhancements

The backend now issues short-lived access tokens and opaque rotating refresh
tokens, and logout revokes the submitted refresh token. The frontend has not
adopted this flow yet, and the final browser-storage strategy must be reviewed
before production. Storing either token in `localStorage` increases the impact
of an XSS vulnerability.

Potential acceptance criteria:

- Keep access tokens short-lived and integrate backend refresh-token rotation.
- Select a secure refresh-token transport and storage design; consider
  `HttpOnly`, `Secure`, appropriately scoped cookies with CSRF protection.
- Detect refresh-token reuse and revoke the associated token family or all user
  sessions.
- Allow administrators and users to revoke all active sessions.
- Inactivity and absolute session expiration.
- Optional MFA for privileged roles.
- Reauthentication for high-risk actions.

## 8. Testing and quality gates

### P0: Repair the root Python test command — resolved

`apps/api/tests` and `apps/worker/tests` are both packages named `tests`
(each has an `__init__.py`), which collided under pytest's default
`prepend` import mode: whichever app's tests were collected first "won" the
bare `tests` name in `sys.modules`, and the second app's test files 404'd
under it (`ModuleNotFoundError: No module named 'tests.test_tasks_import'`
when the worker's test collected after the API's). Fixed with a single
`addopts = ["--import-mode=importlib"]` in the root `pyproject.toml`, which
imports each test file directly instead of caching by dotted module name —
no renaming or restructuring needed. `uv run pytest` from the repo root now
passes all 17 tests (16 API + 1 worker); each app's tests still pass
independently from within its own directory; CI already ran `uv run pytest`
at the root (this fixes that job, no CI file changes needed).

### P0: Add frontend tests and repair `make test` — pnpm test/make test pass now

`pnpm test` and `make test` both pass (verified with explicit exit-code
checks, not just eyeballing output). staff-web has real tests for
`apiFetch` (`shared/utilities/api.test.ts`): auth-header attachment,
exactly-one silent-refresh-then-retry on `401`, session clear +
redirect-to-`/login` when refresh also fails, and 204/error-response
handling — directly the "staff authentication and API error handling"
criterion, using `vi.stubGlobal` for `fetch`/`window` rather than adding a
DOM testing stack for one file. patient-web got two small extractions
specifically to make them unit-testable without jsdom:
`hasIncompleteRequiredAnswers` (`features/dynamic-form/validation.ts`,
pulled out of `MedicalQuestionnairePage`'s inline required-field check) and
`buildSubmissionPayload` (`features/submission/use-submit-consent.ts`,
pulled out of `useSubmitConsent`'s `mutationFn` body) — both are now used
by the real components/hooks, not just duplicated for testing. landing has
no test files; `vite.config.ts` sets `test.passWithNoTests: true` with a
comment explaining why (it's static content plus a placeholder `/reservar`
page — the real public booking flow isn't built yet, see "Connected public
booking experience"), the acceptance criteria's own sanctioned fallback
rather than writing hollow tests against placeholder JSX.

Remaining acceptance criteria:

- Test signature behavior and expired-token handling in patient-web
  (`ConsentStartPage`'s error branch, the signature-pad component) — these
  are component/interaction behaviors that need `jsdom` +
  `@testing-library/react`, which nothing in the frontend workspace has
  today. The tests added this round were deliberately scoped to pure logic
  to avoid that investment; it's still worth doing.
- Test important landing-page and booking interactions — blocked on the
  booking flow itself existing (see "Connected public booking experience").
- Broader component/interaction coverage for staff-web (e.g. the Agenda
  booking flow, the consent-template question builder) once a DOM testing
  stack is in place.

### P1: Backend integration tests — now running against real Postgres in CI

Authentication now has HTTP-to-PostgreSQL integration tests for organization
registration, refresh rotation, logout, invites, and password-reset behavior,
plus newer suites for authorization/cross-tenant isolation
(`test_authorization_and_audit.py`) and the public booking flow
(`test_booking.py`). They still skip when no database is reachable — but as
of this pass, one now always is: CI's backend job (`.github/workflows/ci.yml`)
runs real `postgres:16-alpine` and `redis:7-alpine` service containers, so
`uv run pytest` in CI exercises these for real instead of silently skipping
every DB-backed test on every push. Verified locally by dropping and
recreating a genuinely empty database, running the full migration chain
against it from scratch (`alembic upgrade head` — all 5 migrations apply
cleanly in sequence), and running the full test suite against that fresh
database rather than the polluted local dev one. Availability has
service-level tests with mocked repositories.

Also added: `alembic check` as a CI step, which fails the build if a model
change has no corresponding migration. It can't catch a migration that's
missing because a whole module's models were never imported into
`core/model_registry.py` in the first place (nothing to diff against if
metadata doesn't know about it) — which is the specific bug this session hit
once with the `booking` module — but it does catch the more common case of
an edited model with no `alembic revision --autogenerate` run for it.

`test_auth_flows.py` used to commit real rows with no teardown — discovered
while verifying `apps/api/scripts/seed_reference_data.py` (see "Reference
and demonstration data") when hundreds of throwaway "Test Clinic"
organizations from repeated local `pytest` runs turned up in the dev
database. Fixed by joining each test's session into an external transaction
that's always rolled back at teardown
(`join_transaction_mode="create_savepoint"` — SQLAlchemy's documented
pattern for exactly this: the route handlers' own `await session.commit()`
calls only commit a SAVEPOINT nested inside a transaction that's never
itself committed). The fixture is function-scoped (fresh transaction per
test) but pinned to the module's existing session-scoped event loop via
`pytest_asyncio.fixture(loop_scope="session")` — a plain `@pytest.fixture`
here would put each test's connection on its own per-function loop despite
the module-level `loop_scope="session"` marker, reintroducing the original
cross-loop bug this module's `loop_scope` setting exists to avoid. Also had
to match `expire_on_commit=False` from the app's real `async_session_factory`
— without it, route handlers reading an ORM attribute right after
`session.commit()` (e.g. `organization.id` in `register_organization`)
triggered a sync-style lazy-reload outside the async greenlet context
(`MissingGreenlet`). Verified: ran the file 4 times in a row and queried the
organizations table directly — row count never changed.

Remaining integration coverage:

Acceptance criteria:

- ~~Run authentication tests against PostgreSQL in CI~~ Done — see above.
- Test all repositories and both upgrade/downgrade migration paths against
  PostgreSQL. Upgrade path is now verified from scratch (see above);
  `downgrade()` paths are generated but never actually exercised by anything.
- ~~Expand authentication coverage to permissions, session revocation, abuse
  cases, and cross-tenant isolation.~~ Permissions and cross-tenant isolation
  are covered for patients/appointments/clinical-notes/treatments/booking-requests
  (`test_authorization_and_audit.py`, `test_booking.py` — see "Authorization,
  audit, and security" and "Connected public booking experience"). Session
  revocation (refresh rotation, logout) was already covered. Still open:
  abuse-case testing beyond the booking-request rate limiter (e.g. brute-force
  login attempts, invite/reset-token guessing).
- Test appointment scheduling and status history.
- Add database-backed tests for availability rules, tenant isolation,
  practitioner conflicts, room conflicts, and timezone conversion.
- Test consent request concurrency, validation, eligibility, and immutability.
- Test outbox creation in the same transaction as domain changes.
- Test PDF creation, hashing, and document records.
- Test notification retries and callback idempotency.

### P1: End-to-end tests — Playwright framework chosen and wired into CI; 6 of 7 flows covered

Chose Playwright over Cypress: better multi-origin/multi-context support in
one test (this product's most valuable flows genuinely span two separate
frontend apps — staff-web creates a consent request, patient-web completes
it — which Cypress historically handles worse), native TypeScript, and no
separate paid dashboard needed for CI reporting.

New `apps/e2e` package — see [`apps/e2e/README.md`](../apps/e2e/README.md)
for how to run it locally. Runs against the real `docker compose up` stack
(all nine services), not a mocked environment. Each test is fully
self-contained: `tests/support/api-setup.ts` registers a fresh
organization/practitioner/treatment/published-consent-template directly
against the API before touching a browser, using
`@medical-platform/api-client`'s generated types for the request/response
shapes — no dependency on `make seed` or any other test's data, avoiding
the same shared-dev-database pollution problem `test_auth_flows.py` hit
earlier (see "Backend integration tests").

Covers 8 flows so far (the 7th and 8th, Settings administration and the
consent-lifecycle actions, are coverage beyond the acceptance-criteria
list below — neither maps onto any of the still-open items there):

- Staff logs in **through the real login form** (not a token injected into
  storage), books an available slot for a patient, confirms it lands on
  the agenda.
- The full patient-facing consent flow end to end: questionnaire →
  treatment info → hand-drawn canvas signature → review → submit, driven
  from patient-web via a real single-use token, then confirmed from
  staff-web's review screen (the eligibility badge shows correctly). This
  is the single highest-value flow in the product — the one place the
  API, both frontend apps, and (indirectly) the worker's outbox-consumer
  path all have to agree with each other.
- The public, unauthenticated `/reservar` booking form on landing.
- Staff creates a patient through the real form, confirms it in the list,
  then confirms the field that isn't shown in the list (document ID) also
  saved correctly by opening the detail page.
- A practitioner (not the admin — creating a plan/session requires the
  `practitioner`/`medical_director` role, which `organization_admin` alone
  doesn't have, a real authorization boundary this test exercises rather
  than working around) creates a treatment plan for a patient, then
  records a session against it with clinical evolution notes, confirming
  both the plan and the session actually persisted.
- A practitioner records a full medical-record flow for a patient:
  creates a medical-history entry, finalizes it, then corrects it (the
  correction shows up as a separate new entry, the original stays
  untouched and still finalized); creates and deactivates an allergy;
  creates a condition; creates a medication and marks it no longer
  current.
- An admin manages a practitioner's availability rules from Settings: adds
  a new rule through the real form, confirms it's visible sorted
  alongside the rules `bootstrapClinic()` seeds as fixture data, then
  deletes it.
- Staff revokes a pending consent request with a reason, confirms it and
  a resent replacement both end up in the right lifecycle state, and
  confirms patient-web shows a distinct "no longer available" message on
  both the revoked link and the superseded original — not the old generic
  "invalid or expired" message every failure mode used to share.

Wired into `.github/workflows/ci.yml` as a third job: brings up the full
Docker Compose stack, waits on `/health/ready` plus each frontend's own
readiness, runs the suite, uploads the Playwright report as an artifact on
failure.

**Verified these tests actually catch regressions, not just that they
pass**: deliberately hardcoded the "Confirmar cita" button to
`disabled` in `booking-panel.tsx`, re-ran the appointment-booking test,
watched it fail with a precise error (button not enabled, 30s timeout),
reverted, watched it pass again — repeated the same drill for the
treatment-plan/session test against the "Registrar sesión" button, for
the medical-record test against the "Finalizar" button, for the Settings
availability-rules test against the "Agregar horario" button, and for the
consent-lifecycle test against the "Reenviar" button. Also hit two real
environment issues
while building this that are worth knowing about if these start flaking:
availability-rule time windows are interpreted as UTC and slots are
generated on a grid aligned to the rule's `start_time` — a narrow window
can run out of grid-aligned slots between "now" and day-end depending on
what time the test happens to run (fixed by testing against tomorrow, not
today, and using a near-24-hour rule window); and the public booking
form's rate limiter (5 requests/hour/IP — see "Connected public booking
experience") applies to repeated local test runs from the same machine
just as it would to a real abusive caller, so don't be surprised if
`public-booking.spec.ts` needs a Redis key cleared after several manual
reruns in a row (`redis-cli DEL booking_request:<ip>` — not `FLUSHDB`,
which also clears dramatiq's queue state in the same Redis instance).

Acceptance criteria:

- ~~Staff login through appointment creation.~~ Done.
- ~~Patient creation and medical-history update.~~ Done — patient creation
  is its own assertion-bearing test (not just setup for other flows), and
  the medical-record test above covers medical-history create, finalize,
  and correct.
- ~~Treatment-plan and session recording.~~ Done — see above.
- ~~Appointment-to-consent delivery.~~ Partially — the consent flow test
  covers request creation through patient completion; it doesn't cover
  the WhatsApp delivery step itself (nothing to assert against without
  real Meta credentials — see `docs/whatsapp-setup.md`).
- ~~Mobile questionnaire, signature, and submission.~~ Done.
- Staff medical review and signed-document retrieval. The eligibility
  review is covered; signed-PDF retrieval isn't (depends on the worker's
  PDF-generation step, which the current test doesn't wait on).
- Reminder cancellation after appointment cancellation or patient opt-out.
  Not covered — opt-out handling doesn't exist yet as a feature (see
  "Patient communication preferences and opt-out").

### P2: Performance and resilience tests

Acceptance criteria:

- Patient search and schedule-range performance.
- Concurrent single-use consent submissions.
- Queue backlog and provider outage behavior.
- Large PDF/signature/attachment limits.
- Database backup restoration and object-storage recovery.

### P2: CI completeness — lint/format/tests/migrations/builds done, drift check and image scanning still open

`.github/workflows/ci.yml` was quietly missing two things that made a lot of
the testing work already done in this project (this session's and earlier
ones') not actually count for anything: the backend job had no database, so
every DB-backed integration test silently skipped on every single push; and
the frontend job ran `pnpm turbo lint typecheck build` — no `test` — so
staff-web/patient-web/landing's unit tests never ran in CI at all. Both
fixed:

- Backend job now runs real `postgres:16-alpine` and `redis:7-alpine` service
  containers, applies the full migration chain (`alembic upgrade head`) to a
  fresh database, runs `alembic check` (fails on model changes with no
  matching migration — see "Backend integration tests" above for what it can
  and can't catch), then runs the full test suite against that real database.
- Frontend job now includes `test` in the turbo pipeline.
- Added `.github/dependabot.yml` (pip, npm, docker for every app's
  Dockerfile, and github-actions itself, all weekly) — this repo already had
  Dependabot _alerts_ enabled at the GitHub level (visible as a warning on
  every push) but no config for automated update PRs.

Acceptance criteria:

- ~~Python lint, format, tests, and migration checks.~~ Done — see above.
- ~~Frontend lint, type-check, tests, and builds.~~ Done — see above.
- OpenAPI-client drift check. Still open — blocked on "Generated TypeScript
  API contract" (see "Shared packages and API contract") existing at all;
  there's no generated client yet for anything to drift from.
- Dependency and image security scanning. Dependency scanning via
  Dependabot is done (see above). Image scanning (e.g. Trivy against the
  five built Docker images) is still open.
- Required checks documented for protected branches. Still open — this is a
  GitHub repository setting, not a file in this repo, and changes what's
  required to merge, so it wasn't changed without asking first. Recommended:
  require both the `backend` and `frontend` CI jobs on the `main` branch.

## 9. Documentation

### P1: Architecture documentation

The README references architecture documentation that is not currently present.

Acceptance criteria:

- System context and deployable-unit diagrams.
- Module boundaries and dependency rules.
- Appointment, treatment, consent, document, notification, and audit flows.
- Transactional outbox and retry semantics.
- Tenant-isolation and authorization design.

### P1: Security and compliance documentation

Acceptance criteria:

- Data classification and threat model.
- Authentication, authorization, secret management, encryption, and logging
  policies.
- Audit, retention, backup, deletion, and incident-response policies.
- Consent and electronic-signature assumptions requiring legal review.
- Country-specific compliance requirements identified before launch.

### P1: Architecture Decision Records

At minimum, record decisions for:

- Modular monolith versus microservices.
- PostgreSQL, Redis/Dramatiq, and object storage.
- Tenant model.
- JWT/session strategy.
- Consent versioning and operational immutability.
- Eligibility rules as decision support.
- Notification provider selection.
- Vite landing page versus a server-rendered SEO solution.

### P2: API and operator documentation

Acceptance criteria:

- Authentication and role examples.
- Local setup, seeding, migration, and troubleshooting.
- Worker, queue, webhook, and reminder operations.
- Failed-event replay and document-verification procedures.
- Production deployment, rollback, backup, and recovery runbooks.

## 10. Infrastructure and production operations

### P0: Verify and harden the Docker development stack — MinIO bucket init done

The Compose and Dockerfile setup exists but needs a repeatable end-to-end
verification.

MinIO bucket initialization is now automatic: `ensure_bucket_exists()`
(`apps/api/src/medical_api/integrations/object_storage/client.py`) runs in
the API's FastAPI `lifespan` startup hook, gated to
`not settings.is_production` (a production bucket should be provisioned by
infrastructure with its own lifecycle/versioning/access policy, not created
ad hoc by the app with whatever runtime credentials it happens to have). It
uses `head_bucket`/`create_bucket` so it's a no-op once the bucket already
exists. Verified: deleted the bucket, restarted the `api` container, bucket
reappeared with no manual step; restarted again with the bucket already
present — no error, confirming idempotency; ran a full consent submission
immediately after — no `NoSuchBucket` 500 (this was the exact failure this
session hit manually before this fix existed).

Remaining acceptance criteria:

- Fresh checkout can build and start every service (not verified end-to-end
  from a truly clean checkout this session — only individual container
  restarts against already-provisioned volumes).
- ~~Migrations run exactly once and failures are visible.~~ Done —
  `apps/api/docker-entrypoint.sh` already ran `alembic upgrade head` (with
  `set -e`, so a failure stops the container rather than starting against
  a half-migrated schema) before every API start; this was true before
  this session but undocumented. Also now backstopped by the schema-version
  guard below, which catches the case this alone doesn't: a _second_
  process (the worker) running old code against a schema a newer API
  instance already migrated forward.
- ~~API, worker, queue, and frontend health checks are available.~~ API has
  `/health` (liveness) and the new `/health/ready` (readiness — checks
  Postgres and Redis, see "Observability"). Worker/queue and the three
  frontend apps still have none — they're not HTTP servers, so "health
  check" for them means something different (a heartbeat/liveness signal a
  process supervisor can watch); see "Observability" for what exists there
  today (structured heartbeat logs) versus a real check.
- Development credentials are clearly marked and cannot be reused in
  production. Still open — `docker-compose.yml`'s hardcoded
  `medical`/`medical123` etc. are obviously dev-only by inspection, but
  nothing enforces they can't end up in a production config by copy-paste.

### P1: Production deployment infrastructure — not started, needs a hosting decision

Nothing in this section was touched. Every acceptance criterion below
depends on picking an actual hosting target (a cloud provider, a PaaS like
Fly.io/Render, a single VPS, etc.) and a managed Postgres provider — that's
a real infrastructure/cost decision for the clinic owner, not something to
guess at and build speculative Terraform/IaC for. Flagging this explicitly
rather than silently skipping it: **this is the one piece of item 14 that's
blocked on your input, not on more engineering time.**

Acceptance criteria:

- Independently deploy API, worker, staff web, patient web, and landing page.
- Managed PostgreSQL and private object storage.
- Redis or alternative queue infrastructure with persistence appropriate to the
  retry strategy.
- HTTPS, DNS, CDN, load balancer, and trusted-proxy configuration.
- Environment-specific configuration and secret management.
- Zero- or low-downtime migration and rollback strategy.

### P1: Observability — structured/correlated logging and readiness checks done, metrics/tracing/alerting still need a monitoring backend

What's built, all independent of any hosting decision:

- **Request correlation**: `RequestContextMiddleware`
  (`apps/api/src/medical_api/core/middleware.py`) now binds `request_id`
  into `structlog.contextvars` for the duration of every request, so
  _every_ log line anywhere in that request's call stack — router,
  service, repository, any depth — automatically carries the same
  `request_id` with no per-call-site plumbing. Verified directly: bound a
  request_id, logged, confirmed it appeared; cleared it, logged again,
  confirmed it was gone (no leakage across requests).
- **Consistent structured logging across processes**: the worker processes
  (`medical_worker.main` and the dramatiq CLI's `medical_worker.tasks`)
  never called `configure_logging()` — their logs were structlog's default
  console renderer, a different format from the API's JSON logs, making
  the two impossible to parse/correlate consistently. Both now call it.
  Verified live: worker container logs are now genuine JSON
  (`{"event": "outbox_consumer.started", ...}`) instead of
  `2026-08-02 18:43:20 [info     ] outbox_consumer.started ...`.
- **Worker liveness signal**: the outbox consumer previously only logged
  once, at startup — no way to tell "healthy and idle" from "silently
  stuck" without external verification. It now logs a heartbeat every
  ~5 minutes with the current backlog size
  (`outbox_consumer.heartbeat backlog=N`). The scheduler's reminder/missed-
  appointment loops now log each successful tick (they already run every 5
  minutes, so one line per tick doesn't need its own throttling).
- **Readiness endpoint**: `GET /health/ready` checks Postgres and Redis
  connectivity, returns 503 if either is down; `GET /health` stays a pure
  liveness check (no dependency checks — an orchestrator using it to
  decide whether to _restart_ the process shouldn't kill a healthy API
  just because Redis is briefly down, that compounds an outage). Verified
  live: both return 200 with `{"database": "ok", "redis": "ok"}` against
  the running stack.

Acceptance criteria:

- ~~Correlated structured logs without medical content.~~ Correlation is
  done (see above). "Without medical content" wasn't specifically
  re-audited this pass — worth a grep through `logger.*(...)` calls for
  anything that might pass raw clinical-note/consent-answer content before
  trusting this fully.
- Metrics for API latency/errors, database health, queue depth, outbox age,
  worker failures, notification delivery, and PDF generation. Still open —
  needs a metrics library (e.g. `prometheus-client`) _and_ a real backend
  to scrape/store/graph it (Prometheus+Grafana, Datadog, CloudWatch, etc.).
  Bundling this with the hosting decision above rather than half-building
  a `/metrics` endpoint nobody's monitoring yet.
- ~~Distributed tracing or request correlation across API and worker.~~ The
  "or" is doing the work here — request correlation (above) is the
  lighter-weight option this implements. True distributed tracing spanning
  the outbox → worker → dramatiq actor chain would need OpenTelemetry plus
  a collector backend (Jaeger/Tempo/etc.) — a bigger, separate effort if
  it's ever needed beyond what log correlation already gives you.
- Alerts with documented operator actions. Still open — needs an alerting
  backend (PagerDuty, Opsgenie, or even just a monitored Slack webhook) to
  alert _through_; nothing to configure without one.
- ~~Health and readiness endpoints for deployable processes.~~ Done for the
  API (see above). Worker/queue don't have an HTTP endpoint to check (see
  the note in "Verify and harden the Docker development stack") — their
  heartbeat logs are the closest equivalent today.

### P1: Backup, recovery, and retention — local restore drill verified, production automation blocked on hosting choice

Added [`docs/backup-and-recovery.md`](backup-and-recovery.md): what needs
backing up (Postgres — everything; object storage — signed consent
PDFs/signatures, which a Postgres-only backup would silently lose; Redis —
deliberately not backed up, it's disposable broker/rate-limit state), a
recommended strategy once a managed Postgres provider is chosen, and a
**verified working** local backup/restore drill
(`scripts/backup_local_db.sh` / `scripts/restore_local_db.sh`, also
`make backup-db` / `make restore-db`). Verified this session: dumped the
real local dev database, restored it into a separate throwaway database,
and confirmed row counts matched exactly across `patients`, `organizations`,
`booking_requests`, and `audit_events` before dropping the test database.

Acceptance criteria:

- Automated PostgreSQL backups and tested point-in-time recovery. Manual
  local restore is verified (see above); _automated_ backups need a
  managed Postgres provider chosen first.
- Object-storage backup/versioning appropriate to signed records. Still
  open — needs bucket versioning configured at provisioning time.
- Documented recovery-point and recovery-time objectives. Still open —
  this is a business decision (how much data loss / downtime is
  acceptable), not an engineering default; flagged as such in the runbook.
- ~~Regular restoration tests.~~ One manual restoration test is done and
  documented (see above). "Regular" (scheduled, automated, against a real
  backup) is still open.
- Retention schedules covering medical records, audit data, messages, and
  generated documents. Still open — same category as the legal/privacy
  content review in "Landing page and public booking": needs qualified
  legal counsel per jurisdiction, not an engineering default.
- Legally reviewed deletion and archival processes. Still open, same
  reason.

### P2: Migration and release discipline — CI validation and a startup schema guard done

- ~~Validate Alembic migrations in CI against a clean database.~~ Done —
  see "CI completeness" and "Backend integration tests" (added last pass):
  CI now runs `alembic upgrade head` against a fresh Postgres service
  container and `alembic check` before the test suite.
- ~~Prevent application startup against unsupported schema versions.~~
  Added `core/schema_check.py`: computes the migration head from the
  `migrations/` directory actually bundled in the running build (via
  Alembic's own `ScriptDirectory`, not a hand-maintained constant that's
  easy to forget to update) and compares it against the database's
  `alembic_version` row, raising `SchemaMismatchError` on any mismatch —
  including "no `alembic_version` table at all" (migrations never ran).
  Called from the API's `lifespan` (every environment, not just
  production — a mismatch is exactly as real a problem in local dev) and
  from both worker entry points (`medical_worker.main` and the dramatiq
  CLI's `medical_worker.tasks`, which has no async startup hook of its
  own — the check runs in a one-shot `asyncio.run()` at module import
  time instead). Covered by `test_schema_check.py` (matches-at-head,
  wrong-revision, and missing-table cases, each using an isolated
  throwaway database rather than mutating the shared test database's own
  `alembic_version` row) and verified live: restarted the full Docker
  stack and confirmed both the API and worker start cleanly against the
  real migrated schema.

  Wiring this into `tasks.py` surfaced a real, unrelated, pre-existing
  reliability bug: dramatiq's `--processes` launches multiple OS processes
  that each independently `import medical_worker.tasks` at nearly the same
  instant, and if Python's bytecode cache hasn't been precompiled, several
  processes can race to write the same `__pycache__/*.pyc` file and
  corrupt it (`EOFError: marshal data too short` — a known CPython
  multiprocessing hazard, not specific to this codebase; the extra imports
  this change added just made the race window big enough to hit on the
  very first restart). Fixed by precompiling bytecode at image-build time
  in both `apps/worker/Dockerfile` and `apps/api/Dockerfile` (the latter
  pre-emptively, in case the API ever runs with multiple workers). Verified
  by restarting the `worker-queue` container (8 dramatiq processes) three
  times in a row with zero errors, versus a reproducible failure before the
  fix.

- Define backward-compatible deployment rules. Still open.
- Provide release notes and schema-change procedures. Still open.

## Recommended delivery order

1. ~~Repair root tests~~ Both `uv run pytest` and `pnpm test`/`make test`
   pass now (see "Repair the root Python test command" and "Add frontend
   tests and repair `make test`"). Still open: real component-level
   coverage (signature behavior, expired tokens, booking) once a DOM
   testing stack exists.
2. ~~Lock the product down to a single, operator-bootstrapped clinic~~ Done —
   see "Product scope correction". Still open from this item: seed the
   standard role catalogue and add development reference data.
3. ~~Complete staff login, refresh, logout, and authenticated API requests.~~
   ~~Still open: invite-acceptance and password-reset screens.~~ All done,
   including the org-ID-free login screen. Still open: out-of-band token
   delivery (see "Staff authentication experience").
4. ~~Finish patient and medical-history management.~~ Patient search, create,
   and edit are done. Still open: pagination, contact/emergency-contact
   records, and the full medical-history API/UI (see "Patient management" and
   "Complete medical-record API").
5. ~~Connect the Agenda UI to the new availability APIs (and the Settings UI
   to the new practitioner API)~~ Done — day view, booking, status changes,
   and practitioner management are all live. Still open from this item: week
   view, editing/rescheduling, and room-conflict/exception/timezone
   validation (see "Appointment
   management").
6. ~~Finish treatment plans, sessions, formulas, evolution, and follow-ups.~~
   Catalogue, plans, and session recording with clinical evolution are done.
   Still open: formulas, attachments, follow-ups, linking sessions to
   appointments, and session finalization (see "Treatment catalogue, plans,
   and session workflow").
7. ~~Add consent-template publishing~~ Authoring and publishing are done.
   Still open from this item: strict submission validation (field-key
   uniqueness, options-required-for-choice-questions) and eligibility rule
   authoring (see "Consent-template administration and publishing").
8. ~~Build the staff consent-review~~ workflow. List + detail view with
   answers matched to question prompts are done. Still open: review
   decisions/rationale, filtering, and the signed-document viewer (see
   "Consent review workspace").
9. Configure private, versioned object storage and document verification.
10. ~~Connect real WhatsApp and SMS providers, callbacks, and reminder
    scheduling~~ SMS is out of scope by product decision (WhatsApp only).
    WhatsApp's client fails safely and distinguishes retryable from
    permanent errors; the delivery-status webhook is built and verified
    live; reminders and missed-appointment checks now run on a schedule.
    Still open: the actual Meta Business account/template approval (an
    operator task — nothing here is blocked on it, see
    `docs/whatsapp-setup.md`) and template param validation (see
    "Notification automation").
11. ~~Complete audit coverage and the server authorization review.~~ Two
    real cross-tenant IDOR gaps (clinical notes, treatment sessions) are
    fixed and covered by automated tests; every mutating endpoint now
    records an audit event, and the hash chain is verified working end to
    end (see "Authorization, audit, and security"). Still open: a formal
    permission matrix, record-level (assigned-practitioner) access rules,
    audit export tooling, and retention/integrity-monitoring policy.
12. ~~Connect public booking~~ and finalize landing/legal content. Public
    booking is done — see "Connected public booking experience". Still
    fully open: production landing content/SEO and the legal/privacy
    content review, both of which need real brand content and qualified
    legal counsel rather than engineering work.
13. Add integration and end-to-end test coverage. CI now actually runs the
    backend integration tests (real Postgres/Redis services, migration
    chain verified from scratch, `alembic check`) and frontend unit tests
    that already existed but were silently skipped/excluded before — see
    "Backend integration tests" and "CI completeness". Still fully open:
    the broader integration-coverage checklist (appointment status
    history, availability/practitioner/room conflicts, consent
    concurrency/immutability, outbox-transaction atomicity, PDF/document
    tests, notification-retry idempotency), the entire "End-to-end tests"
    item (needs a browser-automation framework decision — Playwright vs.
    Cypress — nothing installed yet), and "Performance and resilience
    tests" (needs real load-testing tooling and infra to test against).
14. Complete production infrastructure, observability, backup, recovery,
    security, and compliance reviews. Observability (correlated structured
    logs, worker heartbeats, readiness checks) and a startup schema-version
    guard are done; a verified local backup/restore drill and runbook
    exist. See "Infrastructure and production operations" for the full
    breakdown. **Still blocked on your input, not more engineering time:**
    production deployment infrastructure needs an actual hosting/managed-
    Postgres provider decision before anything else in that area can be
    built; metrics/tracing/alerting need a monitoring-backend choice;
    retention/deletion schedules need qualified legal review per
    jurisdiction (same category as the legal-content item). Everything
    else in this item (automated production backups, RPO/RTO, security and
    compliance reviews) is downstream of those decisions.

## Release warning

The existing implementation should be treated as an engineering foundation,
not as a production-ready system for real patient data. Legal requirements for
medical records, privacy, data retention, messaging consent, biometric
signatures, and electronic consent vary by jurisdiction and require review by
qualified security, medical, privacy, and legal professionals before launch.
