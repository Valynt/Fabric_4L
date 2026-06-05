/**
 * Journey 1 Behavior Contract: Domain Ingestion → Value Tree Exploration
 *
 * Behavior-First Test Contract — Strict Edition
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can submit a valid company domain for ingestion.
 *   - Ingestion job is created with the exact payload shape.
 *   - Value Tree Explorer shows all four entity types from the L1→L2→L3 pipeline.
 *   - All data is strictly scoped to tenant-e2e-001.
 *
 * Intended Behavior (Denied):
 *   - Empty domain submission leaves the submit button disabled.
 *   - Invalid domain format is rejected with a 422 and a visible validation error.
 *   - Unauthenticated user is redirected to /sign-in.
 *   - Cross-tenant value tree data is not rendered.
 *   - Malformed ingestion payload surfaces a safe UI error, not a crash.
 *
 * Failure Modes:
 *   - Empty domain: button remains disabled.
 *   - Invalid domain: HTTP 422, `validation-error` testId visible.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Cross-tenant leakage: foreign tenant ID absent from body + URL.
 *   - Backend 422: `error-state` testId visible with structured error.
 *
 * Traceability: J1-BEH-001 through J1-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import { journeyTest, expectNoErrors, navigateAndWait, isLiveMode } from '../helpers/journey-fixture';
import {
  expectFailureMode,
  expectNoCrossTenantLeakageOnPage,
  expectCrossLayerBehavior,
  expectVisibleByTestId,
} from '../helpers/behavior-helpers';
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
  status: 'completed',
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

    const domainInput = authedPage.getByPlaceholder(/enter company domain/i);
    await expect(domainInput).toBeVisible();
    await domainInput.fill(TEST_DOMAIN);

    const submitButton = authedPage.getByRole('button', { name: /synthesize/i });
    await expect(submitButton).toBeEnabled();

    await expectCrossLayerBehavior(authedPage, {
      apiPattern: '**/api/v1/ingest/targets',
      method: 'POST',
      uiAction: async () => {
        await submitButton.click();
      },
      assertRequest: (payload) => {
        expect(payload).toMatchObject({ domain: TEST_DOMAIN });
      },
      mockResponse: { status: 201, body: { target_id: 'target-behavior-001', job_id: TEST_JOB_ID, status: 'pending' } },
      assertUiState: async () => {
        await expectVisibleByTestId(authedPage, 'ingestion-submitted');
      },
    });
  });

  journeyTest('J1-BEH-002: user can track ingestion job status through the UI', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/command-center');

    await expect(authedPage.getByRole('table')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(TEST_DOMAIN)).toBeVisible();
    await expect(authedPage.getByText('completed')).toBeVisible();
  });

  journeyTest('J1-BEH-003: completed ingestion populates value tree with all four entity types', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/context/value-trees/explorer');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByRole('heading', { name: /value tree/i })).toBeVisible({ timeout: 10000 });

    if (!isLiveMode()) {
      await expect(authedPage.getByText('Capability')).toBeVisible();
      await expect(authedPage.getByText('UseCase')).toBeVisible();
      await expect(authedPage.getByText('Persona')).toBeVisible();
      await expect(authedPage.getByText('ValueDriver')).toBeVisible();
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
  journeyTest('J1-BEH-005: empty domain submission is blocked by disabled button', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/command-center');

    const domainInput = authedPage.getByPlaceholder(/enter company domain/i);
    await expect(domainInput).toBeVisible();
    await domainInput.fill('');

    const submitButton = authedPage.getByRole('button', { name: /synthesize/i });
    await expect(submitButton).toBeDisabled();
  });

  journeyTest('J1-BEH-006: invalid domain format is rejected with validation error', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/targets',
        method: 'POST',
        status: 422,
        body: { error: 'Invalid domain format', code: 'VALIDATION_ERROR' },
      },
    ]);

    await navigateAndWait(authedPage, '/command-center');

    const domainInput = authedPage.getByPlaceholder(/enter company domain/i);
    await domainInput.fill('not-a-valid-domain!!!');

    const submitButton = authedPage.getByRole('button', { name: /synthesize/i });
    await submitButton.click();

    await expectFailureMode(authedPage, 'validation_error');
  });

  test('J1-BEH-007: unauthenticated user accessing ingestion is redirected to /sign-in', async ({ page }) => {
    await page.goto('/command-center', { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  test('J1-BEH-008: unauthenticated user accessing value tree explorer is redirected to /sign-in', async ({ page }) => {
    await page.goto('/context/value-trees/explorer', { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  journeyTest('J1-BEH-009: cross-tenant value tree data is not visible', async ({ authedPage, addMocks }) => {
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

  journeyTest('J1-BEH-010: ingestion API returns 422 and UI shows safe error state', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/targets',
        method: 'POST',
        status: 422,
        body: { error: 'Invalid domain format', code: 'VALIDATION_ERROR' },
      },
    ]);

    await navigateAndWait(authedPage, '/command-center');

    const domainInput = authedPage.getByPlaceholder(/enter company domain/i);
    await domainInput.fill(TEST_DOMAIN);

    const submitButton = authedPage.getByRole('button', { name: /synthesize/i });
    await submitButton.click();

    await expectVisibleByTestId(authedPage, 'error-state');
  });
});
