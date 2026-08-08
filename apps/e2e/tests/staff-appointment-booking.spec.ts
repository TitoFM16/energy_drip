import { expect, test } from '@playwright/test';
import { bootstrapClinic, createPatient } from './support/api-setup';
import { STAFF_WEB_URL } from './support/urls';

test('staff logs in, books an available slot for a patient, and sees it on the agenda', async ({
  page,
}) => {
  const clinic = await bootstrapClinic();
  const patient = await createPatient(clinic.adminToken, {
    first_name: 'Valentina',
    last_name: 'Ríos',
  });

  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.adminEmail);
  await page.getByLabel('Contraseña').fill(clinic.adminPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();

  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);
  await page.goto(`${STAFF_WEB_URL}/agenda`);
  await expect(page.getByRole('heading', { name: 'Agenda' })).toBeVisible();

  // Slots are generated on a fixed grid aligned to the availability rule's
  // start_time (00:00), stepping by the slot duration — late in the day,
  // "today" may have no grid-aligned slot left between now and the rule's
  // end_time. Tomorrow always has a full, untouched grid regardless of
  // what time this test happens to run.
  await page.getByRole('button', { name: 'Día siguiente' }).click();

  // Matches a rendered time regardless of exact am/pm punctuation quirks
  // across Intl implementations ("a.m." vs "a. m.", etc.) — the point is
  // "a slot button", not the precise formatting.
  const firstSlotButton = page.locator('button', { hasText: /\d{1,2}:\d{2}/ }).first();
  await expect(firstSlotButton).toBeVisible({ timeout: 15_000 });
  await firstSlotButton.click();

  await page.getByPlaceholder('Buscar por nombre...').fill('Valentina');
  await page.getByRole('button', { name: /Valentina Ríos/ }).click();
  await page.getByRole('button', { name: 'Confirmar cita' }).click();

  // The booking panel closes and the new appointment shows up in the
  // day's list once the mutation settles.
  await expect(page.getByText(patient.first_name).first()).toBeVisible({ timeout: 10_000 });

  // Status history: recorded on creation, and again on every status
  // change, with the actor who made each change.
  const appointmentRow = page.getByText(patient.first_name).locator('xpath=ancestor::li');
  await appointmentRow.getByRole('button', { name: 'Ver historial' }).click();
  await expect(appointmentRow.getByText(/Programada ·.*E2E Admin/)).toBeVisible();

  await appointmentRow.getByRole('button', { name: 'Confirmar' }).click();
  await expect(appointmentRow.getByText(/Programada → Confirmada ·.*E2E Admin/)).toBeVisible();
});
