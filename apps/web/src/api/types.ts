/**
 * API Types — Contract-Aligned Type Definitions
 *
 * These types are manually maintained to align with the OpenAPI specs.
 * All API responses should be validated against these types using Zod.
 */

// ============================================================================
// Common Types
// ============================================================================

export interface ApiError {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: Record<string, unknown> | null;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// ============================================================================
// Layer 3: Knowledge Graph Types
// ============================================================================

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  properties?: Record<string, unknown>;
  confidence_score?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  properties?: Record<string, unknown>;
}

export interface SubgraphResponse {
  root_entity_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  depth: number;
  stats: {
    total_nodes: number;
    total_edges: number;
    density: number;
  };
}

export interface Entity {
  id: string;
  name: string;
  type: string;
  domain?: string;
  status: 'draft' | 'validated' | 'deprecated';
  properties: Record<string, unknown>;
  relationships?: Array<{
    target_id: string;
    relationship_type: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface EntityListResponse {
  results: Entity[];
  total: number;
  page: number;
}

// ============================================================================
// Layer 6: Benchmarks Types (canonical routes)
// ============================================================================

export interface BenchmarkDatasetSummary {
  dataset_id: string;
  name: string;
  description: string;
  industry: string;
  segment?: string;
  geography?: string;
  metrics: string[];
  metric_count: number;
  version: string;
  data_source?: string;
}

export interface BenchmarkComparisonMetric {
  metric_name: string;
  prospect_value: number;
  benchmark_value: number;
  percentile: number;
  delta_percent: number;
}

export interface BenchmarkCompareRequest {
  dataset_id: string;
  prospect_id: string;
  metrics: Array<{
    metric_name: string;
    value: number;
  }>;
}

export interface BenchmarkCompareResponse {
  prospect_id: string;
  metrics: BenchmarkComparisonMetric[];
  overall_percentile: number;
  dataset_id: string;
}

export interface BenchmarkIndustriesResponse {
  industries: string[];
}

// ============================================================================
// Value Trees & Formulas
// ============================================================================

export interface ValueTree {
  id: string;
  entity_id: string;
  root_node: ValueTreeNode;
  total_value: number;
  currency: string;
  confidence: number;
}

export interface ValueTreeNode {
  id: string;
  name: string;
  value: number;
  confidence: number;
  children?: ValueTreeNode[];
  formula_id?: string;
}

// Re-export from formula schema for convenience
export type { Formula, FormulaStatus, FormulaType, ApprovalRequest } from '@/lib/schemas/formula';

// ============================================================================
// Platform Workflow State Contract Types
// ============================================================================

export type WorkflowState =
  | 'created'
  | 'pending'
  | 'queued'
  | 'running'
  | 'waiting_dependency'
  | 'retrying'
  | 'paused'
  | 'interrupted'
  | 'cancelled'
  | 'completed'
  | 'succeeded'
  | 'failed'
  | 'failed_terminal';

export type GraphSyncStatus = 'pending' | 'syncing' | 'succeeded' | 'failed';

export type TruthApprovalStatus = 'pending' | 'approved' | 'rejected';

export interface WorkflowCorrelationIds {
  correlation_id: string;
  trace_id?: string;
  workflow_id?: string;
  job_id?: string;
  content_id?: string;
  extraction_job_id?: string;
}

export interface WorkflowDependencyState {
  graph_sync_status?: GraphSyncStatus;
  truth_approval_status?: TruthApprovalStatus;
}
