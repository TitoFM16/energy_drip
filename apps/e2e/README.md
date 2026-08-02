# End-to-end tests

Playwright tests that exercise real cross-app user journeys against the
full Docker Compose stack — the same nine services (Postgres, Redis, MinIO,
the API, both worker processes, and all three frontend apps) local
development already runs, not a mocked or partial environment.

## Why this exists

Every other test in this repo (`apps/api/tests`, `apps/worker/tests`, each
frontend app's `vitest` suite) tests one layer in isolation. Nothing
automated verified that, say, a staff member creating a consent request in
staff-web actually produces a link a patient can complete in patient-web,
and that the result shows back up correctly in staff-web — that kind of
cross-service flow had only ever been checked by hand, in a browser, once
per feature, during development. These tests automate exactly that.

## Running locally

```sh
# From the repo root — brings up the full stack.
docker compose up -d

# One-time, or after a Playwright version bump.
pnpm --filter @medical-platform/e2e install-browsers

# Run everything.
pnpm --filter @medical-platform/e2e test:e2e

# Interactive UI mode — much easier for writing/debugging a new test.
pnpm --filter @medical-platform/e2e test:e2e:ui

# One file.
pnpm --filter @medical-platform/e2e exec playwright test tests/consent-flow.spec.ts
```

Each test is fully self-contained: `tests/support/api-setup.ts` registers a
fresh organization, practitioner, treatment, and published consent template
directly against the API before the test touches a browser at all — no
dependency on `make seed` or any other pre-existing data, and no shared
state between tests (each gets its own organization). This is deliberate:
the shared local dev Postgres already accumulates leftover data across
sessions (see "Reference and demonstration data" in
`docs/missing_features.md`), and these tests need to stay green regardless
of what's already in that database.

## What's covered

- `staff-appointment-booking.spec.ts` — staff logs in for real (the actual
  login form, not a token injected into storage), books an available
  slot for a patient, confirms it shows up on the agenda.
- `consent-flow.spec.ts` — the full patient-facing consent flow (medical
  questionnaire, treatment information, hand-drawn signature capture,
  review, submit) driven from patient-web using a real single-use token,
  then confirmed from the staff-web review screen. The single highest-value
  flow in the product: it's the one place all three of API, worker (PDF
  generation is enqueued but not currently awaited by this test), and two
  separate frontend apps have to agree with each other.
- `public-booking.spec.ts` — the public, unauthenticated `/reservar` form
  on the landing site.

Not covered yet: PDF generation/signed-document retrieval, WhatsApp
delivery (nothing to assert against without real Meta credentials — see
`docs/whatsapp-setup.md`), and reminder/missed-appointment scheduling
(these run on a 5-minute interval in the worker, not something a test
should wait around for). See "End-to-end tests" in
`docs/missing_features.md` for the full remaining checklist.

## Debugging a failure

Playwright writes a screenshot, video, and trace for every failed test to
`test-results/` (gitignored). Open the trace with:

```sh
pnpm --filter @medical-platform/e2e exec playwright show-trace test-results/<test-name>/trace.zip
```
