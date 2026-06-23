/**
 * useExtractionResults.ts — Query hook for extraction job results
 *
 * Fetches completed extraction results (entities, relationships) from
 * the Layer 2 API for display in the results table.
 *
 * Refactored to use Tier 1 protocol hooks (src/api/protocol/extraction.ts)
 * and standard TanStack Query with shared error handling.
 */
import { useQuery } from '@tanstack/react-query';
import { QK } from '@/hooks/queryKeys';
import { STALE_TIME, RETRY_CONFIG, BaseApiError, withApiError } from '@/hooks/useApiShared';
import {
  fetchExtractionStatus,
  fetchExtractedEntities,
  type ExtractionStatusResponse,
  type ExtractedEntity,
} from '@/api/protocol/extraction';

// ── Domain Mappers ───────────────────────────────────────────────────────────

export interface ExtractionResult {
  /** Job ID */
  jobId: string;
  /** Overall status */
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  /** Extraction phase status */
  extractionStatus: string;
  /** Number of entities extracted */
  entitiesExtracted: number;
  /** Number of relationships extracted */
  relationshipsExtracted: number;
  /** Error message if failed */
  lastError: string | null;
  /** Start time */
  startedAt: string;
  /** Completion time */
  completedAt: string | null;
}

function mapExtractionResult(apiData: ExtractionStatusResponse): ExtractionResult {
  const statusMap: Record<string, ExtractionResult['status']> = {
    'PENDING': 'pending',
    'QUEUED': 'pending',
    'RUNNING': 'running',
    'EXTRACTING': 'running',
    'TRANSFORMING': 'running',
    'STORING': 'running',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'CANCELLED': 'cancelled',
  };

  return {
    jobId: apiData.job_id,
    status: statusMap[apiData.overall_status] || 'pending',
    extractionStatus: apiData.extraction_status,
    entitiesExtracted: apiData.entities_extracted ?? 0,
    relationshipsExtracted: apiData.relationships_extracted ?? 0,
    lastError: apiData.last_error,
    startedAt: apiData.started_at,
    completedAt: apiData.completed_at,
  };
}

// ── Tier 2 Domain Hooks ──────────────────────────────────────────────────────

/**
 * Get extraction job status and results.
 *
 * Uses TanStack Query with shared retry/error handling.
 */
export function useExtractionResults(jobId: string | null) {
  return useQuery<ExtractionResult, BaseApiError>({
    queryKey: QK.extraction.results(jobId || ''),
    queryFn: async () => {
      if (!jobId) throw new BaseApiError('No job ID provided');
      const data = await withApiError(fetchExtractionStatus(jobId), BaseApiError);
      return mapExtractionResult(data);
    },
    enabled: !!jobId,
    staleTime: STALE_TIME.poll,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling if job is complete or failed
      if (data?.status === 'completed' || data?.status === 'failed' || data?.status === 'cancelled') {
        return false;
      }
      return 2000; // Poll every 2 seconds while running
    },
  });
}

/**
 * Get list of extracted entities for a job.
 *
 * Uses TanStack Query with shared retry/error handling.
 *
 * NOTE: Backend endpoint GET /v1/extract/{job_id}/entities is pending (ticket L2-42).
 * The protocol hook returns an empty array until the endpoint is available.
 */
export function useExtractedEntities(jobId: string | null, count: number = 0) {
  return useQuery<ExtractedEntity[], BaseApiError>({
    queryKey: [...QK.extraction.results(jobId || ''), 'entities'],
    queryFn: async () => {
      if (!jobId || count === 0) return [];
      return withApiError(fetchExtractedEntities(jobId), BaseApiError);
    },
    enabled: !!jobId && count > 0,
    staleTime: STALE_TIME.stats,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}
