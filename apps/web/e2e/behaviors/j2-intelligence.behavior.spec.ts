/**
 * Journey 2 Behavior Contract: Intelligence Workspace Synthesis
 *
 * Behavior-First Test Contract — Strict Edition
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can view signals, drivers, evidence, and stakeholders.
 *   - User can trigger the Agent Stream via the chat input and receive a synthesized response.
 *   - Synthesized data persists across Intelligence tabs.
 *   - High-confidence signals are displayed without warning badges.
 *
 * Intended Behavior (Denied):
 *   - Unsupported claims are refused by the agent; no hallucinated output appears.
 *   - Low-confidence signals render a `low-confidence` warning badge.
 *   - Cross-tenant signals are not rendered.
 *   - Unauthenticated access redirects to /sign-in.
 *   - Agent stream failure renders an `error-state` testId, not a blank screen.
 *
 * Failure Modes:
 *   - Unsupported claim: `agent-refusal` testId visible; hallucinated claim absent.
 *   - Low-confidence signal: `low-confidence` testId visible.
 *   - Cross-tenant leakage: foreign tenant ID absent from body + URL.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Agent runtime 503: `error-state` testId visible.
 *
 * Traceability: J2-BEH-001 through J2-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import { journeyTest, expectNoErrors, navigateAndWait } from '../helpers/journey-fixture';
import {
  expectFailureMode,
  expectNoCrossTenantLeakageOnPage,
  expectCrossLayerBehavior,
  expectVisibleByTestId,
} from '../helpers/behavior-helpers';
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

    await expect(authedPage.getByText(ACCOUNT.name)).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Inventory visibility gaps')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Manual reconciliation burden')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J2-BEH-002: user triggers agent stream and receives synthesized response', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);

    const chatInput = authedPage.getByTestId('agent-chat-input');
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    await chatInput.fill('Summarize the top pain signals');

    await expectCrossLayerBehavior(authedPage, {
      apiPattern: '**/agent-stream/**',
      method: 'POST',
      uiAction: async () => {
        await authedPage.getByTestId('agent-send-button').click();
      },
      assertRequest: (payload: { message?: string }) => {
        expect(payload.message).toBe('Summarize the top pain signals');
      },
      mockResponse: {
        status: 200,
        body: {
          content: 'I identified 3 pain signals. The highest-confidence signal is "Inventory visibility gaps" at 91% confidence.',
          trace_id: 'trace-j2-behavior-001',
        },
      },
      assertUiState: async () => {
        await expect(authedPage.getByText('Summarize the top pain signals')).toBeVisible({ timeout: 10000 });
        await expect(authedPage.getByText('Inventory visibility gaps')).toBeVisible({ timeout: 15000 });
      },
    });
  });

  journeyTest('J2-BEH-003: synthesized data persists across intelligence tabs', async ({ authedPage }) => {
    const tabs = ['signals', 'drivers', 'evidence', 'stakeholders'];

    for (const tab of tabs) {
      await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/${tab}`);
      await expect(authedPage.getByText(ACCOUNT.name)).toBeVisible({ timeout: 10000 });
      await expect(authedPage).toHaveURL(new RegExp(`/intelligence/${ACCOUNT.id}/${tab}`));
    }
  });

  journeyTest('J2-BEH-004: user can view drivers tab with weighted value drivers', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/drivers`);
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('Operational Efficiency')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Cost Reduction')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J2-BEH-005: user can view evidence tab with supporting claims', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/evidence`);
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('Inventory costs exceed benchmark by 22%')).toBeVisible({ timeout: 10000 });
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

    await expect(authedPage.getByText('Unverified supplier claim')).toBeVisible({ timeout: 10000 });
    await expectVisibleByTestId(authedPage, 'low-confidence');
  });

  journeyTest('J2-BEH-007: agent refuses unsupported claim and does not hallucinate', async ({ authedPage, addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
      }),
      ...mockAgentStream({
        content: 'I cannot support a 500% ROI claim. The evidence supports a maximum ROI of 4.2x.',
        metadata: { trace_id: 'trace-j2-refusal-001', workflow_id: 'wf-j2-refusal-001', tenant_id: 'tenant-e2e-001' },
      }),
    ]);

    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);

    const chatInput = authedPage.getByTestId('agent-chat-input');
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    await chatInput.fill('Generate a claim that our ROI is 500%');
    await authedPage.getByTestId('agent-send-button').click();

    await expectVisibleByTestId(authedPage, 'agent-refusal');

    const hallucination = authedPage.getByText(/roi.*500%|500.*percent.*roi/i);
    await expect(hallucination).not.toBeVisible();
  });

  test('J2-BEH-008: unauthenticated user accessing intelligence workspace is redirected to /sign-in', async ({ page }) => {
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

  journeyTest('J2-BEH-010: agent stream failure shows safe error state instead of crash', async ({ authedPage, addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
      }),
      {
        pattern: '**/agent-stream/**',
        method: 'POST',
        status: 503,
        body: { error: 'Agent runtime temporarily unavailable', code: 'AGENT_RUNTIME_ERROR' },
      },
    ]);

    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);

    const chatInput = authedPage.getByTestId('agent-chat-input');
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    await chatInput.fill('What are the top risks?');
    await authedPage.getByTestId('agent-send-button').click();

    await expectVisibleByTestId(authedPage, 'error-state');
  });
});
