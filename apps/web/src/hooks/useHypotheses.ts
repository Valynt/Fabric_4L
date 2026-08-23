/**
 * useHypotheses — Value Hypothesis hooks (L4 Agents)
 *
 * Covers all /v1/hypotheses endpoints from the Data Intelligence Layer.
 * Follows Contract C (Hook Architecture) Tier 2 domain hook pattern.
 *
 * Backend: layer4-agents/src/api/routes/value_hypotheses.py
 * Endpoints: 7
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPatch, apiDelete } from '@/api/typedClient';
import type { l4 } from '@/api/generated';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';
import { resolveBackendAccountId } from './useAccounts';

// ── Types ──────────────────────────────────────────────────────────────────

export type HypothesisStatus = 'draft' | 'validated' | 'rejected' | 'converted';

export interface ValueHypothesis {
  id: string;
  account_id: string;
  product_id: string;
  signal_id: string;
  signal_name?: string;
  capability_id?: string;
  hypothesis_text: string;
  capability_name?: string;
  value_path_category?: string;
  confidence: number;
  confidence_score?: number;
  estimated_impact_usd?: number;
  status: HypothesisStatus;
  evidence_ids: string[];
  feedback?: string;
  created_at: string;
  updated_at: string;
}

export interface GenerateHypothesesRequest {
  account_id: string;
  product_ids?: string[];
  max_hypotheses?: number;
  min_confidence?: number;
}

export interface GenerateHypothesesResponse {
  hypotheses: ValueHypothesis[];
  signals_analyzed: number;
  products_matched: number;
}

export interface AccountHypothesesFilters {
  status?: HypothesisStatus;
  value_path_category?: 'revenue_uplift' | 'cost_savings' | 'risk_reduction' | 'blended';
  product_id?: string;
  min_confidence?: number;
  skip?: number;
  limit?: number;
}

export interface AccountHypothesesResponse {
  hypotheses: ValueHypothesis[];
  total: number;
}

export interface ValidateHypothesisRequest {
  new_status: HypothesisStatus;
  feedback: string;
  evidence_ids?: string[];
  confidence_adjustment?: number;
}

export interface PromotedArtifacts {
  drivers?: Array<Record<string, unknown>>;
  levers?: Array<Record<string, unknown>>;
  linkages?: Array<{ hypothesis_id: string; driver_id: string; linkage_id: string }>;
  created?: boolean;
}

export interface ValidateHypothesisResponse {
  status: string;
  hypothesis: ValueHypothesis;
  promoted_artifacts?: PromotedArtifacts | null;
}

export interface HypothesisStats {
  total: number;
  by_status: Record<HypothesisStatus, number>;
  avg_confidence: number;
  conversion_rate: number;
}

export interface ConvertHypothesisToTreeResponse {
  hypothesis_id: string;
  account_id: string;
  tenant_id: string;
  evidence_ids: string[];
  value_model_id?: string | null;
  tree_id?: string | null;
  status: HypothesisStatus;
}

// ── Domain Error ───────────────────────────────────────────────────────────

export class HypothesisApiError extends BaseApiError {
  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message, statusCode, responseData);
    this.name = 'HypothesisApiError';
  }
}

// ── Fetch Functions ────────────────────────────────────────────────────────

function buildHypothesisParams(filters: AccountHypothesesFilters): string {
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.value_path_category) params.set('value_path_category', filters.value_path_category);
  if (filters.product_id) params.set('product_id', filters.product_id);
  if (filters.min_confidence != null) params.set('min_confidence', filters.min_confidence.toString());
  if (filters.skip != null) params.set('skip', filters.skip.toString());
  if (filters.limit != null) params.set('limit', filters.limit.toString());
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

async function fetchHypothesis(id: string): Promise<ValueHypothesis> {
  const response = await apiGet<ValueHypothesis>('l4', `/hypotheses/${id}`);
  return response.data;
}

async function fetchAccountHypotheses(
  accountId: string,
  filters: AccountHypothesesFilters,
): Promise<AccountHypothesesResponse> {
  const backendAccountId = await resolveBackendAccountId(accountId);
  const response = await apiGet<AccountHypothesesResponse>(
    'l4',
    `/hypotheses/account/${backendAccountId}${buildHypothesisParams(filters)}`,
  );
  return response.data;
}

async function fetchHypothesisStats(): Promise<HypothesisStats> {
  const response = await apiGet<HypothesisStats>('l4', '/hypotheses/summary/stats');
  return response.data;
}

// ── Query Hooks ────────────────────────────────────────────────────────────

export function useHypothesis(id: string | null) {
  return useQuery<ValueHypothesis, HypothesisApiError>({
    queryKey: QK.hypotheses.detail(id || ''),
    queryFn: async () => {
      if (!id) throw new HypothesisApiError('No hypothesis ID provided');
      return withApiError(fetchHypothesis(id), HypothesisApiError);
    },
    enabled: !!id,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useAccountHypotheses(accountId: string | null, filters: AccountHypothesesFilters = {}) {
  return useQuery<AccountHypothesesResponse, HypothesisApiError>({
    queryKey: QK.hypotheses.byAccount(accountId || '', filters),
    queryFn: async () => {
      if (!accountId) throw new HypothesisApiError('No account ID provided');
      return withApiError(fetchAccountHypotheses(accountId, filters), HypothesisApiError);
    },
    enabled: !!accountId,
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useHypothesisStats() {
  return useQuery<HypothesisStats, HypothesisApiError>({
    queryKey: QK.hypotheses.stats(),
    queryFn: () => withApiError(fetchHypothesisStats(), HypothesisApiError),
    staleTime: STALE_TIME.stats,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

// ── Mutation Hooks ─────────────────────────────────────────────────────────

export function useGenerateHypotheses() {
  const queryClient = useQueryClient();
  return useMutation<GenerateHypothesesResponse, HypothesisApiError, GenerateHypothesesRequest>({
    mutationFn: async (params) => {
      const backendAccountId = await resolveBackendAccountId(params.account_id);
      const response = await apiPost<GenerateHypothesesResponse>('l4', '/hypotheses/generate', {
        ...params,
        account_id: backendAccountId,
      });
      return response.data;
    },
    onSuccess: (_data, { account_id }) => {
      queryClient.invalidateQueries({ queryKey: QK.hypotheses.all });
      queryClient.invalidateQueries({ queryKey: QK.intelligence.briefing(account_id) });
    },
  });
}

export function useValidateHypothesis() {
  const queryClient = useQueryClient();
  return useMutation<
    ValidateHypothesisResponse,
    HypothesisApiError,
    { hypothesisId: string; data: ValidateHypothesisRequest }
  >({
    mutationFn: async ({ hypothesisId, data }) => {
      const response = await apiPost<ValidateHypothesisResponse | ValueHypothesis>('l4', `/hypotheses/${hypothesisId}/validate`, data);
      const raw = response.data;
      if ('hypothesis' in raw) return raw;
      return { status: 'updated', hypothesis: raw };
    },
    onSuccess: (data, { hypothesisId }) => {
      queryClient.invalidateQueries({ queryKey: QK.hypotheses.all });
      queryClient.invalidateQueries({ queryKey: QK.hypotheses.detail(hypothesisId) });
      queryClient.invalidateQueries({ queryKey: QK.calculators.all });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      if (data.hypothesis?.account_id) {
        queryClient.invalidateQueries({ queryKey: QK.hypotheses.byAccount(data.hypothesis.account_id) });
      }
    },
  });
}

export function useDeleteHypothesis() {
  const queryClient = useQueryClient();
  return useMutation<void, HypothesisApiError, string>({
    mutationFn: async (hypothesisId) => {
      await apiDelete<void>('l4', `/hypotheses/${hypothesisId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.hypotheses.all });
    },
  });
}

export function useConvertHypothesisToTree() {
  const queryClient = useQueryClient();
  return useMutation<
    ConvertHypothesisToTreeResponse,
    HypothesisApiError,
    { hypothesisId: string }
  >({
    mutationFn: async ({ hypothesisId }) => {
      const response = await apiPost<ConvertHypothesisToTreeResponse>('l4', `/hypotheses/${hypothesisId}/convert`, {});
      return response.data;
    },
    onSuccess: (_data, { hypothesisId }) => {
      queryClient.invalidateQueries({ queryKey: QK.hypotheses.all });
      queryClient.invalidateQueries({ queryKey: QK.hypotheses.detail(hypothesisId) });
      queryClient.invalidateQueries({ queryKey: QK.accounts.all });
      queryClient.invalidateQueries({ queryKey: QK.valueTrees.all });
    },
  });
}

export interface SignalReviewRequest {
  review_status: "approved" | "rejected" | "unreviewed";
  review_notes?: string;
  reviewed_at?: string;
}

export interface SignalReviewResponse {
  signal_id: string;
  review_status: string;
  review_notes: string | null;
  reviewed_at: string;
}

export function useReviewSignal() {
  const queryClient = useQueryClient();
  return useMutation<SignalReviewResponse, HypothesisApiError, { signalId: string; data: SignalReviewRequest }>({
    mutationFn: async ({ signalId, data }) => {
      const response = await apiPatch<SignalReviewResponse>('l4', `/signals/${signalId}/review`, data);
      return response.data;
    },
    onSuccess: (_data, { signalId }) => {
      queryClient.invalidateQueries({ queryKey: QK.hypotheses.all });
      queryClient.invalidateQueries({ queryKey: ['workspace', 'tab'] });
    },
  });
}
