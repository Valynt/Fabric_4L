import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPut } from '@/api/typedClient';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';
import { createFeatureLogger } from '@/lib/telemetry';
import type { BenchmarkDatasetSummary } from '@/api/types';
import type { L3BenchmarkStatus } from '@/api/statuses';

const log = createFeatureLogger('useBenchmarks');


export type ConfidenceLevel = 'High' | 'Medium' | 'Low';
export type BenchmarkStatus = L3BenchmarkStatus;

export interface Benchmark {
  id: string;
  benchmark_id: string;
  name: string;
  industry: string;
  vertical?: string;
  value_range: string;
  confidence: ConfidenceLevel;
  source: string;
  source_url?: string;
  year: number;
  status: BenchmarkStatus;
  tags: string[];
  last_verified?: string;
  usage_count: number;
  description?: string;
}

/**
 * L6 dataset shape mapped into legacy benchmark UI fields.
 * Keep this hook L6-only; L3 ROI assumptions live in useROICalculator.
 */
export type L6BenchmarkDataset = BenchmarkDatasetSummary;

export interface BenchmarkPolicy {
  id: string;
  policy_id: string;
  name: string;
  description?: string;
  rules: Array<{
    metric: string;
    threshold: number;
    operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte';
  }>;
  status: 'active' | 'draft' | 'archived';
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface BenchmarkFilters {
  industry?: string;
  status?: BenchmarkStatus | 'all';
  confidence?: ConfidenceLevel | 'all';
  search?: string;
}

const CURRENT_YEAR = new Date().getFullYear();

function mapDatasetSummaryToBenchmark(dataset: BenchmarkDatasetSummary): Benchmark {
  return {
    id: dataset.dataset_id,
    benchmark_id: dataset.dataset_id,
    name: dataset.name,
    industry: dataset.industry,
    vertical: dataset.segment,
    value_range: `${dataset.metric_count} metrics`,
    confidence: 'High',
    source: dataset.data_source || 'Industry Research',
    year: CURRENT_YEAR,
    status: 'active',
    tags: [],
    usage_count: 0,
    description: dataset.description,
  };
}

async function fetchBenchmarks(filters: BenchmarkFilters): Promise<Benchmark[]> {
  const params = new URLSearchParams();
  if (filters.industry) params.set('industry', filters.industry);
  if (filters.status && filters.status !== 'all') params.set('status', filters.status);
  if (filters.confidence && filters.confidence !== 'all') params.set('confidence', filters.confidence);
  if (filters.search) params.set('search', filters.search);

  const response = await apiGet<BenchmarkDatasetSummary[]>('l6', `/datasets?${params.toString()}`);
  return response.data.map(mapDatasetSummaryToBenchmark);
}

/**
 * Hook to fetch a list of benchmarks with filtering support.
 *
 * @param filters - Optional filters for industry, status, confidence level, or search query
 * @returns Query result with Benchmark array and loading/error states
 */
export function useBenchmarks(filters: BenchmarkFilters = {}) {
  return useQuery<Benchmark[], BaseApiError>({
    queryKey: QK.benchmarks.list(filters),
    queryFn: () => withApiError(fetchBenchmarks(filters), BaseApiError),
    staleTime: STALE_TIME.stats,      // 1 minute for benchmark lists
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchBenchmark(benchmarkId: string): Promise<Benchmark> {
  const response = await apiGet<BenchmarkDatasetSummary>('l6', `/datasets/${benchmarkId}`);
  return mapDatasetSummaryToBenchmark(response.data);
}

/**
 * Hook to fetch a single benchmark by ID.
 *
 * @param benchmarkId - The benchmark ID to fetch, or null to disable the query
 * @returns Query result with Benchmark data and loading/error states
 */
export function useBenchmark(benchmarkId: string | null) {
  return useQuery<Benchmark, BaseApiError>({
    queryKey: QK.benchmarks.detail(benchmarkId || ''),
    queryFn: async () => {
      if (!benchmarkId) throw new BaseApiError('No benchmark ID provided');
      return withApiError(fetchBenchmark(benchmarkId), BaseApiError);
    },
    enabled: !!benchmarkId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchBenchmarkPolicies(): Promise<BenchmarkPolicy[]> {
  const response = await apiGet<BenchmarkPolicy[]>('l3', '/benchmarks/policies');
  return response.data;
}

/**
 * Hook to fetch benchmark policy configuration.
 *
 * @returns Query result with policy array and loading/error states
 */
export function useBenchmarkPolicies() {
  return useQuery<BenchmarkPolicy[], BaseApiError>({
    queryKey: QK.benchmarks.policies,
    queryFn: () => withApiError(fetchBenchmarkPolicies(), BaseApiError),
    staleTime: STALE_TIME.policies,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

/** Parameters for updating a benchmark policy */
export interface UpdateBenchmarkPolicyParams extends Partial<BenchmarkPolicy> {
  id: string;
}

/**
 * Hook to update a benchmark policy.
 *
 * @returns Mutation result with execute function and loading/error states
 */
export function useUpdateBenchmarkPolicy() {
  const queryClient = useQueryClient();

  return useMutation<BenchmarkPolicy, BaseApiError, UpdateBenchmarkPolicyParams>({
    mutationFn: async (policy) => {
      if (!policy.id) throw new BaseApiError('Policy ID is required');
      const response = await apiPut<BenchmarkPolicy>('l3', `/benchmarks/policies/${policy.id}`, policy);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.benchmarks.policies });
    },
    onError: (error) => {
      log.error('Benchmark policy update failed', { errorCode: error.message });
    },
  });
}
