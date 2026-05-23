/**
 * Contract tests: Ground Truth (L5)
 *
 * Validates request/response shapes against contracts/openapi/layer5-ground-truth.json.
 * Covers: POST /api/v1/truths, GET /api/v1/truths, GET /api/v1/truths/{id},
 * POST /api/v1/truths/{id}/validate, POST /api/v1/truths/{id}/sources,
 * and the maturity ladder endpoint.
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import {
  TruthObjectResponseSchema,
  TruthObjectListResponseSchema,
  TruthStatusEnum,
  ValidateResponseSchema,
  ApiErrorSchema,
  assertSchema,
  assertSchemaRejects,
  fixtures,
} from './_helpers';

// ── Request schemas ───────────────────────────────────────────────────────────

const TruthObjectCreateSchema = z.object({
  claim: z.string().min(5).max(2000),
  claim_type: z.string().optional(),
  confidence: z.number().min(0).max(1),
  value: z
    .object({
      amount: z.number().optional(),
      unit: z.string().optional(),
      currency: z.string().optional(),
      period: z.string().optional(),
    })
    .nullable()
    .optional(),
  applies_to: z.record(z.string(), z.unknown()).nullable().optional(),
  extraction_job_id: z.string().max(255).nullable().optional(),
  extraction_model: z.string().max(128).nullable().optional(),
  sources: z.array(z.record(z.string(), z.unknown())).optional(),
});

const AddSourceRequestSchema = z.object({
  source_type: z.string().min(1),
  url: z.string().optional(),
  title: z.string().optional(),
  excerpt: z.string().optional(),
  confidence: z.number().min(0).max(1).optional(),
});

const MaturityLadderResponseSchema = z.object({
  truth_id: z.string().uuid(),
  current_level: z.number().int().nonnegative(),
  history: z.array(
    z.object({
      level: z.number().int().nonnegative(),
      status: z.string(),
      transitioned_at: z.string(),
    })
  ),
});

// ── POST /api/v1/truths ───────────────────────────────────────────────────────

describe('Contract: POST /api/v1/truths', () => {
  it('accepts a minimal valid create request', () => {
    assertSchema(
      TruthObjectCreateSchema,
      {
        claim: 'Manual reporting costs 12 hours/week per analyst',
        confidence: 0.82,
      },
      'TruthObjectCreate (minimal)'
    );
  });

  it('accepts a full create request with value and applies_to', () => {
    assertSchema(
      TruthObjectCreateSchema,
      {
        claim: 'Manual reporting costs 12 hours/week per analyst',
        claim_type: 'quantitative',
        confidence: 0.82,
        value: { amount: 12, unit: 'hours', period: 'week' },
        applies_to: { account_id: 'acct-456', opportunity_id: 'opp-123' },
        extraction_job_id: 'job-abc123',
        extraction_model: 'gpt-4-turbo',
      },
      'TruthObjectCreate (full)'
    );
  });

  it('rejects claim shorter than 5 characters', () => {
    assertSchemaRejects(
      TruthObjectCreateSchema,
      { claim: 'Hi', confidence: 0.9 },
      'TruthObjectCreate with short claim'
    );
  });

  it('rejects claim longer than 2000 characters', () => {
    assertSchemaRejects(
      TruthObjectCreateSchema,
      { claim: 'a'.repeat(2001), confidence: 0.9 },
      'TruthObjectCreate with claim > 2000 chars'
    );
  });

  it('rejects confidence > 1', () => {
    assertSchemaRejects(
      TruthObjectCreateSchema,
      { claim: 'Valid claim text here', confidence: 1.1 },
      'TruthObjectCreate with confidence > 1'
    );
  });

  it('rejects confidence < 0', () => {
    assertSchemaRejects(
      TruthObjectCreateSchema,
      { claim: 'Valid claim text here', confidence: -0.1 },
      'TruthObjectCreate with negative confidence'
    );
  });

  it('accepts boundary confidence values 0 and 1', () => {
    assertSchema(TruthObjectCreateSchema, { claim: 'Boundary 0', confidence: 0 }, 'TruthObjectCreate confidence=0');
    assertSchema(TruthObjectCreateSchema, { claim: 'Boundary 1', confidence: 1 }, 'TruthObjectCreate confidence=1');
  });
});

// ── GET /api/v1/truths/{truth_id} ─────────────────────────────────────────────

describe('Contract: GET /api/v1/truths/{truth_id}', () => {
  it('response passes schema with valid fixture', () => {
    assertSchema(TruthObjectResponseSchema, fixtures.truthObject(), 'TruthObjectResponse');
  });

  it('response id is a valid UUID', () => {
    const resp = assertSchema(
      TruthObjectResponseSchema,
      fixtures.truthObject(),
      'TruthObjectResponse (UUID)'
    );
    expect(resp.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
  });

  it('response contains organization_id as tenant proxy', () => {
    const resp = assertSchema(
      TruthObjectResponseSchema,
      fixtures.truthObject(),
      'TruthObjectResponse (tenant)'
    );
    expect(resp.organization_id).toBe('550e8400-e29b-41d4-a716-446655440000');
  });

  it('is_stale is a boolean', () => {
    const fresh = assertSchema(
      TruthObjectResponseSchema,
      fixtures.truthObject({ is_stale: false }),
      'TruthObjectResponse (fresh)'
    );
    expect(fresh.is_stale).toBe(false);

    const stale = assertSchema(
      TruthObjectResponseSchema,
      fixtures.truthObject({ is_stale: true }),
      'TruthObjectResponse (stale)'
    );
    expect(stale.is_stale).toBe(true);
  });

  it('applies_to is optional and nullable', () => {
    assertSchema(
      TruthObjectResponseSchema,
      fixtures.truthObject({ applies_to: null }),
      'TruthObjectResponse (no applies_to)'
    );
  });

  it('rejects non-UUID id', () => {
    assertSchemaRejects(
      TruthObjectResponseSchema,
      { ...fixtures.truthObject(), id: 'not-a-uuid' },
      'TruthObjectResponse with non-UUID id'
    );
  });
});

// ── GET /api/v1/truths (list) ─────────────────────────────────────────────────

describe('Contract: GET /api/v1/truths', () => {
  it('list response has items, total, limit, offset, has_more', () => {
    const resp = assertSchema(
      TruthObjectListResponseSchema,
      {
        items: [fixtures.truthObjectSummary()],
        total: 1,
        limit: 20,
        offset: 0,
        has_more: false,
      },
      'TruthObjectListResponse'
    );
    expect(resp.items).toHaveLength(1);
    expect(resp.total).toBe(1);
  });

  it('empty list is valid', () => {
    const resp = assertSchema(
      TruthObjectListResponseSchema,
      { items: [], total: 0, limit: 20, offset: 0, has_more: false },
      'TruthObjectListResponse (empty)'
    );
    expect(resp.items).toHaveLength(0);
  });

  it('rejects negative total', () => {
    assertSchemaRejects(
      TruthObjectListResponseSchema,
      { items: [], total: -1, limit: 20, offset: 0, has_more: false },
      'TruthObjectListResponse with negative total'
    );
  });
});

// ── POST /api/v1/truths/{truth_id}/validate ───────────────────────────────────

describe('Contract: POST /api/v1/truths/{truth_id}/validate', () => {
  it('validate response has status transition fields', () => {
    const resp = assertSchema(
      ValidateResponseSchema,
      {
        truth_id: '550e8400-e29b-41d4-a716-446655440002',
        previous_status: 'proposed',
        new_status: 'validated',
        maturity_level: 4,
      },
      'ValidateResponse'
    );
    expect(resp.truth_id).toBe('550e8400-e29b-41d4-a716-446655440002');
    expect(resp.previous_status).toBe('proposed');
    expect(resp.new_status).toBe('validated');
    expect(resp.maturity_level).toBe(4);
  });

  it('rejects non-UUID truth_id', () => {
    assertSchemaRejects(
      ValidateResponseSchema,
      { truth_id: 'not-a-uuid', previous_status: 'proposed', new_status: 'validated', maturity_level: 4 },
      'ValidateResponse with non-UUID truth_id'
    );
  });
});

// ── POST /api/v1/truths/{truth_id}/sources ────────────────────────────────────

describe('Contract: POST /api/v1/truths/{truth_id}/sources', () => {
  it('accepts a source with type and url', () => {
    assertSchema(
      AddSourceRequestSchema,
      {
        source_type: 'document',
        url: 'https://example.com/report.pdf',
        title: 'Annual Report 2024',
        excerpt: 'Revenue grew 23% YoY...',
        confidence: 0.88,
      },
      'AddSourceRequest'
    );
  });

  it('accepts minimal source with type only', () => {
    assertSchema(
      AddSourceRequestSchema,
      { source_type: 'interview' },
      'AddSourceRequest (minimal)'
    );
  });

  it('rejects empty source_type', () => {
    assertSchemaRejects(
      AddSourceRequestSchema,
      { source_type: '' },
      'AddSourceRequest with empty source_type'
    );
  });
});

// ── GET /api/v1/maturity-ladder ───────────────────────────────────────────────

describe('Contract: GET /api/v1/maturity-ladder', () => {
  it('maturity ladder has current_level and history', () => {
    const resp = assertSchema(
      MaturityLadderResponseSchema,
      {
        truth_id: '550e8400-e29b-41d4-a716-446655440002',
        current_level: 3,
        history: [
          { level: 1, status: 'proposed', transitioned_at: '2024-01-10T10:00:00Z' },
          { level: 4, status: 'validated', transitioned_at: '2024-01-15T10:00:00Z' },
        ],
      },
      'MaturityLadderResponse'
    );
    expect(resp.current_level).toBe(3);
    expect(resp.history).toHaveLength(3);
  });
});

// ── Auth failures ─────────────────────────────────────────────────────────────

describe('Contract: ground truth auth failures', () => {
  it('401 matches ApiError shape', () => {
    assertSchema(
      ApiErrorSchema,
      { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', trace_id: 'trace-gt-401' },
      'ApiError (401)'
    );
  });

  it('cross-tenant 403 matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { message: 'Truth object does not belong to your tenant', code: 'AUTHORIZATION_ERROR', trace_id: 'trace-gt-403' },
      'ApiError (403 cross-tenant)'
    );
    expect(err.code).toBe('AUTHORIZATION_ERROR');
    expect(err.trace_id).toBeTruthy();
  });

  it('truth not found 404 matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { message: 'Truth object not found', code: 'NOT_FOUND', trace_id: 'trace-gt-404' },
      'ApiError (404 truth)'
    );
    expect(err.code).toBe('NOT_FOUND');
  });
});

describe('Contract: Ground Truth canonical envelope scenarios', () => {
  const CanonicalEnvelopeSchema = z.object({
    content: z.unknown().optional(),
    claim_citations: z.array(z.object({ claim_id: z.string(), source_id: z.string() })),
    evidence_provenance_ids: z.array(z.string()),
    refusal_reason: z.string().nullable().optional(),
    policy_decision: z.enum(['allow', 'allow_with_redaction', 'needs_approval', 'deny']),
    tenant_scope: z.object({ tenant_id: z.string(), scope: z.enum(['tenant', 'cross_tenant_blocked']) }),
    approval_required: z.boolean(),
  });

  it('accepts list payload wrapped with citations/provenance', () => {
    const wrapped = assertSchema(CanonicalEnvelopeSchema, {
      content: { items: [fixtures.truthObjectSummary()], total: 1, limit: 20, offset: 0, has_more: false },
      claim_citations: [{ claim_id: 'truth-1', source_id: 'src-1' }],
      evidence_provenance_ids: ['prov-1'],
      policy_decision: 'allow',
      tenant_scope: { tenant_id: '550e8400-e29b-41d4-a716-446655440000', scope: 'tenant' },
      approval_required: false,
    }, 'GT envelope allow');
    expect(wrapped.claim_citations.length).toBe(1);
  });

  it('supports refusal + approval gate', () => {
    const wrapped = assertSchema(CanonicalEnvelopeSchema, {
      content: null,
      claim_citations: [],
      evidence_provenance_ids: [],
      refusal_reason: 'Human approver required for disputed claim transition',
      policy_decision: 'needs_approval',
      tenant_scope: { tenant_id: '550e8400-e29b-41d4-a716-446655440000', scope: 'tenant' },
      approval_required: true,
    }, 'GT envelope approval gate');
    expect(wrapped.approval_required).toBe(true);
  });
});
