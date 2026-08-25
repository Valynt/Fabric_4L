/**
 * queryKeys.ts — Centralized React Query key registry
 *
 * All query key factories live here. This prevents:
 *   1. Cache key collisions between hooks (e.g., two hooks using ['list'] at root)
 *   2. Stale invalidation bugs from typos in ad-hoc key strings
 *   3. Duplicate key definitions scattered across 14 hook files
 *
 * Usage:
 *   import { QK } from '@/hooks/queryKeys';
 *   queryKey: QK.formulas.list(filters)
 *   queryClient.invalidateQueries({ queryKey: QK.formulas.all })
 */

// ── Filter type imports (kept minimal to avoid circular deps) ─────────────────
import type { BenchmarkFilters } from "./useBenchmarks";
import type { FormulaFilters } from "./useFormulas";
import type { ValuePackFilters } from "./useValuePacks";
import type { ModelFilters } from "./useModels";
import type { VariableFilters } from "./useVariables";
import type {
  GraphQueryRequest,
  EntityTraversalRequest,
} from "./useGraphQuery";
import type { AuditLogFilter } from "./useProvenance";
import type { SourceFilters } from "./useSources";
import type { ProductListFilters } from "./useProducts";
import type { CaseStudyListFilters } from "./useEvidence";
import type { CompetitorListFilters } from "./useCompetitiveIntel";
import type { ROICalculationListFilters } from "./useROICalculator";
import type { AccountHypothesesFilters } from "./useHypotheses";
import type { NarrativeListFilters } from "./useNarratives";

// ── Registry ─────────────────────────────────────────────────────────────────
export const QK = {
  // Layer 1 — Ingestion
  ingestion: {
    all: ["ingestion"] as const,
    jobs: () => ["ingestion", "jobs"] as const,
    recent: () => ["ingestion", "recent"] as const,
    stats: () => ["ingestion", "stats"] as const,
    list: (filters: unknown) =>
      ["ingestion", "list", stableKey(filters)] as const,
    detail: (id: string) => ["ingestion", "detail", id] as const,
    logs: (id: string) => ["ingestion", "logs", id] as const,
  },

  // Layer 1 — Sources (Data Source Configuration)
  sources: {
    all: ["sources"] as const,
    list: (filters: SourceFilters) =>
      ["sources", "list", stableKey(filters)] as const,
    detail: (id: string) => ["sources", "detail", id] as const,
    stats: ["sources", "stats"] as const,
  },

  // Layer 2 — Extraction
  extraction: {
    all: ["extraction"] as const,
    job: (id: string) => ["extraction", "job", id] as const,
    results: (id: string) => ["extraction", "results", id] as const,
  },

  // Layer 3 — Knowledge graph
  graph: {
    all: ["graph"] as const,
    query: (params: GraphQueryRequest) =>
      ["graph", "query", stableKey(params)] as const,
    context: (entityId: string, hops?: number) =>
      ["graph", "context", entityId, hops] as const,
    traversal: (params: EntityTraversalRequest) =>
      ["graph", "traversal", stableKey(params)] as const,
    subgraph: (
      query?: string,
      centerEntityId?: string,
      depth?: number,
      limit?: number
    ) =>
      [
        "graph",
        "subgraph",
        query ?? "",
        centerEntityId ?? "",
        depth ?? 2,
        limit ?? 100,
      ] as const,
  },

  entities: {
    all: ["entities"] as const,
    list: () => ["entities", "list"] as const,
    search: (query: string) => ["entities", "search", query] as const,
    detail: (id: string) => ["entities", "detail", id] as const,
  },

  formulas: {
    all: ["formulas"] as const,
    list: (filters: FormulaFilters) => ["formulas", "list", filters] as const,
    detail: (id: string) => ["formulas", "detail", id] as const,
    approvals: ["formulas", "approvals"] as const,
  },

  benchmarks: {
    all: ["benchmarks"] as const,
    list: (filters: BenchmarkFilters) =>
      ["benchmarks", "datasets", stableKey(filters)] as const,
    detail: (id: string) => ["benchmarks", "detail", id] as const,
    compare: () => ["benchmarks", "compare"] as const,
    industries: () => ["benchmarks", "industries"] as const,
    policies: ["benchmarks", "policies"] as const,
  },

  variables: {
    all: ["variables"] as const,
    list: (filters: VariableFilters) => ["variables", "list", filters] as const,
    detail: (id: string) => ["variables", "detail", id] as const,
    bindings: ["variables", "bindings"] as const,
    stats: ["variables", "stats"] as const,
  },

  valuePacks: {
    all: ["value-packs"] as const,
    list: (filters: ValuePackFilters) =>
      ["value-packs", "list", filters] as const,
    detail: (id: string) => ["value-packs", "detail", id] as const,
    stats: ["value-packs", "stats"] as const,
  },

  models: {
    all: ["models"] as const,
    list: (filters: ModelFilters) =>
      ["models", "list", stableKey(filters)] as const,
    detail: (id: string) => ["models", "detail", id] as const,
    folders: () => ["models", "folders"] as const,
  },

  valueTrees: {
    all: ["value-trees"] as const,
    tree: (entityId: string, direction: string, maxDepth: number) =>
      ["value-trees", "tree", entityId, direction, maxDepth] as const,
    paths: (entityId: string, direction: string, maxDepth: number) =>
      ["value-trees", "paths", entityId, direction, maxDepth] as const,
  },

  provenance: {
    all: ["provenance"] as const,
    trail: (entityId: string) => ["provenance", "trail", entityId] as const,
    audit: (filters: AuditLogFilter) =>
      ["provenance", "audit", filters] as const,
  },

  // Layer 4 — Agents / Governance
  workflows: {
    all: ["workflows"] as const,
    active: () => ["workflows", "active"] as const,
    history: () => ["workflows", "history"] as const,
  },

  businessCases: {
    all: ["business-cases"] as const,
    list: (filters: { status?: string; search?: string; company?: string }) =>
      ["business-cases", "list", stableKey(filters)] as const,
    detail: (id: string) => ["business-cases", "detail", id] as const,
  },

  documents: {
    all: ["documents"] as const,
    export: (id: string) => ["documents", "export", id] as const,
    businessCase: (id: string) => ["documents", "businessCase", id] as const,
  },

  governance: {
    all: ["governance"] as const,
    tenants: ["governance", "tenants"] as const,
    users: (tenantId?: string) => ["governance", "users", tenantId] as const,
    apiKeys: (tenantId?: string) =>
      ["governance", "api-keys", tenantId] as const,
    review: (reviewId: string) => ["governance", "review", reviewId] as const,
    reviewQueue: (filters: { status?: string; subject_type?: string }) =>
      ["governance", "review-queue", stableKey(filters)] as const,
    reviewComments: (reviewId: string) =>
      ["governance", "review-comments", reviewId] as const,
    audit: (reviewId: string) => ["governance", "audit", reviewId] as const,
    auditExport: (jobId: string) => ["governance", "audit-export", jobId] as const,
    lineage: (correlationId: string) =>
      ["governance", "lineage", correlationId] as const,
    complianceStatus: () => ["governance", "compliance-status"] as const,
  },

  versions: {
    all: ["versions"] as const,
    list: (accountId?: string) => ["versions", "list", accountId ?? ""] as const,
    detail: (versionId: string) => ["versions", "detail", versionId] as const,
    compare: (versionId: string, compareToVersionId: string) =>
      ["versions", "compare", versionId, compareToVersionId] as const,
  },

  valueCases: {
    all: ["value-cases"] as const,
    account: (accountId: string) => ["value-cases", "account", accountId] as const,
    detail: (caseId: string) => ["value-cases", "detail", caseId] as const,
  },

  workspace: {
    all: ["workspace"] as const,
    tab: (caseId: string, tab: string) => ["workspace", "tab", caseId, tab] as const,
    accountTab: (accountId: string, tabKey: string) => ["workspace", "account-tab", accountId, tabKey] as const,
    signalReview: (caseId: string, accountId: string) => ["workspace", "signal-review", caseId, accountId] as const,
    evidenceDecision: (caseId: string, accountId: string) => ["workspace", "evidence-decision", caseId, accountId] as const,
    evidenceDriverLinks: (caseId: string, accountId: string) => ["workspace", "evidence-driver-links", caseId, accountId] as const,
  },
  accounts: {
    all: ["accounts"] as const,
    list: (filters: unknown) => ["accounts", "list", filters] as const,
    detail: (id: string) => ["accounts", "detail", id] as const,
    activity: (id: string) => ["accounts", "activity", id] as const,
    syncStatus: ["accounts", "sync-status"] as const,
    filters: ["accounts", "filters"] as const,
  },

  integrations: {
    all: ["integrations"] as const,
    list: ["integrations", "list"] as const,
    detail: (provider: string) => ["integrations", "detail", provider] as const,
  },

  // Narrative generation
  narrative: {
    all: ["narrative"] as const,
    industries: () => ["narrative", "industries"] as const,
  },

  // Platform/Admin Settings
  platform: {
    all: ["platform"] as const,
    settings: ["platform", "settings"] as const,
    health: ["platform", "health"] as const,
    currentUser: ["platform", "currentUser"] as const,
  },

  // Ontology Schema Management
  ontology: {
    all: ["ontology"] as const,
    schema: () => ["ontology", "schema"] as const,
    type: (id: string) => ["ontology", "type", id] as const,
  },

  // ── Data Intelligence Layer (DIL) ─────────────────────────────────────────

  // L3 — Product Portfolio
  products: {
    all: ["products"] as const,
    list: (filters: ProductListFilters) =>
      ["products", "list", stableKey(filters)] as const,
    detail: (id: string) => ["products", "detail", id] as const,
    signalMatching: (accountId?: string) =>
      ["products", "signal-matching", accountId ?? ""] as const,
    summary: () => ["products", "summary"] as const,
    coverage: () => ["products", "coverage"] as const,
  },

  // L3 — Evidence Library
  evidence: {
    all: ["evidence"] as const,
    list: (filters: CaseStudyListFilters) =>
      ["evidence", "list", stableKey(filters)] as const,
    detail: (id: string) => ["evidence", "detail", id] as const,
    industryStats: () => ["evidence", "stats", "industry"] as const,
  },

  // L3 — Competitive Intelligence
  competitive: {
    all: ["competitive"] as const,
    list: (filters: CompetitorListFilters) =>
      ["competitive", "list", stableKey(filters)] as const,
    detail: (id: string) => ["competitive", "detail", id] as const,
    battlecards: (competitorId: string) =>
      ["competitive", "battlecards", competitorId] as const,
    battlecard: (competitorId: string, productId: string) =>
      ["competitive", "battlecard", competitorId, productId] as const,
    winLoss: (competitorId?: string) =>
      ["competitive", "win-loss", competitorId ?? ""] as const,
    landscape: (productId?: string) =>
      ["competitive", "landscape", productId ?? ""] as const,
  },

  // L3 — ROI Calculator
  roi: {
    all: ["roi"] as const,
    list: (filters: ROICalculationListFilters) =>
      ["roi", "list", stableKey(filters)] as const,
    /**
     * L3 ROI benchmark assumptions (separate from L6 benchmark datasets).
     */
    assumptionsByIndustry: (industry: string) => ["roi", "assumptions", industry] as const,
    assumptionsList: () => ["roi", "assumptions-list"] as const,
    assumptionDetail: (id: string) => ["roi", "assumption", id] as const,
    agentCalculation: () => ["roi", "agent-calculation"] as const,
    /** Scenario versions scoped to a case/account/model triple (useROIScenarios). */
    scenarioVersions: (scope: { accountId?: string | null; caseId?: string | null; modelId?: string | null }) =>
      ["roi", "scenario-versions", scope.accountId ?? "", scope.caseId ?? "", scope.modelId ?? ""] as const,
  },

  // L3 — Value Calculators (Workflow)
  calculators: {
    all: ["calculators"] as const,
    levers: (filters: unknown) =>
      ["calculators", "levers", stableKey(filters)] as const,
  },

  // L4 — Account Enrichment
  enrichment: {
    all: ["enrichment"] as const,
    detail: (accountId: string) => ["enrichment", "detail", accountId] as const,
  },

  // L4 — Value Hypotheses
  hypotheses: {
    all: ["hypotheses"] as const,
    detail: (id: string) => ["hypotheses", "detail", id] as const,
    byAccount: (accountId: string, filters?: AccountHypothesesFilters) =>
      ["hypotheses", "account", accountId, stableKey(filters ?? {})] as const,
    stats: () => ["hypotheses", "stats"] as const,
  },

  // L4 — Narratives
  narratives: {
    all: ["narratives"] as const,
    list: (filters: NarrativeListFilters) =>
      ["narratives", "list", stableKey(filters)] as const,
    detail: (id: string) => ["narratives", "detail", id] as const,
  },

  // L5 — Ground Truth Governance
  groundTruth: {
    all: ["ground-truth"] as const,
    list: (filters: unknown) =>
      ["ground-truth", "list", stableKey(filters)] as const,
    audit: (truthId: string) => ["ground-truth", "audit", truthId] as const,
    freshnessSummary: () => ["ground-truth", "freshness-summary"] as const,
    stale: (filters: unknown) =>
      ["ground-truth", "stale", stableKey(filters)] as const,
    maturityLadder: () => ["ground-truth", "maturity-ladder"] as const,
  },

  // L4 — Intelligence Orchestration
  intelligence: {
    all: ["intelligence"] as const,
    briefing: (accountId: string) =>
      ["intelligence", "briefing", accountId] as const,
    dealReadiness: (accountId: string) =>
      ["intelligence", "deal-readiness", accountId] as const,
    pipeline: () => ["intelligence", "pipeline"] as const,
  },

  // Layer 1 — Scraping Targets
  targets: {
    all: ["targets"] as const,
    list: (filters: unknown) =>
      ["targets", "list", stableKey(filters)] as const,
    detail: (id: string) => ["targets", "detail", id] as const,
    stats: ["targets", "stats"] as const,
    jobs: (targetId: string) => ["targets", "jobs", targetId] as const,
  },

  // Layer 4 — Harness (workflow execution engine)
  harness: {
    all: ["harness"] as const,
    runs: (params: unknown) => ["harness", "runs", stableKey(params)] as const,
    run: (runId: string) => ["harness", "run", runId] as const,
    checkpoints: (runId: string) => ["harness", "checkpoints", runId] as const,
    gates: (runId: string) => ["harness", "gates", runId] as const,
    validation: (runId: string) => ["harness", "validation", runId] as const,
    health: () => ["harness", "health"] as const,
  },

  // Layer 4 — Gate reviews
  gates: {
    all: ["gates"] as const,
    account: (accountId: string) => ["gates", "account", accountId] as const,
  },

  // Governance reviews
  reviews: {
    all: ["reviews"] as const,
    list: (accountId: string) => ["reviews", "list", accountId] as const,
    detail: (reviewId: string) => ["reviews", "detail", reviewId] as const,
  },

  // Comments
  comments: {
    all: ["comments"] as const,
    list: (filters: unknown) =>
      ["comments", "list", stableKey(filters)] as const,
    detail: (id: string) => ["comments", "detail", id] as const,
  },

  // Notifications
  notifications: {
    all: ["notifications"] as const,
    list: (filters: unknown) =>
      ["notifications", "list", stableKey(filters)] as const,
    detail: (id: string) => ["notifications", "detail", id] as const,
  },

  // Tasks
  tasks: {
    all: ["tasks"] as const,
    list: (filters: unknown) =>
      ["tasks", "list", stableKey(filters)] as const,
    detail: (id: string) => ["tasks", "detail", id] as const,
  },

  // Layer 1 — Skill job outputs / source corpora
  skillOutputs: {
    all: ["skill-outputs"] as const,
    corpora: (filters?: unknown) =>
      filters != null
        ? ["skill-outputs", "corpora", stableKey(filters)]
        : (["skill-outputs", "corpora"] as const),
    corpus: (id: string) => ["skill-outputs", "corpus", id] as const,
    packets: (filters?: unknown) =>
      filters != null
        ? ["skill-outputs", "packets", stableKey(filters)]
        : (["skill-outputs", "packets"] as const),
    packet: (id: string) => ["skill-outputs", "packet", id] as const,
    jobOutput: (jobId: string) =>
      ["skill-outputs", "job-output", jobId] as const,
  },

  // Layer 3 — Value Signals
  valueSignals: {
    all: ["value-signals"] as const,
    list: (accountId: string, filters?: unknown) =>
      ["value-signals", "list", accountId, stableKey(filters ?? {})] as const,
    detail: (id: string) => ["value-signals", "detail", id] as const,
    account: (accountId: string) =>
      ["value-signals", "account", accountId] as const,
  },

  // Academy — Training & Certification
  academy: {
    all: ["academy"] as const,
    pillars: (tenantId: string) => ["academy", "pillars", tenantId] as const,
    pillar: (tenantId: string, pillarId: string) => ["academy", "pillar", tenantId, pillarId] as const,
    quiz: (tenantId: string, pillarId: string) => ["academy", "quiz", tenantId, pillarId] as const,
    progress: (tenantId: string) => ["academy", "progress", tenantId] as const,
    certifications: (tenantId: string) => ["academy", "certifications", tenantId] as const,
    maturityLevels: (tenantId: string) => ["academy", "maturity-levels", tenantId] as const,
    maturityAssessments: (tenantId: string) => ["academy", "maturity-assessments", tenantId] as const,
    resources: (tenantId: string) => ["academy", "resources", tenantId] as const,
  },
} as const;

// ── Helpers ───────────────────────────────────────────────────────────────────
/**
 * Produces a stable string key from an arbitrary object so that React Query
 * can use it as a cache key without reference equality issues.
 */
function stableKey(obj: unknown): string {
  if (obj == null || typeof obj !== "object") return String(obj);
  return JSON.stringify(obj, Object.keys(obj).sort());
}
