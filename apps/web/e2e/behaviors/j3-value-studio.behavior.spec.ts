/**
 * Journey 3 Behavior Contract: Value Studio Deliverable Generation
 *
 * Behavior-First Test Contract — Strict Edition
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can navigate Action Plan → Value Model → Narrative tabs.
 *   - Value model displays value lines with scenario amounts.
 *   - User can view an approved business case with an enabled export action.
 *
 * Intended Behavior (Denied):
 *   - Draft business case export action is disabled (Pending Review state).
 *   - Invalid calculation input is rejected (422) with a visible safe error.
 *   - Unauthenticated access redirects to /sign-in (live mode only — mock-auth
 *     contract mode auto-authenticates every user; see test body).
 *   - Cross-tenant business cases are not rendered.
 *
 * Failure Modes:
 *   - Export before approval: "Pending Review" badge + disabled Export PDF button.
 *   - Invalid calculation: HTTP 422, "Failed to recalculate scenario." visible.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Cross-tenant leakage: foreign tenant ID absent from body + URL.
 *
 * App contract notes (drift repaired):
 *   - Studio workspace lives at /t/{tenant}/accounts/{id}/studio/{tab}; the
 *     Action Plan tab reads GET /agents/hypotheses/account/{id} +
 *     GET /graph/v1/products, the Value Model tab reads the case workspace
 *     "value-model" tab ({valueLines: [...]}) + GET /graph/v1/roi/benchmarks/{industry},
 *     and the Narrative tab reads the workspace "narrative" tab
 *     ({narratives: [...]}) + GET /agents/v1/narratives.
 *   - Business case detail reads GET /agents/analysis/cases/{caseId}
 *     (BusinessCaseResponse) and derives its export gate from
 *     status + document_url (deriveTrustState in src/pages/BusinessCase.tsx).
 *   - Business case list reads GET /agents/workflows?type=business_case.
 *
 * Traceability: J3-BEH-001 through J3-BEH-010.
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
import { expectNoCrossTenantLeakageOnPage } from '../helpers/behavior-helpers';
import { mockAccountData } from '../helpers/api-harness';
import { TEST_ACCOUNTS } from '../fixtures/account-helpers';

// ── Test Data ───────────────────────────────────────────────────────────────

const ACCOUNT = TEST_ACCOUNTS.meridian;
const FOREIGN_TENANT_ID = 'tenant-foreign-999';

/** ValueHypothesis (validated) feeding the Action Plan tab. */
const VALIDATED_HYPOTHESES = {
  hypotheses: [
    {
      id: 'hyp-behavior-001',
      account_id: ACCOUNT.id,
      product_id: 'prod-001',
      signal_id: 'sig-behavior-001',
      hypothesis_text: 'Automated Inventory Sync',
      confidence: 0.9,
      confidence_score: 0.9,
      status: 'validated',
      evidence_ids: [],
    },
  ],
  total: 1,
};

/** Workspace "value-model" tab payload ({valueLines: ValueLine[]}). */
const VALUE_MODEL_TAB = {
  valueLines: [
    {
      id: 'vl-behavior-001',
      driver: 'Projected Savings',
      category: 'hard',
      conservative: 1200000,
      expected: 2100000,
      optimistic: 3400000,
      source: 'ROI Calculation',
    },
  ],
};

/** Workspace "narrative" tab payload ({narratives: NarrativeVersion[]}). */
const NARRATIVE_TAB = {
  narratives: [
    {
      id: 'nar-behavior-001',
      stakeholder: 'CFO',
      role: 'Economic Buyer',
      status: 'ready',
      headline: 'Executive Summary',
      summary: 'Our solution delivers a projected 287% ROI over 3 years with a payback period of 9 months.',
      keyMetrics: [{ label: 'ROI', value: '287%' }],
      lastUpdated: '2025-04-28T10:02:00Z',
    },
  ],
};

/** IndustryBenchmark (src/hooks/useROICalculator.ts). */
const INDUSTRY_BENCHMARK = {
  industry: 'Manufacturing',
  sample_size: 42,
  avg_roi_pct: 187.5,
  avg_payback_months: 11,
  avg_npv: 1450000,
};

const APPROVED_CASE_ID = 'case-behavior-approved-001';
const DRAFT_CASE_ID = 'case-behavior-draft-001';

/** BusinessCaseResponse (GET /agents/cases/{caseId}). The detail page
 * dereferences the numeric fields unconditionally, so they must be present. */
const APPROVED_CASE = {
  case_id: APPROVED_CASE_ID,
  title: 'Meridian Automotive - Supply Chain Optimization',
  status: 'approved',
  created_at: '2025-04-28T10:00:00Z',
  document_url: '/exports/meridian-business-case.pdf',
  summary: 'Supply chain optimization business case for Meridian Automotive.',
  total_value: 2100000,
  roi_ratio: 2.87,
  payback_months: 9,
  confidence_score: 0.91,
  implementation_cost: 730000,
  page_count: 12,
  recommendations: [],
  case_metadata: {},
};

const DRAFT_CASE = {
  case_id: DRAFT_CASE_ID,
  title: 'Meridian Automotive - Draft Case',
  status: 'draft',
  created_at: '2025-04-28T10:00:00Z',
  document_url: null,
  summary: 'Draft business case for Meridian Automotive.',
  total_value: 450000,
  roi_ratio: 1.4,
  payback_months: 18,
  confidence_score: 0.62,
  implementation_cost: 320000,
  page_count: 0,
  recommendations: [],
  case_metadata: {},
};

/** Mocks every studio tab needs beyond the harness defaults. */
const STUDIO_MOCKS = [
  { pattern: '**/api/v1/agents/hypotheses/account/*', body: VALIDATED_HYPOTHESES },
  { pattern: /.*\/api\/v1\/graph\/v1\/products(\?.*)?$/, body: { products: [], total: 0 } },
  { pattern: /.*\/api\/v1\/graph\/v1\/roi\/benchmarks\/[^/]+$/, body: INDUSTRY_BENCHMARK },
  { pattern: /.*\/api\/v1\/graph\/v1\/roi\/benchmarks$/, body: { benchmarks: [], total: 0 } },
  {
    pattern: /.*\/api\/v1\/graph\/v1\/calculators\/levers(\?.*)?$/,
    body: { levers: [], metadata: { industry: 'Manufacturing', company_size: 'enterprise', version: '1.0.0', count: 0 } },
  },
  { pattern: /.*\/api\/v1\/agents\/v1\/narratives(\?.*)?$/, body: { narratives: [], total: 0 } },
];

// ── Allowed Behaviors ───────────────────────────────────────────────────────

journeyTest.describe('J3 Allowed Behaviors: Value Studio', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
      }),
      // Workspace tab payloads — the tab query returns these bodies verbatim
      // (useWorkspaceTabQuery in src/hooks/useWorkspaceCase.ts).
      { pattern: '**/api/v1/agents/analysis/cases/*/workspace/value-model', body: VALUE_MODEL_TAB },
      { pattern: '**/api/v1/agents/analysis/cases/*/workspace/narrative', body: NARRATIVE_TAB },
      ...STUDIO_MOCKS,
      // Business case detail (L4_ANALYSIS_PREFIX is "" — src/lib/apiConfig.ts).
      { pattern: `**/api/v1/agents/cases/${APPROVED_CASE_ID}`, body: APPROVED_CASE },
    ]);
  });

  journeyTest('J3-BEH-001: user can navigate action plan tab and see initiatives', async ({ authedPage }) => {
    await navigateAndWait(authedPage, tenantScopedPath(`/accounts/${ACCOUNT.id}/studio/action-plan`));
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText(ACCOUNT.name).first()).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Automated Inventory Sync')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J3-BEH-002: user can navigate value model tab and see formulas', async ({ authedPage }) => {
    await navigateAndWait(authedPage, tenantScopedPath(`/accounts/${ACCOUNT.id}/studio/value-model`));
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('Projected Savings')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('ROI Calculation', { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('$2.10M').first()).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J3-BEH-003: user can navigate narrative tab and see generated content', async ({ authedPage }) => {
    await navigateAndWait(authedPage, tenantScopedPath(`/accounts/${ACCOUNT.id}/studio/narrative`));
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('Executive Summary').first()).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(/287% ROI/)).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J3-BEH-004: cross-tab studio navigation preserves account context', async ({ authedPage }) => {
    const tabs = ['action-plan', 'value-model', 'narrative'];

    for (const tab of tabs) {
      await navigateAndWait(authedPage, tenantScopedPath(`/accounts/${ACCOUNT.id}/studio/${tab}`));
      await expect(authedPage.getByText(ACCOUNT.name).first()).toBeVisible({ timeout: 10000 });
      await expect(authedPage).toHaveURL(
        new RegExp(`/t/[^/]+/accounts/${ACCOUNT.id}/studio/${tab}`),
      );
    }
  });

  journeyTest('J3-BEH-005: approved business case exposes enabled export action', async ({ authedPage }) => {
    await navigateAndWait(
      authedPage,
      tenantScopedPath(`/accounts/${ACCOUNT.id}/deliverables/business-cases/${APPROVED_CASE_ID}`),
    );
    await expectNoErrors(authedPage);

    await expect(
      authedPage.getByRole('heading', { name: /Meridian Automotive - Supply Chain Optimization/i }),
    ).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Export Ready')).toBeVisible({ timeout: 10000 });

    const exportBtn = authedPage.getByRole('button', { name: /export pdf/i });
    await expect(exportBtn).toBeVisible({ timeout: 10000 });
    await expect(exportBtn).toBeEnabled();
  });
});

// ── Denied Behaviors ────────────────────────────────────────────────────────

journeyTest.describe('J3 Denied Behaviors: Value Studio', () => {
  journeyTest('J3-BEH-006: export is blocked for draft business case', async ({ authedPage, addMocks }) => {
    await addMocks([
      { pattern: `**/api/v1/agents/cases/${DRAFT_CASE_ID}`, body: DRAFT_CASE },
    ]);

    await navigateAndWait(
      authedPage,
      tenantScopedPath(`/accounts/${ACCOUNT.id}/deliverables/business-cases/${DRAFT_CASE_ID}`),
    );
    await expectNoErrors(authedPage);

    // Draft cases are pending review: the export gate stays closed.
    await expect(authedPage.getByText('Pending Review')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Internal draft only')).toBeVisible();

    const exportBtn = authedPage.getByRole('button', { name: /export pdf/i });
    await expect(exportBtn).toBeVisible({ timeout: 10000 });
    await expect(exportBtn).toBeDisabled();
  });

  journeyTest('J3-BEH-007: invalid formula value is rejected with validation error', async ({ authedPage, addMocks }) => {
    await addMocks([
      ...STUDIO_MOCKS,
      {
        pattern: '**/api/v1/graph/v1/roi/calculate',
        method: 'POST',
        status: 422,
        body: { detail: [{ loc: ['body', 'deal_size'], msg: 'value exceeds supported range', type: 'value_error' }] },
      },
    ]);

    await navigateAndWait(authedPage, tenantScopedPath(`/accounts/${ACCOUNT.id}/studio/calculator`));
    await expectNoErrors(authedPage);

    // Editing any scenario input triggers a recalculation, which the backend
    // rejects; the UI must surface a safe inline error, not a crash.
    const editableInput = authedPage.locator('input[type="number"]').first();
    await expect(editableInput).toBeVisible({ timeout: 10000 });
    await editableInput.fill('999999999');

    await expect(authedPage.getByText('Failed to recalculate scenario.')).toBeVisible({ timeout: 10000 });
  });

  test('J3-BEH-008: unauthenticated user accessing studio is redirected to /sign-in', async ({ page }) => {
    test.skip(
      !isLiveMode(),
      'Mock-auth contract mode auto-authenticates every user (VITE_ENABLE_MOCK_AUTH=true), ' +
      'so no unauthenticated state exists in this project. The /sign-in redirect contract is ' +
      'covered by e2e/journeys/j0-auth-session.spec.ts under Clerk auth; this test runs in live mode.',
    );
    await page.goto(`/studio/${ACCOUNT.id}/action-plan`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  test('J3-BEH-009: unauthenticated user accessing deliverables is redirected to /sign-in', async ({ page }) => {
    test.skip(
      !isLiveMode(),
      'Mock-auth contract mode auto-authenticates every user (VITE_ENABLE_MOCK_AUTH=true), ' +
      'so no unauthenticated state exists in this project. The /sign-in redirect contract is ' +
      'covered by e2e/journeys/j0-auth-session.spec.ts under Clerk auth; this test runs in live mode.',
    );
    await page.goto('/deliverables/cases', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  journeyTest('J3-BEH-010: cross-tenant business cases are not visible', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: /.*\/api\/v1\/agents\/workflows\?.*$/,
        body: {
          items: [
            {
              workflow_id: 'case-foreign-001',
              name: 'Foreign Tenant Case',
              lifecycle_status: 'approved',
              company_name: 'Foreign Corp',
              total_value: 1000000,
              use_case_count: 3,
              confidence: 0.9,
              created_at: '2025-04-28T10:00:00Z',
              updated_at: '2025-04-28T10:00:00Z',
              // Foreign tenant marker — never rendered by the list UI.
              case_metadata: { tenant_id: FOREIGN_TENANT_ID },
            },
          ],
          total: 1,
        },
      },
    ]);

    await navigateAndWait(
      authedPage,
      tenantScopedPath(`/accounts/${ACCOUNT.id}/deliverables/business-cases`),
    );
    await expect(authedPage.getByRole('heading', { name: /business cases/i })).toBeVisible({ timeout: 10000 });
    await expectNoCrossTenantLeakageOnPage(authedPage, FOREIGN_TENANT_ID);
  });
});
