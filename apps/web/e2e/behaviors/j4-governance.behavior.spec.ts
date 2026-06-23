/**
 * Journey 4 Behavior Contract: Governance & Trust Validation
 *
 * Behavior-First Test Contract — Strict Edition
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can view decision traces with provenance chains.
 *   - User can view audit log with tenant-scoped entries.
 *   - User can view health monitoring dashboard with component statuses.
 *   - Every trace links back to original source data.
 *
 * Intended Behavior (Denied):
 *   - Audit log does not show other tenant's actions.
 *   - Traces without provenance render an `incomplete-provenance` testId.
 *   - Unauthenticated access redirects to /sign-in.
 *   - Cross-tenant trace data is not rendered.
 *   - Health degradation renders a `degraded-state` testId, not raw exceptions.
 *
 * Failure Modes:
 *   - Cross-tenant audit: foreign tenant ID invisible.
 *   - Missing provenance: `incomplete-provenance` testId visible.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Health degradation: `degraded-state` testId visible.
 *
 * Traceability: J4-BEH-001 through J4-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import { journeyTest, expectNoErrors, navigateAndWait } from '../helpers/journey-fixture';
import {
  expectFailureMode,
  expectNoCrossTenantLeakageOnPage,
  expectVisibleByTestId,
} from '../helpers/behavior-helpers';

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
    provenance: [],
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

    await expect(authedPage.getByRole('heading', { name: /decision trace/i })).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Inventory visibility gaps')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Q3 Earnings Call Transcript')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J4-BEH-002: user can view audit log with tenant-scoped entries', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/governance/audit-log');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByRole('heading', { name: /audit/i })).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('domain.ingestion.submitted')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('value_model.updated')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J4-BEH-003: user can view health monitor with component statuses', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/governance/health');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('database')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('agent runtime')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('healthy')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J4-BEH-004: provenance chain links back to original source', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/governance/traces');

    const traceRow = authedPage.getByText('Inventory visibility gaps');
    await traceRow.click();

    await expect(authedPage.getByTestId('provenance-list')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Q3 Earnings Call Transcript')).toBeVisible({ timeout: 10000 });
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
    await expectNoCrossTenantLeakageOnPage(authedPage, FOREIGN_TENANT_ID);
  });

  journeyTest('J4-BEH-006: traces without provenance render incomplete-provenance badge', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/traces**',
        body: MOCK_TRACES,
      },
    ]);

    await navigateAndWait(authedPage, '/governance/traces');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('Narrative section generated')).toBeVisible({ timeout: 10000 });
    await expectVisibleByTestId(authedPage, 'incomplete-provenance');
  });

  test('J4-BEH-007: unauthenticated user accessing traces is redirected to /sign-in', async ({ page }) => {
    await page.goto('/governance/traces', { waitUntil: 'domcontentloaded' });
    await expectFailureMode(page, 'unauthenticated_redirect');
  });

  test('J4-BEH-008: unauthenticated user accessing audit log is redirected to /sign-in', async ({ page }) => {
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

  journeyTest('J4-BEH-010: health monitor degradation shows safe degraded state instead of crash', async ({ authedPage, addMocks }) => {
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

    await expectVisibleByTestId(authedPage, 'degraded-state');
    await expect(authedPage.getByText('ingestion pipeline')).toBeVisible({ timeout: 10000 });

    const bodyText = await authedPage.locator('body').innerText();
    expect(bodyText.includes('Traceback') || bodyText.includes('at ')).toBe(false);
  });
});
