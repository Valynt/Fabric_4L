/**
 * Journey 3 Behavior Contract: Value Studio Deliverable Generation
 *
 * Behavior-First Test Contract — Strict Edition
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can navigate Action Plan → Value Model → Narrative tabs.
 *   - Formula evaluations display the expected result.
 *   - User can view approved business case deliverables.
 *   - Approved business case exposes an enabled export action.
 *
 * Intended Behavior (Denied):
 *   - Draft business case export action is disabled (export-blocked testId).
 *   - Invalid formula value triggers a 422 and a `validation-error` testId.
 *   - Unauthenticated access redirects to /sign-in.
 *   - Cross-tenant business cases are not rendered.
 *
 * Failure Modes:
 *   - Export before approval: `export-blocked` testId visible, button disabled.
 *   - Invalid formula: HTTP 422, `validation-error` testId visible.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Cross-tenant leakage: foreign tenant ID absent from body + URL.
 *
 * Traceability: J3-BEH-001 through J3-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import { journeyTest, expectNoErrors, navigateAndWait } from '../helpers/journey-fixture';
import {
  expectFailureMode,
  expectNoCrossTenantLeakageOnPage,
  expectVisibleByTestId,
} from '../helpers/behavior-helpers';
import { mockAccountData } from '../helpers/api-harness';
import { TEST_ACCOUNTS } from '../fixtures/account-helpers';

// ── Test Data ───────────────────────────────────────────────────────────────

const ACCOUNT = TEST_ACCOUNTS.meridian;
const FOREIGN_TENANT_ID = 'tenant-foreign-999';

const ACTION_PLAN_DATA = {
  initiatives: [
    { id: 'init-behavior-001', name: 'Automated Inventory Sync', priority: 'high', timeline: 'Q3 2025', owner: 'VP Operations' },
    { id: 'init-behavior-002', name: 'Predictive Maintenance Platform', priority: 'medium', timeline: 'Q4 2025', owner: 'IT Director' },
  ],
  generated_at: '2025-04-28T10:00:00Z',
  status: 'ready',
};

const VALUE_MODEL_DATA = {
  variables: [
    { id: 'var-behavior-001', name: 'Annual Revenue', value: 500000000, unit: 'USD' },
    { id: 'var-behavior-002', name: 'Operational Cost Ratio', value: 0.32, unit: 'percentage' },
    { id: 'var-behavior-003', name: 'Projected Savings', value: 2100000, unit: 'USD' },
  ],
  formulas: [
    { id: 'frm-behavior-001', name: 'ROI Calculation', expression: '(savings / investment) * 100', result: 287 },
  ],
  projections: {
    conservative: 1200000,
    expected: 2100000,
    optimistic: 3400000,
  },
  generated_at: '2025-04-28T10:01:00Z',
  status: 'ready',
};

const NARRATIVE_DATA = {
  sections: [
    { id: 'sec-behavior-001', title: 'Executive Summary', content: 'Meridian Automotive faces significant supply chain challenges that our solution addresses through predictive automation.' },
    { id: 'sec-behavior-002', title: 'Value Proposition', content: 'Our solution delivers a projected 287% ROI over 3 years with a payback period of 9 months.' },
    { id: 'sec-behavior-003', title: 'Implementation Roadmap', content: 'Phase 1: Inventory sync automation (Q3 2025). Phase 2: Predictive maintenance (Q4 2025).' },
  ],
  generated_at: '2025-04-28T10:02:00Z',
  status: 'ready',
};

const APPROVED_CASE = {
  id: 'case-behavior-approved-001',
  account_id: ACCOUNT.id,
  title: 'Meridian Automotive - Supply Chain Optimization',
  status: 'approved',
  created_at: '2025-04-28T10:00:00Z',
  total_value: 2100000,
  document_url: '/exports/meridian-business-case.pdf',
};

const DRAFT_CASE = {
  id: 'case-behavior-draft-001',
  account_id: ACCOUNT.id,
  title: 'Meridian Automotive - Draft Case',
  status: 'draft',
  created_at: '2025-04-28T10:00:00Z',
  total_value: 450000,
  document_url: null,
};

// ── Allowed Behaviors ───────────────────────────────────────────────────────

journeyTest.describe('J3 Allowed Behaviors: Value Studio', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
        actionPlan: ACTION_PLAN_DATA,
        valueModel: VALUE_MODEL_DATA,
        narrative: NARRATIVE_DATA,
      }),
      {
        pattern: '**/api/v1/agents/cases',
        body: [APPROVED_CASE, DRAFT_CASE],
      },
      {
        pattern: `**/api/v1/agents/cases/${APPROVED_CASE.id}`,
        body: APPROVED_CASE,
      },
      {
        pattern: `**/api/v1/agents/cases/${APPROVED_CASE.id}/export`,
        body: { url: '/mock-export-approved.pdf', format: 'pdf' },
      },
    ]);
  });

  journeyTest('J3-BEH-001: user can navigate action plan tab and see initiatives', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/studio/${ACCOUNT.id}/action-plan`);
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText(ACCOUNT.name)).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Automated Inventory Sync')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J3-BEH-002: user can navigate value model tab and see formulas', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/studio/${ACCOUNT.id}/value-model`);
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('ROI Calculation')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('2,100,000')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J3-BEH-003: user can navigate narrative tab and see generated content', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/studio/${ACCOUNT.id}/narrative`);
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('Executive Summary')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('287% ROI')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J3-BEH-004: cross-tab studio navigation preserves account context', async ({ authedPage }) => {
    const tabs = ['action-plan', 'value-model', 'narrative'];

    for (const tab of tabs) {
      await navigateAndWait(authedPage, `/studio/${ACCOUNT.id}/${tab}`);
      await expect(authedPage.getByText(ACCOUNT.name)).toBeVisible({ timeout: 10000 });
      await expect(authedPage).toHaveURL(new RegExp(`/studio/${ACCOUNT.id}/${tab}`));
    }
  });

  journeyTest('J3-BEH-005: approved business case exposes enabled export action', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/deliverables/cases');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByRole('heading', { name: /business case/i })).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('approved')).toBeVisible({ timeout: 10000 });

    const exportBtn = authedPage.getByTestId(`export-case-${APPROVED_CASE.id}`);
    await expect(exportBtn).toBeVisible({ timeout: 10000 });
    await expect(exportBtn).toBeEnabled();
  });
});

// ── Denied Behaviors ────────────────────────────────────────────────────────

journeyTest.describe('J3 Denied Behaviors: Value Studio', () => {
  journeyTest('J3-BEH-006: export is blocked for draft business case', async ({ authedPage, addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
      }),
      {
        pattern: '**/api/v1/agents/cases',
        body: [DRAFT_CASE],
      },
      {
        pattern: `**/api/v1/agents/cases/${DRAFT_CASE.id}`,
        body: DRAFT_CASE,
      },
    ]);

    await navigateAndWait(authedPage, '/deliverables/cases');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('draft')).toBeVisible({ timeout: 10000 });

    const exportBtn = authedPage.getByTestId(`export-case-${DRAFT_CASE.id}`);
    await expect(exportBtn).toBeVisible({ timeout: 10000 });
    await expect(exportBtn).toBeDisabled();
    await expectVisibleByTestId(authedPage, 'export-blocked');
  });

  journeyTest('J3-BEH-007: invalid formula value is rejected with validation error', async ({ authedPage, addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
      }),
      {
        pattern: '**/api/v1/agents/workspace/**/value-model',
        method: 'PUT',
        status: 422,
        body: { error: 'Invalid assumption: value exceeds supported range', code: 'ASSUMPTION_VALIDATION_FAILED' },
      },
    ]);

    await navigateAndWait(authedPage, `/studio/${ACCOUNT.id}/value-model`);
    await expectNoErrors(authedPage);

    const editableInput = authedPage.getByTestId('value-model-variable-input');
    await expect(editableInput).toBeVisible({ timeout: 5000 });

    await editableInput.fill('999999999');
    await editableInput.blur();

    await expectFailureMode(authedPage, 'validation_error');
  });

  test('J3-BEH-008: unauthenticated user accessing studio is redirected to /sign-in', async ({ page }) => {
    await page.goto(`/studio/${ACCOUNT.id}/action-plan`, { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  test('J3-BEH-009: unauthenticated user accessing deliverables is redirected to /sign-in', async ({ page }) => {
    await page.goto('/deliverables/cases', { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  journeyTest('J3-BEH-010: cross-tenant business cases are not visible', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/cases',
        body: [
          {
            id: 'case-foreign-001',
            account_id: FOREIGN_TENANT_ID,
            title: 'Foreign Tenant Case',
            status: 'approved',
            tenant_id: FOREIGN_TENANT_ID,
          },
        ],
      },
    ]);

    await navigateAndWait(authedPage, '/deliverables/cases');
    await expectNoCrossTenantLeakageOnPage(authedPage, FOREIGN_TENANT_ID);
  });
});
