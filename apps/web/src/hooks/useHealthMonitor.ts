/**
 * Health Monitor React Query Hooks
 *
 * Server state management for system health monitoring:
 * - useSystemHealth: Fetch overall system health status
 * - useServiceHealth: Fetch individual service health
 *
 * All hooks handle loading, error, and automatic refetching.
 */

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/typedClient";
import { QK } from "./queryKeys";
import {
  withApiError,
  BaseApiError,
  STALE_TIME,
  RETRY_CONFIG,
} from "./useApiShared";
import {
  parseHealthAlerts,
  parseSystemHealth,
  type HealthAlert,
  type ServiceHealth,
  type ServiceStatus,
  type SystemHealth,
} from "@/lib/schemas/healthMonitor";

export type { HealthAlert, ServiceHealth, ServiceStatus, SystemHealth };

// ── Fetch Functions ─────────────────────────────────────────────────────────

async function fetchSystemHealth(): Promise<SystemHealth> {
  const response = await apiGet<unknown>("l4", "/health");
  return parseSystemHealth(response.data);
}

async function fetchHealthAlerts(): Promise<HealthAlert[]> {
  const response = await apiGet<unknown>("l4", "/health/alerts");
  return parseHealthAlerts(response.data);
}

// ── Hooks ───────────────────────────────────────────────────────────────────

/**
 * Fetch overall system health status
 * Auto-refetches every 30 seconds for live monitoring
 *
 * @returns Query result with system health and loading/error states
 *
 * @example
 * ```tsx
 * const { data: health, isLoading } = useSystemHealth();
 * // health.overall_status: 'healthy' | 'degraded' | 'unhealthy'
 * // health.services: [{ name: 'l1-ingestion', status: 'healthy', ... }]
 * ```
 */
export function useSystemHealth() {
  return useQuery<SystemHealth, BaseApiError>({
    queryKey: QK.platform.health,
    queryFn: () => withApiError(fetchSystemHealth(), BaseApiError),
    staleTime: STALE_TIME.realtime,
    refetchInterval: STALE_TIME.poll, // 30 seconds for live monitoring
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

/**
 * Fetch active health alerts
 *
 * @returns Query result with active alerts
 *
 * @example
 * ```tsx
 * const { data: alerts } = useHealthAlerts();
 * const criticalAlerts = alerts?.filter(a => a.severity === 'critical');
 * ```
 */
export function useHealthAlerts() {
  return useQuery<HealthAlert[], BaseApiError>({
    queryKey: [...QK.platform.health, "alerts"] as const,
    queryFn: () => withApiError(fetchHealthAlerts(), BaseApiError),
    staleTime: STALE_TIME.poll,
    refetchInterval: STALE_TIME.stats, // 1 minute
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}
