import { expect, test } from '@playwright/test';
import { bootstrapClinic } from './support/api-setup';
import { STAFF_WEB_URL } from './support/urls';

test('staff adds and removes a patient contact and an emergency contact', async ({ page }) => {
  const clinic = await bootstrapClinic();

  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.adminEmail);
  await page.getByLabel('Contraseña').fill(clinic.adminPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);

  await page.goto(`${STAFF_WEB_URL}/patients`);
  await page.getByRole('button', { name: 'Nuevo paciente' }).click();
  await page.getByLabel('Nombre').fill('Contacto');
  await page.getByLabel('Apellido').fill('E2E');
  await page.getByLabel('Teléfono').fill('+573019998877');
  await page.getByRole('button', { name: 'Crear paciente' }).click();
  await page.getByText('Contacto E2E').click();
  await expect(page.getByRole('heading', { name: 'Contacto E2E' })).toBeVisible();

  const contactsSection = page
    .getByRole('heading', { name: 'Otros contactos' })
    .locator('xpath=..');
  await contactsSection.getByLabel('Etiqueta').fill('Trabajo');
  await contactsSection.getByLabel('Teléfono').fill('+573005556677');
  await contactsSection.getByRole('button', { name: 'Agregar' }).click();
  await expect(contactsSection.getByText('Trabajo · +573005556677')).toBeVisible();

  const emergencySection = page
    .getByRole('heading', { name: 'Contactos de emergencia' })
    .locator('xpath=..');
  await emergencySection.getByLabel('Nombre completo').fill('Maria Doe');
  await emergencySection.getByLabel('Parentesco').fill('Madre');
  await emergencySection.getByLabel('Teléfono').fill('+573009998877');
  await emergencySection.getByRole('button', { name: 'Agregar' }).click();
  await expect(emergencySection.getByText('Maria Doe · Madre · +573009998877')).toBeVisible();

  // Confirms the list actually re-fetched from the server, not just a
  // local optimistic add — reloading the page re-hits the real API.
  await page.reload();
  await expect(contactsSection.getByText('Trabajo · +573005556677')).toBeVisible();
  await expect(emergencySection.getByText('Maria Doe · Madre · +573009998877')).toBeVisible();

  await contactsSection.getByRole('button', { name: 'Eliminar' }).click();
  await expect(contactsSection.getByText('Sin otros contactos registrados.')).toBeVisible();
});
