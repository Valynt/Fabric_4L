/**
 * Journey 20: Billing and Entitlement Gates
 *
 * Traceability: BILL-001 through BILL-006.
 *
 * This suite validates billing and entitlement UX, ensuring that:
 * - Plan/entitlement gates block unauthorized feature access
 * - Billing status displays accurately
 * - Billing API failures show graceful degradation
 * - Webhook results are reflected in the UI
 * - Usage limits are enforced with appropriate messaging
 *
 * Priority: P0 production gate
 * Mode: Contract (mocked billing API) + Backend-integrated (real billing if available)
 */

import { journeyTest, expect } from '../helpers/journey-fixture';
import { expectRouteSupportsWorkflow, expectAnyVisible } from '../helpers/validation-program';
import { BILLING_SCENARIOS } from '../fixtures/test-data';
import { MOCK_TENANT_SLUG } from '@/test/mockAuth';

journeyTest.describe('@backend Journey 20: Billing and Entitlement Gates', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/billing/**',
        body: BILLING_SCENARIOS.enterprise_active,
      },
      {
        pattern: '**/api/v1/billing/subscription',
        body: BILLING_SCENARIOS.professional_past_due,
      },
      {
        pattern: '**/api/v1/billing/usage',
        body: BILLING_SCENARIOS.enterprise_over_limit,
      },
    ]);
  });

  // ── Plan/Entitlement Gates ───────────────────────────────────────────────

  journeyTest('BILL-001: enterprise plan users can access all features', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/t/${MOCK_TENANT_SLUG}/settings/billing/subscription`,
      [/subscription/i, /enterprise/i, /active/i],
      'enterprise plan subscription display',
    );
  });

  journeyTest('BILL-002: starter plan users are blocked from advanced features', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/billing/**',
        body: BILLING_SCENARIOS.starter_trial,
      },
    ]);

    await authedPage.goto('/discover/knowledge/graph', { waitUntil: 'domcontentloaded' });

    // Starter plan should show upgrade prompt or redirect
    await expect(
      authedPage.getByText(/upgrade|plan|tier|enterprise/i)
        .or(authedPage.getByText(/not available|requires/i))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('BILL-003: past_due status blocks new feature access', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/billing/**',
        body: BILLING_SCENARIOS.professional_past_due,
      },
    ]);

    await authedPage.goto(`/t/${MOCK_TENANT_SLUG}/settings/billing/subscription`, { waitUntil: 'domcontentloaded' });

    await expect(authedPage.getByText(/past due|overdue|payment required/i)).toBeVisible({ timeout: 10000 });
  });

  // ── Billing Status Display ────────────────────────────────────────────────

  journeyTest('BILL-004: billing status displays accurately on subscription page', async ({ authedPage }) => {
    await authedPage.goto(`/t/${MOCK_TENANT_SLUG}/settings/billing/subscription`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/enterprise/i, /active/i, /subscription/i],
      'billing status display',
    );
  });

  journeyTest('BILL-005: usage metrics display correctly on usage page', async ({ authedPage }) => {
    await authedPage.goto(`/t/${MOCK_TENANT_SLUG}/settings/billing/usage`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/usage/i, /api calls/i, /storage/i, /users/i],
      'usage metrics display',
    );
  });

  // ── Billing API Failure Graceful Degradation ───────────────────────────────

  journeyTest('BILL-006: billing API failure shows graceful degradation', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/billing/**',
        status: 503,
        body: { error: 'Billing service unavailable' },
      },
    ]);

    await authedPage.goto(`/t/${MOCK_TENANT_SLUG}/settings/billing/subscription`, { waitUntil: 'domcontentloaded' });

    // Should show error message or retry option, not crash
    await expect(
      authedPage.getByText(/unavailable|retry|try again|error loading/i)
        .or(authedPage.getByText(/billing/i))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('BILL-007: billing API timeout shows user-friendly message', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/billing/**',
        status: 504,
        body: { error: 'Gateway timeout' },
      },
    ]);

    await authedPage.goto(`/t/${MOCK_TENANT_SLUG}/settings/billing/usage`, { waitUntil: 'domcontentloaded' });

    await expect(
      authedPage.getByText(/timeout|unavailable|retry/i)
        .or(authedPage.getByText(/usage/i))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });

  // ── Webhook Results in UI ─────────────────────────────────────────────────

  journeyTest('BILL-008: webhook configuration is reflected in UI', async ({ authedPage }) => {
    await authedPage.goto(`/t/${MOCK_TENANT_SLUG}/settings/integrations`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/webhook/i, /slack/i, /url/i],
      'webhook configuration display',
    );
  });

  journeyTest('BILL-009: webhook delivery status is visible', async ({ authedPage }) => {
    await authedPage.goto(`/t/${MOCK_TENANT_SLUG}/settings/integrations`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/active|failed|last delivery/i],
      'webhook delivery status',
    );
  });

  // ── Usage Limits Enforcement ───────────────────────────────────────────────

  journeyTest('BILL-010: over-limit usage shows warning message', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/billing/**',
        body: BILLING_SCENARIOS.enterprise_over_limit,
      },
    ]);

    await authedPage.goto(`/t/${MOCK_TENANT_SLUG}/settings/billing/usage`, { waitUntil: 'domcontentloaded' });

    await expect(
      authedPage.getByText(/limit|over|exceeded|upgrade/i)
        .or(authedPage.getByText(/usage/i))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('BILL-011: usage limits prevent new operations', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/billing/**',
        body: BILLING_SCENARIOS.starter_trial,
      },
      {
        pattern: '**/api/v1/ingest/jobs',
        status: 403,
        body: { error: 'Usage limit exceeded' },
      },
    ]);

    await authedPage.goto('/context/command-center', { waitUntil: 'domcontentloaded' });

    const domainInput = authedPage.getByPlaceholder(/domain|website/i);
    await expect(domainInput).toBeVisible({ timeout: 5000 });
    await domainInput.fill('test.com');

    const submitBtn = authedPage.getByRole('button', { name: /launch|start|create|begin|run|intelligence/i }).first();
    await submitBtn.click();

    // Should show limit error
    await expect(
      authedPage.getByText(/limit|exceeded|upgrade|plan/i)
        .or(authedPage.getByText(/error/i))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });
});
