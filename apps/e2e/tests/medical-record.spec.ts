import { expect, test } from '@playwright/test';
import { bootstrapClinic, createPatient } from './support/api-setup';
import { STAFF_WEB_URL } from './support/urls';

test('practitioner records medical history, allergies, conditions, and medications', async ({
  page,
}) => {
  const clinic = await bootstrapClinic();
  const patient = await createPatient(clinic.adminToken, {
    first_name: 'Camila',
    last_name: 'Restrepo',
  });

  // create_medical_history_entry/create_allergy/create_condition/create_medication
  // all require the practitioner/medical_director role — same boundary as
  // treatment plans/sessions (see treatment-plan-and-session.spec.ts).
  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(clinic.practitionerEmail);
  await page.getByLabel('Contraseña').fill(clinic.practitionerPassword);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/`);

  await page.goto(`${STAFF_WEB_URL}/patients/${patient.id}`);
  await expect(page.getByRole('heading', { name: 'Camila Restrepo' })).toBeVisible();

  // Medical history: create a draft entry, finalize it, then correct it
  // with an amendment rather than editing it in place.
  const historyForm = page.getByLabel('Nuevo antecedente').locator('xpath=ancestor::form');
  await page.getByLabel('Nuevo antecedente').fill('Sin antecedentes conocidos');
  await historyForm.getByRole('button', { name: 'Agregar' }).click();

  const originalEntry = page.locator('li', { hasText: 'Sin antecedentes conocidos' });
  await expect(originalEntry).toBeVisible({ timeout: 10_000 });
  await expect(originalEntry.getByText('Borrador')).toBeVisible();
  await originalEntry.getByRole('button', { name: 'Finalizar' }).click();
  await expect(originalEntry.getByText('Finalizado')).toBeVisible({ timeout: 10_000 });

  await originalEntry.getByRole('button', { name: 'Corregir' }).click();
  await originalEntry.getByPlaceholder('Texto de la corrección').fill('Alérgico a la penicilina');
  await originalEntry.getByRole('button', { name: 'Guardar corrección' }).click();

  const correctionEntry = page.locator('li', { hasText: 'Alérgico a la penicilina' });
  await expect(correctionEntry).toBeVisible({ timeout: 10_000 });
  await expect(correctionEntry.getByText('Borrador')).toBeVisible();
  // The original stays exactly as written — a correction is a new entry,
  // never a silent edit of the finalized one.
  await expect(originalEntry.getByText('Sin antecedentes conocidos')).toBeVisible();
  await expect(originalEntry.getByText('Finalizado')).toBeVisible();

  // Allergies: create, then deactivate.
  const allergyForm = page.getByLabel('Sustancia').locator('xpath=ancestor::form');
  await page.getByLabel('Sustancia').fill('Mariscos');
  await page.getByLabel('Severidad').fill('moderada');
  await allergyForm.getByRole('button', { name: 'Agregar' }).click();

  const allergyRow = page.locator('li', { hasText: 'Mariscos' });
  await expect(allergyRow).toBeVisible({ timeout: 10_000 });
  await expect(allergyRow.getByText('moderada')).toBeVisible();
  await allergyRow.getByRole('button', { name: 'Desactivar' }).click();
  await expect(allergyRow.getByRole('button', { name: 'Reactivar' })).toBeVisible({
    timeout: 10_000,
  });

  // Conditions: create.
  const conditionForm = page.getByLabel('Condición').locator('xpath=ancestor::form');
  await page.getByLabel('Condición').fill('Hipertensión');
  await conditionForm.getByRole('button', { name: 'Agregar' }).click();
  await expect(page.locator('li', { hasText: 'Hipertensión' })).toBeVisible({ timeout: 10_000 });

  // Medications: create, then mark as no longer current.
  const medicationForm = page.getByLabel('Medicamento').locator('xpath=ancestor::form');
  await page.getByLabel('Medicamento').fill('Losartán');
  await page.getByLabel('Dosis').fill('50mg');
  await medicationForm.getByRole('button', { name: 'Agregar' }).click();

  const medicationRow = page.locator('li', { hasText: 'Losartán' });
  await expect(medicationRow).toBeVisible({ timeout: 10_000 });
  await medicationRow.getByRole('button', { name: 'Suspender' }).click();
  await expect(medicationRow.getByRole('button', { name: 'Reanudar' })).toBeVisible({
    timeout: 10_000,
  });
});
