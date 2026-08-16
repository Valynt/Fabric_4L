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
import { Page, Route } from "@playwright/test";

// ── Environment Detection ───────────────────────────────────────────────────

const BACKEND_URL = process.env.PLAYWRIGHT_BACKEND_URL || "";

export function isLiveMode(): boolean {
  return BACKEND_URL.length > 0;
}

// ── Types ───────────────────────────────────────────────────────────────────

type LayerKey = "l1" | "l2" | "l3" | "l4" | "l5" | "l6";

export interface MockEndpoint {
  /** HTTP method (GET, POST, etc.) */
  method?: string;
  /** URL glob pattern or RegExp for Playwright route matching */
  pattern: string | RegExp;
  /** Response body (will be JSON.stringify'd) */
  body?: unknown;
  /** Fresh body per request. Used for short-lived authorization snapshots. */
  getBody?: () => unknown;
  /** HTTP status code (default: 200) */
  status?: number;
  /** Optional delay in ms to simulate latency */
  delay?: number;
}

export { verifiedLegacyAuthorizationSnapshot } from "./verified-authorization-snapshot";

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
  l1: "/ingest",
  l2: "/extract",
  l3: "",
  l4: "/agents",
  l5: "/truths",
  l6: "/benchmarks",
};

// ── Default Mock Data ───────────────────────────────────────────────────────
// These represent the minimal valid responses needed for pages to render.
// They are intentionally sparse — journey tests should provide richer data
// via the `mocks` option when testing specific workflows.

const EMPTY_ACCOUNT = {
  id: "acct-test-001",
  name: "Test Account",
  industry: "Technology",
  website: "https://example.com",
  tier: "enterprise",
  created_at: "2025-01-01T00:00:00Z",
};

const JOURNEY_ACCOUNTS = [
  {
    id: "acct-meridian-001",
    name: "Meridian Automotive",
    industry: "Manufacturing",
    website: "https://meridian.example",
    tier: "enterprise",
    created_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "acct-acme-002",
    name: "Acme Corp",
    industry: "Technology",
    website: "https://acme.example",
    tier: "mid-market",
    created_at: "2025-01-02T00:00:00Z",
  },
  {
    id: "acct-gf-003",
    name: "Global Finance Inc",
    industry: "Financial Services",
    website: "https://global-finance.example",
    tier: "enterprise",
    created_at: "2025-01-03T00:00:00Z",
  },
  EMPTY_ACCOUNT,
];

/**
 * Build the canonical backend empty shape for a workspace tab.
 * The backend returns `{ <tab>: [] }`, not a wrapper with `status: 'empty'`.
 */
function emptyWorkspaceTab(tabName: string): Record<string, unknown[]> {
  return { [tabName]: [] };
}

const DEFAULT_MOCKS: MockEndpoint[] = [
  // Fail-closed snapshot used by AuthorizationProvider in legacy e2e mode.
  // TTL is 4 minutes; mint per request so long Playwright files stay verified.
  {
    pattern: /.*\/(?:api\/)?v1\/auth\/authorization-snapshot.*/,
    method: "GET",
    getBody: () => verifiedLegacyAuthorizationSnapshot(),
  },
  // Web-vitals telemetry beacon — fired by src/lib/web-vitals.ts on every
  // page; the strict fail-closed harness must not treat it as unhandled.
  {
    pattern: /.*\/api\/v1\/telemetry\/web-vitals.*/,
    method: "POST",
    body: { accepted: true },
  },
  // Account list — GET /api/v1/agents/accounts?...
  {
    pattern: /.*\/api\/v1\/agents\/accounts\?.*/,
    body: {
      items: JOURNEY_ACCOUNTS,
      total: JOURNEY_ACCOUNTS.length,
      page: 1,
      page_size: 100,
      has_more: false,
    },
  },
  // Account ACL checks used by tenant/account-scoped route guards.
  {
    pattern: /.*\/api\/v1\/agents\/v1\/authz\/accounts\/[^/]+\/access\?.*/,
    body: {
      account_exists: true,
      tenant_bound: true,
      principal_allowed: true,
      reason: "allowed",
    },
  },
  {
    pattern: /.*\/api\/v1\/agents\/me\/permissions$/,
    body: {
      capabilities: {
        personal: { allowed: true, reasons: [], source: "server" },
        billing: { allowed: true, reasons: [], source: "server" },
        team: { allowed: true, reasons: [], source: "server" },
        integrations: { allowed: true, reasons: [], source: "server" },
        governance: { allowed: true, reasons: [], source: "server" },
        super_admin: {
          allowed: false,
          reasons: ["super_admin_only"],
          source: "server",
        },
      },
    },
  },
  ...JOURNEY_ACCOUNTS.map(account => ({
    pattern: `**/api/v1/agents/accounts/${account.id}`,
    body: account,
  })),
  // Account single fetch — GET /api/v1/agents/accounts/:id (no query string)
  {
    pattern: /.*\/api\/v1\/agents\/accounts\/[^/?]+$/,
    body: EMPTY_ACCOUNT,
  },
  // Workspace tab data — canonical backend shape is `{ <tab>: [] }`.
  {
    pattern: "**/api/v1/agents/cases/*/workspace/signals",
    body: emptyWorkspaceTab("signals"),
  },
  {
    pattern: "**/api/v1/agents/analysis/cases/*/workspace/signals",
    body: emptyWorkspaceTab("signals"),
  },
  {
    pattern: "**/api/v1/agents/cases/*/workspace/drivers",
    body: emptyWorkspaceTab("drivers"),
  },
  {
    pattern: "**/api/v1/agents/analysis/cases/*/workspace/drivers",
    body: emptyWorkspaceTab("drivers"),
  },
  {
    pattern: "**/api/v1/agents/cases/*/workspace/evidence",
    body: emptyWorkspaceTab("evidence"),
  },
  {
    pattern: "**/api/v1/agents/analysis/cases/*/workspace/evidence",
    body: emptyWorkspaceTab("evidence"),
  },
  {
    pattern: "**/api/v1/agents/cases/*/workspace/stakeholders",
    body: emptyWorkspaceTab("stakeholders"),
  },
  {
    pattern: "**/api/v1/agents/analysis/cases/*/workspace/stakeholders",
    body: emptyWorkspaceTab("stakeholders"),
  },
  {
    pattern: "**/api/v1/agents/cases/*/workspace/action-plan",
    body: emptyWorkspaceTab("action-plan"),
  },
  {
    pattern: "**/api/v1/agents/analysis/cases/*/workspace/action-plan",
    body: emptyWorkspaceTab("action-plan"),
  },
  {
    pattern: "**/api/v1/agents/cases/*/workspace/value-model",
    body: emptyWorkspaceTab("value-model"),
  },
  {
    pattern: "**/api/v1/agents/analysis/cases/*/workspace/value-model",
    body: emptyWorkspaceTab("value-model"),
  },
  {
    pattern: "**/api/v1/agents/cases/*/workspace/narrative",
    body: emptyWorkspaceTab("narrative"),
  },
  {
    pattern: "**/api/v1/agents/analysis/cases/*/workspace/narrative",
    body: emptyWorkspaceTab("narrative"),
  },
  {
    pattern: "**/api/v1/agents/cases/*/workspace/evidence-links",
    body: emptyWorkspaceTab("evidence-links"),
  },
  {
    pattern: "**/api/v1/agents/analysis/cases/*/workspace/evidence-links",
    body: emptyWorkspaceTab("evidence-links"),
  },
  // Case ID resolution — GET /api/v1/agents/cases?account_id=... returns items list
  {
    pattern: /.*\/api\/v1\/agents\/cases\?account_id=.*/,
    body: {
      items: [
        {
          case_id: "case-test-001",
          account_id: "acct-test-001",
          title: "Test workspace",
          status: "active",
        },
      ],
      total: 1,
    },
  },
  // Current analysis case resolution path used by account workspaces.
  {
    pattern: /.*\/api\/v1\/agents\/analysis\/cases\?account_id=.*/,
    body: {
      items: [
        {
          case_id: "case-test-001",
          account_id: "acct-test-001",
          title: "Test workspace",
          status: "active",
        },
      ],
      total: 1,
    },
  },
  // Case create — POST /api/v1/agents/cases
  {
    method: "POST",
    pattern: /.*\/api\/v1\/agents\/cases$/,
    body: {
      case_id: "case-test-001",
      account_id: "acct-test-001",
      title: "Test workspace",
      status: "active",
    },
    status: 201,
  },
  // Current analysis case create path used by account workspaces.
  {
    method: "POST",
    pattern: /.*\/api\/v1\/agents\/analysis\/cases$/,
    body: {
      case_id: "case-test-001",
      account_id: "acct-test-001",
      title: "Test workspace",
      status: "active",
    },
    status: 201,
  },
  // Legacy canonical path (kept for backward compat)
  {
    pattern: "**/api/v1/agents/cases/canonical/*",
    body: { case_id: "case-test-001" },
  },
  // Feature flags
  {
    pattern: "**/api/v1/agents/feature-flags",
    body: [],
  },
  // Health
  {
    pattern: "**/api/v1/agents/health/**",
    body: { status: "healthy", components: {} },
  },
  // Ingestion jobs — backend returns the JobListResponse envelope
  // ({ data, pagination, aggregation }) per contracts/openapi/layer1-ingestion.json.
  {
    pattern: "**/api/v1/ingest/jobs**",
    body: {
      data: [],
      pagination: { page: 1, limit: 100, total: 0, totalPages: 0 },
      aggregation: {
        by_status: {},
        total_execution_time_ms: 0,
        total_records_extracted: 0,
      },
    },
  },
  // Settings
  {
    pattern: "**/api/v1/agents/settings",
    body: {
      features: {},
      notifications: { email: true, slack: false },
      branding: { primaryColor: "#3B82F6", logoUrl: "" },
    },
  },
  // Users, roles, teams, api-keys
  {
    pattern: "**/api/v1/agents/users",
    body: [],
  },
  {
    pattern: "**/api/v1/agents/api-keys",
    body: [],
  },
  // Workflows
  {
    pattern: "**/api/v1/agents/workflows",
    body: [],
  },
  {
    pattern: "**/api/v1/agents/workflows/types",
    body: [],
  },
  // Graph / Knowledge (L3 layer prefix is /graph — see LAYER_PREFIXES in
  // src/api/client.ts)
  {
    // EntityListResponse per src/lib/validation/schemas.ts (EntityListResponseSchema)
    pattern: "**/api/v1/graph/entities**",
    body: {
      results: [],
      total_count: 0,
      filtered_count: 0,
      limit: 50,
      offset: 0,
      has_more: false,
      available_domains: [],
      available_sources: [],
    },
  },
  {
    pattern: "**/api/v1/graph/value-trees**",
    body: { trees: [], total: 0 },
  },
  {
    pattern: "**/api/v1/graph/subgraph**",
    body: {
      nodes: [],
      edges: [],
      stats: { total_nodes: 0, total_edges: 0, density: 0 },
    },
  },
  {
    pattern: "**/api/v1/graph/packs**",
    body: [],
  },
  {
    pattern: "**/api/v1/graph/valuepacks",
    body: { items: [], total: 0 },
  },
  {
    pattern: "**/api/v1/graph/valuepacks/composable-templates",
    body: { templates: [], template_usage: {} },
  },
  {
    pattern: "**/api/v1/graph/valuepacks/ontology-map",
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
    pattern: "**/api/v1/agents/harness/runs**",
    body: { items: [], total: 0, has_more: false },
  },
  // Wildcard fallback for run sub-resources (checkpoints, gates, etc.).
  // Returns 404 rather than {} so that tests which forget to mock a
  // sub-resource fail loudly instead of silently receiving empty data.
  {
    pattern: "**/api/v1/agents/harness/runs/**",
    status: 404,
    body: {
      detail:
        "Not found — add an explicit mock for this harness sub-resource in your test",
    },
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
    .replace(/[.+^${}()|[\]\\?]/g, "\\$&")
    .replace(/\*\*/g, "<<<DOUBLESTAR>>>")
    .replace(/\*/g, "[^/]*")
    .replace(/<<<DOUBLESTAR>>>/g, ".*");
  // Anchor to full URL
  regex = "^" + regex + "$";
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
  options: ApiHarnessOptions = {}
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

    const mock = allMocks.find(m => {
      const matchesMethod = !m.method || method === m.method.toUpperCase();
      if (!matchesMethod) return false;

      if (typeof m.pattern === "string") {
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
        await new Promise(resolve => setTimeout(resolve, mock.delay));
      }
      await route.fulfill({
        status: mock.status ?? 200,
        contentType: "application/json",
        body: JSON.stringify(mock.getBody ? mock.getBody() : mock.body),
      });
      return;
    }

    if (options.strictMocking) {
      console.warn(`[API Harness] Unmatched request aborted: ${url}`);
      await route.abort("connectionrefused");
    } else {
      options.onUnhandledRequest?.({ url, method });
      await route.fulfill({
        status: 200,
        contentType: "application/json",
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
  return url.replace(/\/v1\//, "/api/v1/");
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
  }
): MockEndpoint[] {
  const mocks: MockEndpoint[] = [];

  if (data.account) {
    mocks.push({
      pattern: `**/api/v1/agents/accounts/${accountId}`,
      body: { id: accountId, ...data.account },
    });
  }

  const tabMap: Record<string, string> = {
    signals: "signals",
    drivers: "drivers",
    evidence: "evidence",
    stakeholders: "stakeholders",
    actionPlan: "action-plan",
    valueModel: "value-model",
    narrative: "narrative",
  };

  for (const [key, tabName] of Object.entries(tabMap)) {
    const tabData = data[key as keyof typeof data];
    if (tabData && typeof tabData === "object") {
      // The frontend reads workspace tabs via
      // GET /api/v1/agents/analysis/cases/{case_id}/workspace/{tab}
      // (see useWorkspaceTabQuery in src/hooks/useWorkspaceCase.ts). Register
      // the legacy /agents/cases/* variant too for older call sites.
      // Match backend tab shape: `{ <tab>: [...] }`.
      const body = { [tabName]: tabData, generated_at: new Date().toISOString() };
      mocks.push({
        pattern: `**/api/v1/agents/analysis/cases/*/workspace/${tabName}`,
        body,
      });
      mocks.push({
        pattern: `**/api/v1/agents/cases/*/workspace/${tabName}`,
        body,
      });
    }
  }

  return mocks;
}

/**
 * Create mock endpoint definitions for ingestion jobs.
 *
 * Emits the canonical L1 JobListResponse envelope
 * (contracts/openapi/layer1-ingestion.json → JobListResponse/JobSummary):
 * `{ data: JobSummary[], pagination, aggregation }`. The frontend reads
 * `response.data.data` and maps `configuration.url` + uppercase `status`.
 */
export function mockIngestionJobs(
  jobs: Array<{
    id: string;
    domain: string;
    status: "pending" | "processing" | "completed" | "failed";
    progress: number;
    created_at?: string;
    pages_processed?: number;
  }>
): MockEndpoint[] {
  const fallbackCreatedAt = new Date().toISOString();
  const mocks: MockEndpoint[] = [
    {
      // Matches `/ingest/jobs` and `/ingest/jobs?...` but not `/ingest/jobs/{id}`.
      pattern: /.*\/api\/v1\/ingest\/jobs(\?.*)?$/,
      body: {
        data: jobs.map(job => ({
          id: job.id,
          target_id: `target-${job.id}`,
          status: job.status.toUpperCase(),
          priority: 5,
          progress_percent_complete: job.progress,
          progress_processed_pages: job.pages_processed ?? 0,
          created_at: job.created_at ?? fallbackCreatedAt,
          configuration: { url: job.domain },
        })),
        pagination: { page: 1, limit: 100, total: jobs.length, totalPages: 1 },
        aggregation: {
          by_status: jobs.reduce<Record<string, number>>((acc, job) => {
            const key = job.status.toUpperCase();
            acc[key] = (acc[key] ?? 0) + 1;
            return acc;
          }, {}),
          total_execution_time_ms: 0,
          total_records_extracted: 0,
        },
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
 *
 * The app (src/agui/AgentEventClient.ts) first POSTs to the SSE endpoint
 * `/agent-stream/chat/stream` and falls back to the legacy JSON endpoint
 * `/agent-stream/chat` on a 404. Mocking the SSE endpoint with a 404 drives
 * the app down the supported legacy path, which returns `response` as-is.
 */
export function mockAgentStream(response: {
  content: string;
  metadata?: Record<string, string>;
}): MockEndpoint[] {
  return [
    {
      pattern: "**/agent-stream/chat/stream",
      method: "POST",
      status: 404,
      body: { detail: "SSE streaming is not available in contract mode" },
    },
    {
      pattern: "**/agent-stream/chat",
      method: "POST",
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
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
}): MockEndpoint[] {
  return [
    {
      pattern: `**/api/v1/agents/workflows/${workflow.id}`,
      body: {
        workflow_instance_id: workflow.id,
        workflow_type: workflow.type,
        status: workflow.status,
        current_state: workflow.status === "running" ? "processing" : null,
        current_node: null,
        progress_percentage: workflow.progress,
      },
    },
    {
      pattern: `**/api/v1/agents/workflows/${workflow.id}/result`,
      body:
        workflow.status === "completed"
          ? { result: "Workflow completed successfully", artifacts: [] }
          : { error: "Workflow not yet complete" },
      status: workflow.status === "completed" ? 200 : 404,
    },
  ];
}
