/**
 * Search API Client
 *
 * Typed API client for global search functionality.
 */

import { apiClient } from "./client";
import type {
  SearchRequest,
  SearchResponse,
  SearchResult,
  SearchResultType,
} from "@/components/search/types";

// Search endpoint is on Layer 3 (Knowledge Graph & Semantic Layer)
const SEARCH_LAYER: 'l3' = 'l3';

/**
 * Execute a search query
 */
export async function search(request: SearchRequest): Promise<SearchResponse> {
  const params = new URLSearchParams();
  params.append("q", request.q);
  
  if (request.scope) {
    params.append("scope", request.scope);
  }
  
  if (request.account_id) {
    params.append("account_id", request.account_id);
  }
  
  if (request.types && request.types.length > 0) {
    params.append("types", request.types.join(","));
  }
  
  if (request.limit) {
    params.append("limit", request.limit.toString());
  }
  
  if (request.cursor) {
    params.append("cursor", request.cursor);
  }
  
  const response = await apiClient.get(
    SEARCH_LAYER,
    `/v1/search?${params.toString()}`
  );
  
  return response.data as SearchResponse;
}

/**
 * Generate a canonical URL for a search result
 */
export function generateSearchResultUrl(
  result: SearchResult,
  tenantSlug: string
): string {
  // Result already has a URL, validate it's tenant-scoped
  if (result.url) {
    // Ensure URL starts with /t/{tenantSlug}
    if (!result.url.startsWith(`/t/${tenantSlug}`)) {
      // If not, prepend tenant scope
      return `/t/${tenantSlug}${result.url.startsWith("/") ? result.url : `/${result.url}`}`;
    }
    return result.url;
  }
  
  // Fallback URL generation based on entity type
  const base = `/t/${tenantSlug}`;
  
  switch (result.type) {
    case "account":
      return result.account_id
        ? `${base}/accounts/${result.account_id}`
        : `${base}/accounts/${result.id}`;
    
    case "signal":
      return result.account_id
        ? `${base}/accounts/${result.account_id}/intelligence/signals/${result.id}`
        : `${base}/intelligence/signals/${result.id}`;
    
    case "evidence":
      return `${base}/governance/evidence/${result.id}`;
    
    case "stakeholder":
      return result.account_id
        ? `${base}/accounts/${result.account_id}/intelligence/stakeholders/${result.id}`
        : `${base}/intelligence/stakeholders/${result.id}`;
    
    case "value_driver":
      return result.account_id
        ? `${base}/accounts/${result.account_id}/intelligence/drivers/${result.id}`
        : `${base}/intelligence/drivers/${result.id}`;
    
    case "value_case":
      return `${base}/deliverables/cases/${result.id}`;
    
    case "formula":
      return `${base}/calculator/formulas/${result.id}`;
    
    case "benchmark":
      return `${base}/benchmarks/${result.id}`;
    
    case "value_pack":
      return `${base}/value-packs/${result.id}`;
    
    case "graph_entity":
      return `${base}/graph/entities/${result.id}`;
    
    case "agent_thread":
      return `${base}/agents/threads/${result.id}`;
    
    case "workflow_run":
      return `${base}/workflows/runs/${result.id}`;
    
    case "deliverable":
      return `${base}/deliverables/${result.id}`;
    
    default:
      return `${base}/search?q=${encodeURIComponent(result.title)}`;
  }
}

/**
 * Validate that a search result URL is safe (tenant-scoped)
 */
export function isSafeSearchResultUrl(
  url: string,
  tenantSlug: string
): boolean {
  // URL must start with /t/{tenantSlug}
  const expectedPrefix = `/t/${tenantSlug}`;
  return url.startsWith(expectedPrefix);
}

/**
 * Get display label for search result type
 */
export function getSearchResultTypeLabel(type: SearchResultType): string {
  const labels: Record<SearchResultType, string> = {
    account: "Account",
    signal: "Signal",
    evidence: "Evidence",
    stakeholder: "Stakeholder",
    value_driver: "Value Driver",
    value_case: "Value Case",
    formula: "Formula",
    benchmark: "Benchmark",
    value_pack: "Value Pack",
    graph_entity: "Graph Entity",
    agent_thread: "Agent Thread",
    workflow_run: "Workflow Run",
    deliverable: "Deliverable",
  };
  
  return labels[type] || type;
}

/**
 * Get icon name for search result type (for lucide-react)
 */
export function getSearchResultTypeIcon(type: SearchResultType): string {
  const icons: Record<SearchResultType, string> = {
    account: "Building2",
    signal: "Activity",
    evidence: "FileText",
    stakeholder: "Users",
    value_driver: "TrendingUp",
    value_case: "Briefcase",
    formula: "Calculator",
    benchmark: "BarChart3",
    value_pack: "Package",
    graph_entity: "Network",
    agent_thread: "MessageSquare",
    workflow_run: "Play",
    deliverable: "FileCheck",
  };
  
  return icons[type] || "Search";
}
