import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPatch, apiDelete } from '@/api/typedClient';
import { createLogger } from '@/lib/telemetry';
import { QK } from './queryKeys';
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG, formatZodError } from './useApiShared';
import {
  FormulaSchema,
  FormulaListSchema,
  ApprovalRequestListSchema,
  FormulaEvaluationResultSchema,
  type Formula,
  type FormulaStatus,
  type ApprovalRequest,
  type FormulaEvaluationResult,
} from '@/lib/schemas/formula';

const log = createLogger('useFormulas');

export type { Formula, FormulaStatus, ApprovalRequest, FormulaEvaluationResult };

/** Parameters for formula approval action */
export interface ApproveFormulaParams {
  formulaId: string;
  action: 'approve' | 'reject' | 'request_changes';
  reason?: string;
}


export interface FormulaFilters {
  status?: FormulaStatus | 'all';
  search?: string;
  pack_id?: string;
}

// Re-export for backward compatibility
export { BaseApiError } from './useApiShared';

async function fetchFormulas(filters: FormulaFilters): Promise<Formula[]> {
  const params = new URLSearchParams();
  if (filters.status && filters.status !== 'all') params.set('status', filters.status);
  if (filters.search) params.set('search', filters.search);
  if (filters.pack_id) params.set('pack_id', filters.pack_id);

  const response = await apiGet<Record<string, unknown>>('l3', `/formulas?${params.toString()}`);

  // Backend returns { formulas: [...], total: number }
  const raw = response.data;
  const formulasArray = Array.isArray(raw) ? raw : (Array.isArray(raw.formulas) ? raw.formulas : []);
  
  // Runtime validation with Zod
  const parsed = FormulaListSchema.safeParse(formulasArray);
  if (!parsed.success) {
    log.error('Formula list validation failed', { error: parsed.error });
    throw new BaseApiError(formatZodError(parsed.error, 'formula list response'));
  }
  return parsed.data;
}

/**
 * Hook to fetch a list of formulas with filtering support.
 *
 * @param filters - Optional filters for status, search query, or pack ID
 * @returns Query result with Formula array and loading/error states
 */
export function useFormulas(filters: FormulaFilters = {}) {
  return useQuery<Formula[], BaseApiError>({
    queryKey: QK.formulas.list(filters),
    queryFn: () => withApiError(fetchFormulas(filters), BaseApiError),
    staleTime: STALE_TIME.list,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchFormula(formulaId: string): Promise<Formula> {
  const response = await apiGet<unknown>('l3', `/formulas/${formulaId}`);
  
  // Runtime validation with Zod
  const parsed = FormulaSchema.safeParse(response.data);
  if (!parsed.success) {
    log.error('Formula detail validation failed', { error: parsed.error });
    throw new BaseApiError(formatZodError(parsed.error, 'formula response'));
  }
  return parsed.data;
}

/**
 * Hook to fetch a single formula by ID.
 *
 * @param formulaId - The formula ID to fetch, or null to disable the query
 * @returns Query result with Formula data and loading/error states
 */
export function useFormula(formulaId: string | null) {
  return useQuery<Formula, BaseApiError>({
    queryKey: QK.formulas.detail(formulaId || ''),
    queryFn: async () => {
      if (!formulaId) throw new BaseApiError('No formula ID provided');
      return withApiError(fetchFormula(formulaId), BaseApiError);
    },
    enabled: !!formulaId,
    staleTime: STALE_TIME.detail,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

async function fetchFormulaApprovals(): Promise<ApprovalRequest[]> {
  const response = await apiGet<unknown>('l3', '/formulas/approvals/pending');
  
  // Runtime validation with Zod
  const parsed = ApprovalRequestListSchema.safeParse(response.data);
  if (!parsed.success) {
    log.error('Formula approvals validation failed', { error: parsed.error });
    throw new BaseApiError(formatZodError(parsed.error, 'formula approvals response'));
  }
  return parsed.data;
}

/**
 * Hook to fetch pending formula approval requests.
 *
 * @returns Query result with approval requests array
 */
export function useFormulaApprovals() {
  return useQuery<ApprovalRequest[], BaseApiError>({
    queryKey: QK.formulas.approvals,
    queryFn: () => withApiError(fetchFormulaApprovals(), BaseApiError),
    staleTime: STALE_TIME.approvals,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

/**
 * Hook to approve, reject, or request changes on a formula.
 *
 * @returns Mutation result with execute function and loading/error states
 */
export function useApproveFormula() {
  const queryClient = useQueryClient();

  return useMutation<unknown, BaseApiError, ApproveFormulaParams>({
    mutationFn: async ({ formulaId, action, reason }) => {
      const response = await apiPost<unknown>('l3', `/formulas/${formulaId}/approve`, {
        action,
        reason,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.formulas.list({}) });
    },
    onError: (error) => {
      log.error('Formula approval failed', { error: error.message });
    },
  });
}

/**
 * Hook to submit a formula for approval.
 *
 * @returns Mutation result with execute function and loading/error states
 */
export function useSubmitFormula() {
  const queryClient = useQueryClient();

  return useMutation<unknown, BaseApiError, string>({
    mutationFn: async (formulaId) => {
      const response = await apiPost<unknown>('l3', `/formulas/${formulaId}/submit`, {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.formulas.list({}) });
    },
    onError: (error) => {
      log.error('Formula submission failed', { error: error.message });
    },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Formula CRUD Operations
// ─────────────────────────────────────────────────────────────────────────────

export interface CreateFormulaInput {
  name: string;
  description?: string;
  expression: string;
  variables: string[];
  pack_id?: string;
}

/**
 * Hook to create a new formula.
 *
 * @returns Mutation result with execute function and loading/error states
 */
export function useCreateFormula() {
  const queryClient = useQueryClient();

  return useMutation<Formula, BaseApiError, CreateFormulaInput, { previousFormulas?: Formula[] }>({
    mutationFn: async (input) => {
      const response = await apiPost<unknown>('l3', '/formulas', input);
      const parsed = FormulaSchema.safeParse(response.data);
      if (!parsed.success) {
        log.error('Formula creation validation failed', { error: parsed.error });
        throw new BaseApiError(formatZodError(parsed.error, 'formula creation response'));
      }
      return parsed.data;
    },
    onMutate: async (newFormula) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: QK.formulas.list({}) });
      
      // Snapshot previous value
      const previousFormulas = queryClient.getQueryData<Formula[]>(QK.formulas.list({}));
      
      // Optimistically add new formula to list with required fields
      // Note: Using a temporary ID that will be replaced by server response
      const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
      const optimisticFormula: Formula = {
        id: tempId,
        formula_id: tempId,
        name: newFormula.name,
        description: newFormula.description,
        expression: newFormula.expression,
        variables: newFormula.variables,
        status: 'draft' as FormulaStatus,
        version: '1.0.0',
        used_in_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        formula_type: 'simple',
        domain: 'general',
      };
      
      queryClient.setQueryData<Formula[]>(QK.formulas.list({}), (old) => {
        return [...(old || []), optimisticFormula];
      });
      
      return { previousFormulas };
    },
    onError: (error, variables, context) => {
      // Rollback to previous value
      if (context?.previousFormulas) {
        queryClient.setQueryData(QK.formulas.list({}), context.previousFormulas);
      }
      log.error('Formula creation failed', { error: error.message });
    },
    onSuccess: (data) => {
      // Invalidate to get fresh data from server
      queryClient.invalidateQueries({ queryKey: QK.formulas.list({}) });
    },
  });
}

export interface UpdateFormulaInput {
  formulaId: string;
  name?: string;
  description?: string;
  expression?: string;
  variables?: string[];
  pack_id?: string;
}

/**
 * Hook to update an existing formula.
 *
 * @returns Mutation result with execute function and loading/error states
 */
export function useUpdateFormula() {
  const queryClient = useQueryClient();

  return useMutation<Formula, BaseApiError, UpdateFormulaInput, { previousFormula?: Formula; previousFormulas?: Formula[] }>({
    mutationFn: async ({ formulaId, ...updates }) => {
      const response = await apiPatch<unknown>('l3', `/formulas/${formulaId}`, updates);
      const parsed = FormulaSchema.safeParse(response.data);
      if (!parsed.success) {
        log.error('Formula update validation failed', { error: parsed.error });
        throw new BaseApiError(formatZodError(parsed.error, 'formula update response'));
      }
      return parsed.data;
    },
    onMutate: async ({ formulaId, ...updates }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: QK.formulas.detail(formulaId) });
      await queryClient.cancelQueries({ queryKey: QK.formulas.list({}) });
      
      // Snapshot previous values
      const previousFormula = queryClient.getQueryData<Formula>(QK.formulas.detail(formulaId));
      const previousFormulas = queryClient.getQueryData<Formula[]>(QK.formulas.list({}));
      
      // Optimistically update formula detail
      queryClient.setQueryData<Formula>(QK.formulas.detail(formulaId), (old) => {
        if (!old) return old;
        return { ...old, ...updates, updated_at: new Date().toISOString() };
      });
      
      // Optimistically update formula in list
      // Compatibility window: accept formula_id until alias removal date, but prefer canonical id
      queryClient.setQueryData<Formula[]>(QK.formulas.list({}), (old) => {
        return (old || []).map(f => 
          f.id === formulaId || f.formula_id === formulaId 
            ? { ...f, ...updates, updated_at: new Date().toISOString() }
            : f
        );
      });
      
      return { previousFormula, previousFormulas };
    },
    onError: (error, { formulaId }, context) => {
      // Rollback to previous values
      if (context?.previousFormula) {
        queryClient.setQueryData(QK.formulas.detail(formulaId), context.previousFormula);
      }
      if (context?.previousFormulas) {
        queryClient.setQueryData(QK.formulas.list({}), context.previousFormulas);
      }
      log.error('Formula update failed', { error: error.message });
    },
    onSuccess: (data, { formulaId }) => {
      // Invalidate to get fresh data from server
      queryClient.invalidateQueries({ queryKey: QK.formulas.list({}) });
      queryClient.invalidateQueries({ queryKey: QK.formulas.detail(formulaId) });
    },
  });
}

/**
 * Hook to delete/archive a formula.
 *
 * @returns Mutation result with execute function and loading/error states
 */
export function useDeleteFormula() {
  const queryClient = useQueryClient();

  return useMutation<unknown, BaseApiError, string>({
    mutationFn: async (formulaId) => {
      const response = await apiDelete<unknown>('l3', `/formulas/${formulaId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.formulas.list({}) });
    },
    onError: (error) => {
      log.error('Formula deletion failed', { error: error.message });
    },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Formula Evaluation
// ─────────────────────────────────────────────────────────────────────────────

export interface FormulaEvaluationInput {
  formulaId?: string;
  expression?: string;
  inputs: Array<{ name: string; value: number; unit?: string }>;
  output_unit?: string;
}

/**
 * Hook to evaluate a formula with test inputs.
 *
 * @returns Mutation result with execute function and loading/error states
 */
export function useEvaluateFormula() {
  return useMutation<FormulaEvaluationResult, BaseApiError, FormulaEvaluationInput>({
    mutationFn: async (input) => {
      const response = await apiPost<unknown>('l3', '/formulas/evaluate', input);
      
      // Runtime validation with Zod
      const parsed = FormulaEvaluationResultSchema.safeParse(response.data);
      if (!parsed.success) {
        log.error('Formula evaluation validation failed', { error: parsed.error });
        throw new BaseApiError(formatZodError(parsed.error, 'formula evaluation response'));
      }
      return parsed.data;
    },
    onError: (error) => {
      log.error('Formula evaluation failed', { error: error.message });
    },
  });
}
