import { defineConfig, devices } from '@playwright/test';

/**
 * Runs against the full Docker Compose stack (`docker compose up`) —
 * intentionally not using Playwright's `webServer` auto-start, since the
 * target here is nine interdependent services (Postgres, Redis, MinIO,
 * API, two worker processes, three frontend apps), not one dev server.
 * See README.md in this directory for how to bring the stack up before
 * running these.
 */
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
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
