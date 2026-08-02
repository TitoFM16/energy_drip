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

- Deliver invite and password-reset tokens out of band (WhatsApp/SMS/email)
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

### P1: Reference and demonstration data

Local development needs repeatable data for appointments, patients, treatment
definitions, consent templates, and notification workflows.

Acceptance criteria:

- Provide an idempotent development seed command.
- Clearly separate demonstration data from production bootstrap data.
- Include at least one usable consent template version and eligibility rule set.
- Include representative staff roles and clinic resources.

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

### P1: Patient management

The Patients screen currently lists basic patient data but lacks the complete
record-management experience.

Acceptance criteria:

- Search, pagination, creation, editing, and patient detail screens.
- Contact details and emergency contacts.
- Medical history, allergies, conditions, and medications.
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

### P1: Treatment catalogue, plans, and session workflow

Backend primitives exist, while the staff Treatments screen is still largely
descriptive.

Acceptance criteria:

- Manage treatment definitions and their active/inactive state.
- Create and update patient treatment plans.
- Schedule and record individual treatment sessions.
- Record formulas, dosages or parameters, clinical evolution, attachments, and
  personalized follow-ups.
- Link appointments to plans and sessions without treating them as the same
  entity.
- Finalize sessions and preserve their history.
- Provide patient-level treatment history and plan progress.

### P1: Consent review workspace

The staff Consent screen needs to become an operational review queue.

Acceptance criteria:

- List pending, expired, completed, invalidated, and failed consent requests.
- Filter by patient, appointment, treatment, eligibility result, and date.
- Clearly surface `requires_manual_review` and `not_eligible` results.
- Allow authorized professionals to record a review decision and rationale.
- Display the exact template version, questions, answers, signature, metadata,
  and generated document.
- Prevent the eligibility engine from being presented as an autonomous medical
  diagnosis.

### P1: Settings administration

The Settings screen is currently a placeholder.

Acceptance criteria:

- Manage users and role assignments.
- Manage locations, rooms, practitioners, and availability rules. The
  practitioner CRUD API now exists (`/api/v1/practitioners`) and the
  availability-rule API already existed; neither has a Settings UI yet.
- Manage treatment catalogue entries.
- Manage consent templates and notification configuration.
- Restrict each section using server-enforced permissions.
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

### P0: Consent-template administration and publishing

The data model supports versioned templates, questions, options, and rules, but
there is no complete management workflow.

Acceptance criteria:

- Create drafts containing consent text, questions, options, and eligibility
  rules.
- Validate field keys, required questions, rule references, and result values.
- Preview the exact mobile experience before publishing.
- Publish immutable versions.
- Never modify a version referenced by an existing consent request.
- Retire a template without invalidating historical submissions.

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

### P0: Real SMS provider integration

The current SMS client calls an example domain and is not connected to a real
provider.

Acceptance criteria:

- Select and integrate a production SMS provider.
- Store provider credentials outside source control.
- Normalize recipient numbers.
- Map provider IDs and errors to internal notification records.
- Implement retries only for retryable failures.
- Provide a development or sandbox adapter.

### P0: WhatsApp production configuration

Acceptance criteria:

- Configure the WhatsApp Business account and approved templates.
- Validate template names, locales, and parameter ordering.
- Store tokens securely and support rotation.
- Handle provider rate limits and retryable errors.
- Provide safe development behavior when credentials are absent.

### P1: Delivery callbacks and message-state reconciliation

Acceptance criteria:

- Authenticated webhook endpoints for WhatsApp and the selected SMS provider.
- Verify webhook signatures or provider authentication.
- Process duplicate and out-of-order callbacks idempotently.
- Track queued, accepted, sent, delivered, failed, and undeliverable states.
- Preserve provider message IDs and normalized failure reasons.
- Audit meaningful delivery events without logging medical content.

### P1: Automated reminder scheduling

Reminder actors exist, but an external scheduler must invoke them.

Acceptance criteria:

- Schedule reminder scans reliably in every deployed environment.
- Send confirmation, consent link, 24-hour reminder, and 2-hour reminder
  according to clinic policy.
- Re-check appointment and consent state immediately before sending.
- Avoid duplicate reminders across retries and multiple workers.
- Respect appointment rescheduling and cancellation.
- Make reminder windows and templates organization-configurable.

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
- Process SMS and WhatsApp opt-out signals.
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

### P0: Repair the root Python test command

Combined `pytest` discovery currently fails because the API and worker both
define a top-level `tests` package.

Acceptance criteria:

- `uv run pytest` succeeds from the repository root.
- API and worker tests can also run independently.
- CI uses the same supported command as local development.

### P0: Add frontend tests and repair `make test`

All frontend projects currently return an error because Vitest finds no test
files.

Acceptance criteria:

- Add unit/component tests for each frontend application, or explicitly
  configure projects without tests to pass until tests are added.
- Test staff authentication and API error handling.
- Test dynamic consent fields, required values, signature behavior, submission,
  and expired tokens.
- Test important landing-page and booking interactions.
- Make `pnpm test` and `make test` pass.

### P1: Backend integration tests

Authentication now has HTTP-to-PostgreSQL integration tests for organization
registration, refresh rotation, logout, invites, and password-reset behavior.
They skip when no database is reachable. Availability has service-level tests
with mocked repositories. The remaining integration coverage is:

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

### P0: Verify and harden the Docker development stack

The Compose and Dockerfile setup exists but needs a repeatable end-to-end
verification.

Acceptance criteria:

- Fresh checkout can build and start every service.
- Migrations run exactly once and failures are visible.
- MinIO bucket initialization is automatic.
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

1. Repair root tests and preserve green quality gates.
2. ~~Lock the product down to a single, operator-bootstrapped clinic~~ Done —
   see "Product scope correction". Still open from this item: seed the
   standard role catalogue and add development reference data.
3. ~~Complete staff login, refresh, logout, and authenticated API requests.~~
   ~~Still open: invite-acceptance and password-reset screens.~~ All done,
   including the org-ID-free login screen. Still open: out-of-band token
   delivery (see "Staff authentication experience").
4. Finish patient and medical-history management.
5. ~~Connect the Agenda UI to the new availability APIs~~ Done — day view,
   booking, and status changes are live. Still open from this item: the
   Settings UI for the practitioner API, week view, editing/rescheduling, and
   room-conflict/exception/timezone validation (see "Appointment
   management").
6. Finish treatment plans, sessions, formulas, evolution, and follow-ups.
7. Add consent-template publishing and strict submission validation.
8. Build the staff consent-review and signed-document workflow.
9. Configure private, versioned object storage and document verification.
10. Connect real WhatsApp and SMS providers, callbacks, and reminder scheduling.
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
