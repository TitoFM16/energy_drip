# MVP browser checks

The default Playwright suite runs the real API, PostgreSQL and three frontend apps. It needs no Redis, workers, messaging providers or hosted storage. Signed consent PDFs use private local storage during tests.

Use a **fresh dedicated E2E database**. The `public-mvp` project runs first and creates the only clinic, verifying owner service creation, image upload, pricing edits, direct worker creation, weekly availability, public slot booking, appointment rescheduling/cancellation and service archiving. It saves desktop and mobile screenshots in `test-results/` for visual review.

The dependent `chromium` project then creates isolated clinics for staff booking, patient records, schedule management and consent signing/review/document verification. Legacy clinical history, treatment-plan, contacts and fine-grained role UI specs are retained in source but excluded from the MVP gate because those screens are no longer part of the MVP navigation.

```sh
pnpm --filter @medical-platform/e2e install-browsers
pnpm test:e2e
```

Default app origins are API `:8000`, staff `:5173`, patient consent `:5174` and landing `:5175`. For an isolated stack, set `E2E_API_URL`, `E2E_STAFF_WEB_URL`, `E2E_PATIENT_WEB_URL` and `E2E_LANDING_URL`. Frontends must be built or started against the same API and the API's `PATIENT_WEB_BASE_URL` must match the consent app.

After a failed run, recreate only the dedicated test database before rerunning the public project. Do not reset a development or production database. To rerun a staff test against its own fresh fixture without the public setup project, use `--project=chromium --no-deps`.

Screenshots, videos and traces are saved for failures. Open a trace with:

```sh
pnpm --filter @medical-platform/e2e exec playwright show-trace test-results/<test-name>/trace.zip
```
