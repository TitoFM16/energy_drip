import { expect, test } from '@playwright/test';
import {
  bootstrapClinic,
  createConsentRequest,
  createPatient,
  submitConsentForm,
} from './support/api-setup';
import { STAFF_WEB_URL } from './support/urls';

test('practitioner records a final decision for a consent requiring review', async ({ page }) => {
  const clinic = await bootstrapClinic();
  const patient = await createPatient(clinic.adminToken, {
    first_name: 'Laura',
    last_name: 'Decision',
  });
  const consentRequest = await createConsentRequest(
    clinic.adminToken,
    patient.id,
    clinic.publishedConsentTemplateVersionId,
  );
  await submitConsentForm(consentRequest.token);

  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.practitionerEmail);
  await page.getByLabel('Contraseña').fill(clinic.practitionerPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);

  await page.goto(`${STAFF_WEB_URL}/consents`);
  const requestButton = page.locator('button').filter({ hasText: 'Laura Decision' });
  await expect(requestButton).toBeVisible({ timeout: 10_000 });
  await requestButton.click();

  await expect(page.getByText('Requiere revisión médica')).toBeVisible({ timeout: 10_000 });
  await page.getByLabel('Decisión').selectOption('approved');
  await page.getByLabel('Justificación clínica').fill('Sin contraindicación clínica identificada.');
  await page.getByRole('button', { name: 'Registrar decisión' }).click();

  await expect(page.getByText('Aprobado', { exact: true })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText('Sin contraindicación clínica identificada.')).toBeVisible();
  await expect(page.getByText(/Revisado por E2E Practitioner/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Registrar decisión' })).toHaveCount(0);

  await page.reload();
  await page.locator('button').filter({ hasText: 'Laura Decision' }).click();
  await expect(page.getByText('Aprobado', { exact: true })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText('Sin contraindicación clínica identificada.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Registrar decisión' })).toHaveCount(0);
});
