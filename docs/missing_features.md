# Missing Features

This document tracks the work still required to turn the current architectural
foundation into a usable, secure, and production-ready medical platform.

Last reviewed: 2026-08-01, after the single-clinic scope correction below
(session following commit `c77858f`).

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

### P1: Complete medical-record API

Clinical-note endpoints exist, but the remainder of the medical-history models
do not yet have complete APIs and services.

Acceptance criteria:

- APIs for medical history, allergies, conditions, and medications.
- Organization and record-level authorization in every operation.
- Append-oriented clinical entries with explicit correction or amendment flows.
- Finalized records cannot be silently overwritten.
- Record authorship, timestamps, and finalization state are preserved.
- Sensitive medical content is excluded from ordinary application logs.

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

### P1: Settings administration — practitioners done, rest still a placeholder

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

Remaining acceptance criteria:

- Manage user role assignments (users can be listed now; nothing lets an
  admin change or add a role after invite time).
- Manage locations, rooms, and availability rules. The availability-rule API
  already existed; there's still no Settings UI for it (rules can only be
  created via a raw API call, same as practitioners were before this).
- Manage treatment catalogue entries.
- Manage consent templates and notification configuration.
- Restrict each section using server-enforced permissions (practitioners
  section already does — create/update require organization_admin or
  medical_director — but this needs to hold for every future section too).
- Audit permission and configuration changes.

### P2: Operational dashboard

The Dashboard currently contains introductory text only.

Acceptance criteria:

- Show upcoming appointments and schedule exceptions.
- Show pending and expired consent requests.
- Show submissions requiring medical review.
- Show notification failures and delivery status.
- Ensure every metric is organization-scoped.

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

### P1: Consent request lifecycle

Acceptance criteria:

- Resend, expire, revoke, and replace consent requests.
- Preserve lifecycle events and the reason for invalidation.
- Make links short-lived and single-use.
- Store only the token hash.
- Avoid leaking tokens through logs, analytics, or referrer headers.
- Provide clear expired, invalid, completed, and unavailable states in the
  patient application.

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

### P1: Connected public booking experience

The `/reservar` route exists but is not yet a complete booking workflow.

Acceptance criteria:

- Display only server-approved public treatment and availability information.
- Collect the minimum patient details required to request a booking.
- Prevent automated abuse with rate limiting and bot protection.
- Create a booking request or appointment according to clinic policy.
- Confirm the request without exposing private schedule or patient data.
- Trigger confirmation and consent workflows when appropriate.

### P2: Production landing-page content and SEO

Acceptance criteria:

- Final Spanish-language brand and service content.
- Accurate professional and treatment information.
- Page-specific titles, descriptions, canonical URLs, and social metadata.
- Sitemap, robots policy, structured data, and accessible navigation.
- Performance and responsive-layout review.
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

### P1: Generated TypeScript API contract

The API client package exists, but the OpenAPI schema and typed client are not
currently generated as part of normal development or CI.

Acceptance criteria:

- Generate TypeScript definitions from FastAPI OpenAPI.
- Provide a repeatable generation command.
- Fail CI when committed generated output is stale.
- Replace manually duplicated response interfaces where practical.
- Preserve public-consent and authenticated-staff client separation.

### P2: Shared UI, forms, and design system

The shared packages currently contain only a small initial set of utilities.

Acceptance criteria:

- Shared accessible form controls and validation presentation.
- Shared dialogs, data tables, status badges, date/time controls, and error
  states.
- Shared design tokens used consistently by all applications.
- Keep application-specific clinical workflows outside generic UI packages.

## 7. Authorization, audit, and security

### P0: Complete server-side authorization review

Some routes have role checks, but every operation needs an explicit policy.

Acceptance criteria:

- Define a permission matrix for every role and resource.
- Apply organization-boundary checks to all reads and writes.
- Add record-level rules such as assigned-practitioner access.
- Ensure reception roles cannot access or modify restricted clinical content.
- Restrict consent invalidation and eligibility overrides.
- Add automated authorization and cross-tenant isolation tests.
- Never depend on React route protection for security.

### P0: Audit coverage and integrity

The audit model and basic listing route exist, but audit recording is not yet
complete across the product.

Acceptance criteria:

- Record all important patient, clinical, consent, document, appointment,
  notification, and permission actions.
- Include actor, organization, resource, timestamp, request ID, trusted IP, user
  agent, and safe metadata.
- Keep audit events append-only.
- Implement and verify the intended previous-hash/event-hash chain.
- Restrict audit access and export.
- Define retention and integrity-monitoring policies.

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

### P1: Backend integration tests — auth tests now leave no permanent rows

Authentication now has HTTP-to-PostgreSQL integration tests for organization
registration, refresh rotation, logout, invites, and password-reset behavior.
They skip when no database is reachable. Availability has service-level tests
with mocked repositories.

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

- Run authentication tests against PostgreSQL in CI rather than allowing them to
  skip.
- Test all repositories and both upgrade/downgrade migration paths against
  PostgreSQL.
- Expand authentication coverage to permissions, session revocation, abuse
  cases, and cross-tenant isolation.
- Test appointment scheduling and status history.
- Add database-backed tests for availability rules, tenant isolation,
  practitioner conflicts, room conflicts, and timezone conversion.
- Test consent request concurrency, validation, eligibility, and immutability.
- Test outbox creation in the same transaction as domain changes.
- Test PDF creation, hashing, and document records.
- Test notification retries and callback idempotency.

### P1: End-to-end tests

Acceptance criteria:

- Staff login through appointment creation.
- Patient creation and medical-history update.
- Treatment-plan and session recording.
- Appointment-to-consent delivery.
- Mobile questionnaire, signature, and submission.
- Staff medical review and signed-document retrieval.
- Reminder cancellation after appointment cancellation or patient opt-out.

### P2: Performance and resilience tests

Acceptance criteria:

- Patient search and schedule-range performance.
- Concurrent single-use consent submissions.
- Queue backlog and provider outage behavior.
- Large PDF/signature/attachment limits.
- Database backup restoration and object-storage recovery.

### P2: CI completeness

Acceptance criteria:

- Python lint, format, tests, and migration checks.
- Frontend lint, type-check, tests, and builds.
- OpenAPI-client drift check.
- Dependency and image security scanning.
- Required checks documented for protected branches.

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
- Migrations run exactly once and failures are visible.
- API, worker, queue, and frontend health checks are available.
- Development credentials are clearly marked and cannot be reused in
  production.

### P1: Production deployment infrastructure

Acceptance criteria:

- Independently deploy API, worker, staff web, patient web, and landing page.
- Managed PostgreSQL and private object storage.
- Redis or alternative queue infrastructure with persistence appropriate to the
  retry strategy.
- HTTPS, DNS, CDN, load balancer, and trusted-proxy configuration.
- Environment-specific configuration and secret management.
- Zero- or low-downtime migration and rollback strategy.

### P1: Observability

Acceptance criteria:

- Correlated structured logs without medical content.
- Metrics for API latency/errors, database health, queue depth, outbox age,
  worker failures, notification delivery, and PDF generation.
- Distributed tracing or request correlation across API and worker.
- Alerts with documented operator actions.
- Health and readiness endpoints for deployable processes.

### P1: Backup, recovery, and retention

Acceptance criteria:

- Automated PostgreSQL backups and tested point-in-time recovery.
- Object-storage backup/versioning appropriate to signed records.
- Documented recovery-point and recovery-time objectives.
- Regular restoration tests.
- Retention schedules covering medical records, audit data, messages, and
  generated documents.
- Legally reviewed deletion and archival processes.

### P2: Migration and release discipline

Acceptance criteria:

- Validate Alembic migrations in CI against a clean database.
- Define backward-compatible deployment rules.
- Provide release notes and schema-change procedures.
- Prevent application startup against unsupported schema versions.

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
11. Complete audit coverage and the server authorization review.
12. Connect public booking and finalize landing/legal content.
13. Add integration and end-to-end test coverage.
14. Complete production infrastructure, observability, backup, recovery,
    security, and compliance reviews.

## Release warning

The existing implementation should be treated as an engineering foundation,
not as a production-ready system for real patient data. Legal requirements for
medical records, privacy, data retention, messaging consent, biometric
signatures, and electronic consent vary by jurisdiction and require review by
qualified security, medical, privacy, and legal professionals before launch.
