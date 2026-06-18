import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '@/api/typedClient';
import type { l4 } from '@/api/generated';
import { QK } from './queryKeys';
import { STALE_TIME, BaseApiError, withApiError } from './useApiShared';
import { formatCompactCurrency } from '@/lib/formatters';
import {
  parseBusinessCaseNarrativeOutput,
  parseBusinessCaseRoiOutput,
  parseWorkflowResult,
  type ApiWorkflowStepDto,
} from '@/types/api';
import { createFeatureLogger } from '@/lib/telemetry';

const log = createFeatureLogger('useBusinessCases');

export interface UseCase {
  name: string;
  persona: string;
  driver: string;
  roi: string;
  payback: string;
  confidence: number;
}

export interface BusinessCaseData {
  id: string;
  company: string;
  totalValue: string;
  useCases: UseCase[];
  avgPayback: string;
  confidence: number;
  executiveSummary: string;
  generatedAt: string;
}

export interface BusinessCaseListItem {
  id: string;
  name: string;
  company: string;
  status: 'draft' | 'active' | 'approved' | 'archived';
  totalValue: string;
  useCaseCount: number;
  confidence: number;
  createdAt: string;
  updatedAt: string;
  owner: string;
}

export interface BusinessCaseFilters {
  status?: 'draft' | 'active' | 'approved' | 'archived' | 'all';
  search?: string;
  company?: string;
}

export interface CreateBusinessCasePayload {
  name: string;
  company: string;
  description?: string;
}

export interface CreateBusinessCaseResponse {
  workflow_id: string;
  name: string;
  status: string;
  created_at: string;
}

/**
 * Get business case from L4 agent workflow results
 * Note: This queries the L4 workflow results for business_case type workflows
 */
export function useBusinessCase(caseId: string | null) {
  return useQuery({
    queryKey: QK.businessCases.detail(caseId || ''),
    queryFn: async () => {
      if (!caseId) throw new Error('No case ID provided');

      // Query L4 for workflow result
      const response = await apiGet<unknown>('l4', `/workflows/${caseId}/result`);
      const result = parseWorkflowResult(response.data);

      // Parse workflow output into business case format
      const output = result.output || {};
      const steps: ApiWorkflowStepDto[] = result.steps || [];

      // Extract data from workflow steps
      const findAgentStep = (agentName: string): ApiWorkflowStepDto | undefined =>
        steps.find((step) => step.agent === agentName);
      const roiResult = parseBusinessCaseRoiOutput(findAgentStep('ROICalculationAgent')?.result?.output);
      const narrativeResult = parseBusinessCaseNarrativeOutput(findAgentStep('NarrativeSynthesisAgent')?.result?.output);

      // Map use cases
      const useCases: UseCase[] = (roiResult.use_cases || []).map((uc) => ({
        name: uc.name || 'Unknown Use Case',
        persona: uc.persona || 'Unknown',
        driver: uc.value_driver || 'Unknown',
        roi: formatCompactCurrency(uc.roi_value ?? 0),
        payback: `${uc.payback_months ?? 12} mo`,
        confidence: Math.round((uc.confidence ?? 0.8) * 100),
      }));

      // Calculate totals
      const totalValue = roiResult.total_value ?? 0;
      const avgPayback = roiResult.avg_payback_months ?? 12;
      const confidence = Math.round((roiResult.confidence ?? 0.85) * 100);

      return {
        id: caseId,
        company: output.company_name || 'Acme Corp',
        totalValue: formatCompactCurrency(totalValue),
        useCases,
        avgPayback: `${avgPayback} months`,
        confidence,
        executiveSummary: narrativeResult.executive_summary || generateSummary(useCases, totalValue),
        generatedAt: result.completed_at || new Date().toISOString(),
      };
    },
    enabled: !!caseId,
    staleTime: STALE_TIME.stats,
  });
}

function generateSummary(useCases: UseCase[], totalValue: number): string {
  if (useCases.length === 0) {
    return 'No use cases available for analysis.';
  }

  const topCase = useCases[0];
  return `${topCase.name} presents the most significant opportunity with an estimated ${topCase.roi} in value. Combined with other identified use cases, the total addressable value is estimated at ${formatCompactCurrency(totalValue)} annually with an average payback period of ${useCases.length > 1 ? 'several months' : '6-9 months'}.`;
}

async function fetchBusinessCases(filters: BusinessCaseFilters): Promise<BusinessCaseListItem[]> {
  const params = new URLSearchParams();
  if (filters.status && filters.status !== 'all') params.set('status', filters.status);
  if (filters.search) params.set('search', filters.search);
  if (filters.company) params.set('company', filters.company);
  params.set('include_completed', 'true');

  // Query L4 for business case workflows
  const response = await apiGet<Record<string, unknown>>('l4', `/workflows?type=business_case&${params.toString()}`);

  // Transform workflow data to BusinessCaseListItem format
  interface WorkflowItem {
    id?: string;
    workflow_id: string;
    name?: string;
    status?: string;
    lifecycle_status?: string;
    case_metadata?: Record<string, unknown>;
    company_name?: string;
    total_value?: number;
    use_case_count?: number;
    confidence?: number;
    created_at?: string;
    updated_at?: string;
    owner?: string;
  }
  const rawData = response.data;
  const items = (Array.isArray(rawData.items) ? rawData.items as WorkflowItem[] : []).map((workflow) => {
    const workflowId = String(workflow.workflow_id ?? workflow.id ?? '');
    const statusSource = String(workflow.lifecycle_status ?? workflow.case_metadata?.lifecycle_status ?? workflow.status ?? 'draft').toLowerCase();
    const status = (
      statusSource === 'approved' || statusSource === 'completed'
        ? 'approved'
        : statusSource === 'archived'
          ? 'archived'
          : statusSource === 'active'
            ? 'active'
            : 'draft'
    ) as BusinessCaseListItem['status'];

    return {
      id: workflowId,
      name: workflow.name || `Case ${workflowId}`,
      company: workflow.company_name || String(workflow.case_metadata?.account_name ?? 'Unknown Company'),
      status,
      totalValue: formatCompactCurrency(workflow.total_value ?? Number(workflow.case_metadata?.total_value ?? 0)),
      useCaseCount: workflow.use_case_count ?? Number(workflow.case_metadata?.use_case_count ?? 0),
      confidence: Math.round((workflow.confidence ?? Number(workflow.case_metadata?.confidence ?? 0.8)) * 100),
      createdAt: workflow.created_at || new Date().toISOString(),
      updatedAt: workflow.updated_at || workflow.created_at || new Date().toISOString(),
      owner: workflow.owner || 'System',
    };
  });

  return items;
}

/**
 * Fetch list of business cases with filtering support
 * 
 * @param filters - Optional filters for status, search, company
 * @returns Query result with business case list
 * 
 * @example
 * ```tsx
 * const { data: cases, isLoading } = useBusinessCases({ status: 'active' });
 * ```
 */
export function useBusinessCases(filters: BusinessCaseFilters = {}) {
  return useQuery<BusinessCaseListItem[], BaseApiError>({
    queryKey: QK.businessCases.list(filters),
    queryFn: () => withApiError(fetchBusinessCases(filters), BaseApiError),
    staleTime: STALE_TIME.list,
  });
}

/**
 * Create a new business case
 *
 * @example
 * ```tsx
 * const createCase = useCreateBusinessCase();
 * createCase.mutate({ name: 'Q2 Expansion', company: 'Acme Corp' });
 * ```
 */
export function useCreateBusinessCase() {
  const queryClient = useQueryClient();

  return useMutation<CreateBusinessCaseResponse, BaseApiError, CreateBusinessCasePayload>({
    mutationFn: async (payload) => {
      const response = await apiPost<Record<string, unknown>>('l4', '/workflows', {
        workflow_type: 'business_case',
        inputs: {
          prospect_company: payload.company,
          custom_data: {
            name: payload.name,
            description: payload.description,
          },
        },
      });
      const data = response.data;
      return {
        workflow_id: String(data.workflow_id ?? data.workflow_instance_id ?? ''),
        name: String(data.name ?? payload.name),
        status: String(data.status ?? ''),
        created_at: String(data.created_at ?? new Date().toISOString()),
      };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-cases'] });
    },
    onError: (error) => {
      log.error('Failed to create business case', { errorCode: error.message });
    },
  });
}

/**
 * Archive a business case
 *
 * @example
 * ```tsx
 * const archiveCase = useArchiveBusinessCase();
 * archiveCase.mutate('case-id-123');
 * ```
 */
export function useArchiveBusinessCase() {
  const queryClient = useQueryClient();

  return useMutation<unknown, BaseApiError, string>({
    mutationFn: async (caseId) => {
      const response = await apiPost<l4.components['schemas']['ArchiveWorkflowResponse']>('l4', `/workflows/${caseId}/archive`, {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-cases'] });
    },
    onError: (error) => {
      log.error('Failed to archive business case', { errorCode: error.message });
    },
  });
}
