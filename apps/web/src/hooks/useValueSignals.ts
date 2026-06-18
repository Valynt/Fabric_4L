/**
 * useValueSignals — Value Signal Layer hooks (L2.5 Signal Refinery)
 *
 * Covers all /api/v1/signals endpoints from the L2.5 Signal Refinery service.
 * All hooks use typed API client wrappers — no raw apiClient calls.
 *
 * Backend: services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/api/routes/signals.py
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/api/typedClient";
import { QK } from "./queryKeys";
import { BaseApiError, RETRY_CONFIG, STALE_TIME, withApiError } from "./useApiShared";
import type {
  SignalPromoteRequest,
  SignalRefineRequest,
  ValueSignal,
  ValueSignalCreate,
  ValueSignalListResponse,
  ValueSignalUpdate,
} from "@/types/valueSignal";

// ---------------------------------------------------------------------------
// Query: list signals for an account
// ---------------------------------------------------------------------------

export interface ValueSignalFilters {
  types?: string[];
  lifecycle_state?: string[];
  min_confidence?: number;
  min_trust_score?: number;
  impact_area?: string;
  limit?: number;
  offset?: number;
}

export function useValueSignals(
  accountId: string | null,
  filters?: ValueSignalFilters,
) {
  return useQuery({
    queryKey: QK.valueSignals.list(accountId ?? "", filters),
    queryFn: () =>
      withApiError(
        apiGet<ValueSignalListResponse>("l2_5", "/api/v1/signals", {
          params: {
            account_id: accountId,
            ...filters,
          },
        }).then((r) => r.data),
        BaseApiError,
      ),
    enabled: !!accountId,
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

// ---------------------------------------------------------------------------
// Query: single signal
// ---------------------------------------------------------------------------

export function useValueSignal(signalId: string | null) {
  return useQuery({
    queryKey: QK.valueSignals.detail(signalId ?? ""),
    queryFn: () =>
      withApiError(
        apiGet<ValueSignal>("l2_5", `/api/v1/signals/${signalId}`).then(
          (r) => r.data,
        ),
        BaseApiError,
      ),
    enabled: !!signalId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

// ---------------------------------------------------------------------------
// Mutation: create signal
// ---------------------------------------------------------------------------

export function useCreateSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ValueSignalCreate) =>
      withApiError(
        apiPost<ValueSignal>("l2_5", "/api/v1/signals", body).then(
          (r) => r.data,
        ),
        BaseApiError,
      ),
    onSuccess: (signal) => {
      queryClient.invalidateQueries({
        queryKey: QK.valueSignals.account(signal.account_id),
      });
      queryClient.invalidateQueries({
        queryKey: QK.valueSignals.list(signal.account_id),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// Mutation: update signal (PATCH)
// ---------------------------------------------------------------------------

export function useUpdateSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      signalId,
      updates,
    }: {
      signalId: string;
      updates: ValueSignalUpdate;
    }) =>
      withApiError(
        apiPatch<ValueSignal>(
          "l2_5",
          `/api/v1/signals/${signalId}`,
          updates,
        ).then((r) => r.data),
        BaseApiError,
      ),
    onSuccess: (signal) => {
      queryClient.invalidateQueries({
        queryKey: QK.valueSignals.detail(signal.id),
      });
      queryClient.invalidateQueries({
        queryKey: QK.valueSignals.list(signal.account_id),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// Mutation: promote signal to hypothesis
// ---------------------------------------------------------------------------

export interface PromoteSignalVars {
  signalId: string;
  accountId: string;
  body: SignalPromoteRequest;
}

export function usePromoteValueSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ signalId, body }: PromoteSignalVars) =>
      withApiError(
        apiPost<ValueSignal & { value_path_category: string }>(
          "l2_5",
          `/api/v1/signals/${signalId}/promote`,
          body,
        ).then((r) => r.data),
        BaseApiError,
      ),
    onSuccess: (signal, vars) => {
      queryClient.invalidateQueries({
        queryKey: QK.valueSignals.detail(signal.id),
      });
      queryClient.invalidateQueries({
        queryKey: QK.valueSignals.list(vars.accountId),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// Mutation: delete signal (soft-delete)
// ---------------------------------------------------------------------------

export function useDeleteSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      signalId,
    }: {
      signalId: string;
      accountId: string;
    }) =>
      withApiError(
        apiDelete<void>("l2_5", `/api/v1/signals/${signalId}`).then(
          () => undefined,
        ),
        BaseApiError,
      ),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: QK.valueSignals.list(vars.accountId),
      });
      queryClient.removeQueries({
        queryKey: QK.valueSignals.detail(vars.signalId),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// Mutation: trigger L2.5 refinement
// ---------------------------------------------------------------------------

export interface RefineSignalsResult {
  refined: number;
  signal_ids: string[];
}

export function useRefineSignals() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: SignalRefineRequest) =>
      withApiError(
        apiPost<RefineSignalsResult>(
          "l2_5",
          "/api/v1/signals/refine",
          body,
        ).then((r) => r.data),
        BaseApiError,
      ),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: QK.valueSignals.list(vars.account_id),
      });
    },
  });
}
