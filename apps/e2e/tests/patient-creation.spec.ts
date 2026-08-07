import { expect, test } from '@playwright/test';
import { bootstrapClinic } from './support/api-setup';
import { STAFF_WEB_URL } from './support/urls';

test('staff creates a new patient through the real form and finds them in the list', async ({
  page,
}) => {
  const clinic = await bootstrapClinic();

  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.adminEmail);
  await page.getByLabel('Contraseña').fill(clinic.adminPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);

  await page.goto(`${STAFF_WEB_URL}/patients`);
  await page.getByRole('button', { name: 'Nuevo paciente' }).click();

  await page.getByLabel('Nombre').fill('Mariana');
  await page.getByLabel('Apellido').fill('Gómez Vélez');
  await page.getByLabel('Documento').fill('CC1029384756');
  await page.getByLabel('Teléfono').fill('+573015558899');
  await page.getByLabel('Correo electrónico').fill('mariana.gomez.e2e@example.com');
  await page.getByRole('button', { name: 'Crear paciente' }).click();

  // The form closes and the new patient shows up in the (now-refetched)
  // list — confirms the create mutation actually persisted, not just that
  // the form submitted without error.
  await expect(page.getByText('Mariana Gómez Vélez')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText('+573015558899')).toBeVisible();

  // Follow through to the detail page and confirm the document number
  // (not shown in the list) actually saved correctly too.
  await page.getByText('Mariana Gómez Vélez').click();
  await expect(page.getByRole('heading', { name: 'Mariana Gómez Vélez' })).toBeVisible();
  await expect(page.getByText('CC1029384756')).toBeVisible();
});
