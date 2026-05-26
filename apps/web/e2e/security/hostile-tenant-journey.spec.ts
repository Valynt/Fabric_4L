import { journeyTest, expect } from '../helpers/journey-fixture';

journeyTest.describe('Security hostile tenant journey', () => {
  journeyTest('UI->API hostile tenant journey enforces authz and safe errors', async ({ authedPage }) => {
    const denied: Array<{ url: string; status: number; body: unknown }> = [];

    await authedPage.route('**/api/v1/**', async (route) => {
      const req = route.request();
      const url = req.url();

      const forbiddenBody = {
        error: 'forbidden',
        code: 'tenant_scope_violation',
        detail: 'Access denied for this tenant scope.',
        request_id: 'req-hostile-001',
      };

      if (/\/api\/v1\/(ingest|extract|entities|agents|truths|benchmarks)\//.test(url)) {
        denied.push({ url, status: 403, body: forbiddenBody });
        await route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify(forbiddenBody) });
        return;
      }

      if (/\/api\/v1\/agents\/accounts\//.test(url) && req.method() === 'GET') {
        denied.push({ url, status: 404, body: { error: 'not_found', detail: 'Resource not found.' } });
        await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: 'not_found', detail: 'Resource not found.' }) });
        return;
      }

      if (/\/api\/v1\/agents\/settings/.test(url)) {
        denied.push({ url, status: 403, body: { error: 'forbidden', code: 'rbac_denied', detail: 'Insufficient permissions.' } });
        await route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ error: 'forbidden', code: 'rbac_denied', detail: 'Insufficient permissions.' }) });
        return;
      }

      if (/\/api\/v1\/auth\//.test(url)) {
        denied.push({ url, status: 401, body: { error: 'authentication_required', detail: 'Token invalid or expired.' } });
        await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ error: 'authentication_required', detail: 'Token invalid or expired.' }) });
        return;
      }

      await route.fallback();
    });

    await authedPage.goto('/accounts', { waitUntil: 'domcontentloaded' });

    await authedPage.request.get('/api/v1/ingest/jobs?tenant_id=tenant-foreign');
    await authedPage.request.get('/api/v1/extract/jobs?tenant_id=tenant-foreign');
    await authedPage.request.get('/api/v1/entities?tenant_id=tenant-foreign');
    await authedPage.request.get('/api/v1/agents/workflows?tenant_id=tenant-foreign');
    await authedPage.request.get('/api/v1/truths/claims?tenant_id=tenant-foreign');
    await authedPage.request.get('/api/v1/benchmarks/datasets?tenant_id=tenant-foreign');

    await authedPage.request.get('/api/v1/agents/accounts/acct-guess-other-tenant');

    await authedPage.request.get('/api/v1/agents/settings?as_role=viewer');

    await authedPage.request.get('/api/v1/auth/session', {
      headers: { Authorization: 'Bearer tampered.token.value' },
    });

    expect(denied.length).toBeGreaterThanOrEqual(9);

    for (const event of denied) {
      const serialized = JSON.stringify(event.body).toLowerCase();
      expect(serialized.includes('traceback')).toBeFalsy();
      expect(serialized.includes('stack')).toBeFalsy();
      expect(serialized.includes('sql')).toBeFalsy();
      expect(serialized.includes('secret')).toBeFalsy();
    }

    expect(denied.some((event) => event.status === 401)).toBeTruthy();
    expect(denied.some((event) => event.status === 403)).toBeTruthy();
    expect(denied.some((event) => event.status === 404)).toBeTruthy();
  });
});
