import { expect, test } from '@playwright/test';
import { bootstrapClinic } from './support/api-setup';
import { STAFF_WEB_URL } from './support/urls';

test('organization admin adds a user role from Settings', async ({ page }) => {
  const clinic = await bootstrapClinic();

  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.adminEmail);
  await page.getByLabel('Contraseña').fill(clinic.adminPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);

  await page.goto(`${STAFF_WEB_URL}/settings`);
  const rolesSection = page.locator('section').filter({
    has: page.getByRole('heading', { name: 'Roles de usuarios' }),
  });
  const practitionerRow = rolesSection.locator('li').filter({ hasText: clinic.practitionerEmail });

  await practitionerRow.getByLabel('Asistente').check();
  await practitionerRow.getByRole('button', { name: 'Guardar roles de E2E Practitioner' }).click();
  await expect(practitionerRow.locator('span', { hasText: 'Asistente' })).toBeVisible({
    timeout: 10_000,
  });

  await page.reload();
  const persistedRow = page
    .locator('section')
    .filter({ has: page.getByRole('heading', { name: 'Roles de usuarios' }) })
    .locator('li')
    .filter({ hasText: clinic.practitionerEmail });
  await expect(persistedRow.getByLabel('Asistente')).toBeChecked();
  await expect(persistedRow.getByLabel('Profesional')).toBeChecked();
});
