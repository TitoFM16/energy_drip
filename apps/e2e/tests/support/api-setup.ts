import type { Schemas } from '@medical-platform/api-client';
import { API_URL } from './urls';

/**
 * Creates fresh, isolated test data for one test run by calling the real
 * API directly (register-organization, invites, practitioners,
 * availability, treatments, consent templates) — the same endpoints
 * apps/api/scripts/seed_reference_data.py uses, just driven from the test
 * itself so each test run gets its own organization instead of depending
 * on whatever's already in the shared dev database (which has ~200
 * leftover throwaway orgs from local development — see
 * docs/missing_features.md's "Reference and demonstration data").
 *
 * Request/response shapes come from @medical-platform/api-client's
 * generated Schemas — same reason the frontend apps use them: a real
 * response-shape change here shows up as a type error, not a runtime
 * surprise mid-test-run.
 *
 * register-organization is only reachable when the API isn't running with
 * ENVIRONMENT=production (see apps/api/src/medical_api/modules/identity/router.py) —
 * exactly the case for the local/CI Docker Compose stack these tests run
 * against.
 */

async function api<T>(path: string, init?: RequestInit & { token?: string }): Promise<T> {
  const { token, ...rest } = init ?? {};
  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...rest.headers,
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${init?.method ?? 'GET'} ${path} failed (${response.status}): ${body}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface ClinicFixture {
  organizationId: string;
  adminEmail: string;
  adminPassword: string;
  adminToken: string;
  practitionerEmail: string;
  practitionerPassword: string;
  practitionerToken: string;
  practitionerUserId: string;
  practitionerId: string;
  treatmentDefinitionId: string;
  publishedConsentTemplateVersionId: string;
}

function unique(label: string): string {
  return `${label}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export async function bootstrapClinic(): Promise<ClinicFixture> {
  const orgName = unique('E2E Clinic');
  const adminEmail = `${unique('admin')}@example.com`;
  const adminPassword = 'e2e-supersecret123';

  const registerBody: Schemas['RegisterOrganizationRequest'] = {
    organization_name: orgName,
    admin_email: adminEmail,
    admin_password: adminPassword,
    admin_full_name: 'E2E Admin',
  };
  const org = await api<Schemas['RegisterOrganizationResponse']>(
    '/api/v1/auth/register-organization',
    { method: 'POST', body: JSON.stringify(registerBody) },
  );
  const adminToken = org.access_token;

  const practitionerEmail = `${unique('practitioner')}@example.com`;
  const practitionerPassword = 'e2e-supersecret123';
  const inviteBody: Schemas['InviteCreate'] = {
    email: practitionerEmail,
    role: 'practitioner',
  };
  const invite = await api<Schemas['InviteCreateResponse']>('/api/v1/auth/invites', {
    method: 'POST',
    token: adminToken,
    body: JSON.stringify(inviteBody),
  });
  const acceptBody: Schemas['InviteAcceptRequest'] = {
    full_name: 'E2E Practitioner',
    password: practitionerPassword,
  };
  const practitionerAuth = await api<Schemas['TokenResponse']>(
    `/api/v1/auth/invites/${invite.token}/accept`,
    { method: 'POST', body: JSON.stringify(acceptBody) },
  );
  const practitionerToken = practitionerAuth.access_token;

  const me = await api<Schemas['UserRead']>('/api/v1/auth/me', { token: practitionerToken });
  const practitionerUserId = me.id;

  const practitionerBody: Schemas['PractitionerCreate'] = {
    user_id: practitionerUserId,
    specialty: 'Dermatología',
  };
  const practitioner = await api<Schemas['PractitionerRead']>('/api/v1/practitioners', {
    method: 'POST',
    token: adminToken,
    body: JSON.stringify(practitionerBody),
  });

  // Every weekday, nearly the full 24 hours — rule times are interpreted
  // as UTC directly (see AvailabilityService's docstring), and slots in
  // the past relative to "now" don't show up, so the test suite shouldn't
  // have to care what day *or time* it happens to run at.
  for (let weekday = 0; weekday <= 6; weekday += 1) {
    const ruleBody: Schemas['AvailabilityRuleCreate'] = {
      practitioner_id: practitioner.id,
      weekday,
      start_time: '00:00:00',
      end_time: '23:45:00',
    };
    await api('/api/v1/appointments/availability-rules', {
      method: 'POST',
      token: adminToken,
      body: JSON.stringify(ruleBody),
    });
  }

  const treatmentBody: Schemas['TreatmentDefinitionCreate'] = {
    name: 'Limpieza facial E2E',
    description: 'Tratamiento de prueba end-to-end',
    default_session_count: 1,
  };
  const treatmentDefinition = await api<Schemas['TreatmentDefinitionRead']>(
    '/api/v1/treatments/definitions',
    { method: 'POST', token: adminToken, body: JSON.stringify(treatmentBody) },
  );

  const templateBody: Schemas['ConsentTemplateCreate'] = {
    name: 'Consentimiento E2E',
    body_markdown: 'Consiento el tratamiento descrito para fines de prueba automatizada.',
    questions: [
      {
        field_key: 'is_pregnant',
        prompt: '¿Estás embarazada?',
        question_type: 'boolean',
        display_order: 0,
        is_required: true,
        options: [],
      },
    ],
  };
  const template = await api<Schemas['ConsentTemplateRead']>('/api/v1/consents/templates', {
    method: 'POST',
    token: adminToken,
    body: JSON.stringify(templateBody),
  });
  const versionId = template.latest_version!.id;
  await api(`/api/v1/consents/templates/${template.id}/versions/${versionId}/publish`, {
    method: 'POST',
    token: adminToken,
  });

  return {
    organizationId: org.organization_id,
    adminEmail,
    adminPassword,
    adminToken,
    practitionerEmail,
    practitionerPassword,
    practitionerToken,
    practitionerUserId,
    practitionerId: practitioner.id,
    treatmentDefinitionId: treatmentDefinition.id,
    publishedConsentTemplateVersionId: versionId,
  };
}

export async function createPatient(
  adminToken: string,
  overrides: Partial<
    Pick<Schemas['PatientCreate'], 'first_name' | 'last_name' | 'phone_number'>
  > = {},
): Promise<Schemas['PatientRead']> {
  const body: Schemas['PatientCreate'] = {
    first_name: overrides.first_name ?? 'Paciente',
    last_name: overrides.last_name ?? unique('E2E'),
    phone_number: overrides.phone_number ?? '+573000000000',
  };
  return api('/api/v1/patients', { method: 'POST', token: adminToken, body: JSON.stringify(body) });
}

export async function createConsentRequest(
  adminToken: string,
  patientId: string,
  templateVersionId: string,
): Promise<{ consent_request_id: string; token: string }> {
  const params = new URLSearchParams({
    patient_id: patientId,
    template_version_id: templateVersionId,
  });
  return api(`/api/v1/consents/requests?${params.toString()}`, {
    method: 'POST',
    token: adminToken,
  });
}

// Drives the same public, token-based endpoints patient-web's real
// questionnaire/signature UI calls (see consent-flow.spec.ts for the full
// UI-driven version) — used when a test only cares about what happens
// *after* a real submission exists (e.g. the staff-side document
// actions), so it doesn't need to re-walk the patient UI just for setup.
export async function submitConsentForm(token: string): Promise<{ submission_id: string }> {
  const form = await api<Schemas['ConsentFormRead']>(`/api/v1/public/consents/${token}`);
  const answers = form.questions.map((question) => ({
    question_id: question.id,
    field_key: question.field_key,
    value: false,
  }));
  return api(`/api/v1/public/consents/${token}/submit`, {
    method: 'POST',
    body: JSON.stringify({ answers, signature_svg: '<svg></svg>', timezone: 'America/Bogota' }),
  });
}
