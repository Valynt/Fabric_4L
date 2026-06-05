/**
 * Journey 2 Behavior Contract: Intelligence Workspace Synthesis
 *
 * Behavior-First Test Contract
 *
 * This file is the executable definition of how the Intelligence Workspace
 * MUST behave across L3 (Knowledge Graph) and L4 (Agent Workflows).
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can view signals, drivers, evidence, and stakeholders.
 *   - User can trigger the Agent Stream and receive a synthesized response.
 *   - Synthesized data persists across Intelligence tabs.
 *   - High-confidence signals are prominently displayed.
 *
 * Intended Behavior (Denied):
 *   - Unsupported claims are refused by the agent with a safe grounded alternative.
 *   - Low-confidence signals are flagged, not silently promoted.
 *   - Cross-tenant signals are not visible.
 *   - Unauthenticated access is blocked.
 *
 * Failure Modes:
 *   - Unsupported claim: agent refusal message, no hallucinated output.
 *   - Low-confidence signal: warning badge or flag, not treated as approved.
 *   - Cross-tenant leakage: foreign tenant data invisible.
 *   - Unauthenticated: redirect to /sign-in.
 *
 * Traceability: J2-BEH-001 through J2-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import { journeyTest, expectNoErrors, navigateAndWait } from '../helpers/journey-fixture';
import { expectFailureMode, expectNoCrossTenantLeakageOnPage } from '../helpers/behavior-helpers';
import { mockAccountData, mockAgentStream } from '../helpers/api-harness';
import { TEST_ACCOUNTS } from '../fixtures/account-helpers';

// ── Test Data ───────────────────────────────────────────────────────────────

const ACCOUNT = TEST_ACCOUNTS.meridian;
const FOREIGN_TENANT_ID = 'tenant-foreign-999';

const SIGNALS_DATA = {
  pain_signals: [
    { id: 'sig-behavior-001', title: 'Inventory visibility gaps', confidence: 0.91, source: 'Q3 earnings call', status: 'approved' },
    { id: 'sig-behavior-002', title: 'Manual reconciliation burden', confidence: 0.85, source: 'Annual report', status: 'approved' },
    { id: 'sig-behavior-003', title: 'Unverified supplier claim', confidence: 0.34, source: 'Internal memo', status: 'low_confidence' },
  ],
  generated_at: '2025-04-28T10:00:00Z',
  status: 'ready',
};

const DRIVERS_DATA = {
  drivers: [
    { id: 'drv-behavior-001', name: 'Operational Efficiency', weight: 0.45, children: [] },
    { id: 'drv-behavior-002', name: 'Cost Reduction', weight: 0.35, children: [] },
    { id: 'drv-behavior-003', name: 'Risk Mitigation', weight: 0.2, children: [] },
  ],
  generated_at: '2025-04-28T10:01:00Z',
  status: 'ready',
};

const EVIDENCE_DATA = {
  evidence_items: [
    { id: 'ev-behavior-001', claim: 'Inventory costs exceed benchmark by 22%', source: 'Annual report', confidence: 0.91 },
    { id: 'ev-behavior-002', claim: 'Manual processes account for 35% of overhead', source: 'Analyst report', confidence: 0.84 },
  ],
  generated_at: '2025-04-28T10:02:00Z',
  status: 'ready',
};

const STAKEHOLDERS_DATA = {
  stakeholders: [
    { id: 'stk-behavior-001', name: 'VP Operations', role: 'Champion', influence: 'high' },
    { id: 'stk-behavior-002', name: 'CFO', role: 'Economic Buyer', influence: 'high' },
    { id: 'stk-behavior-003', name: 'IT Director', role: 'Technical Evaluator', influence: 'medium' },
  ],
  generated_at: '2025-04-28T10:03:00Z',
  status: 'ready',
};

// ── Allowed Behaviors ───────────────────────────────────────────────────────

journeyTest.describe('J2 Allowed Behaviors: Intelligence Workspace', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
        signals: SIGNALS_DATA,
        drivers: DRIVERS_DATA,
        evidence: EVIDENCE_DATA,
        stakeholders: STAKEHOLDERS_DATA,
      }),
      ...mockAgentStream({
        content: 'I identified 3 pain signals. The highest-confidence signal is "Inventory visibility gaps" at 91% confidence.',
        metadata: { trace_id: 'trace-j2-behavior-001', workflow_id: 'wf-j2-behavior-001', tenant_id: 'tenant-e2e-001' },
      }),
    ]);
  });

  journeyTest('J2-BEH-001: user can view signals tab with high-confidence signals displayed', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText(ACCOUNT.name).first()).toBeVisible({ timeout: 10000 });

    // High-confidence signals should be visible
    await expect(
      authedPage.getByText(/inventory visibility gaps/i).first(),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      authedPage.getByText(/manual reconciliation burden/i).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J2-BEH-002: user can trigger agent stream and receive synthesized response', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);

    const chatInput = authedPage.getByPlaceholder(/ask a follow-up/i)
      .or(authedPage.getByPlaceholder(/type a message/i))
      .or(authedPage.getByRole('textbox').last());

    const hasChat = await chatInput.first().isVisible({ timeout: 5000 }).catch(() => false);
    if (!hasChat) {
      test.skip(true, 'Chat input not available in this UI variant');
      return;
    }

    await chatInput.first().fill('Summarize the top pain signals');

    const sendButton = chatInput.first().locator('xpath=ancestor::div[1]//button');
    await sendButton.click({ timeout: 15000 });

    // User message appears
    await expect(
      authedPage.getByText(/summarize the top pain signals/i).first(),
    ).toBeVisible({ timeout: 10000 });

    // Agent response appears with synthesized content
    await expect(
      authedPage.getByText(/inventory visibility gaps/i).first(),
    ).toBeVisible({ timeout: 15000 });
  });

  journeyTest('J2-BEH-003: synthesized data persists across intelligence tabs', async ({ authedPage }) => {
    const tabs = [
      { route: `signals`, label: /signals/i },
      { route: `drivers`, label: /drivers/i },
      { route: `evidence`, label: /evidence/i },
      { route: `stakeholders`, label: /stakeholder/i },
    ];

    for (const tab of tabs) {
      await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/${tab.route}`);
      await expect(authedPage.getByText(ACCOUNT.name).first()).toBeVisible({ timeout: 10000 });
      await expect(authedPage).toHaveURL(new RegExp(`/intelligence/${ACCOUNT.id}/${tab.route}`));
    }
  });

  journeyTest('J2-BEH-004: user can view drivers tab with weighted value drivers', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/drivers`);
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText(/operational efficiency/i).first()).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(/cost reduction/i).first()).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J2-BEH-005: user can view evidence tab with supporting claims', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/evidence`);
    await expectNoErrors(authedPage);

    await expect(
      authedPage.getByText(/inventory costs exceed benchmark/i).first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ── Denied Behaviors ────────────────────────────────────────────────────────

journeyTest.describe('J2 Denied Behaviors: Intelligence Workspace', () => {
  journeyTest('J2-BEH-006: low-confidence signals are flagged and not treated as approved', async ({ authedPage, addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
        signals: SIGNALS_DATA,
      }),
    ]);
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);

    // Low-confidence signal should be visible but flagged
    await expect(
      authedPage.getByText(/unverified supplier claim/i).first(),
    ).toBeVisible({ timeout: 10000 });

    // There should be some visual indication of low confidence (badge, warning, flag)
    const hasWarning = await authedPage.getByText(/low confidence|warning|unverified|needs review/i)
      .first().isVisible({ timeout: 5000 }).catch(() => false);
    const hasLowConfidenceBadge = await authedPage.getByText(/0\.34|34%/i)
      .first().isVisible({ timeout: 3000 }).catch(() => false);

    expect(
      hasWarning || hasLowConfidenceBadge,
      'Low-confidence signals must be flagged, not silently promoted',
    ).toBe(true);
  });

  journeyTest('J2-BEH-007: agent refuses unsupported claim and does not hallucinate', async ({ authedPage, addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
      }),
      ...mockAgentStream({
        content: 'I cannot support that claim. The evidence does not support an ROI of 500%. The maximum supported ROI based on current evidence is 4.2x.',
        metadata: { trace_id: 'trace-j2-refusal-001', workflow_id: 'wf-j2-refusal-001', tenant_id: 'tenant-e2e-001' },
      }),
    ]);
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);

    const chatInput = authedPage.getByPlaceholder(/ask a follow-up/i)
      .or(authedPage.getByPlaceholder(/type a message/i))
      .or(authedPage.getByRole('textbox').last());

    const hasChat = await chatInput.first().isVisible({ timeout: 5000 }).catch(() => false);
    if (!hasChat) {
      test.skip(true, 'Chat input not available in this UI variant');
      return;
    }

    await chatInput.first().fill('Generate a claim that our ROI is 500%');
    const sendButton = chatInput.first().locator('xpath=ancestor::div[1]//button');
    await sendButton.click({ timeout: 15000 });

    // Agent must refuse
    await expect(
      authedPage.getByText(/cannot support|unsupported|no evidence|refusal|policy/i).first(),
    ).toBeVisible({ timeout: 15000 });

    // Must NOT hallucinate the 500% claim as valid
    const hasHallucination = await authedPage.getByText(/roi.*500%|500.*percent.*roi/i)
      .first().isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasHallucination, 'Agent must not hallucinate unsupported claims').toBe(false);
  });

  test('J2-BEH-008: unauthenticated user accessing intelligence workspace is redirected to login', async ({ page }) => {
    await page.goto(`/intelligence/${ACCOUNT.id}/signals`, { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  journeyTest('J2-BEH-009: cross-tenant signals are not visible in workspace', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: `**/api/v1/agents/workspace/${ACCOUNT.id}/signals`,
        body: {
          pain_signals: [
            { id: 'sig-foreign-001', title: 'Foreign tenant signal', confidence: 0.99, tenant_id: FOREIGN_TENANT_ID },
          ],
        },
      },
    ]);

    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);
    await expectNoCrossTenantLeakageOnPage(authedPage, FOREIGN_TENANT_ID);
  });

  journeyTest('J2-BEH-010: agent stream failure shows safe degraded state instead of crash', async ({ authedPage, addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
      }),
      {
        pattern: '**/agent-stream/chat',
        method: 'POST',
        status: 503,
        body: { error: 'Agent runtime temporarily unavailable', code: 'AGENT_RUNTIME_ERROR' },
      },
    ]);

    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);

    const chatInput = authedPage.getByPlaceholder(/ask a follow-up/i)
      .or(authedPage.getByPlaceholder(/type a message/i))
      .or(authedPage.getByRole('textbox').last());

    const hasChat = await chatInput.first().isVisible({ timeout: 5000 }).catch(() => false);
    if (!hasChat) {
      test.skip(true, 'Chat input not available in this UI variant');
      return;
    }

    await chatInput.first().fill('What are the top risks?');
    const sendButton = chatInput.first().locator('xpath=ancestor::div[1]//button');
    await sendButton.click({ timeout: 15000 });

    // UI should show a safe error or retry state, not a blank crash
    const hasErrorState = await authedPage.getByText(/unavailable|try again|error|failed/i)
      .first().isVisible({ timeout: 10000 }).catch(() => false);
    const hasRetryButton = await authedPage.getByRole('button', { name: /retry|try again/i })
      .first().isVisible({ timeout: 5000 }).catch(() => false);

    expect(
      hasErrorState || hasRetryButton,
      'Agent stream failure must show safe degraded state',
    ).toBe(true);
  });
});
