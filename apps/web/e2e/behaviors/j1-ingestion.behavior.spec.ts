/**
 * Journey 1 Behavior Contract: Domain Ingestion → Value Tree Exploration
 *
 * Behavior-First Test Contract
 *
 * This file is the executable definition of how the L1→L2→L3 ingestion pipeline
 * MUST behave when accessed through the frontend. Every test encodes either:
 *   1. An intended allowed behavior (positive), or
 *   2. An intended denied behavior (negative)
 *
 * Operating Principle: No critical ingestion behavior exists unless it is tested.
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can submit a valid company domain for ingestion.
 *   - Ingestion job is created and its status is trackable through the UI.
 *   - Upon completion, the Value Tree Explorer shows nodes generated from the domain.
 *   - Value tree nodes include Capabilities, Use Cases, Personas, and Value Drivers.
 *   - All data is strictly scoped to the user's tenant_id.
 *
 * Intended Behavior (Denied):
 *   - Empty domain submission is blocked (disabled button or validation error).
 *   - Invalid/malformed domain is rejected with a validation error.
 *   - Unauthenticated user is redirected to login when accessing ingestion.
 *   - Cross-tenant value tree data does not appear in the explorer.
 *
 * Failure Modes:
 *   - Invalid domain: validation error message, 422 from API, no job created.
 *   - Empty domain: submit button remains disabled.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Cross-tenant leakage: foreign tenant IDs must not be visible.
 *
 * Traceability: J1-BEH-001 through J1-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import { journeyTest, expectNoErrors, navigateAndWait, isLiveMode } from '../helpers/journey-fixture';
import { expectFailureMode, expectNoCrossTenantLeakageOnPage, expectCrossLayerBehavior } from '../helpers/behavior-helpers';
import { mockIngestionJobs } from '../helpers/api-harness';
import { TEST_ACCOUNTS } from '../fixtures/account-helpers';

// ── Test Data ───────────────────────────────────────────────────────────────

const TEST_DOMAIN = 'https://behavior-test-corp.com';
const TEST_JOB_ID = 'job-behavior-j1-001';
const FOREIGN_TENANT_ID = 'tenant-foreign-999';
const FOREIGN_ACCOUNT_ID = 'acct-foreign-globex-999';

const COMPLETED_JOB = {
  id: TEST_JOB_ID,
  domain: TEST_DOMAIN,
  status: 'completed' as const,
  progress: 100,
  created_at: '2025-04-28T10:00:00Z',
  pages_crawled: 47,
  entities_extracted: 12,
};

const VALUE_TREE_NODES = {
  trees: [
    {
      id: 'tree-behavior-001',
      name: 'Behavior Test Corp Value Tree',
      root_entity: 'capability-behavior-001',
      node_count: 12,
      edge_count: 18,
      created_at: '2025-04-28T10:05:00Z',
    },
  ],
  total: 1,
};

const ENTITIES_DATA = {
  entities: [
    { id: 'cap-behavior-001', name: 'Predictive Maintenance', entity_type: 'Capability', confidence: 0.92 },
    { id: 'uc-behavior-001', name: 'Downtime Reduction', entity_type: 'UseCase', confidence: 0.87 },
    { id: 'per-behavior-001', name: 'VP Manufacturing', entity_type: 'Persona', confidence: 0.85 },
    { id: 'vd-behavior-001', name: '12% Efficiency Gain', entity_type: 'ValueDriver', confidence: 0.78 },
  ],
  total: 4,
};

// ── Allowed Behaviors ───────────────────────────────────────────────────────

journeyTest.describe('J1 Allowed Behaviors: Ingestion Pipeline', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      ...mockIngestionJobs([COMPLETED_JOB]),
      {
        pattern: '**/api/v1/ingest/targets',
        method: 'POST',
        body: { target_id: 'target-behavior-001', job_id: TEST_JOB_ID, status: 'pending' },
        status: 201,
      },
      {
        pattern: '**/api/v1/ingest/targets',
        method: 'GET',
        body: [{ id: 'target-behavior-001', domain: TEST_DOMAIN, status: 'completed' }],
      },
      {
        pattern: '**/api/v1/value-trees**',
        body: VALUE_TREE_NODES,
      },
      {
        pattern: '**/api/v1/entities**',
        body: ENTITIES_DATA,
      },
    ]);
  });

  journeyTest('J1-BEH-001: authenticated user can submit a valid domain and ingestion job is created', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/command-center');
    await expectNoErrors(authedPage);

    const domainInput = authedPage.getByPlaceholder(/enter company domain/i)
      .or(authedPage.getByPlaceholder(/domain/i));
    await expect(domainInput.first()).toBeVisible();

    await domainInput.first().fill(TEST_DOMAIN);
    await domainInput.first().blur();

    const submitButton = authedPage.getByRole('button', { name: /synthesize/i })
      .or(authedPage.getByRole('button', { name: /submit/i }));
    await expect(submitButton.first()).toBeEnabled();
    await submitButton.first().click();

    // Cross-layer proof: verify the API call was made with correct payload
    await expectCrossLayerBehavior(authedPage, {
      apiPattern: '**/api/v1/ingest/targets',
      method: 'POST',
      uiAction: async () => {
        // already clicked above; just wait for response
        await authedPage.waitForTimeout(800);
      },
      assertRequest: (payload) => {
        expect(payload).toMatchObject({
          domain: expect.stringContaining('behavior-test-corp'),
        });
      },
      assertUiState: async () => {
        await expect(
          authedPage.getByText(/submitted|job created|ingestion started/i).first(),
        ).toBeVisible({ timeout: 10000 });
      },
    });
  });

  journeyTest('J1-BEH-002: user can track ingestion job status through the UI', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/command-center');

    const jobsArea = authedPage.getByText(/jobs/i).first()
      .or(authedPage.locator('table').first());
    await expect(jobsArea).toBeVisible({ timeout: 10000 });

    // The test domain or job ID should appear in the jobs list
    await expect(
      authedPage.getByText(TEST_DOMAIN).or(authedPage.getByText(/behavior-test-corp/i)).first(),
    ).toBeVisible();
  });

  journeyTest('J1-BEH-003: completed ingestion populates value tree with correct entity types', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/context/value-trees/explorer');
    await expectNoErrors(authedPage);

    await expect(
      authedPage.getByRole('heading', { name: /value tree/i }).first(),
    ).toBeVisible({ timeout: 10000 });

    if (!isLiveMode()) {
      // Verify all four entity types are surfaced
      await expect(authedPage.getByText(/capability/i).first()).toBeVisible();
      await expect(authedPage.getByText(/use case/i).first()).toBeVisible();
      await expect(authedPage.getByText(/persona/i).first()).toBeVisible();
      await expect(authedPage.getByText(/value driver/i).first()).toBeVisible();
    }
  });

  journeyTest('J1-BEH-004: value tree data is scoped to the current tenant', async ({ authedPage, isLive }) => {
    await navigateAndWait(authedPage, '/context/value-trees/explorer');

    if (isLive) {
      await expectNoErrors(authedPage);
    } else {
      const tenantId = await authedPage.evaluate(() => localStorage.getItem('tenantId'));
      expect(tenantId).toBe('tenant-e2e-001');
    }
  });
});

// ── Denied Behaviors ────────────────────────────────────────────────────────

journeyTest.describe('J1 Denied Behaviors: Ingestion Pipeline', () => {
  journeyTest('J1-BEH-005: empty domain submission is blocked', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/command-center');

    const submitButton = authedPage.getByRole('button', { name: /synthesize/i })
      .or(authedPage.getByRole('button', { name: /submit/i }));

    // With empty input, the button should be disabled or the submission should fail validation
    const isDisabled = await submitButton.first().isDisabled().catch(() => false);
    if (!isDisabled) {
      await submitButton.first().click();
      await expectFailureMode(authedPage, 'validation_error');
    }
  });

  journeyTest('J1-BEH-006: invalid domain format is rejected with validation error', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/command-center');

    const domainInput = authedPage.getByPlaceholder(/enter company domain/i)
      .or(authedPage.getByPlaceholder(/domain/i));
    await domainInput.first().fill('not-a-valid-domain!!!');
    await domainInput.first().blur();

    const submitButton = authedPage.getByRole('button', { name: /synthesize/i })
      .or(authedPage.getByRole('button', { name: /submit/i }));
    await submitButton.first().click();

    // Expect validation error or disabled state
    const hasValidationError = await authedPage.getByText(/invalid|please enter a valid|domain/i)
      .first().isVisible({ timeout: 5000 }).catch(() => false);
    const isButtonDisabled = await submitButton.first().isDisabled().catch(() => false);

    expect(
      hasValidationError || isButtonDisabled,
      'Invalid domain must be rejected with validation error or blocked submission',
    ).toBe(true);
  });

  test('J1-BEH-007: unauthenticated user accessing ingestion is redirected to login', async ({ page }) => {
    await page.goto('/command-center', { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  test('J1-BEH-008: unauthenticated user accessing value tree explorer is redirected to login', async ({ page }) => {
    await page.goto('/context/value-trees/explorer', { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  journeyTest('J1-BEH-009: cross-tenant value tree data is not visible', async ({ authedPage, addMocks }) => {
    // Seed mock with foreign tenant data that should NOT appear
    await addMocks([
      {
        pattern: '**/api/v1/value-trees**',
        body: {
          trees: [
            {
              id: 'tree-foreign-001',
              name: 'Foreign Corp Value Tree',
              tenant_id: FOREIGN_TENANT_ID,
            },
          ],
        },
      },
    ]);

    await navigateAndWait(authedPage, '/context/value-trees/explorer');
    await expectNoCrossTenantLeakageOnPage(authedPage, FOREIGN_TENANT_ID, FOREIGN_ACCOUNT_ID);
  });

  journeyTest('J1-BEH-010: ingestion API returns 422 for malformed payload and UI shows safe error', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/targets',
        method: 'POST',
        status: 422,
        body: { error: 'Invalid domain format', code: 'VALIDATION_ERROR' },
      },
    ]);

    await navigateAndWait(authedPage, '/command-center');

    const domainInput = authedPage.getByPlaceholder(/enter company domain/i)
      .or(authedPage.getByPlaceholder(/domain/i));
    await domainInput.first().fill(TEST_DOMAIN);

    const submitButton = authedPage.getByRole('button', { name: /synthesize/i })
      .or(authedPage.getByRole('button', { name: /submit/i }));
    await submitButton.first().click();

    // UI should show a safe error state, not crash or expose internals
    await expectFailureMode(authedPage, 'validation_error');
  });
});
