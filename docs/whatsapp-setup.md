# WhatsApp production setup (operator runbook)

The code side of WhatsApp is done — see "Notification automation" and
"Delivery callbacks and message-state reconciliation" in
[`missing_features.md`](missing_features.md). Everything below is
account/configuration work in Meta's own dashboards that only a human with
access to the clinic's Meta Business Account can do; nothing in this
codebase is blocked waiting on it, but no message can actually be _sent_ or
tracked until it's done.

This product calls Meta's WhatsApp Business Cloud API directly — no BSP
(Twilio, 360dialog, etc.) — so there's no middleman markup on top of Meta's
own per-conversation pricing, but every step below happens in Meta's own
tools.

## 1. Meta Business Account and app

1. Create (or use an existing) [Meta Business
   Account](https://business.facebook.com/) for the clinic.
2. In [Meta for Developers](https://developers.facebook.com/apps/), create a
   new app → type **Business** → add the **WhatsApp** product.
3. Meta gives you a free **test phone number** and a **test recipient list**
   immediately — good enough to verify the whole pipeline end to end before
   touching real patient numbers. A real business phone number (able to
   message anyone) requires business verification, which Meta can take a
   few days to review — start that early if there's a launch date.

## 2. Credentials → environment variables

Everything below maps directly to `Settings` in
`apps/api/src/medical_api/core/config.py` / `.env.example`:

| Env var                         | Where to find it in Meta's dashboard                                                                                                                                                                                                                                                                             |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `WHATSAPP_API_TOKEN`            | **System Users** (Business Settings → Users → System Users) → create a system user with admin access to the WhatsApp app → generate a **permanent token**. Don't use the 24-hour temporary token shown on the app's WhatsApp → Getting Started page — it expires and every send would start failing a day later. |
| `WHATSAPP_PHONE_NUMBER_ID`      | WhatsApp → API Setup (or Business Settings → Accounts → WhatsApp Accounts → your number) — a numeric ID, not the phone number itself.                                                                                                                                                                            |
| `WHATSAPP_APP_SECRET`           | App Dashboard → Settings → Basic → "App Secret" (click "Show"). This is **not** the API token — it's used only to verify the delivery-status webhook's signature, never sent to Meta.                                                                                                                            |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | Not from Meta — **you make this up**. Any random string works (e.g. `openssl rand -hex 32`). Put the same value in both this env var and Meta's webhook registration form (step 4) — Meta echoes it back on the verification handshake so the app can confirm the registration attempt is really authorized.     |

Set these in whatever `.env`/secret store the deployment actually reads —
for the Docker Compose dev stack, they're read from the host shell
environment (`${WHATSAPP_API_TOKEN:-}` etc. in `docker-compose.yml`), so
`export`-ing them before `docker compose up` is enough locally.

One more setting, unrelated to Meta but easy to miss: `PATIENT_WEB_BASE_URL`
(default `http://localhost:5174`) is what the `consent_link` template's
link actually points at — `apps/worker/src/medical_worker/workflows/consent_request.py`
builds the link as `{PATIENT_WEB_BASE_URL}/c/{token}`. Set it to the real
patient-web production domain, or every consent link sent to a real patient
will point at localhost.

## 3. Message templates

Meta requires every business-initiated message to use a pre-approved
**template** — free-form text only works as a _reply_ within 24 hours of
the patient last messaging the clinic. This codebase sends exactly four
templates today (see `apps/worker/src/medical_worker/workflows/`); create
and submit all four for approval in WhatsApp Manager → Message Templates
before anything can send:

| Template name              | Category | Params (in order)                                                     | Used by                                                 |
| -------------------------- | -------- | --------------------------------------------------------------------- | ------------------------------------------------------- |
| `appointment_confirmation` | Utility  | `{{1}}` patient first name, `{{2}}` appointment start time (ISO 8601) | `appointment_confirmation.py`, sent right after booking |
| `appointment_reminder_24h` | Utility  | `{{1}}` patient first name, `{{2}}` appointment start time (ISO 8601) | `appointment_reminders.py`, ~24h before                 |
| `appointment_reminder_2h`  | Utility  | `{{1}}` patient first name, `{{2}}` appointment start time (ISO 8601) | `appointment_reminders.py`, ~2h before                  |
| `consent_link`             | Utility  | `{{1}}` patient first name, `{{2}}` consent form link                 | `consent_request.py`, sent right after booking          |

All four are submitted to Meta with **language: Spanish (`es`)** — the
client hardcodes `language.code: "es"` in
`apps/api/src/medical_api/integrations/whatsapp/client.py`; if the clinic
ever needs another language, that's a code change too, not just a template
submission.

Template approval is manual review by Meta and can take anywhere from a
few minutes to ~24–48 hours — don't leave this until launch day. If a
template gets rejected, the client will raise `WhatsAppRejectedError` for
every send attempt (logged as `whatsapp.send_failed_permanently`, no
retries) until it's fixed and re-approved.

The appointment-time param is currently sent as a raw ISO 8601 string
(e.g. `2026-08-15T14:30:00+00:00`) — readable enough for a template body
like _"Tu cita es el {{2}}"_, but not pretty. Formatting it nicer (e.g.
`15 de agosto, 2:30 p.m.`) is a small follow-up worth doing once templates
are live and you can see how it actually renders on a phone.

## 4. Register the delivery-status webhook

The webhook endpoint (`GET`/`POST /api/v1/webhooks/whatsapp`) already
exists and is verified working (see `missing_features.md`) — this step is
just telling Meta where it is.

1. The URL **must be publicly reachable over HTTPS** — Meta will not call
   `http://localhost:8000`. For a real deployment this is just the
   production domain; for testing against a local stack before that
   exists, tunnel it (e.g. `ngrok http 8000`) and use the tunnel's HTTPS
   URL.
2. In the app's WhatsApp → Configuration page, set:
   - **Callback URL**: `https://<your-domain>/api/v1/webhooks/whatsapp`
   - **Verify token**: the same string you put in
     `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
3. Click **Verify and Save** — Meta immediately sends the `GET` handshake;
   if the URL and token are right, this succeeds instantly (already tested
   against this exact endpoint this session — see `missing_features.md`).
4. Subscribe to the **`messages`** webhook field (this is what carries
   delivery-status updates — sent/delivered/read/failed). Other fields
   exist (e.g. account alerts) but nothing in this codebase consumes them
   yet.

## 5. End-to-end verification checklist

Once the above is done, confirm the whole pipeline for real (not just the
pieces already verified with synthetic data this session):

- [ ] Book a test appointment for a patient whose phone number is on the
      test number's approved recipient list (or use the real business
      number once verified) and confirm the WhatsApp confirmation message
      actually arrives on the phone.
- [ ] Confirm the corresponding `NotificationMessage` row's `status`
      progresses from `sent` → `delivered` (`GET /api/v1/notifications` as
      a staff user, or query the table directly) once Meta calls back the
      webhook — this closes the loop this session only tested with a
      manually-inserted row and a hand-crafted webhook payload.
- [ ] Trigger the consent-link flow and confirm the link in the received
      message actually opens the real patient-web consent form.
- [ ] Deliberately let a template send fail (e.g. temporarily revoke the
      token) and confirm it shows up as `whatsapp.send_failed_permanently`
      in the worker's logs rather than retrying silently forever.

## Known gaps once this is live

Not blocking the above, but worth knowing about (see `missing_features.md`
for full detail):

- No template param validation before sending — a mismatched param count
  or a typo'd template name only surfaces at send time as a
  `WhatsAppRejectedError`, not earlier.
