/**
 * Contract tests: Agent Stream / C1 / SSE (L4)
 *
 * Validates request/response shapes for POST /v1/c1/stream against
 * contracts/openapi/layer4-agents.json (C1StreamRequest, C1Message).
 * SSE is a streaming protocol — these tests validate the request body
 * contract and the shape of individual SSE event payloads.
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { C1MessageSchema, ApiErrorSchema, assertSchema, assertSchemaRejects } from './_helpers';

// ── C1StreamRequest schema ───────────────────────────────────────────────────

const C1StreamRequestSchema = z.object({
  messages: z.array(C1MessageSchema).min(1),
  business_case_id: z.string().min(1),
  business_case_data: z.record(z.string(), z.unknown()).nullable().optional(),
});

// SSE event payload shapes emitted by the stream
const C1StreamEventSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('token'), content: z.string() }),
  z.object({ type: z.literal('done'), finish_reason: z.string() }),
  z.object({ type: z.literal('error'), message: z.string(), code: z.string().optional() }),
  z.object({ type: z.literal('tool_call'), tool_name: z.string(), arguments: z.record(z.string(), z.unknown()) }),
]);

// ── POST /v1/c1/stream — request body ────────────────────────────────────────

describe('Contract: POST /v1/c1/stream — request body', () => {
  it('accepts a minimal valid request with one user message', () => {
    assertSchema(
      C1StreamRequestSchema,
      {
        messages: [{ role: 'user', content: 'What is the ROI for this account?' }],
        business_case_id: 'case-abc123',
      },
      'C1StreamRequest (minimal)'
    );
  });

  it('accepts a multi-turn conversation', () => {
    assertSchema(
      C1StreamRequestSchema,
      {
        messages: [
          { role: 'system', content: 'You are a value engineering assistant.' },
          { role: 'user', content: 'Summarise the key value drivers.' },
          { role: 'assistant', content: 'The top three drivers are...' },
          { role: 'user', content: 'Which has the highest confidence?' },
        ],
        business_case_id: 'case-abc123',
        business_case_data: { account_id: 'acct-001', industry: 'SaaS' },
      },
      'C1StreamRequest (multi-turn)'
    );
  });

  it('rejects empty messages array', () => {
    assertSchemaRejects(
      C1StreamRequestSchema,
      { messages: [], business_case_id: 'case-abc123' },
      'C1StreamRequest with empty messages'
    );
  });

  it('rejects missing business_case_id', () => {
    assertSchemaRejects(
      C1StreamRequestSchema,
      { messages: [{ role: 'user', content: 'Hello' }] },
      'C1StreamRequest missing business_case_id'
    );
  });

  it('rejects message with empty content', () => {
    assertSchemaRejects(
      C1MessageSchema,
      { role: 'user', content: '' },
      'C1Message with empty content'
    );
  });

  it('rejects message with empty role', () => {
    assertSchemaRejects(
      C1MessageSchema,
      { role: '', content: 'Hello' },
      'C1Message with empty role'
    );
  });
});

// ── SSE event payload shapes ──────────────────────────────────────────────────

describe('Contract: C1 SSE event payloads', () => {
  it('token event has content string', () => {
    const event = assertSchema(
      C1StreamEventSchema,
      { type: 'token', content: 'The ROI is approximately' },
      'C1StreamEvent (token)'
    );
    expect(event.type).toBe('token');
    if (event.type === 'token') {
      expect(typeof event.content).toBe('string');
    }
  });

  it('done event has finish_reason', () => {
    const event = assertSchema(
      C1StreamEventSchema,
      { type: 'done', finish_reason: 'stop' },
      'C1StreamEvent (done)'
    );
    expect(event.type).toBe('done');
    if (event.type === 'done') {
      expect(event.finish_reason).toBe('stop');
    }
  });

  it('error event has message and optional code', () => {
    const event = assertSchema(
      C1StreamEventSchema,
      { type: 'error', message: 'LLM rate limit exceeded', code: 'RATE_LIMITED' },
      'C1StreamEvent (error)'
    );
    expect(event.type).toBe('error');
    if (event.type === 'error') {
      expect(event.message).toBeTruthy();
    }
  });

  it('tool_call event has tool_name and arguments', () => {
    const event = assertSchema(
      C1StreamEventSchema,
      {
        type: 'tool_call',
        tool_name: 'calculate_roi',
        arguments: { prospect_id: 'p-001', value_driver_ids: ['vd-1'] },
      },
      'C1StreamEvent (tool_call)'
    );
    expect(event.type).toBe('tool_call');
    if (event.type === 'tool_call') {
      expect(event.tool_name).toBe('calculate_roi');
    }
  });

  it('rejects event with unknown type', () => {
    assertSchemaRejects(
      C1StreamEventSchema,
      { type: 'unknown', data: 'something' },
      'C1StreamEvent with unknown type'
    );
  });
});

// ── Tenant context ────────────────────────────────────────────────────────────

describe('Contract: C1 stream tenant context', () => {
  it('request includes tenant_id in business_case_data when scoped', () => {
    assertSchema(
      C1StreamRequestSchema,
      {
        messages: [{ role: 'user', content: 'Hello' }],
        business_case_id: 'case-abc123',
        business_case_data: { tenant_id: '550e8400-e29b-41d4-a716-446655440000', account_id: 'acct-001' },
      },
      'C1StreamRequest with tenant context'
    );
  });
});

// ── Auth failure ──────────────────────────────────────────────────────────────

describe('Contract: C1 stream auth failures', () => {
  it('401 before stream opens matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', request_id: 'trace-c1-401' } },
      'ApiError (401 pre-stream)'
    );
    expect(err.error.message).toBeTruthy();
    expect(err.error.request_id).toBeTruthy();
  });

  it('403 when tenant lacks C1 entitlement matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'C1 feature not available on current plan', code: 'FEATURE_NOT_ENTITLED', request_id: 'trace-c1-403' } },
      'ApiError (403 entitlement)'
    );
    expect(err.error.code).toBe('FEATURE_NOT_ENTITLED');
    expect(err.error.request_id).toBeTruthy();
  });

  it('404 when business_case_id does not exist in tenant matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Business case not found', code: 'NOT_FOUND', request_id: 'trace-c1-404' } },
      'ApiError (404 case)'
    );
    expect(err.error.code).toBe('NOT_FOUND');
  });
});

describe('Contract: C1 canonical envelope scenarios', () => {
  const CanonicalEnvelopeSchema = z.object({
    content: z.string().nullable().optional(),
    claim_citations: z.array(z.object({ claim_id: z.string(), source_id: z.string() })),
    evidence_provenance_ids: z.array(z.string()),
    refusal_reason: z.string().nullable().optional(),
    policy_decision: z.enum(['allow', 'allow_with_redaction', 'needs_approval', 'deny']),
    tenant_scope: z.object({ tenant_id: z.string(), scope: z.enum(['tenant', 'cross_tenant_blocked']) }),
    approval_required: z.boolean(),
  });

  it('supports refusal with citation + provenance + deny', () => {
    const event = assertSchema(CanonicalEnvelopeSchema, {
      content: null,
      claim_citations: [{ claim_id: 'clm-1', source_id: 'src-2' }],
      evidence_provenance_ids: ['prov-11'],
      refusal_reason: 'Cross-tenant request blocked',
      policy_decision: 'deny',
      tenant_scope: { tenant_id: '550e8400-e29b-41d4-a716-446655440000', scope: 'cross_tenant_blocked' },
      approval_required: false,
    }, 'CanonicalEnvelope refusal');
    expect(event.policy_decision).toBe('deny');
  });

  it('supports approval gate response with needs_approval', () => {
    const event = assertSchema(CanonicalEnvelopeSchema, {
      content: null,
      claim_citations: [],
      evidence_provenance_ids: [],
      policy_decision: 'needs_approval',
      tenant_scope: { tenant_id: '550e8400-e29b-41d4-a716-446655440000', scope: 'tenant' },
      approval_required: true,
    }, 'CanonicalEnvelope approval gate');
    expect(event.approval_required).toBe(true);
  });
});
