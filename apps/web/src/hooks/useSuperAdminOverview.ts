/**
 * SuperAdmin Overview React Query Hook
 *
 * Fetches cross-tenant overview from the admin console endpoint.
 */

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/typedClient";
import { STALE_TIME, RETRY_CONFIG } from "./useApiShared";

// ── Types ───────────────────────────────────────────────────────────────────

export interface TenantOverviewItem {
  id: string;
  name: string;
  slug: string;
  status: string;
  tier_id: string;
  created_at: string;
  user_count: number;
  active_workflow_count: number;
}

export interface TenantOverviewResponse {
  items: TenantOverviewItem[];
  total: number;
  limit: number;
  offset: number;
}

// ── Fetch Function ──────────────────────────────────────────────────────────

async function fetchTenantOverview(
  limit: number,
  offset: number,
): Promise<TenantOverviewResponse> {
  const response = await apiGet<TenantOverviewResponse>("l4", "/agents/admin/tenant-overview", {
    params: { limit, offset },
  });
  return response.data;
}

// ── Hook ────────────────────────────────────────────────────────────────────

export function useSuperAdminOverview(limit = 100, offset = 0) {
  return useQuery({
    queryKey: ["admin", "tenant-overview", limit, offset],
    queryFn: () => fetchTenantOverview(limit, offset),
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}
