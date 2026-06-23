/**
 * useSources.ts — Data Source Management Hooks
 *
 * Provides React Query hooks for Layer 1 Ingestion Service /targets API.
 * All hooks use standardized error handling, cache configuration, and
 * normalization of ScrapingTarget API responses to frontend DataSource model.
 *
 * Phase 1 Implementation: Data layer foundation for Source Configuration Page
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut, apiDelete } from '@/api/typedClient';
import type { l1 } from '@/api/generated';
import { createLogger } from '@/lib/telemetry';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';

const log = createLogger('useSources');

// ── Constants ─────────────────────────────────────────────────────────────────

/** Default priority for ingestion jobs (1-10 scale, lower = higher priority) */
const DEFAULT_EXECUTION_PRIORITY = 5;

// ── Types ───────────────────────────────────────────────────────────────────

export type SourceType = 'crm' | 'database' | 'file' | 'api' | 'cloud_storage';
export type ConnectionStatus = 'connected' | 'disconnected' | 'error' | 'testing';
export type SyncFrequency = 'realtime' | 'hourly' | 'daily' | 'weekly' | 'manual';
export type AuthType = 'NONE' | 'BEARER' | 'API_KEY' | 'BASIC' | 'OAUTH2';

export interface FieldMapping {
  sourceField: string;
  targetField: string;
  transformation?: string;
  isRequired: boolean;
}

export interface DataSource {
  id: string;
  name: string;
  description?: string;
  type: SourceType;
  status: ConnectionStatus;
  endpoint: string;
  urlPattern?: string;
  lastSyncAt?: string;
  nextSyncAt?: string;
  syncFrequency: SyncFrequency;
  recordCount?: number;
  healthScore: number;
  errorMessage?: string;
  fieldMappings: FieldMapping[];
  // Configuration (for editing)
  extractionConfig: Record<string, unknown>;
  browserConfig: Record<string, unknown>;
  schedule: {
    enabled?: boolean;
    cronExpression?: string;
    timezone?: string;
  } | null;
  rateLimit: Record<string, unknown>;
  compliance: Record<string, unknown>;
  proxyConfig: Record<string, unknown>;
  authentication: {
    type?: AuthType;
    credentialsRef?: string;
  } | null;
  // Metadata
  tenantId: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  successCount: number;
  errorCount: number;
  averageExecutionTimeMs: number;
  tags: string[];
}

export interface SourceFilters {
  search?: string;
  type?: SourceType;
  status?: ConnectionStatus;
  page?: number;
  limit?: number;
  sortBy?: 'created_at' | 'updated_at' | 'last_success_at' | 'name';
  sortOrder?: 'asc' | 'desc';
}

export interface CreateSourceRequest {
  name: string;
  url: string;
  targetType: SourceType;
  description?: string;
  extractionConfig?: Record<string, unknown>;
  browserConfig?: Record<string, unknown>;
  schedule?: DataSource['schedule'];
  rateLimit?: Record<string, unknown>;
  compliance?: Record<string, unknown>;
  proxyConfig?: Record<string, unknown>;
  authentication?: DataSource['authentication'];
  tags?: string[];
  sourceCategory?: SourceType;
}

export interface UpdateSourceRequest extends Partial<CreateSourceRequest> {
  id: string;
}

export interface SourceListResponse {
  sources: DataSource[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

type ApiTargetStatsResponse = l1.components['schemas']['TargetStatsResponse'];

export interface TestConnectionResult {
  success: boolean;
  message: string;
  details?: Record<string, unknown>;
  latencyMs?: number;
}

// ── Payload Builder ──────────────────────────────────────────────────────────

/** Backend target_type values understood by the L1 scraping API */
type BackendTargetType = 'SINGLE_PAGE' | 'PAGINATED' | 'SPIDER' | 'API_ENDPOINT';

/**
 * Map frontend SourceType (WHAT the source is) to backend target_type (HOW to scrape).
 *
 * Frontend SourceType: 'crm' | 'database' | 'file' | 'api' | 'cloud_storage'
 * Backend target_type: 'SINGLE_PAGE' | 'PAGINATED' | 'SPIDER' | 'API_ENDPOINT'
 *
 * These are different axes. The backend now exposes source_category for the
 * semantic category; target_type remains for the scraping method.
 */
const FRONTEND_TO_BACKEND_TARGET_TYPE: Record<SourceType, BackendTargetType> = {
  crm:           'API_ENDPOINT',    // CRM platforms expose REST/SOAP APIs
  database:      'API_ENDPOINT',    // Databases accessed via query adapter API
  file:          'SINGLE_PAGE',     // Direct file downloads (CSV, JSON, etc.)
  api:           'API_ENDPOINT',    // Generic REST/GraphQL endpoints
  cloud_storage: 'API_ENDPOINT',    // S3/GCS/Azure Blob accessed via SDK API
};

/**
 * Build API payload from CreateSourceRequest.
 * Centralizes snake_case conversion and field mapping.
 */
function buildTargetPayload(request: CreateSourceRequest): Record<string, unknown> {
  const backendTargetType = FRONTEND_TO_BACKEND_TARGET_TYPE[request.targetType] ?? 'API_ENDPOINT';

  return {
    name: request.name,
    url: request.url,
    target_type: backendTargetType,
    source_category: request.sourceCategory ?? request.targetType,
    description: request.description,
    extraction_config: request.extractionConfig,
    browser_config: request.browserConfig,
    schedule: request.schedule,
    rate_limit: request.rateLimit,
    compliance: request.compliance,
    proxy_config: request.proxyConfig,
    authentication: request.authentication,
    tags: request.tags,
  };
}

// ── API Response Types (Layer 1) ────────────────────────────────────────────

type ApiScrapingTargetDetail = l1.components['schemas']['ScrapingTargetDetail'];

interface ApiTargetListResponse {
  data: ApiScrapingTargetDetail[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
  };
}

interface ApiValidateTargetResponse {
  valid: boolean;
  message: string;
  details?: Record<string, unknown>;
  latency_ms?: number;
}

// ── Normalization ───────────────────────────────────────────────────────────

/**
 * Map backend source_category to frontend SourceType.
 *
 * Backend source_category (crm, database, file, api, cloud_storage) describes
 * WHAT the source is, aligned with frontend SourceType.
 *
 * Falls back to mapping from target_type for legacy targets without
 * source_category populated.
 */
function mapTargetType(sourceCategory: string | null | undefined, targetType: string, tags: string[] = [], url: string = ''): SourceType {
  // Prefer explicit source_category when available
  if (sourceCategory) {
    const normalized = sourceCategory.toLowerCase();
    if (['crm', 'database', 'file', 'api', 'cloud_storage'].includes(normalized)) {
      return normalized as SourceType;
    }
  }

  // Legacy fallback: infer from tags/URL for targets without source_category
  const tagMap: Record<string, SourceType> = {
    'crm': 'crm',
    'salesforce': 'crm',
    'hubspot': 'crm',
    'database': 'database',
    'postgres': 'database',
    'mysql': 'database',
    's3': 'cloud_storage',
    'gcs': 'cloud_storage',
    'azure': 'cloud_storage',
    'file': 'file',
    'csv': 'file',
    'json': 'file',
  };

  for (const tag of tags) {
    const lowerTag = tag.toLowerCase();
    if (tagMap[lowerTag]) return tagMap[lowerTag];
  }

  // Infer from URL patterns
  const lowerUrl = url.toLowerCase();
  if (lowerUrl.includes('salesforce') || lowerUrl.includes('hubapi')) return 'crm';
  if (lowerUrl.includes('postgres') || lowerUrl.includes('mysql') || lowerUrl.includes('://db')) {
    return 'database';
  }
  if (lowerUrl.includes('s3.') || lowerUrl.includes('blob.core.windows.net')) return 'cloud_storage';

  // Default to API for all backend target types (SINGLE_PAGE, PAGINATED, SPIDER, API_ENDPOINT)
  return 'api';
}

/**
 * Derive connection status from target state
 */
function deriveConnectionStatus(
  targetStatus: string,
  lastSuccessAt: string | null,
  lastErrorAt: string | null,
  errorCount: number
): ConnectionStatus {
  if (targetStatus === 'ERROR') return 'error';
  if (targetStatus === 'PAUSED') return 'disconnected';
  if (errorCount > 0 && lastErrorAt && (!lastSuccessAt || lastErrorAt > lastSuccessAt)) {
    return 'error';
  }
  if (lastSuccessAt) return 'connected';
  return 'disconnected';
}

/**
 * Derive sync frequency from schedule config
 */
function deriveSyncFrequency(schedule: ApiScrapingTargetDetail['schedule']): SyncFrequency {
  if (!schedule || typeof schedule !== 'object') return 'manual';
  if (schedule.enabled !== true) return 'manual';
  const cron = typeof schedule.cron_expression === 'string' ? schedule.cron_expression : '';
  if (cron.includes('*/5') || cron.includes('*/1')) return 'realtime';
  if (cron.includes('0 *')) return 'hourly';
  if (cron.includes('0 0')) return 'daily';
  if (cron.includes('0 0 * * 0')) return 'weekly';
  return 'manual';
}

/**
 * Calculate health score from success/error counts
 */
function calculateHealthScore(successCount: number, errorCount: number): number {
  const total = successCount + errorCount;
  if (total === 0) return 0;
  return Math.round((successCount / total) * 100);
}

/**
 * Extract field mappings from extraction config
 */
function extractFieldMappings(extractionConfig: Record<string, unknown> | null | undefined): FieldMapping[] {
  if (!extractionConfig || typeof extractionConfig !== 'object') return [];

  const mappings = extractionConfig.field_mappings as Array<{
    source: string;
    target: string;
    required?: boolean;
    transformation?: string;
  }> | undefined;

  if (!Array.isArray(mappings)) return [];

  return mappings.map(m => ({
    sourceField: m.source,
    targetField: m.target,
    transformation: m.transformation,
    isRequired: m.required ?? false,
  }));
}

/**
 * Normalize API ScrapingTarget to frontend DataSource model.
 *
 * @param api - Raw API response from Layer 1 /targets endpoint
 * @returns Normalized DataSource for frontend consumption
 */
function normalizeDataSource(api: ApiScrapingTargetDetail): DataSource {
  const status = deriveConnectionStatus(
    api.status,
    api.last_success_at ?? null,
    api.last_error_at,
    api.error_count
  );

  return {
    id: api.id,
    name: api.name,
    description: api.description ?? undefined,
    type: mapTargetType(api.source_category, api.target_type, api.tags, api.url),
    status,
    endpoint: api.url,
    urlPattern: api.url_pattern ?? undefined,
    lastSyncAt: api.last_success_at ?? undefined,
    syncFrequency: deriveSyncFrequency(api.schedule),
    healthScore: calculateHealthScore(api.success_count, api.error_count),
    errorMessage: status === 'error' && api.last_error_at
      ? `Last error at ${new Date(api.last_error_at).toLocaleString()}`
      : undefined,
    fieldMappings: extractFieldMappings(api.extraction_config),
    extractionConfig: api.extraction_config,
    browserConfig: api.browser_config,
    schedule: api.schedule,
    rateLimit: api.rate_limit,
    compliance: api.compliance,
    proxyConfig: api.proxy_config,
    authentication: api.authentication
      ? {
          type: typeof api.authentication.type === 'string' ? (api.authentication.type as AuthType) : undefined,
          credentialsRef: typeof api.authentication.credentials_ref === 'string' ? api.authentication.credentials_ref : undefined,
        }
      : null,
    tenantId: api.tenant_id,
    createdBy: api.created_by,
    createdAt: api.created_at,
    updatedAt: api.updated_at,
    successCount: api.success_count,
    errorCount: api.error_count,
    averageExecutionTimeMs: api.average_execution_time_ms,
    tags: api.tags,
  };
}

// ── Query Hooks ──────────────────────────────────────────────────────────────

/**
 * List data sources with optional filtering and pagination
 */
export function useSources(filters: SourceFilters = {}) {
  const {
    search,
    type,
    status,
    page = 1,
    limit = 20,
    sortBy = 'created_at',
    sortOrder = 'desc',
  } = filters;

  return useQuery<SourceListResponse, BaseApiError>({
    queryKey: QK.sources.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('limit', String(limit));
      params.set('sort_by', sortBy);
      params.set('sort_order', sortOrder);
      if (search) params.set('search', search);
      if (type) params.set('source_category', type);

      const response = await withApiError(
        apiGet<ApiTargetListResponse>('l1', `/targets?${params.toString()}`),
        BaseApiError
      );

      const data = response.data;

      return {
        sources: data.data.map(normalizeDataSource),
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

/**
 * Get detailed information about a specific data source
 */
export function useSource(id: string | null) {
  return useQuery<DataSource, BaseApiError>({
    queryKey: id ? QK.sources.detail(id) : ['sources', 'detail', 'null'],
    queryFn: async () => {
      if (!id) throw new BaseApiError('Source ID is required');
      const response = await withApiError(
        apiGet<ApiScrapingTargetDetail>('l1', `/targets/${id}`),
        BaseApiError
      );
      return normalizeDataSource(response.data);
    },
    enabled: !!id,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
  });
}

/**
 * Get aggregated statistics for all sources.
 *
 * Uses the dedicated /targets/stats endpoint for efficient server-side
 * aggregation instead of fetching all sources client-side.
 */
export function useSourceStats() {
  return useQuery<ApiTargetStatsResponse, BaseApiError>({
    queryKey: QK.sources.stats,
    queryFn: async () => {
      const response = await withApiError(
        apiGet<ApiTargetStatsResponse>('l1', '/targets/stats'),
        BaseApiError
      );
      return response.data;
    },
    staleTime: STALE_TIME.stats,
    retry: RETRY_CONFIG.maxRetries,
  });
}

// ── Mutation Hooks ───────────────────────────────────────────────────────────

/**
 * Create a new data source
 */
export function useCreateSource() {
  const queryClient = useQueryClient();

  return useMutation<DataSource, BaseApiError, CreateSourceRequest>({
    mutationFn: async (request) => {
      const payload = buildTargetPayload(request);

      const response = await withApiError(
        apiPost<ApiScrapingTargetDetail>('l1', '/targets', payload),
        BaseApiError
      );

      return normalizeDataSource(response.data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.sources.all });
    },
    onError: (error) => {
      log.error('Failed to create source', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/**
 * Update an existing data source
 */
export function useUpdateSource() {
  const queryClient = useQueryClient();

  return useMutation<DataSource, BaseApiError, UpdateSourceRequest>({
    mutationFn: async (request) => {
      const { id, ...updates } = request;

      // Build partial payload for PATCH-like update
      const payload: Record<string, unknown> = {};
      const addIfDefined = (key: string, value: unknown) => {
        if (value !== undefined) payload[key] = value;
      };

      addIfDefined('name', updates.name);
      addIfDefined('url', updates.url);
      addIfDefined('target_type', updates.targetType ? FRONTEND_TO_BACKEND_TARGET_TYPE[updates.targetType] : undefined);
      addIfDefined('source_category', updates.sourceCategory ?? updates.targetType);
      addIfDefined('description', updates.description);
      addIfDefined('extraction_config', updates.extractionConfig);
      addIfDefined('browser_config', updates.browserConfig);
      addIfDefined('schedule', updates.schedule);
      addIfDefined('rate_limit', updates.rateLimit);
      addIfDefined('compliance', updates.compliance);
      addIfDefined('proxy_config', updates.proxyConfig);
      addIfDefined('authentication', updates.authentication);
      addIfDefined('tags', updates.tags);

      const response = await withApiError(
        apiPut<ApiScrapingTargetDetail>('l1', `/targets/${id}`, payload),
        BaseApiError
      );

      return normalizeDataSource(response.data);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QK.sources.all });
      queryClient.invalidateQueries({ queryKey: QK.sources.detail(data.id) });
    },
    onError: (error) => {
      log.error('Failed to update source', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/**
 * Delete a data source
 */
export function useDeleteSource() {
  const queryClient = useQueryClient();

  return useMutation<unknown, BaseApiError, string>({
    mutationFn: async (id) => {
      return withApiError(
        apiDelete<unknown>('l1', `/targets/${id}`),
        BaseApiError
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.sources.all });
    },
    onError: (error) => {
      log.error('Failed to delete source', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/**
 * Test connection to a data source
 */
export function useTestConnection() {
  return useMutation<TestConnectionResult, BaseApiError, { id: string; config?: Record<string, unknown> }>({
    mutationFn: async ({ id, config }) => {
      const response = await withApiError(
        apiPost<ApiValidateTargetResponse>('l1', `/targets/${id}/validate`, config ? { config } : {}),
        BaseApiError
      );

      const data = response.data;

      return {
        success: data.valid,
        message: data.message,
        details: data.details,
        latencyMs: data.latency_ms,
      };
    },
    onError: (error) => {
      log.error('Connection test failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

/**
 * Execute/run a data source (trigger ingestion job)
 */
export function useExecuteSource() {
  const queryClient = useQueryClient();

  return useMutation<{ jobId: string }, BaseApiError, { id: string; priority?: number }>({
    mutationFn: async ({ id, priority = DEFAULT_EXECUTION_PRIORITY }) => {
      const response = await withApiError(
        apiPost<l1.components['schemas']['ExecuteTargetResponse']>('l1', `/targets/${id}/execute`, { priority }),
        BaseApiError
      );

      return { jobId: response.data.job_id };
    },
    onSuccess: () => {
      // Invalidate both sources and ingestion jobs
      queryClient.invalidateQueries({ queryKey: QK.sources.all });
      queryClient.invalidateQueries({ queryKey: QK.ingestion.all });
    },
    onError: (error) => {
      log.error('Failed to execute source', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}
