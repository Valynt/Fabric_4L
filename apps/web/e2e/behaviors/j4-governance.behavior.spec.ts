/**
 * Journey 4 Behavior Contract: Governance & Trust Validation
 *
 * Behavior-First Test Contract
 *
 * This file is the executable definition of how the Governance layer MUST behave
 * across L4 (Agent Workflows) and L5 (Ground Truth / Audit / Provenance).
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can view decision traces with provenance chains.
 *   - User can view audit log with tenant-scoped entries.
 *   - User can view health monitoring dashboard with system status.
 *   - Every trace links back to original source data.
 *
 * Intended Behavior (Denied):
 *   - Audit log does not show other tenant's actions.
 *   - Traces without provenance are flagged as incomplete.
 *   - Unauthenticated user cannot access governance pages.
 *   - Cross-tenant trace data is not visible.
 *
 * Failure Modes:
 *   - Cross-tenant audit: foreign tenant IDs invisible, 403 if bypassed.
 *   - Missing provenance: incomplete badge or warning on trace.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Health degradation: safe error state, not raw exception.
 *
 * Traceability: J4-BEH-001 through J4-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import { journeyTest, expectNoErrors, navigateAndWait } from '../helpers/journey-fixture';
import { expectFailureMode, expectNoCrossTenantLeakageOnPage } from '../helpers/behavior-helpers';

// ── Test Data ───────────────────────────────────────────────────────────────

const FOREIGN_TENANT_ID = 'tenant-foreign-999';

const MOCK_TRACES = [
  {
    id: 'trace-behavior-001',
    agent_id: 'agent-signals',
    decision: 'Signal classification: Inventory visibility gaps',
    confidence: 0.91,
    timestamp: '2025-04-28T10:00:00Z',
    provenance: [
      { source: 'Q3 Earnings Call Transcript', type: 'document', confidence: 0.92 },
      { source: 'Industry Report 2024', type: 'report', confidence: 0.85 },
    ],
  },
  {
    id: 'trace-behavior-002',
    agent_id: 'agent-drivers',
    decision: 'Value driver weight assignment: Operational Efficiency = 0.45',
    confidence: 0.88,
    timestamp: '2025-04-28T10:01:00Z',
    provenance: [
      { source: 'Annual Report FY2024', type: 'document', confidence: 0.88 },
    ],
  },
  {
    id: 'trace-behavior-003',
    agent_id: 'agent-narrative',
    decision: 'Narrative section generated: Executive Summary',
    confidence: 0.82,
    timestamp: '2025-04-28T10:02:00Z',
    provenance: [], // Missing provenance — should be flagged
  },
];

const MOCK_AUDIT_LOG = [
  {
    id: 'audit-behavior-001',
    action: 'domain.ingestion.submitted',
    actor: 'user-e2e-001',
    tenant_id: 'tenant-e2e-001',
    timestamp: '2025-04-28T09:55:00Z',
    details: { domain: 'behavior-test-corp.com' },
  },
  {
    id: 'audit-behavior-002',
    action: 'workspace.signals.generated',
    actor: 'agent-signals',
    tenant_id: 'tenant-e2e-001',
    timestamp: '2025-04-28T10:00:00Z',
    details: { account_id: 'acct-meridian-001', signals_count: 6 },
  },
  {
    id: 'audit-behavior-003',
    action: 'value_model.updated',
    actor: 'user-e2e-001',
    tenant_id: 'tenant-e2e-001',
    timestamp: '2025-04-28T10:05:00Z',
    details: { account_id: 'acct-meridian-001', variable: 'projected_savings' },
  },
];

const MOCK_HEALTH = {
  status: 'healthy',
  uptime_seconds: 86400,
  version: '1.0.0',
  components: {
    database: { status: 'healthy', latency_ms: 12 },
    cache: { status: 'healthy', latency_ms: 2 },
    agent_runtime: { status: 'healthy', latency_ms: 45 },
    ingestion_pipeline: { status: 'healthy', latency_ms: 120 },
  },
};

const MOCK_HEALTH_DEGRADED = {
  status: 'degraded',
  uptime_seconds: 86400,
  version: '1.0.0',
  components: {
    database: { status: 'healthy', latency_ms: 12 },
    cache: { status: 'healthy', latency_ms: 2 },
    agent_runtime: { status: 'degraded', latency_ms: 2450 },
    ingestion_pipeline: { status: 'unhealthy', latency_ms: 8500 },
  },
};

// ── Allowed Behaviors ───────────────────────────────────────────────────────

journeyTest.describe('J4 Allowed Behaviors: Governance & Trust', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/traces**',
        body: MOCK_TRACES,
      },
      {
        pattern: '**/api/v1/truths/traces**',
        body: MOCK_TRACES,
      },
      {
        pattern: '**/api/v1/agents/audit/**',
        body: MOCK_AUDIT_LOG,
      },
      {
        pattern: '**/api/v1/truths/audit/**',
        body: MOCK_AUDIT_LOG,
      },
      {
        pattern: '**/api/v1/agents/health',
        body: MOCK_HEALTH,
      },
      {
        pattern: '**/api/v1/agents/health/detailed',
        body: MOCK_HEALTH,
      },
      {
        pattern: '**/api/v1/agents/health/alerts',
        body: [],
      },
    ]);
  });

  journeyTest('J4-BEH-001: user can view decision traces with provenance links', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/governance/traces');
    await expectNoErrors(authedPage);

    await expect(authedPage.locator('h1').filter({ hasText: /decision trace/i })).toBeVisible({ timeout: 10000 });

    // Traces should be visible
    await expect(authedPage.getByText(/inventory visibility gaps/i).first()).toBeVisible({ timeout: 10000 });

    // Provenance sources should be visible
    await expect(authedPage.getByText(/q3 earnings call transcript/i).first()).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J4-BEH-002: user can view audit log with tenant-scoped entries', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/governance/audit-log');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByRole('heading', { name: /audit/i }).first()).toBeVisible({ timeout: 10000 });

    // Audit entries should be visible
    await expect(authedPage.getByText(/domain.ingestion.submitted/i).first()).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(/value_model.updated/i).first()).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J4-BEH-003: user can view health monitor with component statuses', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/governance/health');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText(/healthy|status|system/i).first()).toBeVisible({ timeout: 10000 });

    // Component statuses should be visible
    await expect(authedPage.getByText(/database/i).first()).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(/agent runtime/i).first()).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J4-BEH-004: provenance chain links back to original source', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/governance/traces');

    // Click on a trace to open detail
    const traceRow = authedPage.getByText(/inventory visibility gaps/i).first();
    await traceRow.click();

    // Provenance section or link should be visible
    await expect(
      authedPage.getByText(/source|provenance|origin|document/i).first(),
    ).toBeVisible({ timeout: 10000 });
  });
});

// ── Denied Behaviors ────────────────────────────────────────────────────────

journeyTest.describe('J4 Denied Behaviors: Governance & Trust', () => {
  journeyTest('J4-BEH-005: audit log does not show other tenant actions', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/audit/**',
        body: [
          ...MOCK_AUDIT_LOG,
          {
            id: 'audit-foreign-001',
            action: 'domain.ingestion.submitted',
            actor: 'user-foreign-999',
            tenant_id: FOREIGN_TENANT_ID,
            timestamp: '2025-04-28T09:55:00Z',
            details: { domain: 'foreign-corp.com' },
          },
        ],
      },
    ]);
    await navigateAndWait(authedPage, '/governance/audit-log');
    await expectNoErrors(authedPage);

    // Foreign tenant entries must not leak
    await expectNoCrossTenantLeakageOnPage(authedPage, FOREIGN_TENANT_ID);
  });

  journeyTest('J4-BEH-006: traces without provenance are flagged as incomplete', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/traces**',
        body: MOCK_TRACES,
      },
    ]);
    await navigateAndWait(authedPage, '/governance/traces');
    await expectNoErrors(authedPage);

    // The trace with empty provenance should be visible but flagged
    await expect(
      authedPage.getByText(/narrative section generated/i).first(),
    ).toBeVisible({ timeout: 10000 });

    // There should be some indication of incomplete/missing provenance
    const hasIncompleteFlag = await authedPage.getByText(/incomplete|missing provenance|unverified|no source/i)
      .first().isVisible({ timeout: 5000 }).catch(() => false);
    const hasWarningIcon = await authedPage.locator('[data-testid*="warning"], [data-testid*="incomplete"], .text-amber-500, .text-yellow-500')
      .first().isVisible({ timeout: 3000 }).catch(() => false);

    expect(
      hasIncompleteFlag || hasWarningIcon,
      'Traces without provenance must be flagged as incomplete',
    ).toBe(true);
  });

  test('J4-BEH-007: unauthenticated user accessing traces is redirected to login', async ({ page }) => {
    await page.goto('/governance/traces', { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  test('J4-BEH-008: unauthenticated user accessing audit log is redirected to login', async ({ page }) => {
    await page.goto('/governance/audit-log', { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  journeyTest('J4-BEH-009: cross-tenant trace data is not visible', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/traces**',
        body: [
          {
            id: 'trace-foreign-001',
            agent_id: 'agent-foreign',
            decision: 'Foreign tenant decision',
            tenant_id: FOREIGN_TENANT_ID,
            provenance: [],
          },
        ],
      },
    ]);

    await navigateAndWait(authedPage, '/governance/traces');
    await expectNoCrossTenantLeakageOnPage(authedPage, FOREIGN_TENANT_ID);
  });

  journeyTest('J4-BEH-010: health monitor degradation shows safe warning state instead of crash', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/health',
        body: MOCK_HEALTH_DEGRADED,
      },
      {
        pattern: '**/api/v1/agents/health/detailed',
        body: MOCK_HEALTH_DEGRADED,
      },
    ]);

    await navigateAndWait(authedPage, '/governance/health');
    await expectNoErrors(authedPage);

    // Degraded status should be visible
    await expect(
      authedPage.getByText(/degraded|unhealthy|warning/i).first(),
    ).toBeVisible({ timeout: 10000 });

    // Specific unhealthy component should be called out
    await expect(
      authedPage.getByText(/ingestion pipeline/i).first(),
    ).toBeVisible({ timeout: 10000 });

    // Must NOT show raw exception or stack trace
    const bodyText = await authedPage.locator('body').innerText();
    expect(bodyText.includes('Traceback') || bodyText.includes('at ')).toBe(false);
  });
});
