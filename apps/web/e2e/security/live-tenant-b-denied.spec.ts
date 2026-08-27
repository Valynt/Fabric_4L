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
import { seedAuthState, E2E_TENANT_B_USER } from '../fixtures/auth-helpers';

const MERIDIAN_CASE_ID = 'case-meridian-e2e-001';

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
      await seedAuthState(pageB, E2E_TENANT_B_USER);

      const backendBase = apiBackendBase();

      // The seeded approved Meridian case lives in the ALPHA tenant. Beta must
      // be denied reading it.
      const caseList = await pageB.request.get(`${backendBase}/api/v1/agents/cases`, {
        headers: { Accept: 'application/json' },
      });
      expect([401, 403, 404].includes(caseList.status())).toBeTruthy();

      const caseBody = await caseList.text();
      // Fail-closed: the response must not contain the alpha case content.
      expect(caseBody.toLowerCase()).not.toContain('meridian');
      expect(caseBody.toLowerCase()).not.toContain('approved business case');

      // Anonymous (no session) request must be rejected as well. Use a bare
            // context with NO seeded cookie to prove fail-closed for unauthenticated.
            const anonCtx = await browser.newContext();
            try {
              const anonPage = await anonCtx.newPage();
              const anon = await anonPage.request.get(
                `${backendBase}/api/v1/agents/cases/${MERIDIAN_CASE_ID}`,
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