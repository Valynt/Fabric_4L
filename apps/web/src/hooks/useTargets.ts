/**
 * useTargets.ts — Scraping Target Management Hooks
 *
 * TanStack Query hooks for the Layer 1 /targets API.
 * Covers the full CRUD surface plus status transitions, batch operations,
 * target execution, validation, and per-target job history.
 *
 * Route: /context/targets (admin tier)
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut, apiPatch, apiDelete } from '@/api/typedClient';
import type { l1 } from '@/api/generated';
import { createLogger } from '@/lib/telemetry';
import { QK } from './queryKeys';
import { withApiError, SourceApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';

const log = createLogger('useTargets');

// ── Types ─────────────────────────────────────────────────────────────────────

export type TargetStatus = 'ACTIVE' | 'PAUSED' | 'ARCHIVED' | 'ERROR';
export type TargetType = 'SINGLE_PAGE' | 'PAGINATED' | 'SPIDER' | 'API_ENDPOINT';
export type SourceCategory =
  | 'API' | 'CRM' | 'ERP' | 'HRIS' | 'MARKETING'
  | 'FINANCE' | 'PRODUCT' | 'SUPPORT' | 'GENERAL';
export type CrawlPath = 'fast' | 'browser' | 'fast_fallback';
export type AuthType = 'NONE' | 'BEARER' | 'API_KEY' | 'BASIC' | 'OAUTH2';
export type BatchOperation = 'execute' | 'pause' | 'archive';

export interface TargetSchedule {
  enabled?: boolean;
  cron_expression?: string;
  timezone?: string;
  max_concurrent_jobs?: number;
}

export interface TargetAuthentication {
  type?: AuthType;
  credentials_ref?: string;
}

/** Normalized frontend representation of a ScrapingTarget. */
export interface Target {
  id: string;
  tenantId: string;
  name: string;
  description: string | null;
  url: string;
  urlPattern: string | null;
  targetType: TargetType;
  sourceCategory: string | null;
  crawlPath: CrawlPath;
  status: TargetStatus;
  tags: string[];
  // Config blobs (passed through as-is for the edit form)
  extractionConfig: Record<string, unknown>;
  browserConfig: Record<string, unknown>;
  schedule: TargetSchedule | null;
  rateLimit: Record<string, unknown>;
  compliance: Record<string, unknown>;
  proxyConfig: Record<string, unknown>;
  authentication: TargetAuthentication | null;
  // Metrics
  successCount: number;
  errorCount: number;
  averageExecutionTimeMs: number;
  healthScore: number;
  // Timestamps
  createdAt: string;
  updatedAt: string;
  lastSuccessAt: string | null;
  lastErrorAt: string | null;
  createdBy: string;
}

export interface TargetSummary {
  id: string;
  name: string;
  url: string;
  targetType: TargetType;
  sourceCategory: string | null;
  status: TargetStatus;
  tags: string[];
  successCount: number;
  errorCount: number;
  averageExecutionTimeMs: number;
  healthScore: number;
  lastSuccessAt: string | null;
  createdAt: string;
  updatedAt: string;
  schedule: TargetSchedule | null;
}

export interface TargetFilters {
  search?: string;
  status?: TargetStatus;
  targetType?: TargetType;
  tags?: string[];
  page?: number;
  limit?: number;
  sortBy?: 'created_at' | 'updated_at' | 'last_success_at' | 'name';
  sortOrder?: 'asc' | 'desc';
}

export interface TargetListResponse {
  targets: TargetSummary[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface TargetStats {
  total: number;
  connected: number;
  disconnected: number;
  error: number;
  totalRecords: number;
  averageHealthScore: number;
}

export interface CreateTargetRequest {
  name: string;
  url: string;
  targetType: TargetType;
  sourceCategory?: SourceCategory;
  description?: string;
  urlPattern?: string;
  crawlPath?: CrawlPath;
  tags?: string[];
  extractionConfig?: Record<string, unknown>;
  browserConfig?: Record<string, unknown>;
  schedule?: TargetSchedule | null;
  rateLimit?: Record<string, unknown>;
  compliance?: Record<string, unknown>;
  proxyConfig?: Record<string, unknown>;
  authentication?: TargetAuthentication | null;
}

export interface UpdateTargetRequest extends Partial<CreateTargetRequest> {
  id: string;
}

export interface BatchOperationResult {
  id: string;
  status: 'succeeded' | 'failed' | 'skipped';
  jobId?: string | null;
  error?: string | null;
}

export interface BatchOperationResponse {
  operation: BatchOperation;
  requested: number;
  succeeded: number;
  failed: number;
  results: BatchOperationResult[];
}

// ── API response types ────────────────────────────────────────────────────────

type ApiTargetDetail = l1.components['schemas']['ScrapingTargetDetail'];
type ApiTargetSummary = l1.components['schemas']['ScrapingTargetSummary'];

interface ApiTargetListResponse {
  data: ApiTargetSummary[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
  };
}

// ── Normalization ─────────────────────────────────────────────────────────────

function calcHealthScore(successCount: number, errorCount: number): number {
  const total = successCount + errorCount;
  return total === 0 ? 0 : Math.round((successCount / total) * 100);
}

function normalizeTargetDetail(api: ApiTargetDetail): Target {
  return {
    id: api.id,
    tenantId: api.tenant_id,
    name: api.name,
    description: api.description,
    url: api.url,
    urlPattern: api.url_pattern,
    targetType: api.target_type as TargetType,
    sourceCategory: api.source_category ?? null,
    crawlPath: (api.crawl_path as CrawlPath) ?? 'browser',
    status: api.status as TargetStatus,
    tags: api.tags ?? [],
    extractionConfig: api.extraction_config ?? {},
    browserConfig: api.browser_config ?? {},
    schedule: api.schedule as TargetSchedule | null,
    rateLimit: api.rate_limit ?? {},
    compliance: api.compliance ?? {},
    proxyConfig: api.proxy_config ?? {},
    authentication: api.authentication
      ? {
          type: (api.authentication as Record<string, unknown>).type as AuthType | undefined,
          credentials_ref: (api.authentication as Record<string, unknown>).credentials_ref as string | undefined,
        }
      : null,
    successCount: api.success_count,
    errorCount: api.error_count,
    averageExecutionTimeMs: api.average_execution_time_ms,
    healthScore: calcHealthScore(api.success_count, api.error_count),
    createdAt: api.created_at,
    updatedAt: api.updated_at,
    lastSuccessAt: api.last_success_at ?? null,
    lastErrorAt: api.last_error_at,
    createdBy: api.created_by,
  };
}

function normalizeTargetSummary(api: ApiTargetSummary): TargetSummary {
  return {
    id: api.id,
    name: api.name,
    url: api.url,
    targetType: api.target_type as TargetType,
    sourceCategory: api.source_category ?? null,
    status: api.status as TargetStatus,
    tags: api.tags ?? [],
    successCount: api.success_count,
    errorCount: api.error_count,
    averageExecutionTimeMs: api.average_execution_time_ms,
    healthScore: calcHealthScore(api.success_count, api.error_count),
    lastSuccessAt: api.last_success_at ?? null,
    createdAt: api.created_at,
    updatedAt: api.updated_at,
    schedule: null,
  };
}

// ── Payload builder ───────────────────────────────────────────────────────────

function buildCreatePayload(req: CreateTargetRequest): Record<string, unknown> {
  return {
    name: req.name,
    url: req.url,
    target_type: req.targetType,
    source_category: req.sourceCategory,
    description: req.description,
    url_pattern: req.urlPattern,
    crawl_path: req.crawlPath ?? 'browser',
    tags: req.tags ?? [],
    extraction_config: req.extractionConfig ?? {},
    browser_config: req.browserConfig ?? {},
    schedule: req.schedule ?? null,
    rate_limit: req.rateLimit ?? {},
    compliance: req.compliance ?? {},
    proxy_config: req.proxyConfig ?? {},
    authentication: req.authentication ?? null,
  };
}

// ── Query Hooks ───────────────────────────────────────────────────────────────

/** List scraping targets with optional filtering and pagination. */
export function useTargets(filters: TargetFilters = {}) {
  const {
    search,
    status,
    targetType,
    tags,
    page = 1,
    limit = 25,
    sortBy = 'created_at',
    sortOrder = 'desc',
  } = filters;

  return useQuery<TargetListResponse, SourceApiError>({
    queryKey: QK.targets.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('limit', String(limit));
      params.set('sort_by', sortBy);
      params.set('sort_order', sortOrder);
      if (search) params.set('search', search);
      if (status) params.set('status', status);
      if (targetType) params.set('target_type', targetType);
      if (tags?.length) tags.forEach(t => params.append('tags', t));

      const response = await withApiError(
        apiGet<ApiTargetListResponse>('l1', `/targets?${params.toString()}`),
        SourceApiError,
      );

      const data = response.data;
      return {
        targets: data.data.map(normalizeTargetSummary),
        pagination: {
          page: data.pagination.page,
          limit: data.pagination.limit,
          total: data.pagination.total,
          totalPages: data.pagination.total_pages,
        },
      };
    },
    staleTime: STALE_TIME.poll,
    retry: RETRY_CONFIG.maxRetries,
  });
}

/** Fetch full detail for a single target. */
export function useTarget(id: string | null) {
  return useQuery<Target, SourceApiError>({
    queryKey: id ? QK.targets.detail(id) : ['targets', 'detail', 'null'],
    queryFn: async () => {
      if (!id) throw new SourceApiError('Target ID is required');
      const response = await withApiError(
        apiGet<ApiTargetDetail>('l1', `/targets/${id}`),
        SourceApiError,
      );
      return normalizeTargetDetail(response.data);
    },
    enabled: !!id,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
  });
}

/** Aggregated stats for all targets in the tenant. */
export function useTargetStats() {
  return useQuery<TargetStats, SourceApiError>({
    queryKey: QK.targets.stats,
    queryFn: async () => {
      const response = await withApiError(
        apiGet<l1.components['schemas']['TargetStatsResponse']>('l1', '/targets/stats'),
        SourceApiError,
      );
      const d = response.data;
      return {
        total: d.total,
        connected: d.connected,
        disconnected: d.disconnected,
        error: d.error,
        totalRecords: d.total_records,
        averageHealthScore: d.average_health_score,
      };
    },
    staleTime: STALE_TIME.stats,
    retry: RETRY_CONFIG.maxRetries,
  });
}

/** Recent jobs for a specific target (for the detail panel job history). */
export function useTargetJobs(targetId: string | null) {
  return useQuery({
    queryKey: targetId ? QK.targets.jobs(targetId) : ['targets', 'jobs', 'null'],
    queryFn: async () => {
      if (!targetId) return { jobs: [], pagination: { page: 1, limit: 10, total: 0, totalPages: 0 } };
      const params = new URLSearchParams({
        target_id: targetId,
        limit: '10',
        sort_by: 'created_at',
        sort_order: 'desc',
      });
      const response = await withApiError(
        apiGet<{ data: unknown[]; pagination: { page: number; limit: number; total: number; total_pages: number } }>(
          'l1',
          `/jobs?${params.toString()}`,
        ),
        SourceApiError,
      );
      const d = response.data;
      return {
        jobs: d.data,
        pagination: {
          page: d.pagination.page,
          limit: d.pagination.limit,
          total: d.pagination.total,
          totalPages: d.pagination.total_pages,
        },
      };
    },
    enabled: !!targetId,
    staleTime: STALE_TIME.poll,
    retry: RETRY_CONFIG.maxRetries,
  });
}

// ── Mutation Hooks ────────────────────────────────────────────────────────────

/** Create a new scraping target. */
export function useCreateTarget() {
  const queryClient = useQueryClient();

  return useMutation<Target, SourceApiError, CreateTargetRequest>({
    mutationFn: async (request) => {
      const response = await withApiError(
        apiPost<ApiTargetDetail>('l1', '/targets', buildCreatePayload(request)),
        SourceApiError,
      );
      return normalizeTargetDetail(response.data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.targets.all });
    },
    onError: (error) => {
      log.error('Failed to create target', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/** Full update (PUT) of a scraping target. */
export function useUpdateTarget() {
  const queryClient = useQueryClient();

  return useMutation<Target, SourceApiError, UpdateTargetRequest>({
    mutationFn: async ({ id, ...rest }) => {
      const payload = buildCreatePayload(rest as CreateTargetRequest);
      const response = await withApiError(
        apiPut<ApiTargetDetail>('l1', `/targets/${id}`, payload),
        SourceApiError,
      );
      return normalizeTargetDetail(response.data);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QK.targets.all });
      queryClient.setQueryData(QK.targets.detail(data.id), data);
    },
    onError: (error) => {
      log.error('Failed to update target', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/** Lightweight status transition (PATCH). */
export function useUpdateTargetStatus() {
  const queryClient = useQueryClient();

  return useMutation<Target, SourceApiError, { id: string; status: TargetStatus }>({
    mutationFn: async ({ id, status }) => {
      const response = await withApiError(
        apiPatch<ApiTargetDetail>('l1', `/targets/${id}/status`, { status }),
        SourceApiError,
      );
      return normalizeTargetDetail(response.data);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QK.targets.all });
      queryClient.setQueryData(QK.targets.detail(data.id), data);
    },
    onError: (error) => {
      log.error('Failed to update target status', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/** Delete (soft-archive) a target. */
export function useDeleteTarget() {
  const queryClient = useQueryClient();

  return useMutation<void, SourceApiError, string>({
    mutationFn: async (id) => {
      await withApiError(
        apiDelete<void>('l1', `/targets/${id}`),
        SourceApiError,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.targets.all });
    },
    onError: (error) => {
      log.error('Failed to delete target', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

export interface ExecuteTargetResult {
  jobId: string;
  status: string;
  estimatedStartTime: string | null;
  queuePosition: number | null;
}

/** Trigger an immediate crawl job for a target. */
export function useExecuteTarget() {
  const queryClient = useQueryClient();

  return useMutation<ExecuteTargetResult, SourceApiError, { id: string; priority?: number }>({
    mutationFn: async ({ id, priority = 5 }) => {
      const response = await withApiError(
        apiPost<{
          job_id: string;
          status: string;
          estimated_start_time?: string | null;
          queue_position?: number | null;
        }>('l1', `/targets/${id}/execute`, { priority }),
        SourceApiError,
      );
      const d = response.data;
      return {
        jobId: d.job_id,
        status: d.status,
        estimatedStartTime: d.estimated_start_time ?? null,
        queuePosition: d.queue_position ?? null,
      };
    },
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: QK.targets.jobs(id) });
      queryClient.invalidateQueries({ queryKey: QK.ingestion.jobs() });
    },
    onError: (error) => {
      log.error('Failed to execute target', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

export interface ValidateTargetResult {
  valid: boolean;
  errors: Array<{ loc: (string | number)[]; msg: string; type: string }>;
  warnings: Array<{ field: string; message: string; suggestion?: string | null }>;
  robotsTxtCheck: Record<string, unknown> | null;
  schemaValidation: Record<string, unknown> | null;
  browserTest: Record<string, unknown> | null;
}

/** Validate a target's configuration without executing. */
export function useValidateTarget() {
  return useMutation<
    ValidateTargetResult,
    SourceApiError,
    { id: string; testUrl?: string; testBrowserConnection?: boolean }
  >({
    mutationFn: async ({ id, testUrl, testBrowserConnection = false }) => {
      const response = await withApiError(
        apiPost<{
          valid: boolean;
          errors: Array<{ loc: (string | number)[]; msg: string; type: string }>;
          warnings: Array<{ field: string; message: string; suggestion?: string | null }>;
          robots_txt_check?: Record<string, unknown> | null;
          schema_validation?: Record<string, unknown> | null;
          browser_test?: Record<string, unknown> | null;
        }>(
          'l1',
          `/targets/${id}/validate`,
          {
            test_url: testUrl,
            validate_robots_txt: true,
            validate_schema: true,
            test_browser_connection: testBrowserConnection,
          },
        ),
        SourceApiError,
      );
      const d = response.data;
      return {
        valid: d.valid,
        errors: d.errors ?? [],
        warnings: d.warnings ?? [],
        robotsTxtCheck: d.robots_txt_check ?? null,
        schemaValidation: d.schema_validation ?? null,
        browserTest: d.browser_test ?? null,
      };
    },
    onError: (error) => {
      log.error('Failed to validate target', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/** Bulk execute / pause / archive across multiple targets. */
export function useBatchTargetOperation() {
  const queryClient = useQueryClient();

  return useMutation<
    BatchOperationResponse,
    SourceApiError,
    { operation: BatchOperation; targetIds: string[] }
  >({
    mutationFn: async ({ operation, targetIds }) => {
      const response = await withApiError(
        apiPost<{
          operation: string;
          requested: number;
          succeeded: number;
          failed: number;
          results: Array<{ id: string; status: string; job_id?: string | null; error?: string | null }>;
        }>('l1', '/targets/batch', { operation, target_ids: targetIds }),
        SourceApiError,
      );
      const d = response.data;
      return {
        operation: d.operation as BatchOperation,
        requested: d.requested,
        succeeded: d.succeeded,
        failed: d.failed,
        results: d.results.map(r => ({
          id: r.id,
          status: r.status as BatchOperationResult['status'],
          jobId: r.job_id,
          error: r.error,
        })),
      };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.targets.all });
    },
    onError: (error) => {
      log.error('Failed to execute batch target operation', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}
