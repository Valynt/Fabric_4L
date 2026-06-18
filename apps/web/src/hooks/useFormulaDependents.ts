/**
 * Formula Dependents React Query Hooks
 * 
 * Server state management for formula dependencies:
 * - useFormulaDependents: Fetch assets that depend on this formula
 * - useFormulaDependencies: Fetch formulas this formula depends on
 * 
 * Connected to Layer 3 formula governance API.
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/typedClient';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';

// ── Types ───────────────────────────────────────────────────────────────────

export interface FormulaDependency {
  source_formula_id: string;
  target_formula_id: string;
  dependency_type: 'uses' | 'extends' | 'references';
}

export interface DependentAsset {
  type: 'Business Case' | 'Value Tree' | 'Workflow' | 'Formula';
  id: string;
  name: string;
  pack?: string;
  dependency_type?: string;
}

// ── Fetch Functions ─────────────────────────────────────────────────────────

async function fetchFormulaDependencies(
  formulaId: string,
  direction: 'outgoing' | 'incoming' | 'both' = 'both'
): Promise<FormulaDependency[]> {
  const response = await apiGet<FormulaDependency[]>(
    'l3',
    `/formulas/${encodeURIComponent(formulaId)}/dependencies?direction=${direction}`
  );
  return response.data;
}

// ── Hooks ───────────────────────────────────────────────────────────────────

/**
 * Fetch formulas that depend on this formula (incoming dependencies)
 * 
 * @param formulaId - Formula ID to find dependents for (null to disable)
 * @returns Query result with list of dependent formulas
 * 
 * @example
 * ```tsx
 * const { data: dependents, isLoading } = useFormulaDependents('formula-123');
 * // dependents: [{ type: 'Formula', name: 'Child Formula', pack: '...', ... }]
 * ```
 */
export function useFormulaDependents(formulaId: string | null) {
  return useQuery<DependentAsset[], BaseApiError>({
    queryKey: [...QK.formulas.all, 'dependents', formulaId] as const,
    queryFn: async () => {
      if (!formulaId) throw new BaseApiError('No formula ID provided');
      
      // Fetch incoming dependencies (formulas that depend on this one)
      const deps = await withApiError(
        fetchFormulaDependencies(formulaId, 'incoming'),
        BaseApiError
      );
      
      // Transform to DependentAsset format
      // Note: The API returns formula IDs, we would need to fetch names separately
      // For now, we'll return the dependency structure
      return deps.map(dep => ({
        type: 'Formula' as const,
        id: dep.source_formula_id,
        name: dep.source_formula_id, // Would need separate lookup for name
        dependency_type: dep.dependency_type,
      }));
    },
    enabled: !!formulaId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

/**
 * Fetch formulas this formula depends on (outgoing dependencies)
 * 
 * @param formulaId - Formula ID to find dependencies for (null to disable)
 * @returns Query result with list of formula dependencies
 * 
 * @example
 * ```tsx
 * const { data: dependencies } = useFormulaDependencies('formula-123');
 * // dependencies: [{ type: 'Formula', name: 'Parent Formula', ... }]
 * ```
 */
export function useFormulaDependencies(formulaId: string | null) {
  return useQuery<DependentAsset[], BaseApiError>({
    queryKey: [...QK.formulas.all, 'dependencies', formulaId] as const,
    queryFn: async () => {
      if (!formulaId) throw new BaseApiError('No formula ID provided');
      
      // Fetch outgoing dependencies (formulas this one depends on)
      const deps = await withApiError(
        fetchFormulaDependencies(formulaId, 'outgoing'),
        BaseApiError
      );
      
      return deps.map(dep => ({
        type: 'Formula' as const,
        id: dep.target_formula_id,
        name: dep.target_formula_id, // Would need separate lookup for name
        dependency_type: dep.dependency_type,
      }));
    },
    enabled: !!formulaId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}
