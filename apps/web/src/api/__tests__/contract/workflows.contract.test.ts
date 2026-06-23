/**
 * Contract tests: Agent Workflows (L4)
 *
 * Validates request/response shapes against contracts/openapi/layer4-agents.json.
 * Covers: create, status polling, result retrieval, resume, cancel, and
 * the analysis sub-endpoints (ROI, whitespace). Also asserts auth-failure
 * and tenant-isolation shapes.
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import {
  WorkflowCreateResponseSchema,
  WorkflowStatusResponseSchema,
  WorkflowResultResponseSchema,
  WorkflowResumeResponseSchema,
  WorkflowStatusEnum,
  ApiErrorSchema,
  assertSchema,
  assertSchemaRejects,
  fixtures,
} from './_helpers';

// ── Request schemas (frontend → backend) ────────────────────────────────────

const WorkflowCreateRequestSchema = z.object({
  workflow_type: z.enum([
    'roi_calculator',
    'whitespace_analysis',
    'business_case',
    'business_case_generation',
    'orchestrator',
  ]),
  inputs: z
    .object({
      prospect_id: z.string().optional(),
      prospect_company: z.string().optional(),
      use_case_ids: z.array(z.string()).optional(),
      prospect_metrics: z.record(z.string(), z.number()).optional(),
      custom_data: z.record(z.string(), z.unknown()).optional(),
    })
    .optional(),
  priority: z
    .enum(['CRITICAL', 'HIGH', 'NORMAL', 'LOW', 'BACKGROUND'])
    .optional(),
});

const ROIAnalysisResponseSchema = z.object({
  prospect_id: z.string().min(1),
  aggregated_roi: z.record(z.string(), z.unknown()),
  detailed_results: z.array(z.record(z.string(), z.unknown())),
  benchmark_comparison: z.record(z.string(), z.unknown()).nullable(),
});

const WhitespaceAnalysisResponseSchema = z.object({
  prospect_id: z.string().min(1),
  extracted_needs: z.array(z.string()),
  gap_analysis: z.array(z.record(z.string(), z.unknown())),
  opportunity_score: z.number().min(0).max(1),
  recommendations: z.array(z.string()),
});

// ── POST /v1/workflows ───────────────────────────────────────────────────────

describe('Contract: POST /v1/workflows', () => {
  it('accepts a minimal valid create request', () => {
    const req = {
      workflow_type: 'roi_calculator',
    };
    assertSchema(WorkflowCreateRequestSchema, req, 'WorkflowCreateRequest');
  });

  it('accepts a full create request with inputs and priority', () => {
    const req = {
      workflow_type: 'whitespace_analysis',
      inputs: {
        prospect_id: 'prospect-abc',
        prospect_company: 'Acme Corp',
        use_case_ids: ['uc-1', 'uc-2'],
        prospect_metrics: { employees: 500, revenue_usd: 50000000 },
      },
      priority: 'HIGH',
    };
    assertSchema(WorkflowCreateRequestSchema, req, 'WorkflowCreateRequest (full)');
  });

  it('rejects unknown workflow_type', () => {
    assertSchemaRejects(
      WorkflowCreateRequestSchema,
      { workflow_type: 'unknown_type' },
      'WorkflowCreateRequest with invalid type'
    );
  });

  it('accepts minimal request using auth-context identity', () => {
    assertSchema(
      WorkflowCreateRequestSchema,
      { workflow_type: 'roi_calculator' },
      'WorkflowCreateRequest minimal (auth context fallback)'
    );
  });

  it('response contains workflow_instance_id and status', () => {
    const resp = assertSchema(
      WorkflowCreateResponseSchema,
      fixtures.workflowCreateResponse(),
      'WorkflowCreateResponse'
    );
    expect(resp.workflow_instance_id).toBeTruthy();
    expect(resp.status).toBeTruthy();
    expect(resp.estimated_duration_seconds).toBeGreaterThanOrEqual(0);
  });
});

// ── GET /v1/workflows/{workflow_id} ──────────────────────────────────────────

describe('Contract: GET /v1/workflows/{workflow_id}', () => {
  it('running workflow has progress and no completed_at', () => {
    const resp = assertSchema(
      WorkflowStatusResponseSchema,
      fixtures.workflowStatus({ status: 'running', completed_at: null }),
      'WorkflowStatusResponse (running)'
    );
    expect(resp.status).toBe('running');
    expect(resp.completed_at).toBeNull();
    expect(resp.progress_percentage).toBeGreaterThanOrEqual(0);
    expect(resp.progress_percentage).toBeLessThanOrEqual(100);
  });

  it('completed workflow has has_output=true and results', () => {
    const resp = assertSchema(
      WorkflowStatusResponseSchema,
      fixtures.workflowStatus({
        status: 'completed',
        completed_at: '2024-01-15T10:05:00Z',
        has_output: true,
        results: { roi_percent: 142 },
        progress_percentage: 100,
      }),
      'WorkflowStatusResponse (completed)'
    );
    expect(resp.status).toBe('completed');
    expect(resp.has_output).toBe(true);
    expect(resp.results).not.toBeNull();
  });

  it('failed workflow has error_count > 0', () => {
    const resp = assertSchema(
      WorkflowStatusResponseSchema,
      fixtures.workflowStatus({ status: 'failed', error_count: 3 }),
      'WorkflowStatusResponse (failed)'
    );
    expect(resp.status).toBe('failed');
    expect(resp.error_count).toBeGreaterThan(0);
  });

  it.each([
    'pending', 'running', 'completed', 'failed', 'cancelled', 'paused', 'interrupted',
  ] as const)('accepts valid status value "%s"', (status) => {
    assertSchema(
      WorkflowStatusResponseSchema,
      fixtures.workflowStatus({ status }),
      `WorkflowStatusResponse (${status})`
    );
  });

  it('rejects unknown status value', () => {
    assertSchemaRejects(
      WorkflowStatusResponseSchema,
      fixtures.workflowStatus({ status: 'unknown' as never }),
      'WorkflowStatusResponse with invalid status'
    );
  });

  it('tenant_id is present for tenant isolation', () => {
    const resp = assertSchema(
      WorkflowStatusResponseSchema,
      fixtures.workflowStatus({ tenant_id: 'tenant-abc' }),
      'WorkflowStatusResponse (tenant context)'
    );
    expect(resp.tenant_id).toBe('tenant-abc');
  });
});

// ── GET /v1/workflows/{workflow_id}/result ───────────────────────────────────

describe('Contract: GET /v1/workflows/{workflow_id}/result', () => {
  it('completed result has output and empty errors', () => {
    const resp = assertSchema(
      WorkflowResultResponseSchema,
      fixtures.workflowResult(),
      'WorkflowResultResponse'
    );
    expect(resp.status).toBe('completed');
    expect(resp.output).not.toBeNull();
    expect(resp.errors).toHaveLength(0);
    expect(resp.completed_at).toBeTruthy();
  });

  it('failed result has errors array and null output', () => {
    const resp = assertSchema(
      WorkflowResultResponseSchema,
      {
        workflow_id: 'wf-inst-001',
        status: 'failed',
        output: null,
        errors: ['LLM timeout after 60s', 'Retry limit exceeded'],
        completed_at: '2024-01-15T10:05:00Z',
      },
      'WorkflowResultResponse (failed)'
    );
    expect(resp.errors.length).toBeGreaterThan(0);
    expect(resp.output).toBeNull();
  });
});

// ── POST /v1/workflows/{workflow_id}/resume ──────────────────────────────────

describe('Contract: POST /v1/workflows/{workflow_id}/resume', () => {
  it('resume response contains instance_id and resumed_from_node', () => {
    const resp = assertSchema(
      WorkflowResumeResponseSchema,
      {
        workflow_instance_id: 'wf-inst-001',
        status: 'running',
        resumed_from_node: 'human_review',
        message: 'Workflow resumed successfully',
        estimated_completion_seconds: 120,
      },
      'WorkflowResumeResponse'
    );
    expect(resp.workflow_instance_id).toBeTruthy();
    expect(resp.resumed_from_node).toBe('human_review');
  });

  it('resumed_from_node may be null when resuming from start', () => {
    const resp = assertSchema(
      WorkflowResumeResponseSchema,
      {
        workflow_instance_id: 'wf-inst-001',
        status: 'running',
        resumed_from_node: null,
        message: 'Workflow restarted',
        estimated_completion_seconds: 300,
      },
      'WorkflowResumeResponse (null node)'
    );
    expect(resp.resumed_from_node).toBeNull();
  });
});

// ── DELETE /v1/workflows/{workflow_id} (cancel) ──────────────────────────────

describe('Contract: DELETE /v1/workflows/{workflow_id}', () => {
  it('cancel response contains workflow_id and status', () => {
    const CancelResponseSchema = z.object({
      workflow_id: z.string().min(1),
      status: z.string().min(1),
    });
    const resp = assertSchema(
      CancelResponseSchema,
      { workflow_id: 'wf-inst-001', status: 'cancelled' },
      'WorkflowCancelResponse'
    );
    expect(resp.status).toBe('cancelled');
  });
});

// ── POST /v1/analysis/roi ────────────────────────────────────────────────────

describe('Contract: POST /v1/analysis/roi', () => {
  it('ROI response has prospect_id and aggregated_roi', () => {
    const resp = assertSchema(
      ROIAnalysisResponseSchema,
      {
        prospect_id: 'prospect-abc',
        aggregated_roi: { total_value_usd: 1200000, roi_percent: 142 },
        detailed_results: [{ driver: 'labor_savings', value_usd: 800000 }],
        benchmark_comparison: null,
      },
      'ROIAnalysisResponse'
    );
    expect(resp.prospect_id).toBe('prospect-abc');
    expect(resp.aggregated_roi).toBeDefined();
  });

  it('rejects missing prospect_id', () => {
    assertSchemaRejects(
      ROIAnalysisResponseSchema,
      { aggregated_roi: {}, detailed_results: [], benchmark_comparison: null },
      'ROIAnalysisResponse missing prospect_id'
    );
  });
});

// ── POST /v1/analysis/whitespace ─────────────────────────────────────────────

describe('Contract: POST /v1/analysis/whitespace', () => {
  it('whitespace response has opportunity_score in [0,1]', () => {
    const resp = assertSchema(
      WhitespaceAnalysisResponseSchema,
      {
        prospect_id: 'prospect-abc',
        extracted_needs: ['reduce manual reporting', 'automate approvals'],
        gap_analysis: [{ gap: 'workflow automation', severity: 'high' }],
        opportunity_score: 0.78,
        recommendations: ['Deploy workflow automation module'],
      },
      'WhitespaceAnalysisResponse'
    );
    expect(resp.opportunity_score).toBeGreaterThanOrEqual(0);
    expect(resp.opportunity_score).toBeLessThanOrEqual(1);
  });

  it('rejects opportunity_score > 1', () => {
    assertSchemaRejects(
      WhitespaceAnalysisResponseSchema,
      {
        prospect_id: 'p',
        extracted_needs: [],
        gap_analysis: [],
        opportunity_score: 1.5,
        recommendations: [],
      },
      'WhitespaceAnalysisResponse with score > 1'
    );
  });

  it('rejects opportunity_score < 0', () => {
    assertSchemaRejects(
      WhitespaceAnalysisResponseSchema,
      {
        prospect_id: 'p',
        extracted_needs: [],
        gap_analysis: [],
        opportunity_score: -0.1,
        recommendations: [],
      },
      'WhitespaceAnalysisResponse with score < 0'
    );
  });

  it('accepts boundary opportunity_score values 0 and 1', () => {
    assertSchema(
      WhitespaceAnalysisResponseSchema,
      { prospect_id: 'p', extracted_needs: [], gap_analysis: [], opportunity_score: 0, recommendations: [] },
      'WhitespaceAnalysisResponse score=0'
    );
    assertSchema(
      WhitespaceAnalysisResponseSchema,
      { prospect_id: 'p', extracted_needs: [], gap_analysis: [], opportunity_score: 1, recommendations: [] },
      'WhitespaceAnalysisResponse score=1'
    );
  });
});

// ── Pagination ────────────────────────────────────────────────────────────────

describe('Contract: workflow list pagination', () => {
  it('paginated workflow list has required pagination fields', () => {
    const PaginatedWorkflowSchema = z.object({
      items: z.array(WorkflowStatusResponseSchema),
      total: z.number().int().nonnegative(),
      limit: z.number().int().positive(),
      offset: z.number().int().nonnegative(),
      has_more: z.boolean(),
    });

    const resp = assertSchema(
      PaginatedWorkflowSchema,
      { items: [], total: 0, limit: 50, offset: 0, has_more: false },
      'PaginatedWorkflows (empty)'
    );
    expect(resp.has_more).toBe(false);
  });
});

// ── Auth failure shape ───────────────────────────────────────────────────────

describe('Contract: auth failure responses', () => {
  it('401 response matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', request_id: 'trace-wf-401' } },
      'ApiError (401)'
    );
    expect(err.error.message).toBeTruthy();
    expect(err.error.request_id).toBeTruthy();
  });

  it('403 cross-tenant workflow access matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Workflow does not belong to your tenant', code: 'AUTHORIZATION_ERROR', request_id: 'trace-wf-403' } },
      'ApiError (403 cross-tenant)'
    );
    expect(err.error.code).toBe('AUTHORIZATION_ERROR');
    expect(err.error.request_id).toBeTruthy();
  });

  it('404 workflow not found matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Workflow not found', code: 'NOT_FOUND', request_id: 'trace-wf-404' } },
      'ApiError (404)'
    );
    expect(err.error.code).toBe('NOT_FOUND');
    expect(err.error.request_id).toBeTruthy();
  });
});
