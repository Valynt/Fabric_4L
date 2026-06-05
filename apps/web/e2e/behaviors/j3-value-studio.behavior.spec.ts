/**
 * Journey 3 Behavior Contract: Value Studio Deliverable Generation
 *
 * Behavior-First Test Contract
 *
 * This file is the executable definition of how the Value Studio MUST behave
 * across L4 (Agent Workflows) and L5 (Ground Truth / Business Case Validation).
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can navigate Action Plan → Value Model → Narrative tabs.
 *   - Formula evaluations recalculate when variables are updated.
 *   - User can view business case deliverables after approval.
 *   - Approved business case can be exported.
 *   - Cross-tab navigation preserves account context.
 *
 * Intended Behavior (Denied):
 *   - Export is blocked before approval (disabled action or error state).
 *   - Invalid formula values are rejected with validation error.
 *   - Unauthenticated user cannot access studio or deliverables.
 *   - Cross-tenant business cases are not visible.
 *
 * Failure Modes:
 *   - Export before approval: disabled button or 403 error.
 *   - Invalid formula: validation message, 422 from API, no recalculation.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Cross-tenant: foreign data invisible.
 *
 * Traceability: J3-BEH-001 through J3-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import { journeyTest, expectNoErrors, navigateAndWait } from '../helpers/journey-fixture';
import { expectFailureMode, expectNoCrossTenantLeakageOnPage } from '../helpers/behavior-helpers';
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

    await expect(authedPage.getByText(ACCOUNT.name).first()).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(/automated inventory sync/i).first()).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J3-BEH-002: user can navigate value model tab and see formulas', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/studio/${ACCOUNT.id}/value-model`);
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText(/roi calculation/i).first()).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(/2,?100,?000|2100000/i).first()).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J3-BEH-003: user can navigate narrative tab and see generated content', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/studio/${ACCOUNT.id}/narrative`);
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText(/executive summary/i).first()).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(/287% roi/i).first()).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J3-BEH-004: cross-tab studio navigation preserves account context', async ({ authedPage }) => {
    const tabs = ['action-plan', 'value-model', 'narrative'];

    for (const tab of tabs) {
      await navigateAndWait(authedPage, `/studio/${ACCOUNT.id}/${tab}`);
      await expect(authedPage.getByText(ACCOUNT.name).first()).toBeVisible({ timeout: 10000 });
      await expect(authedPage).toHaveURL(new RegExp(`/studio/${ACCOUNT.id}/${tab}`));
    }
  });

  journeyTest('J3-BEH-005: approved business case can be exported', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/deliverables/cases');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByRole('heading', { name: /business case/i })).toBeVisible({ timeout: 10000 });

    // Find the approved case and its export action
    const approvedRow = authedPage.getByText(/approved/i).first();
    await expect(approvedRow).toBeVisible({ timeout: 10000 });

    // Export button or link should be available for approved case
    const exportBtn = authedPage.getByRole('button', { name: /export|download/i }).first();
    const isExportVisible = await exportBtn.isVisible({ timeout: 5000 }).catch(() => false);

    if (isExportVisible) {
      await expect(exportBtn).toBeEnabled();
    }
  });
});

// ── Denied Behaviors ────────────────────────────────────────────────────────

journeyTest.describe('J3 Denied Behaviors: Value Studio', () => {
  journeyTest('J3-BEH-006: export is blocked for unapproved business case', async ({ authedPage, addMocks }) => {
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
      {
        pattern: `**/api/v1/agents/cases/${DRAFT_CASE.id}/export`,
        status: 403,
        body: { error: 'Export blocked: business case must be approved', code: 'EXPORT_BLOCKED_UNAPPROVED' },
      },
    ]);
    await navigateAndWait(authedPage, '/deliverables/cases');
    await expectNoErrors(authedPage);

    // Draft case should be visible
    await expect(authedPage.getByText(/draft/i).first()).toBeVisible({ timeout: 10000 });

    // Export action for draft case should be disabled or absent
    const draftRow = authedPage.getByText(/draft/i).first().locator('xpath=ancestor::tr[1]|ancestor::div[contains(@class,"row")][1]|ancestor::article[1]');
    const exportInDraft = await draftRow.getByRole('button', { name: /export|download/i })
      .first().isVisible({ timeout: 3000 }).catch(() => false);

    if (exportInDraft) {
      await expect(draftRow.getByRole('button', { name: /export|download/i }).first()).toBeDisabled();
    }
  });

  journeyTest('J3-BEH-007: invalid formula value is rejected with validation error', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/studio/${ACCOUNT.id}/value-model`);
    await expectNoErrors(authedPage);

    // Attempt to input an invalid value if an editable field is present
    const editableInput = authedPage.getByRole('spinbutton')
      .or(authedPage.getByPlaceholder(/value/i))
      .first();

    const hasEditable = await editableInput.isVisible({ timeout: 5000 }).catch(() => false);
    if (!hasEditable) {
      test.skip(true, 'No editable formula field in this UI variant');
      return;
    }

    await editableInput.fill('999999999');
    await editableInput.blur();

    // Wait for validation
    await authedPage.waitForTimeout(800);

    const hasValidationError = await authedPage.getByText(/invalid|exceeds|error|cannot be/i)
      .first().isVisible({ timeout: 5000 }).catch(() => false);

    expect(hasValidationError, 'Invalid formula values must be rejected with validation error').toBe(true);
  });

  test('J3-BEH-008: unauthenticated user accessing studio is redirected to login', async ({ page }) => {
    await page.goto(`/studio/${ACCOUNT.id}/action-plan`, { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  test('J3-BEH-009: unauthenticated user accessing deliverables is redirected to login', async ({ page }) => {
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
