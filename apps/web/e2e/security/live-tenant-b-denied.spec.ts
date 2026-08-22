/**
 * Security: Continuous Live Cross-Tenant Denial — @backend
 *
 * Traceability: TENANT-B-DENIAL-001, CROSS-TENANT-READ-DENIED-001.
 *
 * Proves the live backend enforces tenant isolation when a session minted for
 * the Beta tenant attempts to read a resource owned by the canonical alpha
 * tenant. It uses a fresh Playwright browser context so the Beta cookie stays
 * isolated from any other test's session, and asserts a fail-closed denial
 * (401/403/404) with NO cross-tenant data leakage.
 *
 *   - `pageB` is a tenant-B session (Beta tenant id literal, beta slug).
 *   - Attempt to read the seeded Meridian case / account that belongs to the
 *     alpha tenant → must be denied, never return Meridian's case body.
 *   - Also verifies an anonymous (no session) request is rejected.
 *
 * This targets seeded data only (no live LLM) and is tagged `@backend` so it
 * only runs in the `backend-integrated` Playwright project.
 */
import { test, expect } from '../fixtures/contract-test';
import {
  requireBackendOrThrow,
  expectNoCrossTenantLeakage,
} from '../helpers/validation-program';
import { seedAuthState, E2E_TENANT_BETA_ID } from '../fixtures/auth-helpers';

const MERIDIAN_CASE_ID = 'case-meridian-e2e-001';

/**
 * Backend account UUID that the seeded Meridian case belongs to in the alpha
 * tenant. Mirrors `MERIDIAN_BACKEND_ACCOUNT_UUID` from
 * scripts/db/seed-e2e-data.ts. Used to target the real mounted list route.
 */
const MERIDIAN_BACKEND_ACCOUNT_UUID =
  '00000000-0000-4000-e2e0-000000000101';

/**
 * Ids/emails are seeded by scripts/db/seed-e2e-data.ts as belonging to the
 * Beta tenant. We use a distinct inline id (NOT the auth-helpers collision id
 * 'e2e-reviewer-user') so the Beta user identity is unique in the seed corpus.
 */
function tenantBUser() {
  return {
    id: 'e2e-tenant-b-user',
    email: 'tenant-b@valuefabric.test',
    role: 'reviewer',
    tenantId: E2E_TENANT_BETA_ID,
    tenantSlug: 'tenant-e2e-beta',
  };
}

function apiBackendBase(): string {
  const backendUrl = process.env.PLAYWRIGHT_BACKEND_URL;
  if (!backendUrl) {
    throw new Error('PLAYWRIGHT_BACKEND_URL is required for live cross-tenant denial assertions.');
  }
  return `${backendUrl.replace(/\/$/, '')}`;
}

test.describe('Security Suite: Live Cross-Tenant Denial', () => {
  test('tenant_b_cannot_read_alpha_meridian_case @backend', async ({ browser }) => {
    requireBackendOrThrow('tenant_b_cannot_read_alpha_meridian_case @backend');

    // A fresh, isolated context so the Beta cookie cannot share a browser
    // session with the other (alpha) tests in this project.
    const ctxB = await browser.newContext();
    const pageB = await ctxB.newPage();
    try {
      // Seed the Beta-tenant session into the isolated context.
      await seedAuthState(pageB, tenantBUser());

      const backendBase = apiBackendBase();

      // The seeded approved Meridian case lives in the ALPHA tenant. Beta must
      // be denied reading it. These are the REAL mounted Layer 4 routes
      // (`/v1/cases...`, not the Vite mock-only `/api/v1/agents/cases` paths).

      // 1. Single-case GET: the account is not visible under the Beta tenant,
      //    so the route fails closed with 404 (resource not found for this
      //    tenant). The denial status must be an auth/tenant-fail-closed code
      //    (401/403/404) - never a 200 carrying the alpha case body.
      const singleCase = await pageB.request.get(
        `${backendBase}/v1/cases/${MERIDIAN_CASE_ID}`,
        { headers: { Accept: 'application/json' } },
      );
      expect([401, 403, 404].includes(singleCase.status())).toBeTruthy();
      const singleCaseBody = await singleCase.text();
      expect(singleCaseBody.toLowerCase()).not.toContain('meridian');
      expect(singleCaseBody.toLowerCase()).not.toContain(
        'approved business case',
      );

      // 2. Case-list GET scoped to the Meridian account. Under the Beta tenant
      //    that account does not exist, so the route returns an EMPTY list
      //    (200, `{items:[],total:0}`). This is correct isolation - fail-closed
      //    and leak-free - so we assert the shape and the absence of any alpha
      //    case content rather than requiring an error status.
      const caseList = await pageB.request.get(
        `${backendBase}/v1/cases?account_id=${MERIDIAN_BACKEND_ACCOUNT_UUID}`,
        { headers: { Accept: 'application/json' } },
      );
      const listStatus = caseList.status();
      expect([200, 401, 403].includes(listStatus)).toBeTruthy();
      if (listStatus === 200) {
        const listBody = await caseList.json();
        expect(Array.isArray(listBody.items)).toBeTruthy();
        expect(listBody.total).toBe(0);
      }
      const caseBody = await caseList.text();
      expect(caseBody.toLowerCase()).not.toContain('meridian');
      expect(caseBody.toLowerCase()).not.toContain('approved business case');

      // Anonymous (no session) request must be rejected as well. Use a bare
            // context with NO seeded cookie to prove fail-closed for unauthenticated.
            const anonCtx = await browser.newContext();
            try {
              const anonPage = await anonCtx.newPage();
              const anon = await anonPage.request.get(
                `${backendBase}/v1/cases/${MERIDIAN_CASE_ID}`,
                { headers: { Accept: 'application/json' } },
              );
              expect([401, 403].includes(anon.status())).toBeTruthy();
            } finally {
              await anonCtx.close();
            }

      await expectNoCrossTenantLeakage(pageB);
    } finally {
      await ctxB.close();
    }
  });
});