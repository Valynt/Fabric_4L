/**
 * Formula Scenario React Query Hooks
 *
 * Server state management for what-if scenario analysis:
 * - useFormulaScenario: Calculate a what-if scenario against a base case
 *
 * Connected to Layer 3 formula scenario API:
 *   POST /v1/formulas/scenario
 *
 * OpenAPI contract: ScenarioRequest → ScenarioResponse
 */
import { useMutation } from '@tanstack/react-query';
import { apiPost } from '@/api/typedClient';
import type { l3 } from '@/api/generated';
import { BaseApiError } from './useApiShared';
import { createFeatureLogger } from '@/lib/telemetry';

const log = createFeatureLogger('useFormulaScenario');

// ── Types (aligned to L3 OpenAPI ScenarioRequest / ScenarioResponse) ────────

export interface VariableAdjustment {
  /** Variable name to adjust */
  name: string;
  /** New value for the variable */
  value: number;
  /** Original/base value for delta calculation */
  original_value: number;
}

export interface ScenarioRequest {
  /** Reference business case ID */
  base_case_id: string;
  /** Variable adjustments to apply */
  adjustments: VariableAdjustment[];
}

export interface ScenarioResponse {
  /** Generated scenario identifier */
  scenario_id: string;
  /** Original total value from base case */
  original_value: number;
  /** New total value after adjustments */
  adjusted_value: number;
  /** Percentage change from original */
  delta_percentage: number;
  /** Recalculated ROI ratio */
  new_roi: number;
  /** Recalculated payback period in months */
  new_payback_months: number;
  /** Formula expression used for calculations */
  formula_used: string;
  /** Step-by-step breakdown */
  calculation_steps?: Array<Record<string, unknown>>;
  /** Warning messages (e.g., mock data usage) */
  warnings?: string[];
}

// ── Hook ────────────────────────────────────────────────────────────────────

/**
 * Calculate a what-if scenario by adjusting variables against a base case.
 *
 * @returns Mutation with `mutate(ScenarioRequest)` → `ScenarioResponse`
 *
 * @example
 * ```tsx
 * const scenario = useFormulaScenario();
 * scenario.mutate({
 *   base_case_id: 'case-123',
 *   adjustments: [
 *     { name: 'Customer_Count', value: 1500, original_value: 1000 },
 *   ],
 * });
 * ```
 */
export function useFormulaScenario() {
  return useMutation<ScenarioResponse, BaseApiError, ScenarioRequest>({
    mutationFn: async (request) => {
      const response = await apiPost<l3.components['schemas']['ScenarioResponse']>('l3', '/formulas/scenario', request);
      return response.data;
    },
    onError: (error) => {
      log.error('Formula scenario calculation failed', { errorCode: error.message });
    },
  });
}
