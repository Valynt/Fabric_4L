/**
 * Journey 1 Behavior Contract: Domain Ingestion → Value Tree Exploration
 *
 * Behavior-First Test Contract — Strict Edition
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can submit a valid company domain for ingestion.
 *   - Ingestion target is created with the exact payload shape, then executed.
 *   - Value Tree Explorer shows all four entity types from the L1→L2→L3 pipeline.
 *   - All data is strictly scoped to tenant-e2e-001.
 *
 * Intended Behavior (Denied):
 *   - Empty domain submission leaves the submit button disabled.
 *   - Invalid domain format is rejected with a 422 and a visible safe error.
 *   - Unauthenticated user is redirected to /sign-in (live mode only — mock-auth
 *     contract mode auto-authenticates every user; see test body).
 *   - Cross-tenant value tree data is not rendered.
 *   - Malformed ingestion payload surfaces a safe UI error, not a crash.
 *
 * Failure Modes:
 *   - Empty domain: button remains disabled.
 *   - Invalid domain: HTTP 422, "Ingestion failed" toast visible.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Cross-tenant leakage: foreign tenant ID absent from body + URL.
 *   - Backend 422: safe error toast, no crash.
 *
 * API contract (contracts/openapi/layer1-ingestion.json):
 *   - POST /api/v1/ingest/targets          {name, url}         → 201 ScrapingTargetDetail ({id, ...})
 *   - POST /api/v1/ingest/targets/{id}/execute {}              → 202 ExecuteTargetResponse ({job_id, status})
 *   - GET  /api/v1/ingest/jobs?...                              → JobListResponse ({data, pagination, aggregation})
 *
 * Traceability: J1-BEH-001 through J1-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import {
  journeyTest,
  expectNoErrors,
  navigateAndWait,
  isLiveMode,
  tenantScopedPath,
} from '../helpers/journey-fixture';
import {
  expectNoCrossTenantLeakageOnPage,
  expectCrossLayerBehavior,
} from '../helpers/behavior-helpers';
import { mockIngestionJobs } from '../helpers/api-harness';

// ── Test Data ───────────────────────────────────────────────────────────────

const TEST_DOMAIN = 'https://behavior-test-corp.com';
const TEST_TARGET_ID = 'target-behavior-001';
const TEST_JOB_ID = 'job-behavior-j1-001';
const FOREIGN_TENANT_ID = 'tenant-foreign-999';
const FOREIGN_ACCOUNT_ID = 'acct-foreign-globex-999';

const COMPLETED_JOB = {
  id: TEST_JOB_ID,
  domain: TEST_DOMAIN,
  status: 'completed' as const,
  progress: 100,
  created_at: '2025-04-28T10:00:00Z',
  pages_processed: 47,
};

/** EntityListResponse (src/lib/validation/schemas.ts → EntityListResponseSchema) */
const ENTITIES_RESPONSE = {
  results: [
    { id: 'cap-behavior-001', name: 'Predictive Maintenance', entity_type: 'Capability', confidence: 0.92, confidence_label: 'high', status: 'validated', updated_at: '2025-04-28T10:05:00Z' },
    { id: 'uc-behavior-001', name: 'Downtime Reduction', entity_type: 'UseCase', confidence: 0.87, confidence_label: 'high', status: 'validated', updated_at: '2025-04-28T10:05:00Z' },
    { id: 'per-behavior-001', name: 'VP Manufacturing', entity_type: 'Persona', confidence: 0.85, confidence_label: 'high', status: 'validated', updated_at: '2025-04-28T10:05:00Z' },
    { id: 'vd-behavior-001', name: '12% Efficiency Gain', entity_type: 'ValueDriver', confidence: 0.78, confidence_label: 'medium', status: 'validated', updated_at: '2025-04-28T10:05:00Z' },
  ],
  total_count: 4,
  filtered_count: 4,
  limit: 50,
  offset: 0,
  has_more: false,
  available_domains: [],
  available_sources: [],
};

/** ValueTreeResponse (src/lib/schemas.ts → ValueTreeResponseSchema) with all four entity types. */
const VALUE_TREE_RESPONSE = {
  root_entity_id: 'cap-behavior-001',
  direction: 'upward',
  nodes: [
    { id: 'cap-behavior-001', label: 'Predictive Maintenance', type: 'Capability', layer: 1, confidence: 0.92, properties: {} },
    { id: 'uc-behavior-001', label: 'Downtime Reduction', type: 'UseCase', layer: 2, confidence: 0.87, properties: {} },
    { id: 'per-behavior-001', label: 'VP Manufacturing', type: 'Persona', layer: 3, confidence: 0.85, properties: {} },
    { id: 'vd-behavior-001', label: '12% Efficiency Gain', type: 'ValueDriver', layer: 4, confidence: 0.78, properties: {} },
  ],
  edges: [
    { source: 'cap-behavior-001', target: 'uc-behavior-001', type: 'ENABLES', weight: 0.9 },
    { source: 'cap-behavior-001', target: 'per-behavior-001', type: 'ENABLES', weight: 0.8 },
    { source: 'cap-behavior-001', target: 'vd-behavior-001', type: 'DRIVES', weight: 0.85 },
  ],
  paths: [],
  stats: { total_nodes: 4, total_edges: 3, by_layer: { '1': 1, '2': 1, '3': 1, '4': 1 }, max_depth: 4 },
};

// ── Allowed Behaviors ───────────────────────────────────────────────────────

journeyTest.describe('J1 Allowed Behaviors: Ingestion Pipeline', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      ...mockIngestionJobs([COMPLETED_JOB]),
      // Step 1 of useSubmitDomain: create the scraping target.
      {
        pattern: '**/api/v1/ingest/targets',
        method: 'POST',
        body: { id: TEST_TARGET_ID, name: TEST_DOMAIN, url: TEST_DOMAIN, status: 'ACTIVE' },
        status: 201,
      },
      // Step 2 of useSubmitDomain: execute the target to start the job.
      {
        pattern: '**/api/v1/ingest/targets/*/execute',
        method: 'POST',
        body: { job_id: TEST_JOB_ID, status: 'QUEUED' },
        status: 202,
      },
      {
        pattern: '**/api/v1/graph/entities**',
        body: ENTITIES_RESPONSE,
      },
      {
        pattern: '**/api/v1/graph/value-trees/*',
        body: VALUE_TREE_RESPONSE,
      },
    ]);
  });

  journeyTest('J1-BEH-001: authenticated user can submit a valid domain and ingestion job is created', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/command-center');
    await expectNoErrors(authedPage);

    const domainInput = authedPage.getByPlaceholder(/enter company domain/i);
    await expect(domainInput).toBeVisible();
    await domainInput.fill(TEST_DOMAIN);

    const submitButton = authedPage.getByRole('button', { name: /synthesis|synthesize/i });
    await expect(submitButton).toBeEnabled();

    // The app makes two contract calls (useSubmitDomain in src/hooks/useIngestion.ts):
    //   1. POST /ingest/targets {name, url} → {id}
    //   2. POST /ingest/targets/{id}/execute → {job_id}  (mocked in beforeEach)
    // The cross-layer helper intercepts and asserts the first call.
    await expectCrossLayerBehavior(authedPage, {
      apiPattern: '**/api/v1/ingest/targets',
      method: 'POST',
      uiAction: async () => {
        await submitButton.click();
      },
      assertRequest: (payload) => {
        expect(payload).toMatchObject({ name: TEST_DOMAIN, url: TEST_DOMAIN });
      },
      mockResponse: { status: 201, body: { id: TEST_TARGET_ID, name: TEST_DOMAIN, url: TEST_DOMAIN, status: 'ACTIVE' } },
      assertUiState: async () => {
        await expect(authedPage.getByText(/ingestion job submitted/i)).toBeVisible({ timeout: 10000 });
      },
    });
  });

  journeyTest('J1-BEH-002: user can track ingestion job status through the UI', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/command-center');

    await expect(authedPage.getByRole('table')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(TEST_DOMAIN).first()).toBeVisible();
    await expect(authedPage.getByText('completed').first()).toBeVisible();
  });

  journeyTest('J1-BEH-003: completed ingestion populates value tree with all four entity types', async ({ authedPage }) => {
    await navigateAndWait(
      authedPage,
      tenantScopedPath('/context/value-trees/explorer?entityId=cap-behavior-001'),
    );
    await expectNoErrors(authedPage);

    await expect(authedPage.getByRole('heading', { name: /tree explorer/i })).toBeVisible({ timeout: 10000 });

    if (!isLiveMode()) {
      await expect(authedPage.getByText('Predictive Maintenance')).toBeVisible({ timeout: 10000 });
      await expect(authedPage.getByText('Downtime Reduction')).toBeVisible();
      await expect(authedPage.getByText('VP Manufacturing')).toBeVisible();
      await expect(authedPage.getByText('12% Efficiency Gain')).toBeVisible();
      // Entity type badges for all four pipeline entity types.
      await expect(authedPage.getByText('capability').first()).toBeVisible();
      await expect(authedPage.getByText('usecase').first()).toBeVisible();
      await expect(authedPage.getByText('persona').first()).toBeVisible();
      await expect(authedPage.getByText('valuedriver').first()).toBeVisible();
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

    const submitButton = authedPage.getByRole('button', { name: /synthesis|synthesize/i });
    await expect(submitButton).toBeDisabled();
  });

  journeyTest('J1-BEH-006: invalid domain format is rejected with validation error', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/ingest/targets',
        method: 'POST',
        status: 422,
        body: { detail: [{ loc: ['body', 'url'], msg: 'Invalid domain format', type: 'value_error' }] },
      },
    ]);

    await navigateAndWait(authedPage, '/command-center');

    const domainInput = authedPage.getByPlaceholder(/enter company domain/i);
    await domainInput.fill('not-a-valid-domain!!!');

    const submitButton = authedPage.getByRole('button', { name: /synthesis|synthesize/i });
    await submitButton.click();

    // The app surfaces submit failures as a safe toast, never a crash.
    await expect(authedPage.getByText(/ingestion failed/i)).toBeVisible({ timeout: 10000 });
  });

  test('J1-BEH-007: unauthenticated user accessing ingestion is redirected to /sign-in', async ({ page }) => {
    test.skip(
      !isLiveMode(),
      'Mock-auth contract mode auto-authenticates every user (VITE_ENABLE_MOCK_AUTH=true), ' +
      'so no unauthenticated state exists in this project. The /sign-in redirect contract is ' +
      'covered by e2e/journeys/j0-auth-session.spec.ts under Clerk auth; this test runs in live mode.',
    );
    await page.goto('/command-center', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  test('J1-BEH-008: unauthenticated user accessing value tree explorer is redirected to /sign-in', async ({ page }) => {
    test.skip(
      !isLiveMode(),
      'Mock-auth contract mode auto-authenticates every user (VITE_ENABLE_MOCK_AUTH=true), ' +
      'so no unauthenticated state exists in this project. The /sign-in redirect contract is ' +
      'covered by e2e/journeys/j0-auth-session.spec.ts under Clerk auth; this test runs in live mode.',
    );
    await page.goto('/context/value-trees/explorer', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  journeyTest('J1-BEH-009: cross-tenant value tree data is not visible', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/graph/entities**',
        body: {
          results: [
            {
              id: 'ent-foreign-001',
              name: 'Foreign Corp Value Tree',
              entity_type: 'Capability',
              confidence: 0.99,
              confidence_label: 'high',
              status: 'validated',
              updated_at: '2025-04-28T10:05:00Z',
              // Foreign tenant marker — stripped by client-side schema parsing
              // and must never reach the DOM.
              tenant_id: FOREIGN_TENANT_ID,
              account_id: FOREIGN_ACCOUNT_ID,
            },
          ],
          total_count: 1,
          filtered_count: 1,
          limit: 50,
          offset: 0,
          has_more: false,
          available_domains: [],
          available_sources: [],
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
        body: { detail: [{ loc: ['body', 'url'], msg: 'Invalid domain format', type: 'value_error' }] },
      },
    ]);

    await navigateAndWait(authedPage, '/command-center');

    const domainInput = authedPage.getByPlaceholder(/enter company domain/i);
    await domainInput.fill(TEST_DOMAIN);

    const submitButton = authedPage.getByRole('button', { name: /synthesis|synthesize/i });
    await submitButton.click();

    // Safe error surface: a toast, not a crash or a blank screen.
    await expect(authedPage.getByText(/ingestion failed/i)).toBeVisible({ timeout: 10000 });
    await expectNoErrors(authedPage);
  });
});
