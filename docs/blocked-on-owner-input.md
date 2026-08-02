# Blocked on your input

A running list of everything in [`missing_features.md`](missing_features.md)
that isn't blocked on engineering time — it's blocked on a decision, an
account, or a review only the clinic owner (or their counsel) can do. Check
items off as you close them out; ask me to update this file if something
here turns out to already be resolved or the plan changes.

## 1. WhatsApp / Meta Business setup

**What's needed**: a Meta Business Account and app, message templates
submitted for approval, and the delivery-status webhook registered.

**Why it's yours**: only someone with access to the clinic's real Meta
Business Account can create it, submit templates for review, and register a
production webhook URL. Nothing in the codebase is blocked waiting on this —
the WhatsApp client already fails safely when unconfigured — but no message
can actually send or be tracked until it's done.

**Where**: full step-by-step runbook in
[`whatsapp-setup.md`](whatsapp-setup.md), including the exact credentials →
environment-variable mapping and the four message templates that need
approval.

- [ ] Meta Business Account + app created
- [ ] `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET`,
      `WHATSAPP_WEBHOOK_VERIFY_TOKEN` set in the real deployment's env
- [ ] All 4 templates (`appointment_confirmation`,
      `appointment_reminder_24h`, `appointment_reminder_2h`,
      `consent_link`) submitted and approved
- [ ] Webhook registered against the real production URL

## 2. Where this actually runs (hosting + managed database)

**What's needed**: a decision on a hosting target — a cloud provider (AWS,
GCP, Azure), a PaaS (Fly.io, Render, Railway), or a single VPS — and a
managed PostgreSQL provider (or self-managed, if that's the call).

**Why it's yours**: this is a real infrastructure/cost decision. Building
Terraform or deployment config against a guessed provider would likely be
throwaway work, and provisioning real paid cloud resources isn't something
to do without you choosing the target first.

**What's downstream of this decision** (see "Production deployment
infrastructure" in `missing_features.md`):

- [ ] Hosting target chosen
- [ ] Managed Postgres provider chosen (unlocks automated backups + PITR —
      see `backup-and-recovery.md`)
- [ ] Independent deploys for API, worker, staff-web, patient-web, landing
- [ ] Private object storage (replacing local MinIO)
- [ ] HTTPS, DNS, CDN, load balancer, trusted-proxy config
- [ ] Secret management for the real environment
- [ ] Zero/low-downtime migration and rollback strategy

## 3. Legal and privacy review

**What's needed**: qualified legal counsel (in whatever jurisdiction(s) the
clinic operates) to review and approve the actual legal content, and to set
retention/deletion policy for medical records.

**Why it's yours**: this is explicitly not an engineering decision. The
existing `/terminos`, `/politica-de-privacidad`, and
`/seguridad-y-privacidad` pages on the landing site are placeholders — real
ones need review before any real patient uses this product.

- [ ] Terms of service approved
- [ ] Privacy policy approved
- [ ] Cookie/analytics policy (if applicable)
- [ ] Patient data processing, retention, and rights language approved
- [ ] Electronic-signature/consent language reviewed by counsel
- [ ] Retention and deletion schedule defined (medical records, audit data,
      messages, generated documents/PDFs) — see "Backup, recovery, and
      retention" in `missing_features.md` and `backup-and-recovery.md`

## 4. Real landing-page content

**What's needed**: final Spanish-language brand copy, accurate
professional/treatment information, and photos/assets — whatever the
clinic actually wants public.

**Why it's yours**: this is brand/marketing content, not something to
invent. The current landing site's copy was written to get the site
structurally complete, not as final public-facing content.

- [ ] Final service/treatment copy
- [ ] Practitioner bios/photos
- [ ] SEO metadata decisions (what the clinic wants to rank for)
- [ ] Content ownership — who updates this after launch

## 5. Monitoring/alerting backend

**What's needed**: a choice of where metrics and alerts actually go —
Prometheus+Grafana (self-hosted or managed), Datadog, CloudWatch, or
something else.

**Why it's yours**: usually tied to the hosting decision above (some
providers bundle this), and often has its own cost. Building a `/metrics`
endpoint with nothing scraping it isn't useful yet — structured, correlated
logs already exist as a stopgap (see "Observability" in
`missing_features.md`).

- [ ] Monitoring backend chosen
- [ ] Alert routing chosen (PagerDuty, Opsgenie, a monitored Slack webhook,
      etc.) and documented operator actions per alert

## 6. GitHub branch protection

**What's needed**: a decision to require the `backend` and `frontend` CI
jobs (see `.github/workflows/ci.yml`) as required status checks on `main`.

**Why it's yours**: this is a repository setting that changes what's
required to merge — I didn't change it without asking, since it affects
your (and Codex's) ability to push/merge.

- [ ] Decide whether to require `backend` + `frontend` CI jobs on `main`
- [ ] Configure it in GitHub repo settings (or tell me to, if you'd rather I
      did it once you've decided)
