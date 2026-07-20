import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { createLogger } from '@/lib/telemetry';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';
import {
  type ValuePack,
  type PackStatus,
} from '@/lib/schemas/valuePack';
import {
  applyValuePack,
  getValuePackDetail,
  listValuePackSummaries,
  type ApplyValuePackResponse,
  type ValuePackFilters,
} from '@/api/packs';
import {
  compareFrameworkValuePacks,
  getFrameworkValuePack,
  getOntologyMap,
  getTemplateLibrary,
  listFrameworkValuePacks,
  type OntologyMapData,
  type TemplateLibraryData,
  type ValuePackComparisonData,
  type ValuePackComparisonRequest,
  type ValuePackFrameworkData,
} from '@/api/valuePackFramework';

// Domain-specific error class
const log = createLogger('useValuePacks');

export class ValuePackApiError extends BaseApiError {
  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message, statusCode, responseData);
    this.name = 'ValuePackApiError';
  }
}

// Re-export types from schema for backward compatibility
export type { ValuePack, PackStatus };
export type { ValuePackFilters };
export type {
  ValuePackFrameworkData,
  OntologyMapData,
  TemplateLibraryData,
  ValuePackComparisonData,
  ValuePackComparisonRequest,
};

/**
 * Fetch value packs with optional filtering.
 * @param filters - Optional filters for industry, status, scope, category, or search
 * @returns Array of value packs matching the filters
 */
async function fetchValuePacks(filters: ValuePackFilters): Promise<ValuePack[]> {
  try {
    return await listValuePackSummaries(filters);
  } catch (error) {
    if (error instanceof Error) {
      log.error('Value pack list validation failed', { error: error.message });
      throw error;
    }
    throw new ValuePackApiError('Invalid value pack list response');
  }
}

/**
 * Hook to fetch a list of value packs with optional filtering.
 * Results are cached for 1 minute (STALE_TIME.stats).
 *
 * @param filters - Optional filters for industry, status, scope, category, or search term
 * @returns React Query result with array of ValuePack objects
 *
 * @example
 * const { data: packs, isLoading } = useValuePacks({ industry: 'SaaS / B2B', status: 'published' });
 */
export function useValuePacks(filters: ValuePackFilters = {}) {
  return useQuery<ValuePack[], ValuePackApiError>({
    queryKey: QK.valuePacks.list(filters),
    queryFn: () => withApiError(fetchValuePacks(filters), ValuePackApiError),
    staleTime: STALE_TIME.stats,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

/**
 * Fetch a single value pack by ID.
 * @param packId - The unique identifier of the value pack
 * @returns The value pack details
 * @throws ValuePackApiError if the pack is not found or request fails
 */
async function fetchValuePack(packId: string): Promise<ValuePack> {
  try {
    return await getValuePackDetail(packId);
  } catch (error) {
    if (error instanceof Error) {
      log.error('Value pack detail validation failed', { error: error.message });
      throw error;
    }
    throw new ValuePackApiError('Invalid value pack response');
  }
}

/**
 * Hook to fetch a single value pack by ID.
 *
 * @param packId - The pack ID to fetch, or null to disable the query
 * @returns Query result with ValuePack data and loading/error states
 */
export function useValuePack(packId: string | null) {
  return useQuery<ValuePack, ValuePackApiError>({
    queryKey: QK.valuePacks.detail(packId || ''),
    queryFn: () =>
      packId
        ? withApiError(fetchValuePack(packId), ValuePackApiError)
        : Promise.reject(new ValuePackApiError('Pack ID is required')),
    enabled: packId !== null,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

/** Parameters for applying/deploying a value pack */
export interface ApplyValuePackParams {
  packId: string;
}

/**
 * Hook to apply/deploy a value pack to the current tenant.
 * Invalidates the value packs list query on success.
 *
 * @returns Mutation object with typed data/error/parameter types
 */
export function useApplyValuePack() {
  const queryClient = useQueryClient();

  return useMutation<ApplyValuePackResponse, ValuePackApiError, ApplyValuePackParams, { previousPack?: ValuePack; previousPacks?: ValuePack[] }>({
    mutationFn: async ({ packId }) => {
      if (!packId) throw new ValuePackApiError('Pack ID is required');
      return applyValuePack(packId);
    },
    onMutate: async ({ packId }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: QK.valuePacks.detail(packId) });
      await queryClient.cancelQueries({ queryKey: QK.valuePacks.list({}) });
      
      // Snapshot previous values
      const previousPack = queryClient.getQueryData<ValuePack>(QK.valuePacks.detail(packId));
      const previousPacks = queryClient.getQueryData<ValuePack[]>(QK.valuePacks.list({}));
      
      // Optimistically update pack detail to show applying status
      // Note: Only updating status, not scope, since scope is determined by server-side logic
      queryClient.setQueryData<ValuePack>(QK.valuePacks.detail(packId), (old) => {
        if (!old) return old;
        return { ...old, status: 'active' as PackStatus };
      });

      // Optimistically update pack in list
      queryClient.setQueryData<ValuePack[]>(QK.valuePacks.list({}), (old) => {
        return (old || []).map(p =>
          p.pack_id === packId
            ? { ...p, status: 'active' as PackStatus }
            : p
        );
      });
      
      return { previousPack, previousPacks };
    },
    onError: (error, { packId }, context) => {
      // Rollback to previous values
      if (context?.previousPack) {
        queryClient.setQueryData(QK.valuePacks.detail(packId), context.previousPack);
      }
      if (context?.previousPacks) {
        queryClient.setQueryData(QK.valuePacks.list({}), context.previousPacks);
      }
      // Log error for monitoring/debugging; UI handles display via error state
      log.error('Deployment failed', { error: error.message });
    },
    onSuccess: () => {
      // Invalidate to get fresh data from server
      queryClient.invalidateQueries({ queryKey: QK.valuePacks.list({}) });
    },
  });
}


/**
 * Fetch ValuePack Framework data for all industries.
 */
async function fetchValuePackFrameworkList(tier?: number, search?: string): Promise<ValuePackFrameworkData[]> {
  return listFrameworkValuePacks(tier, search);
}

/**
 * Hook to list ValuePacks with Framework v1.0 schema.
 */
export function useValuePackFrameworkList(tier?: number, search?: string) {
  return useQuery<ValuePackFrameworkData[], ValuePackApiError>({
    queryKey: [...QK.valuePacks.all, 'framework', 'list', tier, search],
    queryFn: () => withApiError(fetchValuePackFrameworkList(tier, search), ValuePackApiError),
    staleTime: STALE_TIME.stats,
    retry: RETRY_CONFIG.maxRetries,
  });
}

/**
 * Fetch single ValuePack Framework data.
 */
async function fetchValuePackFramework(industryId: string): Promise<ValuePackFrameworkData> {
  return getFrameworkValuePack(industryId);
}

/**
 * Hook to get a single ValuePack Framework v1.0 data.
 */
export function useValuePackFramework(industryId: string | null) {
  return useQuery<ValuePackFrameworkData, ValuePackApiError>({
    queryKey: [...QK.valuePacks.all, 'framework', 'detail', industryId],
    queryFn: () =>
      industryId
        ? withApiError(fetchValuePackFramework(industryId), ValuePackApiError)
        : Promise.reject(new ValuePackApiError('Industry ID is required')),
    enabled: industryId !== null,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
  });
}

/**
 * Hook to get cross-industry ontology map.
 */
export function useValuePackOntologyMap() {
  return useQuery<OntologyMapData, ValuePackApiError>({
    queryKey: [...QK.valuePacks.all, 'framework', 'ontology'],
    queryFn: () => withApiError(getOntologyMap(), ValuePackApiError),
    staleTime: STALE_TIME.stats,
    retry: RETRY_CONFIG.maxRetries,
  });
}

/**
 * Hook to get composable template library.
 */
export function useValuePackTemplates() {
  return useQuery<TemplateLibraryData, ValuePackApiError>({
    queryKey: [...QK.valuePacks.all, 'framework', 'templates'],
    queryFn: () => withApiError(getTemplateLibrary(), ValuePackApiError),
    staleTime: STALE_TIME.stats,
    retry: RETRY_CONFIG.maxRetries,
  });
}

/**
 * Hook to compare multiple ValuePacks.
 */
export function useValuePackComparison() {
  return useMutation<ValuePackComparisonData, ValuePackApiError, ValuePackComparisonRequest>({
    mutationFn: (request) => compareFrameworkValuePacks(request),
    onError: (error) => {
      log.error('Comparison failed', { error: error.message });
    },
  });
}

/**
 * Suggest ValuePacks based on prospect profile.
 */
export interface ProspectProfile {
  industry?: string;
  sub_industry?: string;
  employee_count?: number;
  annual_revenue?: string;
  pain_points?: string[];
  current_tech_stack?: string[];
}

export interface ValuePackSuggestion {
  industry_id: string;
  display_name: string;
  match_score: number;
  match_breakdown: {
    industry_match: number;
    pain_point_alignment: number;
    size_compatibility: number;
    tech_fit: number;
  };
  recommended_drivers: Array<{
    driver_id: string;
    relevance: string;
  }>;
}

/**
 * Hook to suggest ValuePacks for a prospect.
 */
export function useSuggestValuePacks() {
  // For now, this is a local calculation based on available data
  // In the future, this could call an agent endpoint
  const { data: allValuePacks } = useValuePackFrameworkList();
  
  return {
    suggest: (profile: ProspectProfile): ValuePackSuggestion[] => {
      if (!allValuePacks) return [];
      const painPoints = profile.pain_points ?? [];
      
      // Simple matching algorithm
      return allValuePacks.map(vp => {
        let industryMatch = 0;
        let painPointAlignment = 0;
        
        // Industry match
        if (profile.industry) {
          const profileInd = profile.industry.toLowerCase();
          const vpInd = vp.industry_id.toLowerCase();
          if (vpInd.includes(profileInd) || profileInd.includes(vpInd.replace('_', ' '))) {
            industryMatch = 1.0;
          } else {
            // Check ontology tags
            const hasRelatedTag = vp.pre_wired_ontology_tags.some(tag => 
              tag.related_tags.some(rt => profileInd.includes(rt.toLowerCase()))
            );
            if (hasRelatedTag) industryMatch = 0.7;
          }
        }
        
        // Pain point alignment
        if (painPoints.length > 0) {
          const matchedDrivers = vp.primary_value_drivers.filter(driver =>
            painPoints.some(pp => 
              driver.name.toLowerCase().includes(pp.toLowerCase()) ||
              driver.description.toLowerCase().includes(pp.toLowerCase())
            )
          );
          painPointAlignment = Math.min(matchedDrivers.length * 0.25, 1.0);
        }
        
        const matchScore = (industryMatch * 0.4) + (painPointAlignment * 0.3) + 0.3;
        
        return {
          industry_id: vp.industry_id,
          display_name: vp.display_name,
          match_score: matchScore,
          match_breakdown: {
            industry_match: industryMatch,
            pain_point_alignment: painPointAlignment,
            size_compatibility: 0.8, // Default
            tech_fit: 1.0, // Default
          },
          recommended_drivers: vp.primary_value_drivers.flatMap(d =>
            painPoints.some(pp =>
              d.description.toLowerCase().includes(pp.toLowerCase())
            )
              ? [{ driver_id: d.id, relevance: `Matches pain point` }]
              : []
          ),
        };
      }).sort((a, b) => b.match_score - a.match_score);
    },
    isReady: !!allValuePacks,
  };
}
