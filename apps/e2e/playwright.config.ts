import { defineConfig, devices } from '@playwright/test';

// The public flow needs an unambiguous, fresh single-clinic database. Run it
// first, then staff/consent tests may create their isolated organizations.
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  timeout: 30_000,
  use: {
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // This clinic and its patients are Colombia-based (see the product's
    // own scope notes) — real users see Spanish date/time formatting
    // ("8:00 a. m.", not "8:00 AM"), so tests should exercise that, not
    // whatever locale the CI runner's browser happens to default to.
    locale: 'es-CO',
    timezoneId: 'America/Bogota',
  },
  projects: [
    {
      name: 'public-mvp',
      testMatch: 'public-booking.spec.ts',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'chromium',
      dependencies: ['public-mvp'],
      testMatch: [
        'staff-appointment-booking.spec.ts',
        'settings-availability-rules.spec.ts',
        'patient-creation.spec.ts',
        'consent-*.spec.ts',
        'document-verification.spec.ts',
      ],
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
