/**
 * Contract tests: Formulas (L3)
 *
 * Validates request/response shapes against contracts/openapi/layer3-knowledge.json.
 * Covers: POST /v1/formulas/evaluate, GET /v1/formulas, GET /v1/formulas/{id},
 * governance lifecycle (submit, approve, activate, deprecate), and the
 * approval queue. Uses existing FormulaSchema from lib/schemas/formula.
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import {
  FormulaEvaluateResponseSchema,
  ApiErrorSchema,
  assertSchema,
  assertSchemaRejects,
} from './_helpers';
import {
  FormulaSchema,
  FormulaEvaluationResultSchema,
  ApprovalRequestSchema,
} from '@/lib/schemas/formula';

// ── Local request schemas ────────────────────────────────────────────────────

const FormulaEvaluateRequestSchema = z.object({
  formula_id: z.string().nullable().optional(),
  expression: z.string().nullable().optional(),
  variables: z.record(z.string(), z.number()),
  context: z.record(z.string(), z.unknown()).optional(),
});

const FormulaScenarioRequestSchema = z.object({
  formula_id: z.string().min(1),
  scenarios: z.array(
    z.object({
      name: z.string().min(1),
      variables: z.record(z.string(), z.number()),
    })
  ).min(1),
});

const FormulaScenarioResponseSchema = z.object({
  formula_id: z.string().min(1),
  scenarios: z.array(
    z.object({
      name: z.string().min(1),
      result: z.number(),
      unit: z.string(),
      confidence: z.number().min(0).max(1),
    })
  ),
});

// ── POST /v1/formulas/evaluate ────────────────────────────────────────────────

describe('Contract: POST /v1/formulas/evaluate', () => {
  it('accepts evaluate request with formula_id', () => {
    assertSchema(
      FormulaEvaluateRequestSchema,
      {
        formula_id: 'formula-roi-001',
        variables: { annual_savings: 500000, implementation_cost: 200000 },
      },
      'FormulaEvaluateRequest (by id)'
    );
  });

  it('accepts evaluate request with inline expression', () => {
    assertSchema(
      FormulaEvaluateRequestSchema,
      {
        expression: '(annual_savings - implementation_cost) / implementation_cost * 100',
        variables: { annual_savings: 500000, implementation_cost: 200000 },
      },
      'FormulaEvaluateRequest (inline expression)'
    );
  });

  it('accepts empty variables object', () => {
    assertSchema(
      FormulaEvaluateRequestSchema,
      { formula_id: 'f-001', variables: {} },
      'FormulaEvaluateRequest (no variables)'
    );
  });

  it('response has result, unit, confidence, and calculation_steps', () => {
    const resp = assertSchema(
      FormulaEvaluateResponseSchema,
      {
        result: 150.0,
        unit: 'percent',
        confidence: 0.92,
        calculation_steps: [
          { step: 1, operation: 'annual_savings - implementation_cost', result: '300000' },
          { step: 2, operation: '300000 / 200000 * 100', result: '150.0' },
        ],
        formula_used: 'roi_basic_v2',
      },
      'FormulaEvaluateResponse'
    );
    expect(resp.result).toBe(150.0);
    expect(resp.confidence).toBeGreaterThanOrEqual(0);
    expect(resp.confidence).toBeLessThanOrEqual(1);
    expect(resp.calculation_steps).toHaveLength(2);
  });

  it('confidence is in [0,1]', () => {
    assertSchemaRejects(
      FormulaEvaluateResponseSchema,
      {
        result: 150,
        unit: 'percent',
        confidence: 1.1,
        calculation_steps: [],
        formula_used: 'f',
      },
      'FormulaEvaluateResponse with confidence > 1'
    );
  });

  it('calculation_steps have sequential step numbers', () => {
    const resp = assertSchema(
      FormulaEvaluationResultSchema,
      {
        result: 42,
        unit: 'USD',
        confidence: 0.85,
        calculation_steps: [
          { step: 1, operation: 'a + b', result: '42' },
          { step: 2, operation: 'result * 1', result: '42' },
        ],
        formula_used: 'test_formula',
      },
      'FormulaEvaluationResult'
    );
    const steps = resp.calculation_steps.map((s) => s.step);
    expect(steps).toEqual([1, 2]);
  });
});

// ── POST /v1/formulas/scenario ────────────────────────────────────────────────

describe('Contract: POST /v1/formulas/scenario', () => {
  it('accepts scenario request with multiple scenarios', () => {
    assertSchema(
      FormulaScenarioRequestSchema,
      {
        formula_id: 'formula-roi-001',
        scenarios: [
          { name: 'conservative', variables: { annual_savings: 300000, implementation_cost: 200000 } },
          { name: 'expected', variables: { annual_savings: 500000, implementation_cost: 200000 } },
          { name: 'optimistic', variables: { annual_savings: 800000, implementation_cost: 200000 } },
        ],
      },
      'FormulaScenarioRequest'
    );
  });

  it('rejects empty scenarios array', () => {
    assertSchemaRejects(
      FormulaScenarioRequestSchema,
      { formula_id: 'f-001', scenarios: [] },
      'FormulaScenarioRequest with empty scenarios'
    );
  });

  it('scenario response has result per scenario', () => {
    const resp = assertSchema(
      FormulaScenarioResponseSchema,
      {
        formula_id: 'formula-roi-001',
        scenarios: [
          { name: 'conservative', result: 50, unit: 'percent', confidence: 0.9 },
          { name: 'expected', result: 150, unit: 'percent', confidence: 0.92 },
          { name: 'optimistic', result: 300, unit: 'percent', confidence: 0.85 },
        ],
      },
      'FormulaScenarioResponse'
    );
    expect(resp.scenarios).toHaveLength(3);
    const names = resp.scenarios.map((s) => s.name);
    expect(names).toContain('conservative');
    expect(names).toContain('optimistic');
  });
});

// ── GET /v1/formulas ──────────────────────────────────────────────────────────

describe('Contract: GET /v1/formulas', () => {
  it('formula list item matches FormulaSchema', () => {
    const formula = assertSchema(
      FormulaSchema,
      {
        id: 'formula-roi-001',
        name: 'ROI Calculator',
        status: 'active',
        version: '2.1.0',
        domain: 'finance',
        formula_type: 'composite',
        used_in_count: 14,
      },
      'Formula (list item)'
    );
    expect(formula.id).toBeTruthy();
    expect(formula.name).toBeTruthy();
  });

  it('rejects formula with empty name', () => {
    assertSchemaRejects(
      FormulaSchema,
      { id: 'f-001', name: '' },
      'Formula with empty name'
    );
  });
});

// ── Governance lifecycle ──────────────────────────────────────────────────────

describe('Contract: formula governance lifecycle', () => {
  it('approval request has required governance fields', () => {
    const req = assertSchema(
      ApprovalRequestSchema,
      {
        id: '550e8400-e29b-41d4-a716-446655440000',
        formula_id: 'formula-roi-001',
        formula_name: 'ROI Calculator',
        submitted_by: 'analyst@example.com',
        submitted_at: '2024-01-15T10:00:00.000Z',
        change_summary: 'Updated discount rate variable to use market rate',
        previous_version: '2.0.0',
        status: 'pending',
      },
      'ApprovalRequest'
    );
    expect(req.status).toBe('pending');
    expect(req.submitted_by).toContain('@');
  });

  it('rejects approval request with invalid email', () => {
    assertSchemaRejects(
      ApprovalRequestSchema,
      {
        id: '550e8400-e29b-41d4-a716-446655440000',
        formula_id: 'f-001',
        formula_name: 'Test',
        submitted_by: 'not-an-email',
        submitted_at: '2024-01-15T10:00:00.000Z',
        change_summary: 'Test change',
        previous_version: '1.0.0',
        status: 'pending',
      },
      'ApprovalRequest with invalid email'
    );
  });

  it('rejects approval request with non-semver version', () => {
    assertSchemaRejects(
      ApprovalRequestSchema,
      {
        id: '550e8400-e29b-41d4-a716-446655440000',
        formula_id: 'f-001',
        formula_name: 'Test',
        submitted_by: 'user@example.com',
        submitted_at: '2024-01-15T10:00:00.000Z',
        change_summary: 'Test',
        previous_version: 'v2',
        status: 'pending',
      },
      'ApprovalRequest with non-semver version'
    );
  });

  it('all approval status values are valid', () => {
    for (const status of ['pending', 'approved', 'rejected'] as const) {
      assertSchema(
        ApprovalRequestSchema,
        {
          id: '550e8400-e29b-41d4-a716-446655440000',
          formula_id: 'f-001',
          formula_name: 'Test',
          submitted_by: 'user@example.com',
          submitted_at: '2024-01-15T10:00:00.000Z',
          change_summary: 'Test',
          previous_version: '1.0.0',
          status,
        },
        `ApprovalRequest (${status})`
      );
    }
  });
});

// ── Tenant context ────────────────────────────────────────────────────────────

describe('Contract: formula tenant context', () => {
  it('formula list item is scoped to a tenant', () => {
    const TenantScopedFormulaSchema = FormulaSchema.extend({
      tenant_id: z.string().uuid(),
    });
    const formula = assertSchema(
      TenantScopedFormulaSchema,
      {
        id: 'formula-roi-001',
        name: 'ROI Calculator',
        status: 'active',
        version: '2.1.0',
        domain: 'finance',
        formula_type: 'composite',
        used_in_count: 14,
        tenant_id: '550e8400-e29b-41d4-a716-446655440000',
      },
      'TenantScopedFormula'
    );
    expect(formula.tenant_id).toBe('550e8400-e29b-41d4-a716-446655440000');
  });
});

// ── Pagination ────────────────────────────────────────────────────────────────

describe('Contract: formula list pagination', () => {
  it('paginated formula list has required pagination fields', () => {
    const PaginatedFormulaSchema = z.object({
      items: z.array(FormulaSchema),
      total: z.number().int().nonnegative(),
      page: z.number().int().positive(),
      page_size: z.number().int().positive(),
      has_more: z.boolean(),
    });

    const resp = assertSchema(
      PaginatedFormulaSchema,
      { items: [], total: 0, page: 1, page_size: 20, has_more: false },
      'PaginatedFormulas (empty)'
    );
    expect(resp.has_more).toBe(false);
  });
});

// ── Auth failures ─────────────────────────────────────────────────────────────

describe('Contract: formula auth failures', () => {
  it('401 matches ApiError shape', () => {
    assertSchema(
      ApiErrorSchema,
      { error: { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', request_id: 'trace-formula-401' } },
      'ApiError (401)'
    );
  });

  it('403 cross-tenant formula access matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Formula does not belong to your tenant', code: 'AUTHORIZATION_ERROR', request_id: 'trace-formula-403' } },
      'ApiError (403 cross-tenant)'
    );
    expect(err.error.code).toBe('AUTHORIZATION_ERROR');
    expect(err.error.request_id).toBeTruthy();
  });

  it('formula not found 404 matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Formula not found', code: 'NOT_FOUND', request_id: 'trace-formula-404' } },
      'ApiError (404)'
    );
    expect(err.error.code).toBe('NOT_FOUND');
  });
});
