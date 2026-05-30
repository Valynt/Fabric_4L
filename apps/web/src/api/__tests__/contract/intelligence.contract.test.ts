/**
 * Contract tests: Intelligence / Signals / Narratives (L4 + L3 composition)
 *
 * These endpoints are composed product surfaces. The contract tests
 * assert the frontend expectation of the composed shape, regardless
 * of whether the backing implementation is a single layer or a BFF.
 *
 * Endpoints covered (contracts/openapi/layer4-agents.json):
 *   GET /v1/intelligence/account/{account_id}/briefing
 *   GET /v1/intelligence/account/{account_id}/deal-readiness
 *   GET /v1/intelligence/pipeline-summary
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { ApiErrorSchema, assertSchema, assertSchemaRejects } from './_helpers';

// ── Response schemas ──────────────────────────────────────────────────────────

const SignalSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  category: z.string().min(1),
  confidence: z.number().min(0).max(100),
  impact: z.enum(['Low', 'Medium', 'High', 'Critical']),
  trend: z.string().optional(),
});

const AccountBriefingResponseSchema = z.object({
  account_id: z.string().min(1),
  signals: z.array(SignalSchema),
  top_opportunities: z.array(z.string()),
  risk_factors: z.array(z.string()),
  recommended_actions: z.array(z.string()),
  generated_at: z.string(),
});

const DealReadinessResponseSchema = z.object({
  account_id: z.string().min(1),
  readiness_score: z.number().min(0).max(100),
  readiness_level: z.enum(['low', 'medium', 'high']),
  blockers: z.array(z.string()),
  accelerators: z.array(z.string()),
  next_best_action: z.string().optional(),
});

const PipelineSummaryResponseSchema = z.object({
  total_accounts: z.number().int().nonnegative(),
  accounts_with_signals: z.number().int().nonnegative(),
  high_readiness_count: z.number().int().nonnegative(),
  average_readiness_score: z.number().min(0).max(100),
  top_signals: z.array(SignalSchema),
});

// ── GET /v1/intelligence/account/{account_id}/briefing ───────────────────────

describe('Contract: GET /v1/intelligence/account/{account_id}/briefing', () => {
  it('briefing response passes schema with valid payload', () => {
    assertSchema(
      AccountBriefingResponseSchema,
      {
        account_id: 'acct-001',
        signals: [
          { id: 'sig-1', name: 'Operational inefficiency', category: 'Operational', confidence: 85, impact: 'High', trend: 'Increasing' },
        ],
        top_opportunities: ['Automate approval workflows'],
        risk_factors: ['Budget freeze in Q2'],
        recommended_actions: ['Schedule executive briefing'],
        generated_at: '2024-01-15T10:00:00Z',
      },
      'AccountBriefingResponse'
    );
  });

  it('briefing response account_id matches request', () => {
    const resp = assertSchema(
      AccountBriefingResponseSchema,
      {
        account_id: 'acct-001',
        signals: [
          { id: 'sig-1', name: 'Operational inefficiency', category: 'Operational', confidence: 85, impact: 'High', trend: 'Increasing' },
        ],
        top_opportunities: ['Automate approval workflows'],
        risk_factors: ['Budget freeze in Q2'],
        recommended_actions: ['Schedule executive briefing'],
        generated_at: '2024-01-15T10:00:00Z',
      },
      'AccountBriefingResponse (account_id)'
    );
    expect(resp.account_id).toBe('acct-001');
    expect(resp.signals).toHaveLength(1);
  });

  it('briefing with empty signals is valid', () => {
    const resp = assertSchema(
      AccountBriefingResponseSchema,
      {
        account_id: 'acct-002',
        signals: [],
        top_opportunities: [],
        risk_factors: [],
        recommended_actions: [],
        generated_at: '2024-01-15T10:00:00Z',
      },
      'AccountBriefingResponse (no signals)'
    );
    expect(resp.signals).toHaveLength(0);
  });

  it('rejects signal with confidence > 100', () => {
    assertSchemaRejects(
      SignalSchema,
      { id: 's1', name: 'Test', category: 'Cost', confidence: 150, impact: 'High' },
      'Signal with confidence > 100'
    );
  });

  it('rejects signal with unknown impact level', () => {
    assertSchemaRejects(
      SignalSchema,
      { id: 's1', name: 'Test', category: 'Cost', confidence: 80, impact: 'Extreme' },
      'Signal with unknown impact'
    );
  });
});

// ── GET /v1/intelligence/account/{account_id}/deal-readiness ─────────────────

describe('Contract: GET /v1/intelligence/account/{account_id}/deal-readiness', () => {
  it('deal readiness response has score in [0,100] and level', () => {
    const resp = assertSchema(
      DealReadinessResponseSchema,
      {
        account_id: 'acct-001',
        readiness_score: 72,
        readiness_level: 'high',
        blockers: ['No executive sponsor identified'],
        accelerators: ['Active RFP in progress'],
        next_best_action: 'Schedule C-suite demo',
      },
      'DealReadinessResponse'
    );
    expect(resp.readiness_score).toBeGreaterThanOrEqual(0);
    expect(resp.readiness_score).toBeLessThanOrEqual(100);
    expect(['low', 'medium', 'high']).toContain(resp.readiness_level);
  });

  it('next_best_action is optional', () => {
    assertSchema(
      DealReadinessResponseSchema,
      {
        account_id: 'acct-001',
        readiness_score: 30,
        readiness_level: 'low',
        blockers: ['No budget allocated'],
        accelerators: [],
      },
      'DealReadinessResponse (no next_best_action)'
    );
  });

  it('rejects unknown readiness_level', () => {
    assertSchemaRejects(
      DealReadinessResponseSchema,
      {
        account_id: 'acct-001',
        readiness_score: 50,
        readiness_level: 'critical',
        blockers: [],
        accelerators: [],
      },
      'DealReadinessResponse with unknown level'
    );
  });
});

// ── GET /v1/intelligence/pipeline-summary ────────────────────────────────────

describe('Contract: GET /v1/intelligence/pipeline-summary', () => {
  it('pipeline summary has counts and average score', () => {
    const resp = assertSchema(
      PipelineSummaryResponseSchema,
      {
        total_accounts: 42,
        accounts_with_signals: 28,
        high_readiness_count: 12,
        average_readiness_score: 61.4,
        top_signals: [
          { id: 'sig-1', name: 'Cost overrun', category: 'Financial', confidence: 90, impact: 'High' },
        ],
      },
      'PipelineSummaryResponse'
    );
    expect(resp.total_accounts).toBeGreaterThanOrEqual(resp.accounts_with_signals);
    expect(resp.average_readiness_score).toBeGreaterThanOrEqual(0);
    expect(resp.average_readiness_score).toBeLessThanOrEqual(100);
  });

  it('accounts_with_signals cannot exceed total_accounts', () => {
    // Schema does not enforce this cross-field constraint — document it here
    // so a future validator can catch it.
    const resp = assertSchema(
      PipelineSummaryResponseSchema,
      {
        total_accounts: 10,
        accounts_with_signals: 10,
        high_readiness_count: 5,
        average_readiness_score: 55,
        top_signals: [],
      },
      'PipelineSummaryResponse (all accounts have signals)'
    );
    expect(resp.accounts_with_signals).toBeLessThanOrEqual(resp.total_accounts);
  });
});

// ── Pagination ────────────────────────────────────────────────────────────────

describe('Contract: intelligence pagination', () => {
  it('paginated signal list has required pagination fields', () => {
    const PaginatedSignalsSchema = z.object({
      items: z.array(SignalSchema),
      total: z.number().int().nonnegative(),
      page: z.number().int().positive(),
      page_size: z.number().int().positive(),
      has_more: z.boolean(),
    });

    const resp = assertSchema(
      PaginatedSignalsSchema,
      {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        has_more: false,
      },
      'PaginatedSignals (empty)'
    );
    expect(resp.has_more).toBe(false);
  });
});

// ── Tenant context ────────────────────────────────────────────────────────────

describe('Contract: intelligence tenant context', () => {
  it('briefing response can include tenant-scoped account_id', () => {
    const TenantScopedBriefingSchema = AccountBriefingResponseSchema.extend({
      tenant_id: z.string().uuid(),
    });
    const resp = assertSchema(
      TenantScopedBriefingSchema,
      {
        account_id: 'acct-001',
        signals: [{ id: 'sig-1', name: 'Operational inefficiency', category: 'Operational', confidence: 85, impact: 'High', trend: 'Increasing' }],
        top_opportunities: ['Automate approval workflows'],
        risk_factors: ['Budget freeze in Q2'],
        recommended_actions: ['Schedule executive briefing'],
        generated_at: '2024-01-15T10:00:00Z',
        tenant_id: '550e8400-e29b-41d4-a716-446655440000',
      },
      'TenantScopedBriefing'
    );
    expect(resp.tenant_id).toBe('550e8400-e29b-41d4-a716-446655440000');
  });
});

// ── Auth failures ─────────────────────────────────────────────────────────────

describe('Contract: intelligence auth failures', () => {
  it('401 matches ApiError shape', () => {
    assertSchema(
      ApiErrorSchema,
      { error: { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', request_id: 'trace-intel-401' } },
      'ApiError (401)'
    );
  });

  it('cross-tenant 403 matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Account does not belong to your tenant', code: 'AUTHORIZATION_ERROR', request_id: 'trace-intel-403' } },
      'ApiError (403 cross-tenant)'
    );
    expect(err.error.code).toBe('AUTHORIZATION_ERROR');
    expect(err.error.request_id).toBeTruthy();
  });

  it('account not found 404 matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Account not found', code: 'NOT_FOUND', request_id: 'trace-intel-404' } },
      'ApiError (404 account)'
    );
    expect(err.error.code).toBe('NOT_FOUND');
  });
});
