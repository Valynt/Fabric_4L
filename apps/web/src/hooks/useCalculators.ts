/**
 * useCalculators — Calculator API hooks (L3 Knowledge Graph)
 *
 * Covers all /v1/calculators endpoints from the Data Intelligence Layer.
 * Follows Contract C (Hook Architecture) Tier 2 domain hook pattern.
 *
 * Backend: layer3-knowledge/src/api/routes/calculators.py
 * Endpoints: 4
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/api/typedClient";
import { QK } from "./queryKeys";
import {
  withApiError,
  BaseApiError,
  STALE_TIME,
  RETRY_CONFIG,
} from "./useApiShared";

// ── Types ──────────────────────────────────────────────────────────────────

export interface ValueLever {
  id: string;
  name: string;
  base_value: number;
  min_value: number;
  max_value: number;
  unit: string;
  annual_impact: number;
  confidence: number;
  category: string;
}

export interface LeverConfigRequest {
  industry?: string;
  company_size?: string;
  product_line?: string;
}

export interface LeverConfigResponse {
  levers: ValueLever[];
  metadata: {
    industry: string;
    company_size: string;
    version: string;
    count: number;
  };
}

export interface ValueCaseRequest {
  account_id: string;
  prospect_id?: string;
  levers: Array<{
    lever_id: string;
    scenario_a: number;
    scenario_b: number;
    scenario_c?: number;
  }>;
  scenarios: Array<{
    name: "Conservative" | "Expected" | "Optimistic";
    total_value: number;
    breakdown: Array<{
      area: string;
      value: number;
      percentage: number;
    }>;
  }>;
  metadata: {
    generated_by: string;
    confidence_score: number;
    hypothesis_id?: string;
    evidence_link_count?: number;
    [key: string]: unknown;
  };
}

export interface ValueCaseResponse {
  case_id: string;
  account_id: string;
  created_at: string;
  updated_at: string;
  levers: ValueCaseRequest["levers"];
  scenarios: ValueCaseRequest["scenarios"];
  metadata: ValueCaseRequest["metadata"];
}

// ── Domain Error ───────────────────────────────────────────────────────────

export class CalculatorsApiError extends BaseApiError {
  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message, statusCode, responseData);
    this.name = "CalculatorsApiError";
  }
}

// ── Fetch Functions ────────────────────────────────────────────────────────

function buildLeverParams(filters: LeverConfigRequest): string {
  const params = new URLSearchParams();
  if (filters.industry) params.set("industry", filters.industry);
  if (filters.company_size) params.set("company_size", filters.company_size);
  if (filters.product_line) params.set("product_line", filters.product_line);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

async function fetchValueLevers(
  filters: LeverConfigRequest
): Promise<LeverConfigResponse> {
  const response = await apiGet<LeverConfigResponse>(
    "l3",
    `/v1/calculators/levers${buildLeverParams(filters)}`
  );
  return response.data;
}

async function createValueCase(
  data: ValueCaseRequest
): Promise<ValueCaseResponse> {
  const response = await apiPost<ValueCaseResponse>("l3", "/v1/calculators/value-cases", data);
  return response.data;
}

// ── Query Hooks ────────────────────────────────────────────────────────────

export function useValueLevers(
  filters: LeverConfigRequest = {},
  options: { enabled?: boolean } = {}
) {
  return useQuery<LeverConfigResponse, CalculatorsApiError>({
    queryKey: QK.calculators.levers(filters),
    queryFn: () => withApiError(fetchValueLevers(filters), CalculatorsApiError),
    enabled: options.enabled ?? true,
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

// ── Mutation Hooks ─────────────────────────────────────────────────────────

export function useCreateValueCase() {
  const queryClient = useQueryClient();
  return useMutation<
    ValueCaseResponse,
    CalculatorsApiError,
    ValueCaseRequest
  >({
    mutationFn: (data) => withApiError(createValueCase(data), CalculatorsApiError),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calculators"] });
    },
  });
}
