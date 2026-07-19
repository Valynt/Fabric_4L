/**
 * Canonical frontend workflow contract types.
 *
 * Consumed by the cross-stack state-alignment gate
 * (tests/state/test_state_alignment.py), which asserts these types stay
 * exactly aligned with the Layer 4 backend enums in
 * services/layer4-agents/src/layer4_agents/models/agent_state.py.
 *
 * Restored 2026-07-17 after 7b2be9560 removed the full workflows.ts module
 * (runtime API functions moved to hooks/generated clients) — the type-level
 * contract must remain for the alignment gate. Keep this file type-only.
 */

export type WorkflowStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'paused'
  | 'interrupted';

export interface WorkflowCreateRequest {
  workflow_type:
    | 'roi_calculator'
    | 'whitespace_analysis'
    | 'business_case'
    | 'business_case_generation'
    | 'orchestrator';
  inputs?: Record<string, unknown>;
  priority?: 'CRITICAL' | 'HIGH' | 'NORMAL' | 'LOW' | 'BACKGROUND';
}
