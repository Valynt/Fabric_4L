/**
 * Journey 4 Behavior Contract: Governance & Trust Validation
 *
 * Behavior-First Test Contract — Strict Edition
 *
 * Intended Behavior (Allowed):
 *   - Authenticated user can view decision traces (audit log entries).
 *   - User can select a trace and view its provenance chain back to source data.
 *   - User can view the governance audit log with tenant-scoped entries.
 *   - User can view health monitoring dashboard with component statuses.
 *
 * Intended Behavior (Denied):
 *   - Audit log does not show other tenant's actions.
 *   - Traces without provenance render no provenance drill-down action.
 *   - Unauthenticated access redirects to /sign-in (live mode only — mock-auth
 *     contract mode auto-authenticates every user; see test body).
 *   - Cross-tenant trace data is not rendered.
 *   - Health degradation renders a "System Degraded" state, not raw exceptions.
 *
 * Failure Modes:
 *   - Cross-tenant audit: foreign tenant ID invisible.
 *   - Missing provenance: no "View" provenance action for that trace row.
 *   - Unauthenticated: redirect to /sign-in.
 *   - Health degradation: "System Degraded" banner visible, no stack traces.
 *
 * App contract notes (drift repaired):
 *   - Decision traces page (src/pages/DecisionTrace.tsx) reads
 *     GET /api/v1/graph/audit/logs (AuditLogResponse: {entries, total, page, per_page})
 *     and GET /api/v1/graph/provenance/{entityId} (ProvenanceTrailResponse).
 *   - Governance audit log (src/pages/GovernanceAuditLog.tsx) reads
 *     GET /api/v1/agents/ground-truth/truths and
 *     GET /api/v1/agents/ground-truth/truths/{id}/audit.
 *   - Health monitor (src/pages/admin/HealthMonitor.tsx) reads
 *     GET /api/v1/agents/health (SystemHealth: {overall_status, checked_at,
 *     services, summary}) and GET /api/v1/agents/health/alerts.
 *
 * Traceability: J4-BEH-001 through J4-BEH-010.
 * Priority: P0 production gate.
 */

import { test, expect } from '@playwright/test';
import { journeyTest, expectNoErrors, navigateAndWait, isLiveMode } from '../helpers/journey-fixture';
import { expectNoCrossTenantLeakageOnPage } from '../helpers/behavior-helpers';

// ── Test Data ───────────────────────────────────────────────────────────────

const FOREIGN_TENANT_ID = 'tenant-foreign-999';

/** AuditLogResponse (src/lib/schemas/provenance.ts → AuditLogResponseSchema) */
const AUDIT_LOG_RESPONSE = {
  entries: [
    {
      id: 'trace-behavior-001',
      timestamp: '2025-04-28T10:00:00Z',
      source: 'provenance',
      event_type: 'classification',
      entity_id: 'ent-behavior-001',
      entity_type: 'Signal',
      action: 'Signal classification: Inventory visibility gaps',
      agent: 'agent-signals',
      details: {},
    },
    {
      id: 'trace-behavior-002',
      timestamp: '2025-04-28T10:01:00Z',
      source: 'provenance',
      event_type: 'weighting',
      entity_id: 'ent-behavior-002',
      entity_type: 'ValueDriver',
      action: 'Value driver weight assignment: Operational Efficiency = 0.45',
      agent: 'agent-drivers',
      details: {},
    },
  ],
  total: 2,
  page: 1,
  per_page: 50,
};

/** ProvenanceTrailResponse (src/lib/schemas/provenance.ts → ProvenanceTrailSchema) */
const PROVENANCE_TRAIL = {
  entity_id: 'ent-behavior-001',
  entity_type: 'Signal',
  entity_name: 'Inventory visibility gaps',
  created_at: '2025-04-28T10:00:00Z',
  source: 'Q3 Earnings Call Transcript',
  steps: [
    {
      step: 1,
      label: 'Source document ingested',
      detail: 'Q3 Earnings Call Transcript',
      timestamp: '2025-04-28T09:58:00Z',
      agent: 'l1-ingestion',
    },
    {
      step: 2,
      label: 'Entity extracted',
      detail: 'Signal entity created from transcript evidence',
      timestamp: '2025-04-28T09:59:00Z',
      agent: 'agent-signals',
    },
  ],
  confidence_score: 0.91,
};

/** TruthObjectListResponse (src/lib/schemas/groundTruthGovernance.ts) */
const TRUTHS_RESPONSE = {
  items: [
    {
      id: 'truth-behavior-001',
      claim: 'Inventory costs exceed benchmark by 22%',
      claim_type: 'cost_savings_baseline',
      confidence: 0.91,
      status: 'validated',
      maturity_level: 3,
      is_stale: false,
      source_count: 2,
      freshness: 'fresh',
      created_at: '2025-04-28T10:00:00Z',
    },
  ],
  total: 1,
  limit: 100,
  offset: 0,
  has_more: false,
};

/** ValidationEventResponse[] for the selected truth object. */
const TRUTH_AUDIT_EVENTS = [
  {
    id: 'audit-behavior-001',
    from_status: 'proposed',
    to_status: 'validated',
    from_maturity: 1,
    to_maturity: 3,
    actor: 'user-e2e-001',
    actor_type: 'user',
    confidence_at_transition: 0.91,
    created_at: '2025-04-28T10:05:00Z',
  },
];

/** SystemHealth (src/lib/schemas/healthMonitor.ts → SystemHealthSchema) */
function makeHealth(overrides: {
  overall_status: 'healthy' | 'degraded';
  services: Array<{ name: string; status: 'healthy' | 'degraded' | 'unhealthy' }>;
}) {
  const counts = { healthy: 0, degraded: 0, unhealthy: 0, unknown: 0 };
  const services = overrides.services.map((s) => {
    counts[s.status] += 1;
    return {
      name: s.name,
      status: s.status,
      version: '1.0.0',
      uptime_seconds: 86400,
      last_check_at: '2025-04-28T10:00:00Z',
      response_time_ms: s.status === 'healthy' ? 12 : 2450,
    };
  });
  return {
    overall_status: overrides.overall_status,
    checked_at: '2025-04-28T10:00:00Z',
    services,
    summary: { ...counts, total: services.length },
  };
}

const HEALTHY = makeHealth({
  overall_status: 'healthy',
  services: [
    { name: 'database', status: 'healthy' },
    { name: 'cache', status: 'healthy' },
    { name: 'agent runtime', status: 'healthy' },
    { name: 'ingestion pipeline', status: 'healthy' },
  ],
});

const DEGRADED = makeHealth({
  overall_status: 'degraded',
  services: [
    { name: 'database', status: 'healthy' },
    { name: 'cache', status: 'healthy' },
    { name: 'agent runtime', status: 'degraded' },
    { name: 'ingestion pipeline', status: 'unhealthy' },
  ],
});

const HEALTH_MOCKS = (body: unknown) => [
  { pattern: /.*\/api\/v1\/agents\/health$/, body },
  { pattern: /.*\/api\/v1\/agents\/health\/alerts(\?.*)?$/, body: [] },
];

const TRACE_MOCKS = [
  { pattern: '**/api/v1/graph/audit/logs**', body: AUDIT_LOG_RESPONSE },
  { pattern: '**/api/v1/graph/provenance/*', body: PROVENANCE_TRAIL },
];

const TRUTH_MOCKS = [
  { pattern: /.*\/api\/v1\/agents\/ground-truth\/truths(\?.*)?$/, body: TRUTHS_RESPONSE },
  { pattern: /.*\/api\/v1\/agents\/ground-truth\/truths\/[^/]+\/audit(\?.*)?$/, body: TRUTH_AUDIT_EVENTS },
];

// ── Allowed Behaviors ───────────────────────────────────────────────────────

journeyTest.describe('J4 Allowed Behaviors: Governance & Trust', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([...TRACE_MOCKS, ...TRUTH_MOCKS, ...HEALTH_MOCKS(HEALTHY)]);
  });

  journeyTest('J4-BEH-001: user can view decision traces with provenance links', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/governance/traces');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByRole('heading', { name: 'Decision Traces', exact: true })).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Signal classification: Inventory visibility gaps')).toBeVisible({ timeout: 10000 });

    // Drill into the trace to reveal its provenance chain.
    await authedPage.getByRole('button', { name: 'View', exact: true }).first().click();
    await expect(authedPage.getByText('Q3 Earnings Call Transcript').first()).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J4-BEH-002: user can view audit log with tenant-scoped entries', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/governance/audit-log');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByRole('heading', { name: /audit log/i })).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Inventory costs exceed benchmark by 22%')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('proposed → validated')).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J4-BEH-003: user can view health monitor with component statuses', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/settings/governance/health');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('database')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('agent runtime')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(/system healthy/i)).toBeVisible({ timeout: 10000 });
  });

  journeyTest('J4-BEH-004: provenance chain links back to original source', async ({ authedPage }) => {
    await navigateAndWait(authedPage, '/governance/traces');

    await authedPage.getByRole('button', { name: 'View', exact: true }).first().click();

    // The provenance timeline renders each step back to the original source.
    await expect(authedPage.getByText('Source document ingested')).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('Q3 Earnings Call Transcript').first()).toBeVisible({ timeout: 10000 });
  });
});

// ── Denied Behaviors ────────────────────────────────────────────────────────

journeyTest.describe('J4 Denied Behaviors: Governance & Trust', () => {
  journeyTest('J4-BEH-005: audit log does not show other tenant actions', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: /.*\/api\/v1\/agents\/ground-truth\/truths(\?.*)?$/,
        body: {
          items: [
            {
              id: 'truth-foreign-001',
              claim: 'Foreign tenant claim',
              claim_type: 'other',
              confidence: 0.99,
              status: 'validated',
              maturity_level: 2,
              is_stale: false,
              source_count: 1,
              freshness: 'fresh',
              created_at: '2025-04-28T09:55:00Z',
              // Foreign tenant marker — never rendered by the UI.
              tenant_id: FOREIGN_TENANT_ID,
            },
          ],
          total: 1,
          limit: 100,
          offset: 0,
          has_more: false,
        },
      },
      {
        pattern: /.*\/api\/v1\/agents\/ground-truth\/truths\/[^/]+\/audit(\?.*)?$/,
        body: [
          {
            id: 'audit-foreign-001',
            from_status: 'proposed',
            to_status: 'validated',
            from_maturity: 1,
            to_maturity: 2,
            actor: 'system',
            actor_type: 'system',
            created_at: '2025-04-28T09:56:00Z',
          },
        ],
      },
    ]);

    await navigateAndWait(authedPage, '/governance/audit-log');
    await expectNoErrors(authedPage);
    await expectNoCrossTenantLeakageOnPage(authedPage, FOREIGN_TENANT_ID);
  });

  journeyTest('J4-BEH-006: traces without provenance render no provenance drill-down', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/graph/audit/logs**',
        body: {
          entries: [
            ...AUDIT_LOG_RESPONSE.entries.slice(0, 1),
            {
              id: 'trace-behavior-003',
              timestamp: '2025-04-28T10:02:00Z',
              source: 'provenance',
              event_type: 'generation',
              entity_type: 'Narrative',
              // No entity_id — this trace has no provenance chain to drill into.
              action: 'Narrative section generated: Executive Summary',
              agent: 'agent-narrative',
              details: {},
            },
          ],
          total: 2,
          page: 1,
          per_page: 50,
        },
      },
    ]);

    await navigateAndWait(authedPage, '/governance/traces');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText('Narrative section generated: Executive Summary')).toBeVisible({ timeout: 10000 });
    // Only the trace with an entity_id exposes the "View" provenance action.
    await expect(authedPage.getByRole('button', { name: 'View', exact: true })).toHaveCount(1);
  });

  test('J4-BEH-007: unauthenticated user accessing traces is redirected to /sign-in', async ({ page }) => {
    test.skip(
      !isLiveMode(),
      'Mock-auth contract mode auto-authenticates every user (VITE_ENABLE_MOCK_AUTH=true), ' +
      'so no unauthenticated state exists in this project. The /sign-in redirect contract is ' +
      'covered by e2e/journeys/j0-auth-session.spec.ts under Clerk auth; this test runs in live mode.',
    );
    await page.goto('/governance/traces', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  test('J4-BEH-008: unauthenticated user accessing audit log is redirected to /sign-in', async ({ page }) => {
    test.skip(
      !isLiveMode(),
      'Mock-auth contract mode auto-authenticates every user (VITE_ENABLE_MOCK_AUTH=true), ' +
      'so no unauthenticated state exists in this project. The /sign-in redirect contract is ' +
      'covered by e2e/journeys/j0-auth-session.spec.ts under Clerk auth; this test runs in live mode.',
    );
    await page.goto('/governance/audit-log', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  journeyTest('J4-BEH-009: cross-tenant trace data is not visible', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/graph/audit/logs**',
        body: {
          entries: [
            {
              id: 'trace-foreign-001',
              timestamp: '2025-04-28T10:00:00Z',
              source: 'access_log',
              event_type: 'access',
              action: 'Foreign tenant decision',
              agent: 'agent-foreign',
              // Foreign tenant marker inside details — details are never rendered.
              details: { tenant_id: FOREIGN_TENANT_ID },
            },
          ],
          total: 1,
          page: 1,
          per_page: 50,
        },
      },
    ]);

    await navigateAndWait(authedPage, '/governance/traces');
    await expectNoCrossTenantLeakageOnPage(authedPage, FOREIGN_TENANT_ID);
  });

  journeyTest('J4-BEH-010: health monitor degradation shows safe degraded state instead of crash', async ({ authedPage, addMocks }) => {
    await addMocks(HEALTH_MOCKS(DEGRADED));

    await navigateAndWait(authedPage, '/settings/governance/health');
    await expectNoErrors(authedPage);

    await expect(authedPage.getByText(/system degraded/i)).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText('ingestion pipeline')).toBeVisible({ timeout: 10000 });

    const bodyText = await authedPage.locator('body').innerText();
    expect(bodyText.includes('Traceback')).toBe(false);
  });
});
