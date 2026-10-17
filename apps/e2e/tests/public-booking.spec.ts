import { expect, test } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { API_URL, LANDING_URL, STAFF_WEB_URL } from './support/urls';

test('owner publishes a service and worker schedule; visitor books and owner manages the appointment', async ({
  page,
  context,
  request,
}, testInfo) => {
  test.setTimeout(120_000);
  // Runs first on a clean E2E database: public routing must never guess between clinics.
  const email = `mvp-owner-${Date.now()}@example.com`;
  const password = 'mvp-owner-secret123';
  const registration = await request.post(`${API_URL}/api/v1/auth/register-organization`, {
    data: {
      organization_name: 'Clínica MVP',
      admin_full_name: 'Propietaria MVP',
      admin_email: email,
      admin_password: password,
    },
  });
  expect(registration.ok()).toBeTruthy();
  await page.goto(`${STAFF_WEB_URL}/login`);
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Entrar', exact: true }).click();
  await expect(page).toHaveURL(`${STAFF_WEB_URL}/agenda`);
  await expect(page.getByRole('navigation').getByText('Dashboard')).toHaveCount(0);

  await page.getByRole('link', { name: 'Servicios', exact: true }).click();
  await page.getByLabel('Nombre del servicio').fill('Servicio de enfermería MVP');
  await page.getByLabel('Duración (minutos)').fill('60');
  await page.getByLabel('Precio', { exact: true }).fill('120000');
  await page
    .getByLabel('Descripción', { exact: true })
    .fill('Atención personalizada con nuestro equipo de enfermería.');
  await page.getByLabel('Imagen del servicio').setInputFiles({
    name: 'servicio.png',
    mimeType: 'image/png',
    buffer: Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jB4kAAAAASUVORK5CYII=',
      'base64',
    ),
  });
  await page.getByRole('button', { name: 'Agregar servicio', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Servicio guardado');
  const serviceCard = page.locator('article', { hasText: 'Servicio de enfermería MVP' });
  await expect(serviceCard.getByRole('img')).toBeVisible();
  const firstImage = await serviceCard.getByRole('img').getAttribute('src');
  await serviceCard.getByRole('button', { name: 'Editar Servicio de enfermería MVP' }).click();
  await page.getByLabel('Precio', { exact: true }).fill('125000');
  await page.getByLabel('Duración (minutos)').fill('45');
  await page
    .getByLabel('Imagen del servicio')
    .setInputFiles(
      fileURLToPath(
        new URL('../../landing/public/brand/energy-drip-home-care.webp', import.meta.url),
      ),
    );
  await page.getByRole('button', { name: 'Guardar cambios', exact: true }).click();
  await expect(serviceCard).toContainText('125.000');
  await expect(serviceCard).toContainText('45 min');
  await expect(serviceCard.getByRole('img')).not.toHaveAttribute('src', firstImage!);
  await page.screenshot({ path: testInfo.outputPath('admin-services.png'), fullPage: true });

  await page.getByRole('link', { name: 'Equipo y horarios', exact: true }).click();
  await page.getByLabel('Nombre completo', { exact: true }).fill('Enfermera Ana MVP');
  await page.getByLabel('Especialidad (opcional)', { exact: true }).fill('Enfermería');
  await page.getByRole('button', { name: 'Agregar profesional', exact: true }).click();
  await expect(page.locator('li', { hasText: 'Enfermera Ana MVP' })).toBeVisible();
  await page
    .getByRole('combobox', { name: 'Profesional', exact: true })
    .selectOption({ label: 'Enfermera Ana MVP' });
  const today = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
  const date = new Date(`${today}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + 1);
  const dateValue = date.toISOString().slice(0, 10);
  const weekday = (date.getUTCDay() + 6) % 7;
  await page.getByRole('combobox', { name: 'Día', exact: true }).selectOption(String(weekday));
  await page.getByLabel('Desde', { exact: true }).fill('09:00');
  await page.getByLabel('Hasta', { exact: true }).fill('12:00');
  await page.getByRole('button', { name: 'Agregar horario', exact: true }).click();
  const rule = page.locator('li', { hasText: '09:00–12:00' });
  await expect(rule).toBeVisible();
  await rule.getByRole('button', { name: 'Eliminar', exact: true }).click();
  await expect(rule).toHaveCount(0);
  await page.getByLabel('Hasta', { exact: true }).fill('13:00');
  await page.getByRole('button', { name: 'Agregar horario', exact: true }).click();
  await expect(page.locator('li', { hasText: '09:00–13:00' })).toBeVisible();

  const visitor = await context.newPage();
  await visitor.goto(LANDING_URL);
  const publicService = visitor.locator('article', { hasText: 'Servicio de enfermería MVP' });
  await expect(publicService).toContainText('125.000');
  await expect(publicService).toContainText('45 minutos');
  await expect(publicService.getByRole('img')).toBeVisible();
  await expect
    .poll(async () =>
      publicService
        .getByRole('img')
        .evaluate((image) => (image as unknown as { naturalWidth: number }).naturalWidth),
    )
    .toBeGreaterThan(0);
  await visitor.screenshot({ path: testInfo.outputPath('landing-desktop.png'), fullPage: true });
  await publicService.getByRole('link', { name: 'Reservar', exact: true }).click();
  await visitor
    .getByLabel('Profesional', { exact: true })
    .selectOption({ label: 'Enfermera Ana MVP · Enfermería' });
  await visitor.getByLabel('Fecha', { exact: true }).fill(dateValue);
  const slots = visitor.getByRole('group', { name: 'Horarios disponibles' });
  await expect(slots.getByRole('button').first()).toContainText('9:00');
  await slots.getByRole('button').first().click();
  await visitor.getByLabel('Nombre', { exact: true }).fill('Isabella');
  await visitor.getByLabel('Apellido', { exact: true }).fill('Torres MVP');
  await visitor.getByLabel('Teléfono', { exact: true }).fill('+573001234567');
  await visitor.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() => visitor.locator('html').evaluate((element) => element.scrollWidth))
    .toBeLessThanOrEqual(390);
  for (const label of ['Servicio', 'Profesional']) {
    expect(
      await visitor
        .getByLabel(label, { exact: true })
        .evaluate((element) => element.getBoundingClientRect().right),
    ).toBeLessThanOrEqual(390);
  }
  await visitor.screenshot({ path: testInfo.outputPath('booking-mobile.png'), fullPage: true });
  await visitor.getByRole('button', { name: 'Confirmar cita', exact: true }).click();
  await expect(visitor.getByRole('heading', { name: 'Tu cita está confirmada' })).toBeVisible();
  await expect(visitor.getByRole('status')).toContainText('Enfermera Ana MVP');
  await expect(visitor.getByRole('status')).toContainText('125.000');
  await expect(visitor.getByRole('status')).toContainText('9:00');
  await visitor.screenshot({
    path: testInfo.outputPath('confirmation-mobile.png'),
    fullPage: true,
  });

  await page.getByRole('link', { name: 'Agenda', exact: true }).click();
  await page.getByLabel('Fecha de la agenda').fill(dateValue);
  const appointment = page.locator('li', { hasText: 'Isabella Torres MVP' });
  await expect(appointment).toBeVisible();
  await expect(appointment).toContainText('Servicio de enfermería MVP');
  await expect(appointment).toContainText('+573001234567');
  await expect(appointment).toContainText('Confirmada');
  await appointment.getByRole('button', { name: 'Reprogramar', exact: true }).click();
  const newSlot = page.getByRole('button').filter({ hasText: /^0?9:45/ });
  await expect(newSlot).toBeVisible();
  const rescheduled = page.waitForResponse(
    (response) => response.url().endsWith('/reschedule') && response.request().method() === 'PATCH',
  );
  await newSlot.click();
  expect((await rescheduled).ok()).toBeTruthy();
  await expect(page.getByText(/Reprogramando cita de/)).toHaveCount(0);
  await expect(appointment.locator('p').first()).toHaveText(/^0?9:45.*10:30/);
  // Reload to prove the new start and end persisted, rather than only matching
  // the old appointment's 09:45 end time or transient optimistic state.
  await page.reload();
  await page.getByLabel('Fecha de la agenda').fill(dateValue);
  await expect(appointment.locator('p').first()).toHaveText(/^0?9:45.*10:30/);
  await expect(appointment).toContainText('Confirmada');
  await page.screenshot({ path: testInfo.outputPath('admin-agenda.png'), fullPage: true });
  await appointment.getByRole('button', { name: 'Cancelar', exact: true }).click();
  await expect(appointment).toContainText('Cancelada');

  await page.getByRole('link', { name: 'Servicios', exact: true }).click();
  await page
    .locator('article', { hasText: 'Servicio de enfermería MVP' })
    .getByRole('button', { name: 'Archivar', exact: true })
    .click();
  await expect(page.locator('article', { hasText: 'Servicio de enfermería MVP' })).toContainText(
    'Archivado',
  );
  await visitor.goto(LANDING_URL);
  await expect(
    visitor.getByText('Pronto publicaremos nuestros servicios y horarios.'),
  ).toBeVisible();
  await expect(
    visitor.getByRole('heading', { name: 'Servicio de enfermería MVP', exact: true }),
  ).toHaveCount(0);
});
