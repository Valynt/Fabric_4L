/**
 * Search Mock Data
 *
 * Mock search results for testing global search functionality.
 */

import type { SearchResult, SearchResponse, SearchResultType } from "@/components/search/types";

const mockAccounts: SearchResult[] = [
  {
    id: "acc_123",
    type: "account",
    title: "Meridian Health Group",
    subtitle: "Healthcare • 500-1000 employees",
    excerpt: "Leading healthcare provider in the Northeast region",
    url: "/t/acme/accounts/acc_123",
    tenant_id: "acme",
    account_id: "acc_123",
    score: 0.95,
    source_layer: "frontend_mock",
  },
  {
    id: "acc_456",
    type: "account",
    title: "TechCorp Industries",
    subtitle: "Technology • 1000-5000 employees",
    excerpt: "Enterprise software solutions provider",
    url: "/t/acme/accounts/acc_456",
    tenant_id: "acme",
    account_id: "acc_456",
    score: 0.88,
    source_layer: "frontend_mock",
  },
];

const mockSignals: SearchResult[] = [
  {
    id: "sig_789",
    type: "signal",
    title: "Revenue Decline Risk",
    subtitle: "Signal • High confidence",
    excerpt: "Detected 15% revenue decline in Q3 compared to Q2",
    url: "/t/acme/accounts/acc_123/intelligence/signals/sig_789",
    tenant_id: "acme",
    account_id: "acc_123",
    score: 0.92,
    source_layer: "frontend_mock",
  },
  {
    id: "sig_012",
    type: "signal",
    title: "Competitor Expansion",
    subtitle: "Signal • Medium confidence",
    excerpt: "Competitor launching new product line in target market",
    url: "/t/acme/accounts/acc_456/intelligence/signals/sig_012",
    tenant_id: "acme",
    account_id: "acc_456",
    score: 0.75,
    source_layer: "frontend_mock",
  },
];

const mockEvidence: SearchResult[] = [
  {
    id: "ev_001",
    type: "evidence",
    title: "Manual Reconciliation Process",
    subtitle: "Evidence • Customer data",
    excerpt: "Current process requires 4 hours per account for manual reconciliation",
    url: "/t/acme/governance/evidence/ev_001",
    tenant_id: "acme",
    score: 0.89,
    source_layer: "frontend_mock",
  },
  {
    id: "ev_002",
    type: "evidence",
    title: "Q3 Earnings Call Transcript",
    subtitle: "Evidence • Benchmark",
    excerpt: "CEO discusses strategic initiatives and market expansion",
    url: "/t/acme/governance/evidence/ev_002",
    tenant_id: "acme",
    score: 0.82,
    source_layer: "frontend_mock",
  },
];

const mockStakeholders: SearchResult[] = [
  {
    id: "sh_001",
    type: "stakeholder",
    title: "Sarah Chen",
    subtitle: "Stakeholder • CFO",
    excerpt: "Chief Financial Officer at Meridian Health Group",
    url: "/t/acme/accounts/acc_123/intelligence/stakeholders/sh_001",
    tenant_id: "acme",
    account_id: "acc_123",
    score: 0.91,
    source_layer: "frontend_mock",
  },
];

const mockValueDrivers: SearchResult[] = [
  {
    id: "vd_001",
    type: "value_driver",
    title: "Operational Efficiency",
    subtitle: "Value Driver • High impact",
    excerpt: "Reducing manual processes through automation",
    url: "/t/acme/accounts/acc_123/intelligence/drivers/vd_001",
    tenant_id: "acme",
    account_id: "acc_123",
    score: 0.87,
    source_layer: "frontend_mock",
  },
];

const mockValueCases: SearchResult[] = [
  {
    id: "vc_001",
    type: "value_case",
    title: "Meridian Automation ROI",
    subtitle: "Value Case • Approved",
    excerpt: "Business case for RPA implementation showing 40% efficiency gain",
    url: "/t/acme/deliverables/cases/vc_001",
    tenant_id: "acme",
    score: 0.94,
    source_layer: "frontend_mock",
  },
];

const mockFormulas: SearchResult[] = [
  {
    id: "fm_001",
    type: "formula",
    title: "ROI Calculator v2",
    subtitle: "Formula • Active",
    excerpt: "Advanced ROI calculation with risk-adjusted returns",
    url: "/t/acme/calculator/formulas/fm_001",
    tenant_id: "acme",
    score: 0.85,
    source_layer: "frontend_mock",
  },
];

const mockBenchmarks: SearchResult[] = [
  {
    id: "bm_001",
    type: "benchmark",
    title: "Healthcare Industry KPIs",
    subtitle: "Benchmark • 2025",
    excerpt: "Industry benchmarks for healthcare financial metrics",
    url: "/t/acme/benchmarks/bm_001",
    tenant_id: "acme",
    score: 0.80,
    source_layer: "frontend_mock",
  },
];

const mockValuePacks: SearchResult[] = [
  {
    id: "vp_001",
    type: "value_pack",
    title: "Healthcare Value Pack",
    subtitle: "Value Pack • Enterprise",
    excerpt: "Pre-configured value drivers and formulas for healthcare",
    url: "/t/acme/value-packs/vp_001",
    tenant_id: "acme",
    score: 0.78,
    source_layer: "frontend_mock",
  },
];

const mockGraphEntities: SearchResult[] = [
  {
    id: "ge_001",
    type: "graph_entity",
    title: "Capability: Process Automation",
    subtitle: "Graph Entity • Capability",
    excerpt: "Core capability for business process automation",
    url: "/t/acme/graph/entities/ge_001",
    tenant_id: "acme",
    score: 0.76,
    source_layer: "frontend_mock",
  },
];

const mockAgentThreads: SearchResult[] = [
  {
    id: "at_001",
    type: "agent_thread",
    title: "Business Case Generation Thread",
    subtitle: "Agent Thread • Completed",
    excerpt: "AI-generated business case for Meridian Health Group",
    url: "/t/acme/agents/threads/at_001",
    tenant_id: "acme",
    score: 0.83,
    source_layer: "frontend_mock",
  },
];

const mockWorkflowRuns: SearchResult[] = [
  {
    id: "wr_001",
    type: "workflow_run",
    title: "ROI Analysis Run #42",
    subtitle: "Workflow Run • Completed",
    excerpt: "ROI analysis for Meridian Health Group opportunity",
    url: "/t/acme/workflows/runs/wr_001",
    tenant_id: "acme",
    score: 0.81,
    source_layer: "frontend_mock",
  },
];

const mockDeliverables: SearchResult[] = [
  {
    id: "dl_001",
    type: "deliverable",
    title: "Executive Summary Q3",
    subtitle: "Deliverable • PDF",
    excerpt: "Quarterly executive summary for board presentation",
    url: "/t/acme/deliverables/dl_001",
    tenant_id: "acme",
    score: 0.79,
    source_layer: "frontend_mock",
  },
];

const allMockResults: Record<SearchResultType, SearchResult[]> = {
  account: mockAccounts,
  signal: mockSignals,
  evidence: mockEvidence,
  stakeholder: mockStakeholders,
  value_driver: mockValueDrivers,
  value_case: mockValueCases,
  formula: mockFormulas,
  benchmark: mockBenchmarks,
  value_pack: mockValuePacks,
  graph_entity: mockGraphEntities,
  agent_thread: mockAgentThreads,
  workflow_run: mockWorkflowRuns,
  deliverable: mockDeliverables,
};

/**
 * Filter mock results by query string
 */
export function filterMockResults(query: string, results: Record<SearchResultType, SearchResult[]>): Record<SearchResultType, SearchResult[]> {
  const lowerQuery = query.toLowerCase();
  const filtered: Record<SearchResultType, SearchResult[]> = {} as Record<SearchResultType, SearchResult[]>;

  for (const [type, items] of Object.entries(results)) {
    const filteredItems = items.filter((item) => {
      return (
        item.title.toLowerCase().includes(lowerQuery) ||
        item.subtitle?.toLowerCase().includes(lowerQuery) ||
        item.excerpt?.toLowerCase().includes(lowerQuery)
      );
    });
    filtered[type as SearchResultType] = filteredItems;
  }

  return filtered;
}

/**
 * Count total results by type
 */
export function countByType(results: Record<SearchResultType, SearchResult[]>): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const [type, items] of Object.entries(results)) {
    counts[type] = items.length;
  }
  return counts;
}

/**
 * Create a mock search response
 */
export function createMockSearchResponse(query: string): SearchResponse {
  const filteredResults = filterMockResults(query, allMockResults);

  return {
    query,
    scope: "tenant",
    tenant_id: "acme",
    results: filteredResults,
    total_by_type: countByType(filteredResults),
    processing_time_ms: 50,
  };
}

/**
 * Get all mock results
 */
export { allMockResults as mockSearchResults };
