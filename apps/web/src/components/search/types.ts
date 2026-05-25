/**
 * Global Search Types
 *
 * Shared types for global search functionality across the application.
 */

export type SearchResultType =
  | "account"
  | "signal"
  | "evidence"
  | "stakeholder"
  | "value_driver"
  | "value_case"
  | "formula"
  | "benchmark"
  | "value_pack"
  | "graph_entity"
  | "agent_thread"
  | "workflow_run"
  | "deliverable";

export type SearchScope = "tenant" | "account";

export type SourceLayer = "l3" | "l4" | "l5" | "l6" | "frontend_mock";

export interface SearchResult {
  id: string;
  type: SearchResultType;
  title: string;
  subtitle?: string;
  excerpt?: string;
  url: string;
  tenant_id: string;
  account_id?: string;
  score?: number;
  source_layer?: SourceLayer;
  metadata?: Record<string, unknown>;
}

export interface SearchRequest {
  q: string;
  scope?: SearchScope;
  account_id?: string;
  types?: SearchResultType[];
  limit?: number;
  cursor?: string;
}

export interface SearchResponse {
  query: string;
  scope: SearchScope;
  tenant_id: string;
  account_id?: string;
  results: Record<SearchResultType, SearchResult[]>;
  total_by_type: Record<string, number>;
  processing_time_ms: number;
}

export interface GroupedSearchResults {
  [key: string]: SearchResult[];
}

export interface GlobalSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenantSlug?: string;
  accountId?: string;
}
