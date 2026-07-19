/**
 * Journey 2 Behavior Contract: Intelligence Workspace Synthesis
 *
 * Behavior-First Test Contract — Strict Edition
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can view signals, drivers, evidence, and stakeholders.
 *   - User can trigger the Agent Stream via the right-rail chat and receive a
 *     synthesized response.
 *   - Synthesized data persists across Intelligence tabs.
 *   - High-confidence signals are displayed without warning badges.
 *
 * Intended Behavior (Denied):
 *   - Unsupported claims are refused by the agent; no hallucinated output appears.
 *   - Low-confidence signals render a low-confidence marker (percentage +
 *     non-accepted status badge).
 *   - Cross-tenant signals are not rendered.
 *   - Unauthenticated access redirects to /sign-in (live mode only — mock-auth
 *     contract mode auto-authenticates every user; see test body).
 *   - Agent stream failure renders a safe agent error message, not a blank screen.
 *
 * Failure Modes:
 *   - Unsupported claim: refusal content visible; hallucinated claim absent.
 *   - Low-confidence signal: confidence percentage + "Assumption" badge visible.
 *   - Cross-tenant leakage: foreign tenant ID absent from body + URL.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Agent runtime 503: "I couldn't complete that request" agent message visible.
 *
 * App contract notes (drift repaired):
 *   - Workspace tabs read GET /api/v1/agents/analysis/cases/{caseId}/workspace/{tab}
 *     with shape `{ <tab>: [...] }` (src/hooks/useWorkspaceCase.ts).
 *   - The agent chat lives in the workspace right rail ("Agent Stream" mode) on
 *     the Hypotheses tab. It POSTs {messages: [{role, content}], ...} to
 *     /agents/agent-stream/chat/stream (SSE) and falls back to the legacy JSON
 *     endpoint /agents/agent-stream/chat on 404 (src/agui/AgentEventClient.ts).
 *
 * Traceability: J2-BEH-001 through J2-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import { journeyTest, expectNoErrors, navigateAndWait, isLiveMode } from '../helpers/journey-fixture';
import {
  expectNoCrossTenantLeakageOnPage,
  expectCrossLayerBehavior,
} from '../helpers/behavior-helpers';
import { mockAccountData, mockAgentStream } from '../helpers/api-harness';
import { TEST_ACCOUNTS } from '../fixtures/account-helpers';

// ── Test Data ───────────────────────────────────────────────

const ACCOUNT = TEST_ACCOUNTS.meridian;
const FOREIGN_TENANT_ID = 'tenant-foreign-999';

const AGENT_ANSWER =
  'I identified 3 pain signals. The highest-confidence signal is "Inventory visibility gaps" at 91% confidence.';

/** WorkspaceSignal[] (features/intelligence-workspace/tabs/_shared/types.ts) */
const SIGNALS = [
  { id: 'sig-behavior-001', title: 'Inventory visibility gaps', type: 'pain', confidence: 0.91, source: 'Q3 earnings call', status: 'accepted' },
  { id: 'sig-behavior-002', title: 'Manual reconciliation burden', type: 'pain', confidence: 0.85, source: 'Annual report', status: 'accepted' },
  { id: 'sig-behavior-003', title: 'Unverified supplier claim', type: 'risk', confidence: 0.34, source: 'Internal memo', status: 'assumption' },
];

/** WorkspaceDriver[] */
const DRIVERS = [
  { id: 'drv-behavior-001', name: 'Operational Efficiency', contribution: 45 },
  { id: 'drv-behavior-002', name: 'Cost Reduction', contribution: 35 },
  { id: 'drv-behavior-003', name: 'Risk Mitigation', contribution: 20 },
];

/** WorkspaceEvidenceItem[] */
const EVIDENCE = [
  { id: 'ev-behavior-001', title: 'Inventory cost benchmark', claim: 'Inventory costs exceed benchmark by 22%', source: 'Annual report', confidence: 0.91 },
  { id: 'ev-behavior-002', title: 'Manual process overhead', claim: 'Manual processes account for 35% of overhead', source: 'Analyst report', confidence: 0.84 },
];

/** WorkspaceStakeholder[] */
const STAKEHOLDERS = [
  { id: 'stk-behavior-001', name: 'VP Operations', title: 'Champion', influence: 'high' },
  { id: 'stk-behavior-002', name: 'CFO', title: 'Economic Buyer', influence: 'high' },
  { id: 'stk-behavior-003', name: 'IT Director', title: 'Technical Evaluator', influence: 'medium' },
];

const HYPOTHESES_EMPTY = {
  pattern: '**/api/v1/agents/hypotheses/account/*',
  body: { hypotheses: [], total: 0 },
};

/** Open the right-rail agent chat on the Hypotheses tab. */
async function openAgentStream(authedPage: import('@playwright/test').Page) {
  await authedPage.getByRole('button', { name: /agent stream/i }).click();
  const chatInput = authedPage.getByPlaceholder(/ask a follow-up/i);
  await expect(chatInput).toBeVisible({ timeout: 10000 });
  return chatInput;
}

// ── Allowed Behaviors ───────────────────────────────────────────────────────

journeyTest.describe('J2 Allowed Behaviors: Intelligence Workspace', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
        signals: SIGNALS,
        drivers: DRIVERS,
        evidence: EVIDENCE,
        stakeholders: STAKEHOLDERS,
      }),
      HYPOTHESES_EMPTY,
      ...mockAgentStream({
        content: AGENT_ANSWER,
        metadata: { trace_id: 'trace-j2-behavior-001', workflow_id: 'wf-j2-behavior-001', tenant_id: 'tenant-e2e-001' },
      }),
    ]);
  });

  journeyTest('J2-BEH-001: user can view signals tab with high-confidence signals displayed', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText(ACCOUNT.name).first()).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Inventory visibility gaps')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Manual reconciliation burden')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J2-BEH-002: user triggers agent stream and receives synthesized response', async ({ authedPage }) => {
    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/hypotheses`);

    const chatInput = await openAgentStream(authedPage);
    await chatInput.fill('Summarize the top pain signals');

    await expectCrossLayerBehavior(authedPage, {
      apiPattern: '**/agent-stream/chat',
      method: 'POST',
      uiAction: async () => {
        await authedPage.getByRole('button', { name: /send message/i }).click();
      },
      assertRequest: (payload: { messages?: Array<{ role: string; content: string }> }) => {
        const contents = (payload.messages ?? []).map((m) => m.content);
        expect(contents).toContain('Summarize the top pain signals');
      },
      mockResponse: {
        status: 200,
        body: {
          content: AGENT_ANSWER,
          metadata: { trace_id: 'trace-j2-behavior-001', workflow_id: 'wf-j2-behavior-001', tenant_id: 'tenant-e2e-001' },
        },
      },
      assertUiState: async () => {
        await expect(authedPage.getByText('Summarize the top pain signals')).toBeVisible({ timeout: 10000 });
        await expect(authedPage.getByText(/i identified 3 pain signals/i)).toBeVisible({ timeout: 15000 });
      },
    });
  });

  journeyTest('J2-BEH-003: synthesized data persists across intelligence tabs', async ({ authedPage }) => {
    const tabs = ['signals', 'drivers', 'evidence', 'stakeholders'];

    for (const tab of tabs) {
      await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/${tab}`);
      await expect(authedPage.getByText(ACCOUNT.name).first()).toBeVisible({ timeout: 10000 });
      // Legacy /intelligence/:accountId/:tabId redirects to the canonical
      // tenant-scoped workspace route.
      await expect(authedPage).toHaveURL(
        new RegExp(`/t/[^/]+/accounts/${ACCOUNT.id}/intelligence/${tab}`),
      );
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
        signals: SIGNALS,
      }),
    ]);

    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/signals`);

    await expect(authedPage.getByText('Unverified supplier claim')).toBeVisible({ timeout: 10000 });
    // Low-confidence markers: the 34% confidence readout and the non-accepted
    // "Assumption" status badge (accepted signals show "Accepted").
    await expect(authedPage.getByText('34%').first()).toBeVisible();
    await expect(authedPage.getByText('Assumption').first()).toBeVisible();
  });

  journeyTest('J2-BEH-007: agent refuses unsupported claim and does not hallucinate', async ({ authedPage, addMocks }) => {
    const refusal =
      'I cannot support a 500% ROI claim. The evidence supports a maximum ROI of 4.2x.';
    await addMocks([
      ...mockAccountData(ACCOUNT.id, {
        account: { name: ACCOUNT.name, industry: ACCOUNT.industry, tier: ACCOUNT.tier },
      }),
      HYPOTHESES_EMPTY,
      ...mockAgentStream({
        content: refusal,
        metadata: { trace_id: 'trace-j2-refusal-001', workflow_id: 'wf-j2-refusal-001', tenant_id: 'tenant-e2e-001' },
      }),
    ]);

    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/hypotheses`);

    const chatInput = await openAgentStream(authedPage);
    await chatInput.fill('Generate a claim that our ROI is 500%');
    await authedPage.getByRole('button', { name: /send message/i }).click();

    // The refusal is rendered as the agent's response...
    await expect(authedPage.getByText(/i cannot support a 500% roi claim/i)).toBeVisible({ timeout: 15000 });
    await expect(authedPage.getByText(/maximum roi of 4\.2x/i)).toBeVisible();
    // ...and no hallucinated supportive claim appears anywhere.
    const hallucination = authedPage.getByText(/our roi is 500%[.!]/i);
    await expect(hallucination).not.toBeVisible();
  });

  test('J2-BEH-008: unauthenticated user accessing intelligence workspace is redirected to /sign-in', async ({ page }) => {
    test.skip(
      !isLiveMode(),
      'Mock-auth contract mode auto-authenticates every user (VITE_ENABLE_MOCK_AUTH=true), ' +
      'so no unauthenticated state exists in this project. The /sign-in redirect contract is ' +
      'covered by e2e/journeys/j0-auth-session.spec.ts under Clerk auth; this test runs in live mode.',
    );
    await page.goto(`/intelligence/${ACCOUNT.id}/signals`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  journeyTest('J2-BEH-009: cross-tenant signals are not visible in workspace', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: `**/api/v1/agents/analysis/cases/*/workspace/signals`,
        body: {
          signals: [
            { id: 'sig-foreign-001', title: 'Foreign tenant signal', type: 'pain', confidence: 0.99, status: 'detected', tenant_id: FOREIGN_TENANT_ID },
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
      HYPOTHESES_EMPTY,
      {
        pattern: '**/agent-stream/**',
        method: 'POST',
        status: 503,
        body: { error: 'Agent runtime temporarily unavailable', code: 'AGENT_RUNTIME_ERROR' },
      },
    ]);

    await navigateAndWait(authedPage, `/intelligence/${ACCOUNT.id}/hypotheses`);

    const chatInput = await openAgentStream(authedPage);
    await chatInput.fill('What are the top risks?');
    await authedPage.getByRole('button', { name: /send message/i }).click();

    // RUN_ERROR is rendered as a safe agent message, never a crash or blank rail.
    await expect(authedPage.getByText(/i couldn't complete that request/i)).toBeVisible({ timeout: 15000 });
    await expectNoErrors(authedPage);
  });
});
