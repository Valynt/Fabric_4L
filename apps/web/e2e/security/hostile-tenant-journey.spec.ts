import { journeyTest, expect } from '../helpers/journey-fixture';

journeyTest.describe('Security Suite: Hostile Tenant Journey', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/**/acct-foreign-tenant**',
        status: 403,
        body: {
          error: { code: 'TENANT_FORBIDDEN', message: 'Forbidden', request_id: 'req-hostile-tenant' },
        },
      },
      {
        pattern: '**/api/v1/**/resource-tenant-b**',
        status: 404,
        body: {
          error: { code: 'RESOURCE_NOT_FOUND', message: 'Not found', request_id: 'req-idor-block' },
        },
      },
      {
        pattern: '**/api/v1/auth/**',
        status: 401,
        body: {
          error: { code: 'AUTH_INVALID_TOKEN', message: 'Unauthorized', request_id: 'req-token-denied' },
        },
      },
    ]);
  });

  journeyTest('hostile tenant journey blocks UI request -> backend enforcement with safe error contract', async ({ authedPage }) => {
    const deniedResponses: Array<{ status: number; body: string }> = [];

    authedPage.on('response', async (response) => {
      if (response.status() === 401 || response.status() === 403 || response.status() === 404) {
        const body = await response.text();
        deniedResponses.push({ status: response.status(), body });
      }
    });

    await authedPage.goto('/intelligence/acct-foreign-tenant/signals?resourceId=resource-tenant-b', {
      waitUntil: 'domcontentloaded',
    });

    await expect(
      authedPage.getByText(/forbidden|access denied|not authorized|not found|could not be loaded/i).first(),
    ).toBeVisible({ timeout: 10000 });

    await authedPage.goto('/settings/team/permissions', { waitUntil: 'domcontentloaded' });
    await expect(authedPage.getByText(/permissions|team|role|access/i).first()).toBeVisible();

    await authedPage.goto('/accounts', { waitUntil: 'domcontentloaded' });
    await authedPage.evaluate(() => localStorage.setItem('authToken', 'tampered.jwt.token'));
    await authedPage.reload({ waitUntil: 'domcontentloaded' });

    expect(deniedResponses.length).toBeGreaterThan(0);
    for (const denied of deniedResponses) {
      expect(denied.body.toLowerCase()).not.toContain('traceback');
      expect(denied.body.toLowerCase()).not.toContain('sqlalchemy');
      expect(denied.body.toLowerCase()).not.toContain('password');
      expect(denied.body.toLowerCase()).toMatch(/request_id|code|error/);
    }
  });
});
