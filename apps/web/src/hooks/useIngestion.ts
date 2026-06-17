import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiDelete } from '@/api/typedClient';
import { QK } from './queryKeys';
import { STALE_TIME } from './useApiShared';
import { POLL_INTERVALS } from './usePolling';
import { parseIngestionAggregation, parseIngestionJobs, type ApiIngestionJobDto, type ApiComplianceLogDto } from '@/types/api';
import type { l1 } from '@/api/generated';
import { createLogger } from '@/lib/telemetry';

const log = createLogger('useIngestion');

export interface IngestionJob {
  id: string;
  domain: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  pagesFound?: number;
  pagesProcessed?: number;
  createdAt: string;
  updatedAt?: string;
  completedAt?: string;
}

export interface IngestionStats {
  totalDomains: number;
  pagesSynthesized: number;
  sourcesAnalyzed: number;
  avgProcessingTime: number;
}

export interface JobListFilters {
  status?: string[];
  dateFrom?: string;
  dateTo?: string;
  sortBy?: 'created_at' | 'started_at' | 'completed_at' | 'priority';
  sortOrder?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

export interface JobStage {
  stage: string;
  status: string;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  errorMessage?: string;
}

export interface JobError {
  id: string;
  stage: string;
  errorCode: string;
  errorMessage: string;
  url?: string;
  retryable: boolean;
  retryCount: number;
  occurredAt: string;
  resolvedAt?: string;
}

export interface JobProgress {
  totalPages?: number;
  processedPages: number;
  failedPages: number;
  currentUrl?: string;
  currentStage: string;
  percentComplete: number;
}

export interface JobResults {
  rawContentCount: number;
  extractedRecordCount: number;
  storageBytesUsed: number;
  outputLocation?: string;
}

export interface JobResources {
  browserSessionsUsed: number;
  proxyRequestsMade: number;
  llmTokensConsumed: number;
  computeTimeMs: number;
}

export interface IngestionJobDetail {
  id: string;
  targetId: string;
  tenantId: string;
  domain: string;
  configuration: Record<string, unknown>;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  priority: number;
  scheduledAt?: string;
  startedAt?: string;
  completedAt?: string;
  triggeredBy: string;
  correlationId?: string;
  createdBy: string;
  createdAt: string;
  updatedAt?: string;
  progress: JobProgress;
  results: JobResults;
  resources: JobResources;
  stages: JobStage[];
  errors: JobError[];
}

export interface ComplianceLogEntry {
  id: string;
  eventType: string;
  severity: string;
  requestUrl?: string;
  requestTimestamp: string;
  responseActionTaken?: string;
  createdAt: string;
}

export interface JobListResponse {
  jobs: IngestionJob[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
  aggregation: {
    byStatus: Record<string, number>;
    totalExecutionTimeMs: number;
    totalRecordsExtracted: number;
  };
}

type ComplianceLogsResponse = {
  items?: ApiComplianceLogDto[];
};

type JobDetailResponse = l1.components['schemas']['ScrapingJobDetail'] & {
  updated_at?: string | null;
};

function asObject(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function asNumber(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function asNumberRecord(value: unknown): Record<string, number> {
  const source = asObject(value);
  return Object.fromEntries(
    Object.entries(source).filter((entry): entry is [string, number] => typeof entry[1] === 'number' && Number.isFinite(entry[1]))
  );
}

function mapIngestionJob(job: ApiIngestionJobDto): IngestionJob {
  return {
    id: job.id || 'unknown',
    domain: job.configuration?.url || 'unknown',
    status: mapJobStatus(job.status || ''),
    progress: job.progress_percent_complete ?? 0,
    pagesProcessed: job.progress_processed_pages ?? 0,
    createdAt: job.created_at || new Date(0).toISOString(),
    updatedAt: job.started_at || job.updated_at || job.created_at || new Date(0).toISOString(),
  };
}

export function useIngestionJobs() {
  return useQuery<IngestionJob[], Error>({
    queryKey: QK.ingestion.jobs(),
    queryFn: async () => {
      const response = await apiGet<l1.components['schemas']['JobListResponse']>('l1', '/jobs');
      const jobs = parseIngestionJobs(response.data.data);
      return jobs.map(mapIngestionJob);
    },
    staleTime: STALE_TIME.poll,
  });
}

interface RecentIngestionJobsOptions {
  suppressAuthRedirect?: boolean;
}

export function useRecentIngestionJobs(
  limit = 5,
  options: RecentIngestionJobsOptions = {},
) {
  const requestConfig = options.suppressAuthRedirect
    ? { headers: { 'X-Fabric-Skip-Auth-Redirect': '1' } }
    : undefined;

  return useQuery<IngestionJob[], Error>({
    queryKey: QK.ingestion.recent(),
    queryFn: async () => {
      const response = await apiGet<l1.components['schemas']['JobListResponse']>('l1', `/jobs?limit=${limit}&sort_by=created_at&sort_order=desc`, requestConfig);
      const jobs = parseIngestionJobs(response.data.data);
      return jobs.map(mapIngestionJob);
    },
    staleTime: STALE_TIME.poll,
    refetchInterval: POLL_INTERVALS.ingestion,
  });
}

// Map backend job status to frontend status
function mapJobStatus(status: string): IngestionJob['status'] {
  const statusMap: Record<string, IngestionJob['status']> = {
    'PENDING': 'pending',
    'QUEUED': 'pending',
    'VALIDATING': 'processing',
    'BROWSER_ACQUIRING': 'processing',
    'NAVIGATING': 'processing',
    'EXTRACTING': 'processing',
    'TRANSFORMING': 'processing',
    'STORING': 'processing',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'CANCELLED': 'failed',
    'PARTIAL_SUCCESS': 'completed',
  };
  return statusMap[status] || 'pending';
}

export function useIngestionStats() {
  return useQuery<IngestionStats, Error>({
    queryKey: QK.ingestion.stats(),
    queryFn: async () => {
      const response = await apiGet<l1.components['schemas']['JobListResponse']>('l1', '/jobs?limit=1');
      const agg = parseIngestionAggregation(response.data.aggregation);
      const byStatus = agg.by_status || {};
      return {
        totalDomains: Object.values(byStatus).reduce((a, b) => a + b, 0),
        pagesSynthesized: agg.total_records_extracted ?? 0,
        sourcesAnalyzed: Object.keys(byStatus).length,
        avgProcessingTime: agg.total_execution_time_ms ?? 0,
      };
    },
    staleTime: STALE_TIME.stats,
  });
}

export interface SubmitDomainPayload {
  /** Domain to synthesize */
  domain: string;
  /** Extraction profile (e.g., "Default", "Deep Crawl") */
  profile?: string;
  /** Ontology target (e.g., "SaaS / B2B") */
  ontology?: string;
  /** Crawl depth (1–5) */
  depth?: string;
}

export function useSubmitDomain() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SubmitDomainPayload) => {
      const { domain, profile, ontology, depth } = payload;
      const url = domain.startsWith('http') ? domain : `https://${domain}`;

      // Step 1: Create a scraping target with the domain URL
      const targetResponse = await apiPost<l1.components['schemas']['ScrapingTargetDetail']>('l1', '/targets', {
        name: domain,
        url,
      });
      const targetId = targetResponse.data.id;
      if (!targetId) {
        throw new Error('Target creation response missing target id');
      }

      // Step 2: Execute the target to start the ingestion job
      // Pass advanced configuration through to the execution payload
      const executePayload: Record<string, unknown> = {};
      if (profile) executePayload.extraction_profile = profile;
      if (ontology) executePayload.ontology_target = ontology;
      if (depth) executePayload.crawl_depth = parseInt(depth, 10);

      const executeResponse = await apiPost<l1.components['schemas']['ExecuteTargetResponse']>('l1', `/targets/${targetId}/execute`, executePayload);
      const jobId = executeResponse.data.job_id;
      if (!jobId) {
        throw new Error('Target execution response missing job id');
      }
      return jobId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.ingestion.recent() });
      queryClient.invalidateQueries({ queryKey: QK.ingestion.stats() });
    },
    onError: (error) => {
      log.error('SubmitDomain failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/** List ingestion jobs with filtering and pagination */
export function useIngestionJobList(filters: JobListFilters = {}) {
  const { status, dateFrom, dateTo, sortBy = 'created_at', sortOrder = 'desc', page = 1, limit = 20 } = filters;

  return useQuery<JobListResponse, Error>({
    queryKey: QK.ingestion.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('limit', String(limit));
      params.set('sort_by', sortBy);
      params.set('sort_order', sortOrder);
      if (status?.length) status.forEach(s => params.append('status', s));
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);

      const response = await apiGet<l1.components['schemas']['JobListResponse']>('l1', `/jobs?${params.toString()}`);
      const data = response.data;
      const jobs = parseIngestionJobs(data.data);
      const pagination = asObject(data.pagination);
      const aggregation = asObject(data.aggregation);

      return {
        jobs: jobs.map(mapIngestionJob),
        pagination: {
          page: asNumber(pagination.page, page),
          limit: asNumber(pagination.limit, limit),
          total: asNumber(pagination.total, 0),
          totalPages: asNumber(pagination.totalPages, 0),
        },
        aggregation: {
          byStatus: asNumberRecord(aggregation.by_status),
          totalExecutionTimeMs: asNumber(aggregation.total_execution_time_ms, 0),
          totalRecordsExtracted: asNumber(aggregation.total_records_extracted, 0),
        },
      };
    },
    staleTime: STALE_TIME.poll,
    refetchInterval: POLL_INTERVALS.ingestion,
  });
}

/** Get detailed job information including stages and errors */
export function useIngestionJobDetail(jobId: string | null) {
  return useQuery<IngestionJobDetail, Error>({
    queryKey: jobId ? QK.ingestion.detail(jobId) : ['ingestion', 'detail', 'null'],
    queryFn: async () => {
      if (!jobId) throw new Error('Job ID is required');
      const response = await apiGet<JobDetailResponse>('l1', `/jobs/${jobId}`);
      const data = response.data;

      return {
        id: data.id,
        targetId: data.target_id,
        tenantId: data.tenant_id,
        domain: String((data.configuration as Record<string, unknown>)?.url || 'unknown'),
        configuration: data.configuration as Record<string, unknown> || {},
        status: mapJobStatus(data.status || ''),
        priority: data.priority ?? 5,
        createdAt: data.created_at || new Date(0).toISOString(),
        updatedAt: (data.updated_at ?? data.created_at) || new Date(0).toISOString(),
        scheduledAt: data.scheduled_at ?? undefined,
        startedAt: data.started_at ?? undefined,
        completedAt: data.completed_at ?? undefined,
        triggeredBy: data.triggered_by || 'manual',
        correlationId: data.correlation_id ?? undefined,
        createdBy: data.created_by,
        progress: {
          totalPages: data.progress.total_pages ?? undefined,
          processedPages: data.progress.processed_pages ?? 0,
          failedPages: data.progress.failed_pages ?? 0,
          currentUrl: data.progress.current_url ?? undefined,
          currentStage: data.progress.current_stage ?? 'INIT',
          percentComplete: data.progress.percent_complete ?? 0,
        },
        results: {
          rawContentCount: data.results.raw_content_count ?? 0,
          extractedRecordCount: data.results.extracted_record_count ?? 0,
          storageBytesUsed: data.results.storage_bytes_used ?? 0,
          outputLocation: data.results.output_location ?? undefined,
        },
        resources: {
          browserSessionsUsed: data.resources.browser_sessions_used ?? 0,
          proxyRequestsMade: data.resources.proxy_requests_made ?? 0,
          llmTokensConsumed: data.resources.llm_tokens_consumed ?? 0,
          computeTimeMs: data.resources.compute_time_ms ?? 0,
        },
        stages: data.stages.map(s => ({
          stage: s.stage,
          status: s.status,
          startedAt: s.started_at ?? undefined,
          completedAt: s.completed_at ?? undefined,
          durationMs: s.duration_ms ?? undefined,
          errorMessage: s.error_message ?? undefined,
        })),
        errors: data.errors.map(e => ({
          id: e.id,
          stage: e.stage,
          errorCode: e.error_code,
          errorMessage: e.error_message,
          url: e.url ?? undefined,
          retryable: e.retryable,
          retryCount: e.retry_count,
          occurredAt: e.occurred_at,
          resolvedAt: e.resolved_at ?? undefined,
        })),
      };
    },
    enabled: !!jobId,
    staleTime: STALE_TIME.poll,
    refetchInterval: POLL_INTERVALS.ingestion,
  });
}

/** Get compliance logs for a specific job */
export function useJobComplianceLogs(jobId: string | null) {
  return useQuery<ComplianceLogEntry[], Error>({
    queryKey: jobId ? QK.ingestion.logs(jobId) : ['ingestion', 'logs', 'null'],
    queryFn: async () => {
      if (!jobId) throw new Error('Job ID is required');
      const response = await apiGet<ComplianceLogsResponse>('l1', `/compliance/logs?job_id=${jobId}`);
      const items = response.data.items || [];

      return items.map(item => ({
        id: item.id,
        eventType: item.event_type,
        severity: item.severity,
        requestUrl: item.request_url,
        requestTimestamp: item.request_timestamp,
        responseActionTaken: item.response_action_taken,
        createdAt: item.created_at,
      }));
    },
    enabled: !!jobId,
    staleTime: STALE_TIME.list,
  });
}

/** Cancel a running or queued job */
export function useCancelJob() {
  const queryClient = useQueryClient();

  return useMutation<unknown, Error, string>({
    mutationFn: async (jobId: string) => {
      return apiDelete('l1', `/jobs/${jobId}`);
    },
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: QK.ingestion.detail(jobId) });
      queryClient.invalidateQueries({ queryKey: QK.ingestion.all });
    },
    onError: (error) => {
      log.error('CancelJob failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/** Retry a failed or partially successful job */
export function useRetryJob() {
  const queryClient = useQueryClient();

  return useMutation<unknown, Error, string>({
    mutationFn: async (jobId: string) => {
      return apiPost('l1', `/jobs/${jobId}/retry`, { retry_strategy: 'FULL' });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.ingestion.all });
    },
    onError: (error) => {
      log.error('RetryJob failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

// =============================================================================
// Batch Operations
// =============================================================================

export interface BatchOperationRequest {
  operation: 'execute' | 'cancel' | 'retry';
  target_ids?: string[];
  job_ids?: string[];
  options?: Record<string, unknown>;
}

export interface BatchOperationItemResult {
  id: string;
  status: 'succeeded' | 'failed' | 'skipped';
  job_id?: string;
  error?: string;
}

export interface BatchOperationResponse {
  operation: string;
  requested: number;
  succeeded: number;
  failed: number;
  results: BatchOperationItemResult[];
}

/** Execute batch operations on ingestion jobs and targets */
export function useBatchOperation() {
  const queryClient = useQueryClient();

  return useMutation<BatchOperationResponse, Error, BatchOperationRequest>({
    mutationFn: async (request: BatchOperationRequest) => {
      const response = await apiPost<BatchOperationResponse>('l1', '/jobs/batch', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.ingestion.all });
    },
    onError: (error) => {
      log.error('BatchOperation failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}
