import { expect, test } from '@playwright/test';
import {
  bootstrapClinic,
  createConsentRequest,
  createPatient,
  submitConsentForm,
} from './support/api-setup';
import { STAFF_WEB_URL } from './support/urls';

test('staff downloads, verifies, regenerates, and invalidates a signed consent document', async ({
  page,
}) => {
  const clinic = await bootstrapClinic();
  const patient = await createPatient(clinic.adminToken, {
    first_name: 'Elena',
    last_name: 'DocumentTest',
  });
  const { token } = await createConsentRequest(
    clinic.adminToken,
    patient.id,
    clinic.publishedConsentTemplateVersionId,
  );
  await submitConsentForm(token);

  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.adminEmail);
  await page.getByLabel('Contraseña').fill(clinic.adminPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);

  await page.goto(`${STAFF_WEB_URL}/consents`);
  await page
    .getByRole('button', { name: new RegExp(`${patient.first_name} ${patient.last_name}`) })
    .click();

  // Scoped to the "Documento firmado" section's own list specifically —
  // the Consentimientos page also has a template list above with its own
  // "Versión 1" text (a published template's version number), which an
  // unscoped `li` + hasText locator would match instead of the actual
  // document row. `has:` on an ancestor `div` isn't precise enough either:
  // it matches every ancestor div up the tree that contains the heading
  // as a descendant, not just the immediate wrapper, so it still picked
  // up the whole-page container. Going straight to the heading's sibling
  // `<ul>` is unambiguous.
  const documentSection = page
    .getByRole('heading', { name: 'Documento firmado' })
    .locator('xpath=following-sibling::ul[1]');

  // PDF generation happens asynchronously in the worker off the
  // consent.submitted event (see missing_features.md's "Document version
  // history and regeneration") — the detail panel doesn't poll, so reload
  // and reselect until the document actually shows up rather than racing
  // a fixed sleep.
  const version1Row = documentSection.locator('li', { hasText: 'Versión 1' });
  await expect(async () => {
    await page.reload();
    await page
      .getByRole('button', { name: new RegExp(`${patient.first_name} ${patient.last_name}`) })
      .click();
    await expect(version1Row).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 20_000 });

  await expect(version1Row.getByText('Vigente')).toBeVisible();

  await version1Row.getByRole('button', { name: 'Verificar' }).click();
  await expect(version1Row.getByText('Integridad verificada: el hash coincide.')).toBeVisible({
    timeout: 10_000,
  });

  // Regenerate: a second, distinct version should show up alongside the
  // first, which is never deleted — just superseded.
  await version1Row.getByRole('button', { name: 'Regenerar' }).click();
  await version1Row.getByPlaceholder('Motivo').fill('E2E regeneration test');
  await version1Row.getByRole('button', { name: 'Confirmar regeneración' }).click();
  await expect(version1Row.getByText('Regeneración solicitada')).toBeVisible();

  const version2Row = documentSection.locator('li', { hasText: 'Versión 2' });
  await expect(async () => {
    await page.reload();
    await page
      .getByRole('button', { name: new RegExp(`${patient.first_name} ${patient.last_name}`) })
      .click();
    await expect(version2Row).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 20_000 });
  await expect(version2Row.getByText('Vigente')).toBeVisible();
  await expect(version1Row.getByText('Reemplazado')).toBeVisible();

  // Invalidate the now-current version 2, with a reason.
  await version2Row.getByRole('button', { name: 'Invalidar' }).click();
  await version2Row.getByPlaceholder('Motivo').fill('E2E invalidation test');
  await version2Row.getByRole('button', { name: 'Confirmar invalidación' }).click();
  await expect(version2Row.getByText('Invalidado')).toBeVisible({ timeout: 10_000 });
});
