import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '@/api/typedClient';
import type { l4 } from '@/api/generated';
import { QK } from './queryKeys';
import { STALE_TIME, withApiError, BaseApiError } from './useApiShared';
import { L4_ANALYSIS_PREFIX } from '@/lib/apiConfig';
import { POLL_INTERVALS } from './usePolling';
import { createLogger } from '@/lib/telemetry';

const log = createLogger('useDocuments');

export class DocumentApiError extends BaseApiError {
  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message, statusCode, responseData);
    this.name = 'DocumentApiError';
  }
}

export interface BusinessCase {
  case_id: string;
  title: string;
  summary: string;
  total_value: number;
  implementation_cost: number;
  roi_ratio: number;
  payback_months: number;
  confidence_score: number;
  recommendations: string[];
  status: string;
  created_at?: string;
  document_url?: string;
  page_count: number;
  file_size_bytes: number;
  truth_references?: Array<Record<string, unknown>>;
  remediation_items?: Array<Record<string, unknown>>;
  case_metadata?: Record<string, unknown>;
  revision_history?: Array<Record<string, unknown>>;
  diff_summary?: Record<string, unknown>;
}

function normalizeBusinessCase(data: l4.components['schemas']['BusinessCaseResponse']): BusinessCase {
  return {
    ...data,
    created_at: data.created_at ?? undefined,
    document_url: data.document_url ?? undefined,
    recommendations: data.recommendations ?? [],
  };
}

// Constants for document operations
// EXPORT_POLL_INTERVAL_MS removed — use POLL_INTERVALS.exportStatus from usePolling
const ALLOWED_SCHEMES = ['http:', 'https:', 'blob:', 'data:'];


/**
 * Export a business case PDF.
 * Uses L4 analysis export endpoint.
 */
export function useBusinessCaseExport() {
  return useMutation<
    {
      case_id: string;
      format: string;
      document_url?: string;
      download_ready: boolean;
      blocked?: boolean;
      remediation_items?: Array<Record<string, unknown>>;
      truth_references?: Array<Record<string, unknown>>;
      manifest?: Record<string, unknown>;
    },
    DocumentApiError,
    { caseId: string; format?: string }
  >({
    mutationFn: async ({ caseId, format = 'pdf' }) => {
      const response = await apiGet<{
        case_id: string;
        format: string;
        document_url?: string;
        download_ready: boolean;
        blocked?: boolean;
        remediation_items?: Array<Record<string, unknown>>;
        truth_references?: Array<Record<string, unknown>>;
        manifest?: Record<string, unknown>;
      }>('l4', `${L4_ANALYSIS_PREFIX}/cases/${caseId}/export?format=${format}`);
      return response.data;
    },
    onError: (error) => {
      log.error('BusinessCaseExport failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/**
 * Fetch a business case by ID from Layer 4.
 * Cached for 5 minutes.
 */
export function useBusinessCase(businessCaseId: string | null) {
  return useQuery<BusinessCase, DocumentApiError>({
    queryKey: QK.documents.businessCase(businessCaseId || ''),
    queryFn: async () => {
      if (!businessCaseId) throw new Error('No business case ID provided');
      const response = await apiGet<l4.components['schemas']['BusinessCaseResponse']>('l4', `${L4_ANALYSIS_PREFIX}/cases/${businessCaseId}`);
      return normalizeBusinessCase(response.data);
    },
    enabled: !!businessCaseId,
    staleTime: STALE_TIME.detail,
  });
}

export function useRegenerateBusinessCase() {
  const queryClient = useQueryClient();
  return useMutation<BusinessCase, DocumentApiError, { caseId: string; accountId: string; valueCaseVersion?: string; valueCaseHash?: string }>({
    mutationFn: async ({ caseId, accountId, valueCaseVersion, valueCaseHash }) => {
      const response = await apiPost<l4.components['schemas']['BusinessCaseResponse']>(
        'l4',
        `${L4_ANALYSIS_PREFIX}/cases/${caseId}/regenerate`,
        {
          previous_case_id: caseId,
          account_id: accountId,
          custom_inputs: {
            value_case_version: valueCaseVersion ?? 'latest',
            value_case_hash: valueCaseHash ?? 'latest',
          },
        }
      );
      return normalizeBusinessCase(response.data);
    },
    onSuccess: (_data, { caseId }) => {
      // Regeneration changes case content — refetch the cached detail view
      queryClient.invalidateQueries({ queryKey: QK.documents.businessCase(caseId) });
    },
    onError: (error) => {
      log.error('RegenerateBusinessCase failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}


/**
 * Trigger a file download with URL validation.
 * Validates URL scheme to prevent XSS via javascript: protocol.
 * @throws Error if URL is malformed or uses an unsupported protocol
 */
export function downloadExport(downloadUrl: string, filename: string) {
  // Validate URL scheme to prevent XSS via javascript: protocol
  let url: URL;
  try {
    url = new URL(downloadUrl, window.location.href); // navigation-guardrail: ignore - file download URL construction, not navigation
  } catch {
    throw new Error('Invalid download URL: malformed URL');
  }

  if (!ALLOWED_SCHEMES.includes(url.protocol)) {
    throw new Error(`Invalid download URL: unsupported protocol "${url.protocol}"`);
  }

  // Store validated URL to prevent TOCTOU attacks
  const validatedHref = url.href;

  const link = document.createElement('a');
  link.href = validatedHref;
  link.download = filename;
  link.rel = 'noopener noreferrer'; // Security best practice
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
