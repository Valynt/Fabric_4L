import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { apiGet, apiPost } from '@/api/typedClient';
import { withApiError, BaseApiError, STALE_TIME } from './useApiShared';
import { createLogger } from '@/lib/telemetry';

const log = createLogger('useUsage');

// ============================================================================
// Types
// ============================================================================

export interface UsageMetric {
  metric: string;
  total_quantity: number;
  unit: string;
  period_start: string;
  period_end: string;
}

export interface UsageLimit {
  metric: string;
  limit: number;
  unit: string;
  warning_threshold: number;
  hard_limit: number;
  overage_rate: number;
}

export interface UsageEvent {
  id: string;
  event_name: string;
  metric_name: string;
  quantity: number;
  timestamp: string;
  status: string;
}

export interface OverageCheck {
  allowed: boolean;
  overage: boolean;
  message: string;
  current: number;
  limit: number;
  projected: number;
}

// ============================================================================
// Query Keys
// ============================================================================

export const usageKeys = {
  all: ['usage'] as const,
  summary: (customerId: string) => [...usageKeys.all, 'summary', customerId] as const,
  limits: (customerId: string) => [...usageKeys.all, 'limits', customerId] as const,
  events: (customerId: string) => [...usageKeys.all, 'events', customerId] as const,
};

// ============================================================================
// Hooks
// ============================================================================

/**
 * Hook for fetching usage summary data.
 * Returns aggregated usage metrics for the current billing period.
 */
export function useUsageSummary(customerId: string) {
  return useQuery({
    queryKey: usageKeys.summary(customerId),
    queryFn: async () => {
      const response = await apiGet<{ metrics: UsageMetric[] }>(
        'l4',
        `/billing/usage?customer_id=${encodeURIComponent(customerId)}`
      );
      return response.data;
    },
    enabled: !!customerId,
    staleTime: STALE_TIME.detail,
  });
}

/**
 * Hook for fetching usage limits for a customer's plan.
 * Returns plan limits with warning thresholds and overage rates.
 */
export function useUsageLimits(customerId: string) {
  return useQuery({
    queryKey: usageKeys.limits(customerId),
    queryFn: async () => {
      const response = await apiGet<{ limits: UsageLimit[] }>(
        'l4',
        `/billing/limits?customer_id=${encodeURIComponent(customerId)}`
      );
      return response.data;
    },
    enabled: !!customerId,
    staleTime: STALE_TIME.detail,
  });
}

/**
 * Hook for fetching recent usage events.
 * Returns raw usage events for the customer.
 */
export function useUsageEvents(customerId: string) {
  return useQuery({
    queryKey: usageKeys.events(customerId),
    queryFn: async () => {
      const response = await apiGet<{ events: UsageEvent[] }>(
        'l4',
        `/billing/events?customer_id=${encodeURIComponent(customerId)}`
      );
      return response.data;
    },
    enabled: !!customerId,
    staleTime: STALE_TIME.list,
  });
}

/**
 * Hook for checking if an operation would exceed usage limits.
 * Used before performing costly operations.
 */
export function useCheckLimits(customerId: string) {
  const queryClient = useQueryClient();

  const checkMutation = useMutation({
    mutationFn: async (params: { metric: string; quantity: number }) => {
      return withApiError(
        apiPost<OverageCheck>('l4', `/billing/check?customer_id=${encodeURIComponent(customerId)}`, params)
          .then((r) => r.data),
        BaseApiError
      );
    },
    onSuccess: () => {
      // Invalidate usage summary after check (may have changed)
      queryClient.invalidateQueries({
        queryKey: usageKeys.summary(customerId),
      });
    },
    onError: (error) => {
      log.error('CheckLimits failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });

  const checkLimits = useCallback(
    async (metric: string, quantity: number): Promise<OverageCheck> => {
      return checkMutation.mutateAsync({ metric, quantity });
    },
    [checkMutation]
  );

  return {
    checkLimits,
    overageStatus: checkMutation.data,
    isChecking: checkMutation.isPending,
    error: checkMutation.error,
  };
}

/**
 * Combined hook for all usage-related data.
 * Provides a unified interface for usage dashboard.
 */
export function useUsage(customerId: string) {
  const summaryQuery = useUsageSummary(customerId);
  const limitsQuery = useUsageLimits(customerId);
  const eventsQuery = useUsageEvents(customerId);
  const checkLimitsHook = useCheckLimits(customerId);

  // Merge metrics with limits for display
  const metricsWithLimits = (summaryQuery.data?.metrics || []).map((metric) => {
    const limit = limitsQuery.data?.limits.find((l) => l.metric === metric.metric);
    return {
      ...metric,
      limit: limit?.limit || 0,
      warning_threshold: limit?.warning_threshold || 0,
      overage_rate: limit?.overage_rate || 0,
      percentage: limit?.limit ? (metric.total_quantity / limit.limit) * 100 : 0,
    };
  });

  return {
    // Data
    metrics: metricsWithLimits,
    limits: limitsQuery.data?.limits || [],
    events: eventsQuery.data?.events || [],

    // Loading states
    isLoading: summaryQuery.isLoading || limitsQuery.isLoading,
    isLoadingEvents: eventsQuery.isLoading,

    // Errors
    error: summaryQuery.error || limitsQuery.error || eventsQuery.error,

    // Actions
    checkLimits: checkLimitsHook.checkLimits,
    overageStatus: checkLimitsHook.overageStatus,
    isChecking: checkLimitsHook.isChecking,

    // Refetch
    refetch: () => {
      summaryQuery.refetch();
      limitsQuery.refetch();
      eventsQuery.refetch();
    },
  };
}
