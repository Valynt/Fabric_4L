/**
 * Value Studio (mission-led) — projection data hook.
 *
 * TanStack Query wrapper over the projection adapter seam (adapter.ts).
 * Phase 1 resolves deterministic fixtures; Phase 2 swaps the adapter for the
 * backend projection endpoint without touching components (FE-DATA-001: the
 * cache is never authoritative — the projection payload is).
 */

import { useQuery } from "@tanstack/react-query";

import { fixtureValueStudioAdapter, type ValueStudioProjectionAdapter } from "./adapter";
import type { ValueStudioViewState } from "./types";

export const VALUE_STUDIO_QUERY_KEY = "value-studio-mission-projection";

export function valueStudioProjectionKey(
  tenantSlug: string,
  accountId: string,
  fixtureName: string | null,
): readonly [string, string, string, string | null] {
  return [VALUE_STUDIO_QUERY_KEY, tenantSlug, accountId, fixtureName];
}

export interface UseValueStudioProjectionResult {
  readonly view: ValueStudioViewState | undefined;
  readonly isLoading: boolean;
  readonly error: Extract<ValueStudioViewState, { kind: "error" }> | null;
  readonly refetch: () => void;
}

function normalizeProjectionError(error: unknown): Extract<ValueStudioViewState, { kind: "error" }> {
  const candidate = error as { correlationId?: unknown; retryable?: unknown; message?: unknown };
  return {
    kind: "error",
    message:
      typeof candidate.message === "string" && candidate.message.length > 0
        ? candidate.message
        : "The value case could not be loaded.",
    correlationId:
      typeof candidate.correlationId === "string" && candidate.correlationId.length > 0
        ? candidate.correlationId
        : "corr_value_studio_projection_error",
    retryable: candidate.retryable !== false,
  };
}

export function useValueStudioProjection(
  tenantSlug: string,
  accountId: string,
  fixtureName: string | null,
  adapter: ValueStudioProjectionAdapter = fixtureValueStudioAdapter,
): UseValueStudioProjectionResult {
  const query = useQuery({
    queryKey: valueStudioProjectionKey(tenantSlug, accountId, fixtureName),
    queryFn: () =>
      adapter.getProjection({ tenantSlug, accountId, fixtureName }),
    // Fixture data is static; no polling in Phase 1. The backend adapter owns
    // refetch policy (contract §10.2) when it lands.
    staleTime: Infinity,
    retry: false,
  });

  return {
    view: query.data,
    isLoading: query.isLoading,
    error: query.error ? normalizeProjectionError(query.error) : null,
    refetch: () => {
      void query.refetch().catch(() => undefined);
    },
  };
}
