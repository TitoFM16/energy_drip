import { expect, test } from '@playwright/test';
import { bootstrapClinic, createConsentRequest, createPatient } from './support/api-setup';
import { PATIENT_WEB_URL, STAFF_WEB_URL } from './support/urls';

test('staff revokes and resends a consent request, patient sees a clear state for each', async ({
  page,
}) => {
  const clinic = await bootstrapClinic();
  const patient = await createPatient(clinic.adminToken, {
    first_name: 'Diego',
    last_name: 'Lifecycle',
  });
  const { token } = await createConsentRequest(
    clinic.adminToken,
    patient.id,
    clinic.publishedConsentTemplateVersionId,
  );

  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.adminEmail);
  await page.getByLabel('Contraseña').fill(clinic.adminPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);

  await page.goto(`${STAFF_WEB_URL}/patients/${patient.id}`);
  const pendingRow = page.locator('li', { hasText: 'Pendiente' });
  await expect(pendingRow).toBeVisible({ timeout: 10_000 });

  await pendingRow.getByRole('button', { name: 'Revocar' }).click();
  await pendingRow.getByPlaceholder('Motivo de la revocación').fill('Cita reprogramada');
  await pendingRow.getByRole('button', { name: 'Confirmar revocación' }).click();

  await expect(page.locator('li', { hasText: 'Invalidado' })).toBeVisible({ timeout: 10_000 });
  await expect(page.locator('li', { hasText: 'Pendiente' })).toHaveCount(0);

  // The revoked link must show a clear, specific "no longer available"
  // state to the patient — not a generic error.
  await page.goto(`${PATIENT_WEB_URL}/c/${token}`);
  await expect(page.getByText('Este enlace ya no está disponible.')).toBeVisible();

  // Create a second, fresh request and resend it — the original gets
  // superseded (also ends up Invalidado) and a new Pendiente request with
  // a new link takes its place.
  const second = await createConsentRequest(
    clinic.adminToken,
    patient.id,
    clinic.publishedConsentTemplateVersionId,
  );
  await page.goto(`${STAFF_WEB_URL}/patients/${patient.id}`);
  const secondPendingRow = page.locator('li', { hasText: 'Pendiente' });
  await expect(secondPendingRow).toBeVisible({ timeout: 10_000 });
  await secondPendingRow.getByRole('button', { name: 'Reenviar' }).click();

  await expect(page.locator('li', { hasText: 'Invalidado' })).toHaveCount(2, { timeout: 10_000 });
  const newLinkCallout = page.getByText(/nuevo enlace de consentimiento/);
  await expect(newLinkCallout).toBeVisible({ timeout: 10_000 });
  const newLinkText = await page.locator('code').first().textContent();
  const newToken = newLinkText?.split('/c/')[1];
  expect(newToken).toBeTruthy();
  expect(newToken).not.toBe(second.token);

  await page.goto(`${PATIENT_WEB_URL}/c/${newToken}`);
  await expect(page.getByRole('heading', { name: 'Antes de tu cita' })).toBeVisible();

  // The superseded original link is dead now too.
  await page.goto(`${PATIENT_WEB_URL}/c/${second.token}`);
  await expect(page.getByText('Este enlace ya no está disponible.')).toBeVisible();
});
