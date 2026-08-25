/**
 * useCompetitiveIntel — Competitive Intelligence hooks (L3 Knowledge Graph)
 *
 * Covers all /v1/competitive endpoints from the Data Intelligence Layer.
 * Follows Contract C (Hook Architecture) Tier 2 domain hook pattern.
 *
 * Backend: layer3-knowledge/src/api/routes/competitive_intel.py
 * Endpoints: 10
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "@/api/typedClient";
import {
  parseBattlecard,
  parseBattlecardList,
  parseCompetitor,
  parseCompetitorListResponse,
} from "@/lib/schemas/competitiveIntel";
import type {
  Battlecard,
  Competitor,
  CompetitorListResponse,
} from "@/lib/schemas/competitiveIntel";
import { QK } from "./queryKeys";
import {
  withApiError,
  BaseApiError,
  STALE_TIME,
  RETRY_CONFIG,
} from "./useApiShared";

export type {
  Battlecard,
  Competitor,
  CompetitorListResponse,
  WinLossOutcome,
} from "@/lib/schemas/competitiveIntel";

// ── Request Types ────────────────────────────────────────────────────────────

export interface CreateCompetitorRequest {
  name: string;
  description: string;
  domain?: string | null;
  founded_year?: number | null;
  strengths?: string[];
  weaknesses?: string[];
  market_position?: string;
  pricing_tier?: string;
  target_segments?: string[];
}

export interface UpdateCompetitorRequest {
  name?: string | null;
  description?: string | null;
  domain?: string | null;
  founded_year?: number | null;
  strengths?: string[] | null;
  weaknesses?: string[] | null;
  market_position?: string | null;
  pricing_tier?: string | null;
  target_segments?: string[] | null;
}

export interface CompetitorListFilters {
  search?: string;
  market_position?: string;
  skip?: number;
  limit?: number;
}

// ── Domain Error ───────────────────────────────────────────────────────────

export class CompetitiveIntelApiError extends BaseApiError {
  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message, statusCode, responseData);
    this.name = "CompetitiveIntelApiError";
  }
}

// ── Fetch Functions ────────────────────────────────────────────────────────

function buildCompetitorParams(filters: CompetitorListFilters): string {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.market_position)
    params.set("market_position", filters.market_position);
  if (filters.skip != null) params.set("skip", filters.skip.toString());
  if (filters.limit != null) params.set("limit", filters.limit.toString());
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

async function fetchCompetitors(
  filters: CompetitorListFilters
): Promise<CompetitorListResponse> {
  const response = await apiGet<unknown>(
    "l3",
    `/v1/competitive/competitors${buildCompetitorParams(filters)}`
  );
  return parseCompetitorListResponse(response.data);
}

async function fetchCompetitor(id: string): Promise<Competitor> {
  const response = await apiGet<unknown>(
    "l3",
    `/v1/competitive/competitors/${encodeURIComponent(id)}`
  );
  return parseCompetitor(response.data);
}

async function fetchBattlecards(competitorId: string): Promise<Battlecard[]> {
  const response = await apiGet<unknown>(
    "l3",
    `/v1/competitive/competitors/${encodeURIComponent(competitorId)}/battlecards`
  );
  return parseBattlecardList(response.data);
}

async function fetchBattlecard(
  competitorId: string,
  productId: string
): Promise<Battlecard> {
  const response = await apiGet<unknown>(
    "l3",
    `/v1/competitive/competitors/${encodeURIComponent(competitorId)}/battlecard?product_id=${encodeURIComponent(productId)}`
  );
  return parseBattlecard(response.data);
}

// ── Query Hooks ────────────────────────────────────────────────────────────

export function useCompetitors(filters: CompetitorListFilters = {}) {
  return useQuery<CompetitorListResponse, CompetitiveIntelApiError>({
    queryKey: QK.competitive.list(filters),
    queryFn: () =>
      withApiError(fetchCompetitors(filters), CompetitiveIntelApiError),
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useCompetitor(id: string | null) {
  return useQuery<Competitor, CompetitiveIntelApiError>({
    queryKey: QK.competitive.detail(id || ""),
    queryFn: async () => {
      if (!id) throw new CompetitiveIntelApiError("No competitor ID provided");
      return withApiError(fetchCompetitor(id), CompetitiveIntelApiError);
    },
    enabled: !!id,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useBattlecards(competitorId: string | null) {
  return useQuery<Battlecard[], CompetitiveIntelApiError>({
    queryKey: QK.competitive.battlecards(competitorId || ""),
    queryFn: async () => {
      if (!competitorId)
        throw new CompetitiveIntelApiError("No competitor ID provided");
      return withApiError(
        fetchBattlecards(competitorId),
        CompetitiveIntelApiError
      );
    },
    enabled: !!competitorId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useBattlecard(
  competitorId: string | null,
  productId: string | null
) {
  return useQuery<Battlecard, CompetitiveIntelApiError>({
    queryKey: QK.competitive.battlecard(competitorId || "", productId || ""),
    queryFn: async () => {
      if (!competitorId || !productId)
        throw new CompetitiveIntelApiError("Competitor ID and Product ID are required");
      return withApiError(
        fetchBattlecard(competitorId, productId),
        CompetitiveIntelApiError
      );
    },
    enabled: !!competitorId && !!productId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

// ── Mutation Hooks ─────────────────────────────────────────────────────────

export function useCreateCompetitor() {
  const queryClient = useQueryClient();
  return useMutation<
    Competitor,
    CompetitiveIntelApiError,
    CreateCompetitorRequest
  >({
    mutationFn: async params => {
      const response = await apiPost<unknown>(
        "l3",
        "/v1/competitive/competitors",
        params
      );
      return parseCompetitor(response.data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.competitive.all });
    },
  });
}

export function useUpdateCompetitor() {
  const queryClient = useQueryClient();
  return useMutation<
    Competitor,
    CompetitiveIntelApiError,
    { id: string; data: UpdateCompetitorRequest }
  >({
    mutationFn: async ({ id, data }) => {
      const response = await apiPut<unknown>(
        "l3",
        `/v1/competitive/competitors/${encodeURIComponent(id)}`,
        data
      );
      return parseCompetitor(response.data);
    },
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: QK.competitive.all });
      queryClient.invalidateQueries({ queryKey: QK.competitive.detail(id) });
    },
  });
}

export function useDeleteCompetitor() {
  const queryClient = useQueryClient();
  return useMutation<void, CompetitiveIntelApiError, string>({
    mutationFn: async id => {
      await apiDelete<void>(
        "l3",
        `/v1/competitive/competitors/${encodeURIComponent(id)}`
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.competitive.all });
    },
  });
}
