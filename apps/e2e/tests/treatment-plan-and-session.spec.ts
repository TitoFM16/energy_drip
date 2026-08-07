import { expect, test } from '@playwright/test';
import { bootstrapClinic, createPatient } from './support/api-setup';
import { STAFF_WEB_URL } from './support/urls';

test('practitioner creates a treatment plan and records a session with clinical evolution notes', async ({
  page,
}) => {
  const clinic = await bootstrapClinic();
  const patient = await createPatient(clinic.adminToken, {
    first_name: 'Laura',
    last_name: 'Mendoza',
  });

  // create_treatment_plan and record_treatment_session both require the
  // practitioner/medical_director role — organization_admin alone can't
  // do either (see require_roles in scheduling/treatments routers), so
  // this has to log in as the practitioner, not the admin.
  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.practitionerEmail);
  await page.getByLabel('Contraseña').fill(clinic.practitionerPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);

  await page.goto(`${STAFF_WEB_URL}/patients/${patient.id}`);
  await expect(page.getByRole('heading', { name: 'Laura Mendoza' })).toBeVisible();

  await page.getByLabel('Tratamiento').selectOption({ label: 'Limpieza facial E2E' });
  await page.getByLabel('Notas').fill('Primera valoración, piel sensible.');
  await page.getByRole('button', { name: 'Nuevo plan' }).click();

  const planButton = page.getByRole('button', { name: /Limpieza facial E2E/ });
  await expect(planButton).toBeVisible({ timeout: 10_000 });
  await planButton.click();

  // Newly-created plans default to 'active', which is what makes the
  // "record a session" form appear at all (see PlanDetail's status check).
  await page.getByLabel('Profesional').selectOption({ label: 'E2E Practitioner' });
  await page.getByLabel('Evolución clínica').fill('Buena tolerancia, sin reacciones adversas.');
  await page.getByRole('button', { name: 'Registrar sesión' }).click();

  await expect(page.getByText('Sesión 1')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText('Buena tolerancia, sin reacciones adversas.')).toBeVisible();
});
