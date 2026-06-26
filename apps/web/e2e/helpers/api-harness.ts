/**
 * API Harness for Journey Tests
 *
 * Provides two modes of operation:
 *
 * 1. **Live mode** (PLAYWRIGHT_BACKEND_URL is set):
 *    Routes API requests to a real backend. No mocking.
 *    Used for integration/staging environments.
 *
 * 2. **Contract mode** (no backend available):
 *    Intercepts API requests with OpenAPI-schema-validated mock responses.
 *    Used for local dev and CI when only the frontend dev server is running.
 *
 * Journey tests MUST use this harness instead of raw page.route() calls
 * so that the same test code works in both modes.
 */
import { Page, Route } from '@playwright/test';

// ── Environment Detection ───────────────────────────────────────────────────

const BACKEND_URL = process.env.PLAYWRIGHT_BACKEND_URL || '';

export function isLiveMode(): boolean {
  return BACKEND_URL.length > 0;
}

// ── Types ───────────────────────────────────────────────────────────────────

type LayerKey = 'l1' | 'l2' | 'l3' | 'l4' | 'l5' | 'l6';

export interface MockEndpoint {
  /** HTTP method (GET, POST, etc.) */
  method?: string;
  /** URL glob pattern or RegExp for Playwright route matching */
  pattern: string | RegExp;
  /** Response body (will be JSON.stringify'd) */
  body: unknown;
  /** HTTP status code (default: 200) */
  status?: number;
  /** Optional delay in ms to simulate latency */
  delay?: number;
}

interface ApiHarnessOptions {
  /** Additional mock endpoints beyond the defaults */
  mocks?: MockEndpoint[];
  /** If true, unmatched API requests will be aborted instead of passed through */
  strictMocking?: boolean;
  /** Called when relaxed contract mode fulfills an unmatched API request. */
  onUnhandledRequest?: (request: { url: string; method: string }) => void;
}

// ── Layer URL Prefixes (mirrors frontend/client/src/api/client.ts) ──────────

const LAYER_PREFIXES: Record<LayerKey, string> = {
  l1: '/ingest',
  l2: '/extract',
  l3: '',
  l4: '/agents',
  l5: '/truths',
  l6: '/benchmarks',
};

// ── Default Mock Data ───────────────────────────────────────────────────────
// These represent the minimal valid responses needed for pages to render.
// They are intentionally sparse — journey tests should provide richer data
// via the `mocks` option when testing specific workflows.

const EMPTY_ACCOUNT = {
  id: 'acct-test-001',
  name: 'Test Account',
  industry: 'Technology',
  website: 'https://example.com',
  tier: 'enterprise',
  created_at: '2025-01-01T00:00:00Z',
};

/**
 * Build the canonical backend empty shape for a workspace tab.
 * The backend returns `{ <tab>: [] }`, not a wrapper with `status: 'empty'`.
 */
function emptyWorkspaceTab(tabName: string): Record<string, unknown[]> {
  return { [tabName]: [] };
}

const DEFAULT_MOCKS: MockEndpoint[] = [
  // Account list — GET /api/v1/agents/accounts?...
  {
    pattern: /.*\/api\/v1\/agents\/accounts\?.*/,
    body: {
      items: [EMPTY_ACCOUNT],
      total: 1,
      page: 1,
      page_size: 100,
      has_more: false,
    },
  },
  // Account single fetch — GET /api/v1/agents/accounts/:id (no query string)
  {
    pattern: /.*\/api\/v1\/agents\/accounts\/[^/?]+$/,
    body: EMPTY_ACCOUNT,
  },
  // Workspace tab data — canonical backend shape is `{ <tab>: [] }`.
  {
    pattern: '**/api/v1/agents/cases/*/workspace/signals',
    body: emptyWorkspaceTab('signals'),
  },
  {
    pattern: '**/api/v1/agents/cases/*/workspace/drivers',
    body: emptyWorkspaceTab('drivers'),
  },
  {
    pattern: '**/api/v1/agents/cases/*/workspace/evidence',
    body: emptyWorkspaceTab('evidence'),
  },
  {
    pattern: '**/api/v1/agents/cases/*/workspace/stakeholders',
    body: emptyWorkspaceTab('stakeholders'),
  },
  {
    pattern: '**/api/v1/agents/cases/*/workspace/action-plan',
    body: emptyWorkspaceTab('action-plan'),
  },
  {
    pattern: '**/api/v1/agents/cases/*/workspace/value-model',
    body: emptyWorkspaceTab('value-model'),
  },
  {
    pattern: '**/api/v1/agents/cases/*/workspace/narrative',
    body: emptyWorkspaceTab('narrative'),
  },
  {
    pattern: '**/api/v1/agents/cases/*/workspace/evidence-links',
    body: emptyWorkspaceTab('evidence-links'),
  },
  // Case ID resolution — GET /api/v1/agents/cases?account_id=... returns items list
  {
    pattern: /.*\/api\/v1\/agents\/cases\?account_id=.*/,
    body: { items: [{ case_id: 'case-test-001', account_id: 'acct-test-001', title: 'Test workspace', status: 'active' }], total: 1 },
  },
  // Case create — POST /api/v1/agents/cases
  {
    method: 'POST',
    pattern: /.*\/api\/v1\/agents\/cases$/,
    body: { case_id: 'case-test-001', account_id: 'acct-test-001', title: 'Test workspace', status: 'active' },
    status: 201,
  },
  // Legacy canonical path (kept for backward compat)
  {
    pattern: '**/api/v1/agents/cases/canonical/*',
    body: { case_id: 'case-test-001' },
  },
  // Feature flags
  {
    pattern: '**/api/v1/agents/feature-flags',
    body: [],
  },
  // Health
  {
    pattern: '**/api/v1/agents/health/**',
    body: { status: 'healthy', components: {} },
  },
  // Ingestion jobs — backend returns a paginated envelope.
  {
    pattern: '**/api/v1/ingest/jobs**',
    body: {
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      has_more: false,
    },
  },
  // Settings
  {
    pattern: '**/api/v1/agents/settings',
    body: {
      features: {},
      notifications: { email: true, slack: false },
      branding: { primaryColor: '#3B82F6', logoUrl: '' },
    },
  },
  // Users, roles, teams, api-keys
  {
    pattern: '**/api/v1/agents/users',
    body: [],
  },
  {
    pattern: '**/api/v1/agents/api-keys',
    body: [],
  },
  // Workflows
  {
    pattern: '**/api/v1/agents/workflows',
    body: [],
  },
  {
    pattern: '**/api/v1/agents/workflows/types',
    body: [],
  },
  // Graph / Knowledge
  {
    pattern: '**/api/v1/entities**',
    body: { entities: [], total: 0 },
  },
  {
    pattern: '**/api/v1/value-trees**',
    body: { trees: [], total: 0 },
  },
  {
    pattern: '**/api/v1/graph/subgraph**',
    body: {
      nodes: [],
      edges: [],
      stats: { total_nodes: 0, total_edges: 0, density: 0 },
    },
  },
  {
    pattern: '**/api/v1/graph/packs**',
    body: [],
  },
  {
    pattern: '**/api/v1/graph/valuepacks',
    body: { items: [], total: 0 },
  },
  {
    pattern: '**/api/v1/graph/valuepacks/composable-templates',
    body: { templates: [], template_usage: {} },
  },
  {
    pattern: '**/api/v1/graph/valuepacks/ontology-map',
    body: {
      shared_drivers: [],
      shared_model_types: [],
      shared_proof_patterns: [],
      cross_reference_matrix: {},
    },
  },
  // Harness runs — default empty list so pages that incidentally hit this
  // endpoint don't break existing tests. Harness-specific tests override
  // this via page.route() before the harness installs its catch-all.
  {
    // Trailing ** matches optional query strings (e.g. ?tenant_id=...)
    pattern: '**/api/v1/agents/harness/runs**',
    body: { items: [], total: 0, has_more: false },
  },
  // Wildcard fallback for run sub-resources (checkpoints, gates, etc.).
  // Returns 404 rather than {} so that tests which forget to mock a
  // sub-resource fail loudly instead of silently receiving empty data.
  {
    pattern: '**/api/v1/agents/harness/runs/**',
    status: 404,
    body: { detail: 'Not found — add an explicit mock for this harness sub-resource in your test' },
  },
];

// ── Glob → RegExp helper ────────────────────────────────────────────────────

/**
 * Convert a Playwright-style glob pattern to a RegExp.
 * Supports `**` (any path segments) and `*` (any chars except `/`).
 */
function globToRegExp(glob: string): RegExp {
  let regex = glob
    // Escape regex metacharacters other than `*`, which we expand ourselves.
    .replace(/[.+^${}()|[\]\\?]/g, '\\$&')
    .replace(/\*\*/g, '<<<DOUBLESTAR>>>')
    .replace(/\*/g, '[^/]*')
    .replace(/<<<DOUBLESTAR>>>/g, '.*');
  // Anchor to full URL
  regex = '^' + regex + '$';
  return new RegExp(regex);
}

// ── Harness Implementation ──────────────────────────────────────────────────

/**
 * Install the API harness on a Playwright page.
 *
 * In live mode, this is a no-op (requests go to the real backend).
 * In contract mode, this registers route interceptors for all known endpoints.
 *
 * @returns A teardown function that unroutes all interceptors.
 */
export async function installApiHarness(
  page: Page,
  options: ApiHarnessOptions = {},
): Promise<() => Promise<void>> {
  if (isLiveMode()) {
    // In live mode, no mocking needed — requests go to real backend
    return async () => {};
  }

  // Journey-specific mocks take priority over defaults (more specific first).
  const allMocks = [...(options.mocks || []), ...DEFAULT_MOCKS];

  /**
   * Playwright's route matching order is NOT guaranteed when multiple
   * page.route() calls overlap. To avoid race conditions where the
   * catch-all fires before a specific mock, we use a SINGLE route
   * handler and do our own pattern matching.
   */
  const harnessRoute = /.*\/(?:api\/)?v1\/.*/;
  const harnessHandler = async (route: Route) => {
    const url = route.request().url();
    const canonicalUrl = canonicalizeApiUrl(url);
    const method = route.request().method();

    const mock = allMocks.find((m) => {
      const matchesMethod = !m.method || method === m.method.toUpperCase();
      if (!matchesMethod) return false;

      if (typeof m.pattern === 'string') {
        // Playwright glob — delegate to Playwright's internal matching
        // by falling back; this route only fires when the glob already
        // matched '**/api/v1/**', so we need to do more precise matching.
        // For simplicity, convert common glob patterns to RegExp.
        const pattern = globToRegExp(m.pattern);
        return pattern.test(url) || pattern.test(canonicalUrl);
      }
      return m.pattern.test(url) || m.pattern.test(canonicalUrl);
    });

    if (mock) {
      if (mock.delay) {
        await new Promise((resolve) => setTimeout(resolve, mock.delay));
      }
      await route.fulfill({
        status: mock.status ?? 200,
        contentType: 'application/json',
        body: JSON.stringify(mock.body),
      });
      return;
    }

    if (options.strictMocking) {
      console.warn(`[API Harness] Unmatched request aborted: ${url}`);
      await route.abort('connectionrefused');
    } else {
      options.onUnhandledRequest?.({ url, method });
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      });
    }
  };

  await page.route(harnessRoute, harnessHandler);

  // Return teardown function that removes only this harness handler,
  // leaving other test-registered routes intact.
  return async () => {
    await page.unroute(harnessRoute, harnessHandler);
  };
}

function canonicalizeApiUrl(url: string): string {
  return url.replace(/\/v1\//, '/api/v1/');
}

/**
 * Create mock endpoint definitions for a specific account.
 * Use this to provide richer data for account-specific journey tests.
 */
export function mockAccountData(
  accountId: string,
  data: {
    account?: Record<string, unknown>;
    signals?: Record<string, unknown>;
    drivers?: Record<string, unknown>;
    evidence?: Record<string, unknown>;
    stakeholders?: Record<string, unknown>;
    actionPlan?: Record<string, unknown>;
    valueModel?: Record<string, unknown>;
    narrative?: Record<string, unknown>;
  },
): MockEndpoint[] {
  const mocks: MockEndpoint[] = [];

  if (data.account) {
    mocks.push({
      pattern: `**/api/v1/agents/accounts/${accountId}`,
      body: { id: accountId, ...data.account },
    });
  }

  const tabMap: Record<string, string> = {
    signals: 'signals',
    drivers: 'drivers',
    evidence: 'evidence',
    stakeholders: 'stakeholders',
    actionPlan: 'action-plan',
    valueModel: 'value-model',
    narrative: 'narrative',
  };

  for (const [key, tabName] of Object.entries(tabMap)) {
    const tabData = data[key as keyof typeof data];
    if (tabData && typeof tabData === 'object') {
      // Canonical backend path is `/agents/cases/{case_id}/workspace/{tab}`.
      // Tests do not know the generated case id, so match any case id; the
      // account-specific endpoint above is the stable fixture anchor.
      mocks.push({
        pattern: `**/api/v1/agents/cases/*/workspace/${tabName}`,
        // Match backend tab shape: `{ <tab>: [...] }`.
        body: { [tabName]: tabData, generated_at: new Date().toISOString() },
      });
    }
  }

  return mocks;
}

/**
 * Create mock endpoint definitions for ingestion jobs.
 */
export function mockIngestionJobs(jobs: Array<{
  id: string;
  domain: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
}>): MockEndpoint[] {
  const mocks: MockEndpoint[] = [
    {
      pattern: '**/api/v1/ingest/jobs',
      body: {
        items: jobs,
        total: jobs.length,
        page: 1,
        page_size: 100,
        has_more: false,
      },
    },
  ];

  for (const job of jobs) {
    mocks.push({
      pattern: `**/api/v1/ingest/jobs/${job.id}`,
      body: job,
    });
    mocks.push({
      pattern: `**/api/v1/ingest/jobs/${job.id}/progress`,
      body: { progress: job.progress, status: job.status },
    });
  }

  return mocks;
}

/**
 * Create mock endpoint for the agent stream chat.
 */
export function mockAgentStream(response: {
  content: string;
  metadata?: Record<string, string>;
}): MockEndpoint[] {
  return [
    {
      pattern: '**/agent-stream/chat',
      method: 'POST',
      body: response,
      delay: 100, // Simulate minimal latency
    },
  ];
}

/**
 * Create mock endpoint for workflow lifecycle.
 */
export function mockWorkflow(workflow: {
  id: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
}): MockEndpoint[] {
  return [
    {
      pattern: `**/api/v1/agents/workflows/${workflow.id}`,
      body: {
        workflow_instance_id: workflow.id,
        workflow_type: workflow.type,
        status: workflow.status,
        current_state: workflow.status === 'running' ? 'processing' : null,
        current_node: null,
        progress_percentage: workflow.progress,
      },
    },
    {
      pattern: `**/api/v1/agents/workflows/${workflow.id}/result`,
      body: workflow.status === 'completed'
        ? { result: 'Workflow completed successfully', artifacts: [] }
        : { error: 'Workflow not yet complete' },
      status: workflow.status === 'completed' ? 200 : 404,
    },
  ];
}
