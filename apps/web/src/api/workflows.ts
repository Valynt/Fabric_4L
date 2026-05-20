import { apiClient } from './client';

// ── L4 Workflow Types ────────────────────────────────────────────────────────

export interface WorkflowCreateRequest {
  workflow_type: 'roi_calculator' | 'whitespace_analysis' | 'business_case' | 'business_case_generation' | 'orchestrator';
  inputs?: WorkflowInputs;
  priority?: 'CRITICAL' | 'HIGH' | 'NORMAL' | 'LOW' | 'BACKGROUND';
}

export interface WorkflowInputs {
  prospect_id?: string;
  prospect_company?: string;
  use_case_ids?: string[];
  prospect_metrics?: Record<string, number>;
  custom_data?: Record<string, unknown>;
}

export interface WorkflowCreateResponse {
  workflow_instance_id: string;
  status: string;
  estimated_duration_seconds: number;
}

export interface WorkflowProgress {
  step_id: string | null;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'unknown';
  percent: number;
  message: string;
  started_at: string | null;
  updated_at: string;
  completed_at: string | null;
  actionable_next_state: {
    can_retry: boolean;
    can_resume: boolean;
    can_cancel: boolean;
    requires_user_action: boolean;
    next_action: string | null;
  };
}

export interface WorkflowStatusResponse {
  workflow_instance_id: string;
  workflow_type: string;
  status: WorkflowStatus;
  current_state: string | null;
  current_node: string | null;
  progress_percentage: number;
  started_at: string | null;
  completed_at: string | null;
  error_count: number;
  has_output: boolean;
  results: Record<string, unknown> | null;
  tenant_id: string | null;
  user_id: string | null;
  priority: number | null;
  scheduler_status: string | null;
  progress: WorkflowProgress | null;
}

export type WorkflowStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused' | 'interrupted';

export interface WorkflowListItem {
  id: string;
  name: string;
  workflow_type: string;
  status: WorkflowStatus;
  progress: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface WorkflowListResponse {
  items: WorkflowListItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface WorkflowEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  message: string;
  payload?: Record<string, unknown>;
}

export interface WorkflowResumeRequest {
  user_id: string;
  resume_data?: Record<string, unknown>;
  tenant_id?: string;
}

export interface WorkflowResumeResponse {
  workflow_instance_id: string;
  status: string;
  resumed_from_node: string | null;
  message: string;
  estimated_completion_seconds: number;
}

export interface WorkflowOutput {
  data?: unknown;
  summary?: string | null;
  artifacts?: Record<string, unknown>[];
  metrics?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface WorkflowResultResponse {
  workflow_id: string;
  status: WorkflowStatus;
  output: WorkflowOutput | null;
  errors: (string | Record<string, unknown>)[];
  completed_at: string | null;
}

export interface WorkflowCancelResponse {
  workflow_id: string;
  status: 'cancelled';
}

export interface AvailableWorkflow {
  type: string;
  name: string;
  description: string;
}

export interface AvailableWorkflowsResponse {
  workflows: AvailableWorkflow[];
}

// ── Analysis Types ───────────────────────────────────────────────────────────

export interface ROIAnalysisRequest {
  prospect_id: string;
  value_driver_ids: string[];
  prospect_data?: Record<string, number>;
  industry_vertical?: string;
  company_size?: string;
}

export interface ROIAnalysisResponse {
  prospect_id: string;
  aggregated_roi: Record<string, unknown>;
  detailed_results: Record<string, unknown>[];
  benchmark_comparison: Record<string, unknown> | null;
}

export interface WhitespaceAnalysisRequest {
  prospect_id: string;
  prospect_needs: string;
  analysis_depth?: 'quick' | 'standard' | 'deep';
}

export interface WhitespaceAnalysisResponse {
  prospect_id: string;
  extracted_needs: string[];
  gap_analysis: Record<string, unknown>[];
  opportunity_score: number;
  recommendations: string[];
}

// ── API Functions ────────────────────────────────────────────────────────────

const L4: 'l4' = 'l4';

export const workflowApi = {
  create: (data: WorkflowCreateRequest) =>
    apiClient.post(L4, '/workflows', data).then(r => r.data as WorkflowCreateResponse),

  getStatus: (workflowId: string) =>
    apiClient.get(L4, `/workflows/${workflowId}`).then(r => r.data as WorkflowStatusResponse),

  getResult: (workflowId: string) =>
    apiClient.get(L4, `/workflows/${workflowId}/result`).then(r => r.data as WorkflowResultResponse),

  listActive: () =>
    apiClient.get(L4, '/workflows/active').then(r => r.data as WorkflowListResponse),

  listTypes: () =>
    apiClient.get(L4, '/workflows/types').then(r => r.data as AvailableWorkflowsResponse),

  cancel: (workflowId: string) =>
    apiClient.delete(L4, `/workflows/${workflowId}`).then(r => r.data as WorkflowCancelResponse),

  resume: (workflowId: string, data: WorkflowResumeRequest) =>
    apiClient.post(L4, `/workflows/${workflowId}/resume`, data).then(r => r.data as WorkflowResumeResponse),

  pause: (workflowId: string, data: { user_id: string; reason?: string; tenant_id?: string }) =>
    apiClient.post(L4, `/workflows/${workflowId}/pause`, data).then(r => r.data),
};

export const analysisApi = {
  roi: (data: ROIAnalysisRequest) =>
    apiClient.post(L4, '/analysis/roi', data).then(r => r.data as ROIAnalysisResponse),

  whitespace: (data: WhitespaceAnalysisRequest) =>
    apiClient.post(L4, '/analysis/whitespace', data).then(r => r.data as WhitespaceAnalysisResponse),
};
