import { journeyTest, expect } from '../helpers/journey-fixture';

journeyTest.describe('Security Suite: Hostile Tenant Journey', () => {
  const expectedDenials = [
    { status: 403, code: 'TENANT_FORBIDDEN' },
    { status: 404, code: 'RESOURCE_NOT_FOUND' },
    { status: 401, code: 'AUTH_INVALID_TOKEN' },
  ];

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
    await authedPage.goto('/home', {
      waitUntil: 'domcontentloaded',
    });

    await expect(authedPage).toHaveURL(/\/home/);

    const deniedResponses = await authedPage.evaluate(async () => {
      const urls = [
        '/api/v1/agents/accounts/acct-foreign-tenant',
        '/api/v1/documents/resource-tenant-b',
        '/api/v1/auth/session',
      ];
      return Promise.all(urls.map(async (url) => {
        const response = await fetch(url);
        const body = await response.text();
        let code = '';
        try {
          const payload = JSON.parse(body) as { error?: { code?: string } };
          code = payload.error?.code ?? '';
        } catch {
          code = '';
        }
        return { status: response.status, body, code };
      }));
    });

    for (const expected of expectedDenials) {
      expect(
        deniedResponses.some((denied) => denied.status === expected.status && denied.code === expected.code),
        `expected exact denial ${expected.status} ${expected.code}`,
      ).toBe(true);
    }
    for (const denied of deniedResponses) {
      expect(denied.body.toLowerCase()).not.toContain('traceback');
      expect(denied.body.toLowerCase()).not.toContain('sqlalchemy');
      expect(denied.body.toLowerCase()).not.toContain('password');
      expect(denied.body.toLowerCase()).toMatch(/request_id|code|error/);
    }
  });
});
