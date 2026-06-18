/**
 * Formula Versions React Query Hooks
 * 
 * Server state management for formula versioning:
 * - useFormulaVersions: Fetch version history for a formula
 * - useFormulaGovernance: Fetch governance metadata with versions
 * 
 * Connected to Layer 3 formula governance API.
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/typedClient';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';
import type { FormulaVersionStatus } from '@/api/statuses';

// ── Types ───────────────────────────────────────────────────────────────────

export interface FormulaVersion {
  version: string;
  formula_id: string;
  status: FormulaVersionStatus;
  created_at: string;
  created_by: string;
  change_summary: string;
  previous_version: string | null;
}

export interface FormulaGovernance {
  formula_id: string;
  current_version: string;
  status: string;
  owner: string | null;
  department: string | null;
  review_cycle_days: number;
  approved_by: string | null;
  approved_at: string | null;
  last_reviewed_at: string | null;
  next_review_at: string | null;
  versions: FormulaVersion[];
}

// ── Fetch Functions ─────────────────────────────────────────────────────────

async function fetchFormulaVersions(formulaId: string, includeRetired = false): Promise<FormulaVersion[]> {
  const response = await apiGet<FormulaVersion[]>(
    'l3',
    `/formulas/${encodeURIComponent(formulaId)}/versions?include_retired=${includeRetired}`
  );
  return response.data;
}

async function fetchFormulaGovernance(formulaId: string): Promise<FormulaGovernance> {
  const response = await apiGet<FormulaGovernance>(
    'l3',
    `/formulas/${encodeURIComponent(formulaId)}/governance`
  );
  return response.data;
}

// ── Hooks ───────────────────────────────────────────────────────────────────

/**
 * Fetch version history for a formula
 * 
 * @param formulaId - Formula ID to fetch versions for (null to disable)
 * @param includeRetired - Whether to include retired versions
 * @returns Query result with version list
 * 
 * @example
 * ```tsx
 * const { data: versions, isLoading } = useFormulaVersions('formula-123');
 * // versions: [{ version: '1.2.0', status: 'active', created_at: '...', ... }]
 * ```
 */
export function useFormulaVersions(formulaId: string | null, includeRetired = false) {
  return useQuery<FormulaVersion[], BaseApiError>({
    queryKey: [...QK.formulas.all, 'versions', formulaId, includeRetired] as const,
    queryFn: async () => {
      if (!formulaId) throw new BaseApiError('No formula ID provided');
      return withApiError(fetchFormulaVersions(formulaId, includeRetired), BaseApiError);
    },
    enabled: !!formulaId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

/**
 * Fetch governance metadata including version history
 * 
 * @param formulaId - Formula ID to fetch governance for (null to disable)
 * @returns Query result with governance data including versions
 * 
 * @example
 * ```tsx
 * const { data: governance } = useFormulaGovernance('formula-123');
 * // governance: { owner: '...', versions: [...], status: '...', ... }
 * ```
 */
export function useFormulaGovernance(formulaId: string | null) {
  return useQuery<FormulaGovernance, BaseApiError>({
    queryKey: [...QK.formulas.all, 'governance', formulaId] as const,
    queryFn: async () => {
      if (!formulaId) throw new BaseApiError('No formula ID provided');
      return withApiError(fetchFormulaGovernance(formulaId), BaseApiError);
    },
    enabled: !!formulaId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}
