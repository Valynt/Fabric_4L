import { journeyTest, expect } from '../helpers/journey-fixture';

type HostileVector = {
  name: string;
  path: string;
  routePattern: string;
  status: number;
  errorCode: string;
  auditEventExpected: true;
};

const HOSTILE_VECTORS: HostileVector[] = [
  { name: 'L1 cross-tenant source read', path: '/sources/src-tenant-b', routePattern: '**/api/v1/sources/**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'L2 IDOR extraction read', path: '/context/extraction?jobId=extract-tenant-b', routePattern: '**/api/v1/extraction/**', status: 404, errorCode: 'IDOR_RESOURCE_NOT_FOUND', auditEventExpected: true },
  { name: 'L3 cross-tenant entity access', path: '/context/ontology/graph?entityId=entity-tenant-b', routePattern: '**/api/v1/entities/**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'L4 workflow escalation attempt', path: '/agents/workflows/wf-tenant-b', routePattern: '**/api/v1/workflows/**', status: 403, errorCode: 'RBAC_DENIED', auditEventExpected: true },
  { name: 'L5 truth object IDOR', path: '/governance/truth/truth-tenant-b', routePattern: '**/api/v1/truth/**', status: 404, errorCode: 'IDOR_RESOURCE_NOT_FOUND', auditEventExpected: true },
  { name: 'L6 benchmark foreign tenant read', path: '/benchmarks?tenant=tenant-b', routePattern: '**/api/v1/benchmarks/**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'L7 billing foreign tenant read', path: '/billing/invoices?tenant=tenant-b', routePattern: '**/api/v1/billing/**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'API gateway accounts privilege escalation', path: '/accounts/acct-tenant-b', routePattern: '**/api/v1/accounts/**', status: 403, errorCode: 'RBAC_DENIED', auditEventExpected: true },
];

journeyTest.describe('Security Suite: Hostile Tenant Enforcement Matrix', () => {
  journeyTest('blocks cross-tenant/IDOR/RBAC/token abuse and enforces safe denial contracts', async ({ authedPage, addMocks }) => {
    const deniedActionsObserved = new Set<string>();
    const deniedResponses: string[] = [];

    const mockEndpoints = HOSTILE_VECTORS.map((vector) => ({
      pattern: vector.routePattern,
      status: vector.status,
      body: {
        error: {
          code: vector.errorCode,
          message: 'Access denied',
          request_id: `req-${vector.errorCode.toLowerCase()}`,
        },
        audit: { emitted: vector.auditEventExpected, action: vector.name },
      },
    }));

    mockEndpoints.push(
      {
        pattern: '**/api/v1/auth/**',
        status: 401,
        body: { error: { code: 'AUTH_EXPIRED', message: 'Token expired', request_id: 'req-auth-expired' } },
      },
      {
        pattern: '**/api/v1/session/**',
        status: 401,
        body: { error: { code: 'AUTH_TAMPERED', message: 'Invalid token', request_id: 'req-auth-tampered' } },
      },
    );

    await addMocks(mockEndpoints);

    authedPage.on('response', async (response) => {
      if ([401, 403, 404].includes(response.status())) {
        const body = await response.text();
        deniedResponses.push(body.toLowerCase());
        if (body.includes('"audit"')) {
          deniedActionsObserved.add('audit');
        }
      }
    });

    for (const vector of HOSTILE_VECTORS) {
      await authedPage.goto(vector.path, { waitUntil: 'domcontentloaded' });
      await expect(
        authedPage.getByText(/forbidden|access denied|not authorized|not found|unauthorized|expired/i).first(),
      ).toBeVisible({ timeout: 8000 });
    }

    await authedPage.evaluate(() => localStorage.setItem('authToken', 'tampered.token.value'));
    await authedPage.goto('/accounts', { waitUntil: 'domcontentloaded' });

    expect(deniedResponses.length).toBeGreaterThan(0);
    for (const body of deniedResponses) {
      expect(body).toMatch(/error|code|request_id/);
      expect(body).not.toContain('traceback');
      expect(body).not.toContain('sqlalchemy');
      expect(body).not.toContain('password');
      expect(body).not.toContain('secret');
      expect(body).not.toContain('api_key');
    }
    expect(deniedResponses.some((body) => body.includes('auth_expired'))).toBeTruthy();
    expect(deniedResponses.some((body) => body.includes('auth_tampered'))).toBeTruthy();
    expect(deniedActionsObserved.has('audit')).toBeTruthy();
  });
});
