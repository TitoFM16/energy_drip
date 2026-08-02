import { expect, test } from '@playwright/test';
import { bootstrapClinic } from './support/api-setup';
import { LANDING_URL } from './support/urls';

test('a visitor submits the public booking form and sees a confirmation', async ({ page }) => {
  // GET /api/v1/public/treatments resolves "the" organization via
  // OrganizationRepository.get_first() (oldest-created-first) — this
  // product is single-tenant in production, but the shared dev/CI
  // database can have other orgs from other tests. This bootstrap just
  // guarantees *some* org with a published treatment exists; it doesn't
  // (and doesn't need to) guarantee *this* one is what the public form
  // shows — same reasoning as apps/api/tests/test_booking.py's docstring.
  await bootstrapClinic();

  await page.goto(`${LANDING_URL}/reservar`);
  await expect(page.getByRole('heading', { name: 'Reserva tu valoración' })).toBeVisible();

  await page.getByLabel('Nombre').fill('Isabella');
  await page.getByLabel('Apellido').fill('Torres');
  await page.getByLabel('Teléfono (WhatsApp)').fill('+573001234567');

  const treatmentSelect = page.getByLabel('Tratamiento de interés');
  await expect(treatmentSelect.locator('option').nth(1)).toBeAttached({ timeout: 15_000 });
  await treatmentSelect.selectOption({ index: 1 });

  await page.getByRole('button', { name: 'Enviar solicitud' }).click();

  await expect(page.getByRole('heading', { name: 'Solicitud recibida' })).toBeVisible({
    timeout: 10_000,
  });
});
