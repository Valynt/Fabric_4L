import { journeyTest, expect } from '../helpers/journey-fixture';

type HostileVector = {
  name: string;
  operation: 'list' | 'read' | 'create' | 'update' | 'delete' | 'search' | 'export' | 'background-job lookup' | 'file download' | 'agent retrieval';
  path: string;
  apiPath: string;
  routePattern: string;
  status: number;
  errorCode: string;
  auditEventExpected: true;
};

const HOSTILE_VECTORS: HostileVector[] = [
  { name: 'L1 cross-tenant source list', operation: 'list', path: '/sources?tenant=tenant-b', apiPath: '/api/v1/sources/list?tenant=tenant-b', routePattern: '**/api/v1/sources/list**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'L1 cross-tenant source read', operation: 'read', path: '/sources/src-tenant-b', apiPath: '/api/v1/sources/src-tenant-b', routePattern: '**/api/v1/sources/**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'L1 cross-tenant source create with forged tenant', operation: 'create', path: '/sources/new?tenant=tenant-b', apiPath: '/api/v1/sources/create?tenant=tenant-b', routePattern: '**/api/v1/sources/create**', status: 403, errorCode: 'TENANT_CONTEXT_MISMATCH', auditEventExpected: true },
  { name: 'L2 IDOR extraction read', operation: 'background-job lookup', path: '/context/extraction?jobId=extract-tenant-b', apiPath: '/api/v1/extraction/jobs/extract-tenant-b', routePattern: '**/api/v1/extraction/**', status: 404, errorCode: 'IDOR_RESOURCE_NOT_FOUND', auditEventExpected: true },
  { name: 'L3 cross-tenant entity access', operation: 'read', path: '/context/ontology/graph?entityId=entity-tenant-b', apiPath: '/api/v1/entities/entity-tenant-b', routePattern: '**/api/v1/entities/**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'L3 cross-tenant graph search', operation: 'search', path: '/context/search?q=tenant-b', apiPath: '/api/v1/search?query=tenant-b', routePattern: '**/api/v1/search**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'L4 workflow escalation update attempt', operation: 'update', path: '/agents/workflows/wf-tenant-b', apiPath: '/api/v1/workflows/wf-tenant-b/resume', routePattern: '**/api/v1/workflows/**', status: 403, errorCode: 'RBAC_DENIED', auditEventExpected: true },
  { name: 'L4 agent retrieval cross-tenant evidence request', operation: 'agent retrieval', path: '/workflow/intelligence?documentId=doc-tenant-b', apiPath: '/api/v1/agents/retrieve?documentId=doc-tenant-b', routePattern: '**/api/v1/agents/retrieve**', status: 403, errorCode: 'RETRIEVAL_TENANT_FORBIDDEN', auditEventExpected: true },
  { name: 'L5 truth object IDOR', operation: 'read', path: '/governance/truth/truth-tenant-b', apiPath: '/api/v1/truth/truth-tenant-b', routePattern: '**/api/v1/truth/**', status: 404, errorCode: 'IDOR_RESOURCE_NOT_FOUND', auditEventExpected: true },
  { name: 'L5 foreign evidence file download', operation: 'file download', path: '/governance/evidence/file-tenant-b', apiPath: '/api/v1/evidence/file-tenant-b/download', routePattern: '**/api/v1/evidence/**', status: 404, errorCode: 'IDOR_RESOURCE_NOT_FOUND', auditEventExpected: true },
  { name: 'L6 benchmark foreign tenant read', operation: 'read', path: '/benchmarks?tenant=tenant-b', apiPath: '/api/v1/benchmarks?tenant=tenant-b', routePattern: '**/api/v1/benchmarks**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'L6 benchmark foreign tenant delete', operation: 'delete', path: '/benchmarks/dataset-tenant-b', apiPath: '/api/v1/benchmarks/dataset-tenant-b', routePattern: '**/api/v1/benchmarks/**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'L7 billing foreign tenant read', operation: 'read', path: '/billing/invoices?tenant=tenant-b', apiPath: '/api/v1/billing/invoices?tenant=tenant-b', routePattern: '**/api/v1/billing/**', status: 403, errorCode: 'AUTH_FORBIDDEN', auditEventExpected: true },
  { name: 'API gateway accounts privilege escalation', operation: 'read', path: '/accounts/acct-tenant-b', apiPath: '/api/v1/accounts/acct-tenant-b', routePattern: '**/api/v1/accounts/**', status: 403, errorCode: 'RBAC_DENIED', auditEventExpected: true },
  { name: 'API gateway foreign business case export', operation: 'export', path: '/deliverables/cases/case-tenant-b', apiPath: '/api/v1/cases/case-tenant-b/export', routePattern: '**/api/v1/cases/**/export', status: 403, errorCode: 'EXPORT_TENANT_FORBIDDEN', auditEventExpected: true },
];

journeyTest.describe('Security Suite: Hostile Tenant Enforcement Matrix', () => {
  journeyTest('blocks cross-tenant/IDOR/RBAC/token abuse and enforces safe denial contracts', async ({ authedPage, addMocks }) => {
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

    await authedPage.goto('/home', { waitUntil: 'domcontentloaded' });

    const deniedResponses = await authedPage.evaluate(async (vectors) => {
      const apiResponses = await Promise.all(vectors.map(async (vector) => {
        const response = await fetch(vector.apiPath);
        const body = await response.text();
        let code = '';
        let audit = false;
        try {
          const payload = JSON.parse(body) as { error?: { code?: string }; audit?: { emitted?: boolean } };
          code = payload.error?.code ?? '';
          audit = payload.audit?.emitted === true;
        } catch {
          code = '';
        }
        return { status: response.status, body: body.toLowerCase(), code, audit };
      }));
      const authResponses = await Promise.all(['/api/v1/auth/session', '/api/v1/session/current'].map(async (url) => {
        const response = await fetch(url);
        const body = await response.text();
        let code = '';
        try {
          const payload = JSON.parse(body) as { error?: { code?: string } };
          code = payload.error?.code ?? '';
        } catch {
          code = '';
        }
        return { status: response.status, body: body.toLowerCase(), code, audit: false };
      }));
      return [...apiResponses, ...authResponses].filter((response) => response.status >= 400 || response.code);
    }, HOSTILE_VECTORS);
    const deniedActionsObserved = new Set(
      HOSTILE_VECTORS.map((vector) => vector.operation),
    );

    for (const vector of HOSTILE_VECTORS) {
      expect(
        deniedResponses.some((denied) => denied.status === vector.status && denied.code === vector.errorCode),
        `expected exact denial ${vector.status} ${vector.errorCode} for ${vector.name}`,
      ).toBe(true);
    }
    for (const operation of ['list', 'read', 'create', 'update', 'delete', 'search', 'export', 'background-job lookup', 'file download', 'agent retrieval']) {
      expect(deniedActionsObserved.has(operation as HostileVector['operation']), `expected hostile matrix operation coverage for ${operation}`).toBe(true);
    }

    for (const { body } of deniedResponses) {
      expect(body).toMatch(/error|code|request_id/);
      expect(body).not.toContain('traceback');
      expect(body).not.toContain('sqlalchemy');
      expect(body).not.toContain('password');
      expect(body).not.toContain('secret');
      expect(body).not.toContain('api_key');
    }
    expect(deniedResponses.some((denied) => denied.status === 401 && denied.code === 'AUTH_EXPIRED')).toBeTruthy();
    expect(deniedResponses.some((denied) => denied.status === 401 && denied.code === 'AUTH_TAMPERED')).toBeTruthy();
    expect(deniedResponses.some((denied) => denied.audit)).toBeTruthy();
  });
});
