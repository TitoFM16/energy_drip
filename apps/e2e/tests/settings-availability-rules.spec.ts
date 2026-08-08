import { expect, test } from '@playwright/test';
import { bootstrapClinic } from './support/api-setup';
import { STAFF_WEB_URL } from './support/urls';

test('admin manages a practitioner availability rule from Settings', async ({ page }) => {
  const clinic = await bootstrapClinic();

  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.adminEmail);
  await page.getByLabel('Contraseña').fill(clinic.adminPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);

  await page.goto(`${STAFF_WEB_URL}/settings`);
  // A plain getByLabel('Profesional') is ambiguous on this page: the
  // "Manage user role assignments" section also has a per-user
  // "Profesional" role checkbox for each seeded user. Scoping to the
  // combobox role picks out only the <select>, not those checkboxes.
  await page
    .getByRole('combobox', { name: 'Profesional' })
    .selectOption({ label: 'E2E Practitioner' });

  // bootstrapClinic already seeds one all-day rule per weekday as test
  // fixture data — add a distinct, narrower rule through the real form and
  // confirm it shows up alongside them without disturbing them.
  await page.getByLabel('Día').selectOption({ label: 'Miércoles' });
  await page.getByLabel('Desde').fill('09:00');
  await page.getByLabel('Hasta').fill('10:00');
  await page.getByRole('button', { name: 'Agregar horario' }).click();

  const newRule = page.locator('li', { hasText: 'Miércoles · 09:00–10:00' });
  await expect(newRule).toBeVisible({ timeout: 10_000 });

  await newRule.getByRole('button', { name: 'Eliminar' }).click();
  await expect(newRule).toBeHidden({ timeout: 10_000 });
});
