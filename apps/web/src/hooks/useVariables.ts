import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { z, type ZodError } from 'zod';
import { apiGet, apiPost } from '@/api/typedClient';
import { createLogger } from '@/lib/telemetry';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from './useApiShared';
import {
  VariableSchema,
  VariableListSchema,
  SourceBindingListSchema,
  VariableStatsSchema,
  type Variable,
  type VariableType,
  type SourceType,
  type ValidationStatus,
  type SourceBinding,
  type VariableStats,
} from '@/lib/schemas/variable';

const log = createLogger('useVariables');

/**
 * Format Zod validation errors into a human-readable string.
 */
function formatZodError(error: ZodError, context: string): string {
  const details = error.issues.map((e: { path: (string | number | symbol)[]; message: string }) => `${String(e.path)}: ${e.message}`).join(', ');
  return `Invalid ${context}: ${details}`;
}

export type { Variable, VariableType, SourceType, ValidationStatus, SourceBinding, VariableStats };

export interface VariableFilters {
  type?: VariableType | 'all';
  source?: SourceType | 'all';
  status?: ValidationStatus | 'all';
  search?: string;
}

export type TestBindingFailureClass =
  | 'missing_source_binding'
  | 'invalid_variable_config'
  | 'connector_unavailable'
  | 'authorization'
  | 'unknown';

export interface TestVariableBindingRequest {
  sample_input?: Record<string, unknown>;
  context?: Record<string, unknown>;
}

export interface TestVariableBindingDiagnostics {
  code: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
  path?: string;
}

export interface TestVariableBindingSourceTrace {
  source: string;
  binding: string;
  resolved_path?: string | null;
  connector_status?: string | null;
}

export interface TestVariableBindingResponse {
  pass: boolean;
  evaluated_value?: unknown;
  failure_class?: TestBindingFailureClass;
  diagnostics: TestVariableBindingDiagnostics[];
  source_trace: TestVariableBindingSourceTrace;
}

const TestVariableBindingResponseSchema = z.object({
  pass: z.boolean(),
  evaluated_value: z.unknown().optional(),
  failure_class: z.enum(['missing_source_binding', 'invalid_variable_config', 'connector_unavailable', 'authorization', 'unknown']).optional(),
  diagnostics: z.array(z.object({
    code: z.string(),
    message: z.string(),
    severity: z.enum(['error', 'warning', 'info']),
    path: z.string().optional(),
  })).default([]),
  source_trace: z.object({
    source: z.string(),
    binding: z.string(),
    resolved_path: z.string().nullable().optional(),
    connector_status: z.string().nullable().optional(),
  }),
});

// Re-export for backward compatibility
export { BaseApiError } from './useApiShared';

async function fetchVariables(filters: VariableFilters): Promise<Variable[]> {
  const params = new URLSearchParams();
  if (filters.type && filters.type !== 'all') params.set('type', filters.type);
  if (filters.source && filters.source !== 'all') params.set('source', filters.source);
  if (filters.status && filters.status !== 'all') params.set('status', filters.status);
  if (filters.search) params.set('search', filters.search);

  const response = await apiGet<unknown>('l3', `/variables?${params.toString()}`);

  // Runtime validation with Zod
  const parsed = VariableListSchema.safeParse(response.data);
  if (!parsed.success) {
    log.error('Variable list validation failed', { error: parsed.error });
    throw new BaseApiError(formatZodError(parsed.error, 'variable list response'));
  }
  return parsed.data;
}

export function useVariables(filters: VariableFilters = {}) {
  return useQuery<Variable[], BaseApiError>({
    queryKey: QK.variables.list(filters),
    queryFn: () => withApiError(fetchVariables(filters), BaseApiError),
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchVariable(variableId: string): Promise<Variable> {
  const response = await apiGet<unknown>('l3', `/variables/${variableId}`);

  // Runtime validation with Zod
  const parsed = VariableSchema.safeParse(response.data);
  if (!parsed.success) {
    log.error('Variable detail validation failed', { error: parsed.error });
    throw new BaseApiError(formatZodError(parsed.error, 'variable response'));
  }
  return parsed.data;
}

export function useVariable(variableId: string | null) {
  return useQuery<Variable, BaseApiError>({
    queryKey: QK.variables.detail(variableId || ''),
    queryFn: async () => {
      if (!variableId) throw new BaseApiError('No variable ID provided');
      return withApiError(fetchVariable(variableId), BaseApiError);
    },
    enabled: !!variableId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchVariableStats(): Promise<VariableStats> {
  const response = await apiGet<unknown>('l3', '/variables/stats');

  // Runtime validation with Zod
  const parsed = VariableStatsSchema.safeParse(response.data);
  if (!parsed.success) {
    log.error('Variable stats validation failed', { error: parsed.error });
    throw new BaseApiError(formatZodError(parsed.error, 'variable stats response'));
  }
  return parsed.data;
}

export function useVariableStats() {
  return useQuery<VariableStats, BaseApiError>({
    queryKey: QK.variables.stats,
    queryFn: () => withApiError(fetchVariableStats(), BaseApiError),
    staleTime: STALE_TIME.stats,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchSourceBindings(): Promise<SourceBinding[]> {
  const response = await apiGet<unknown>('l3', '/variables/bindings');

  // Runtime validation with Zod
  const parsed = SourceBindingListSchema.safeParse(response.data);
  if (!parsed.success) {
    log.error('Source binding list validation failed', { error: parsed.error });
    throw new BaseApiError(formatZodError(parsed.error, 'source binding list response'));
  }
  return parsed.data;
}

export function useSourceBindings() {
  return useQuery<SourceBinding[], BaseApiError>({
    queryKey: QK.variables.bindings,
    queryFn: () => withApiError(fetchSourceBindings(), BaseApiError),
    staleTime: STALE_TIME.bindings,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useValidateVariable() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (variableId: string) => {
      if (!variableId) throw new BaseApiError('Variable ID is required');
      const response = await apiPost<unknown>('l3', `/variables/${variableId}/validate`, {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.variables.all });
    },
    onError: (error) => {
      log.error('ValidateVariable failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

export function useTestVariableBinding() {
  return useMutation<TestVariableBindingResponse, BaseApiError, { variableId: string; payload: TestVariableBindingRequest }>({
    mutationFn: async ({ variableId, payload }) => {
      if (!variableId) throw new BaseApiError('Variable ID is required');
      const response = await apiPost<unknown>('l3', `/variables/${variableId}/test-binding`, payload);
      const parsed = TestVariableBindingResponseSchema.safeParse(response.data);
      if (!parsed.success) {
        log.error('Test variable binding validation failed', { error: parsed.error, variableId });
        throw new BaseApiError(formatZodError(parsed.error, 'test binding response'));
      }
      return parsed.data;
    },
    onError: (error) => {
      log.error('TestVariableBinding failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}
