/**
 * useRunExtraction.ts - Start extraction job mutation
 * 
 * Provides a mutation hook for initiating extraction jobs
 * via the Layer 2 API.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '@/api/typedClient';
import { QK } from '@/hooks/queryKeys';
import { createFeatureLogger } from '@/lib/telemetry';

const log = createFeatureLogger('useRunExtraction');

export interface RunExtractionParams {
  /** Source URL to extract from */
  sourceUrl: string;
  /** Markdown content (optional - if not provided, URL will be crawled) */
  markdownContent?: string;
  /** Extraction configuration */
  extractionConfig: {
    entity_types: string[];
    confidence_threshold: number;
    chunk_size: number;
    chunk_overlap: number;
  };
  /** Batch size for processing (frontend-only hint) */
  batchSize?: number;
  /** Priority hint (frontend-only) */
  priority?: 'low' | 'normal' | 'high';
}

export interface RunExtractionResult {
  /** Job ID for tracking */
  jobId: string;
  /** Initial status */
  status: string;
  /** Confirmation message */
  message: string;
}

type RunExtractionApiResponse = {
  extraction_job_id?: string;
  status?: string;
  message?: string;
};

/**
 * Start a new extraction job
 * 
 * @returns Mutation result with jobId on success
 */
export function useRunExtraction() {
  const queryClient = useQueryClient();

  return useMutation<RunExtractionResult, Error, RunExtractionParams>({
    mutationFn: async (params) => {
      // Generate a content ID based on source URL
      const contentId = `source-${Date.now()}`;
      
      const request = {
        content_id: contentId,
        source_url: params.sourceUrl,
        markdown_content: params.markdownContent || '',
        extraction_config: params.extractionConfig,
      };

      const response = await apiPost<RunExtractionApiResponse>('l2', '/v1/extract', request);
      const jobId = response.data.extraction_job_id;
      if (!jobId) {
        throw new Error('Extraction response missing job id');
      }
      
      return {
        jobId,
        status: response.data.status ?? 'pending',
        message: response.data.message ?? 'Extraction started',
      };
    },
    onSuccess: () => {
      // Invalidate extraction lists to refresh job history
      queryClient.invalidateQueries({ queryKey: QK.extraction.all });
    },
    onError: (error) => {
      log.error('Failed to start extraction', { errorCode: String(error) });
    },
  });
}
