import { expect, test } from '@playwright/test';
import { bootstrapClinic, createConsentRequest, createPatient } from './support/api-setup';
import { PATIENT_WEB_URL, STAFF_WEB_URL } from './support/urls';

test('patient completes the consent flow and staff sees it reviewed', async ({ page }) => {
  const clinic = await bootstrapClinic();
  const patient = await createPatient(clinic.adminToken, {
    first_name: 'Camila',
    last_name: 'Suárez',
  });
  const { token } = await createConsentRequest(
    clinic.adminToken,
    patient.id,
    clinic.publishedConsentTemplateVersionId,
  );

  // --- Patient side: the actual single-use link a real patient gets over
  // WhatsApp. No auth — the token in the URL is the only credential. ---
  await page.goto(`${PATIENT_WEB_URL}/c/${token}`);
  await expect(page.getByRole('heading', { name: 'Antes de tu cita' })).toBeVisible();
  await page.getByRole('button', { name: 'Comenzar' }).click();

  await expect(page.getByRole('heading', { name: 'Filtro médico' })).toBeVisible();
  await expect(page.getByText('¿Estás embarazada?')).toBeVisible();
  // The E2E template has exactly one question, so this "No" is unambiguous.
  await page.getByRole('button', { name: 'No', exact: true }).click();
  await page.getByRole('button', { name: 'Continuar' }).click();

  await expect(page.getByRole('heading', { name: 'Consentimiento informado' })).toBeVisible();
  await page.getByRole('button', { name: 'Ir a firmar' }).click();

  await expect(page.getByRole('heading', { name: 'Firma con tu dedo' })).toBeVisible();
  const canvas = page.locator('canvas');
  const box = await canvas.boundingBox();
  if (!box) throw new Error('signature canvas not found');
  await page.mouse.move(box.x + 40, box.y + 40);
  await page.mouse.down();
  await page.mouse.move(box.x + 200, box.y + 100, { steps: 10 });
  await page.mouse.move(box.x + 280, box.y + 40, { steps: 10 });
  await page.mouse.up();
  await page.getByRole('button', { name: 'Confirmar firma' }).click();

  await expect(page.getByRole('heading', { name: 'Revisa tus respuestas' })).toBeVisible();
  await page.getByRole('button', { name: 'Enviar consentimiento' }).click();

  // No eligibility rules are configured on the E2E template (see
  // api-setup.ts), so every submission safely falls through to manual
  // review rather than silently auto-approving — matches the backend's
  // documented default behavior (see ConsentTemplateCreate's docstring).
  await expect(page.getByRole('heading', { name: 'Recibimos tus respuestas' })).toBeVisible({
    timeout: 10_000,
  });

  // --- Staff side: confirm the submission actually landed. ---
  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.adminEmail);
  await page.getByLabel('Contraseña').fill(clinic.adminPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);

  // The eligibility result specifically lives on the Consentimientos
  // review panel (clicking a request opens its detail), not the patient
  // detail page — that one only shows the request's lifecycle status
  // (Completado/Pendiente/etc.), not the clinical eligibility outcome.
  await page.goto(`${STAFF_WEB_URL}/consents`);
  await page
    .getByRole('button', { name: new RegExp(`${patient.first_name} ${patient.last_name}`) })
    .click();
  await expect(page.getByText('Requiere revisión médica')).toBeVisible({ timeout: 10_000 });
});
