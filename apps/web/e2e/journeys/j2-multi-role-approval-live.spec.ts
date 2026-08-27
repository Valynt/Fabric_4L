/**
 * Journey 2: Continuous Live Reviewer/Admin Governance — @backend
 *
 * Traceability: MULTIROLE-APPROVAL-001, REVIEWER-AUTHZ-001, CONTENT-ADMIN-WRITE-001.
 *
 * This suite exercises the live role-authenticated governance review boundary
 * against the running backend, working at the authorization boundary directly:
 *
 *   1. A reviewer session can list governance reviews (200 + JSON array).
 *   2. A reviewer session is DENIED the content_admin-only write surface
 *      (create review → exactly 403, not 401/405).
 *   3. The admin session can create a review and post an approved decision
 *      (200/201) — proving the write path is gated to content_admin+.
 *
 * The reviewer list must return 200 with an array body: the reviewer has
 * proven authentication via that successful request, so the subsequent
 * create-denial must be exactly 403. Accepting 405 can conceal a route or
 * method regression on the same POST route the admin test exercises.
 *
 * This spec targets seeded identities only (no live LLM generation) and is
 * tagged `@backend` so it only runs in the `backend-integrated` Playwright
 * project, failing closed via `requireBackendOrThrow` when no backend URL is
 * configured.
 *
 * NOTE: `require_content_admin` (backend) permits SUPER_ADMIN / TENANT_ADMIN /
 * CONTENT_ADMIN. The seeded `reviewer` session role is a non-content role, so
 * it must be rejected from governance writes. This is the authorization
 * boundary the spec asserts; it does NOT depend on any UI routing.
 */
import { test, expect } from '../fixtures/contract-test';
import {
  requireBackendOrThrow,
  expectNoCrossTenantLeakage,
} from '../helpers/validation-program';
import {
  BACKEND_E2E_TENANT_ID,
  E2E_REVIEWER_USER,
  seedAuthState,
} from '../fixtures/auth-helpers';

const TENANT_SLUG = 'e2e-test';

function backendGovernanceBase(): string {
  const backendUrl = process.env.PLAYWRIGHT_BACKEND_URL;
  if (!backendUrl) {
    throw new Error('PLAYWRIGHT_BACKEND_URL is required for j2 @live governance assertions.');
  }
  return `${backendUrl.replace(/\/$/, '')}/v1/governance`;
}

function newCorrelationId(): string {
  return `corr-live-${Date.now()}`;
}

function reviewPayload(reviewId: string, correlationId: string) {
  return {
    review_id: reviewId,
    status: 'submitted',
    subject_type: 'business_case',
    submitted_at: new Date().toISOString(),
    lineage: {
      business_case_id: 'case-draft-001',
      value_model_id: null,
      correlation_id: correlationId,
      trace_id: correlationId,
    },
  };
}

test.describe('Journey 2: Reviewer/Admin Live Governance', () => {
  test('reviewer_can_list_reviews_but_write_is_denied @backend', async ({ page }) => {
    requireBackendOrThrow('journey2_reviewer_can_list_reviews_but_write_is_denied @backend');

    await seedAuthState(page, E2E_REVIEWER_USER);
        await page.goto('/', { waitUntil: 'domcontentloaded' });

    const base = backendGovernanceBase();

    // 1. Reviewer may LIST governance reviews (auth-only surface). This must
    //    return 200 with an array body; accepting 401/403 here would let a
    //    misconfigured auth surface masquerade as the intended behavior.
    const list = await page.request.get(`${base}/reviews`, {
      headers: { Accept: 'application/json' },
    });
    expect(list.status()).toBe(200);
    const listBody = await list.json();
    const listItems = Array.isArray(listBody)
      ? listBody
      : Array.isArray((listBody as { data?: unknown })?.data)
        ? ((listBody as { data: unknown[] }).data)
        : Array.isArray((listBody as { items?: unknown })?.items)
          ? ((listBody as { items: unknown[] }).items)
          : null;
    expect(Array.isArray(listItems), `governance reviews list body must be an array, got: ${JSON.stringify(listBody).slice(0, 200)}`).toBe(true);

    // 2. Reviewer must NOT be able to CREATE a review (content_admin gated).
    //    The reviewer has already proven authentication via the successful
    //    list request above, so the expected result is exactly 403 — not 401
    //    (unauthenticated) and not 405 (route/method regression on the same
    //    POST route the admin test exercises below).
    const create = await page.request.post(`${base}/reviews`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify(reviewPayload(`rev-live-denied-${Date.now()}`, newCorrelationId())),
    });
    expect(create.status()).toBe(403);

    await expectNoCrossTenantLeakage(page);
  });

  test('admin_can_create_review_and_decision @backend', async ({ page }) => {
    requireBackendOrThrow('journey2_admin_can_create_review_and_decision @backend');

    await seedAuthState(page, {
          id: 'test-user-e2e',
          email: 'e2e@valuefabric.test',
          role: 'admin',
          tenantId: BACKEND_E2E_TENANT_ID,
          tenantSlug: TENANT_SLUG,
        });
        await page.goto('/', { waitUntil: 'domcontentloaded' });

    const base = backendGovernanceBase();
    const reviewId = `review-live-${Date.now()}`;
    const correlationId = newCorrelationId();

    const create = await page.request.post(`${base}/reviews`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify(reviewPayload(reviewId, correlationId)),
    });
    expect([201, 200].includes(create.status())).toBeTruthy();

    const decide = await page.request.post(`${base}/reviews/${reviewId}/decisions`, {
      headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({
        decision_id: `decision-live-${Date.now()}`,
        review_id: reviewId,
        decision: 'approved',
        decided_at: new Date().toISOString(),
        immutable_audit_hash: 'sha256:unset',
        lineage: {
          business_case_id: 'case-draft-001',
          value_model_id: null,
          correlation_id: correlationId,
          trace_id: correlationId,
        },
      }),
    });
    expect([201, 200].includes(decide.status())).toBeTruthy();

    await expectNoCrossTenantLeakage(page);
  });
});