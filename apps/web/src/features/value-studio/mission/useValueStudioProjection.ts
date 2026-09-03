/**
 * Value Studio (mission-led) — projection data hook.
 *
 * TanStack Query wrapper over the projection adapter seam (adapter.ts).
 * Phase 1 resolves deterministic fixtures; Phase 2 swaps the adapter for the
 * backend projection endpoint without touching components (FE-DATA-001: the
 * cache is never authoritative — the projection payload is).
 */

import { useQuery } from "@tanstack/react-query";

import { fixtureValueStudioAdapter } from "./adapter";
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
  readonly refetch: () => void;
}

export function useValueStudioProjection(
  tenantSlug: string,
  accountId: string,
  fixtureName: string | null,
): UseValueStudioProjectionResult {
  const query = useQuery({
    queryKey: valueStudioProjectionKey(tenantSlug, accountId, fixtureName),
    queryFn: () =>
      fixtureValueStudioAdapter.getProjection({ tenantSlug, accountId, fixtureName }),
    // Fixture data is static; no polling in Phase 1. The backend adapter owns
    // refetch policy (contract §10.2) when it lands.
    staleTime: Infinity,
    retry: false,
  });

  return {
    view: query.data,
    isLoading: query.isLoading,
    refetch: () => {
      void query.refetch();
    },
  };
}
