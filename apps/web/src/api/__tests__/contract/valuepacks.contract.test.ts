/**
 * Contract tests: Value Packs (L3)
 *
 * Validates request/response shapes against contracts/openapi/layer3-knowledge.json
 * (PackSummary schema) and the frontend ValuePackSchema from lib/schemas/valuePack.
 * Covers: GET /v1/packs, GET /v1/packs/{pack_id}, POST /v1/packs/{pack_id}/apply,
 * POST /v1/packs/{pack_id}/fork, and filter/pagination shapes.
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { PackSummarySchema, ApiErrorSchema, assertSchema, assertSchemaRejects, fixtures } from './_helpers';
import { ValuePackSchema, PackStatusSchema, PackScopeSchema } from '@/lib/schemas/valuePack';

// ── Local schemas ─────────────────────────────────────────────────────────────

const ApplyValuePackResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  appliedAt: z.string().optional(),
  pack_id: z.string().optional(),
  entity_id: z.string().optional(),
});

const ForkValuePackResponseSchema = z.object({
  pack_id: z.string().min(1),
  name: z.string().min(1),
  forked_from: z.string().min(1),
  status: z.string(),
});

// ── GET /v1/packs ─────────────────────────────────────────────────────────────

describe('Contract: GET /v1/packs', () => {
  it('pack summary has required fields', () => {
    const pack = assertSchema(PackSummarySchema, fixtures.packSummary(), 'PackSummary');
    expect(pack.pack_id).toBeTruthy();
    expect(pack.name).toBeTruthy();
    expect(pack.industry).toBeTruthy();
  });

  it('full ValuePack shape has counts and scope', () => {
    const pack = assertSchema(
      ValuePackSchema,
      {
        id: 'pack-saas-001',
        pack_id: 'pack-saas-001',
        name: 'SaaS Value Pack',
        industry: 'Technology',
        description: 'Pre-built value drivers for SaaS companies',
        driver_count: 12,
        formula_count: 8,
        benchmark_count: 5,
        workflow_count: 3,
        status: 'active',
        scope: 'global',
        updated_at: '2024-01-15T10:00:00Z',
        version: '2.1.0',
      },
      'ValuePack (full)'
    );
    expect(pack.driver_count).toBeGreaterThanOrEqual(0);
    expect(pack.formula_count).toBeGreaterThanOrEqual(0);
  });

  it('all valid status values are accepted', () => {
    const statuses: z.infer<typeof PackStatusSchema>[] = ['active', 'draft', 'archived', 'published'];
    for (const status of statuses) {
      assertSchema(
        ValuePackSchema,
        {
          id: 'p1', pack_id: 'p1', name: 'Test', industry: 'Tech',
          driver_count: 0, formula_count: 0, benchmark_count: 0, workflow_count: 0,
          status, scope: 'global', updated_at: '2024-01-01T00:00:00Z',
        },
        `ValuePack (${status})`
      );
    }
  });

  it('all valid scope values are accepted', () => {
    const scopes: z.infer<typeof PackScopeSchema>[] = ['global', 'tenant'];
    for (const scope of scopes) {
      assertSchema(
        ValuePackSchema,
        {
          id: 'p1', pack_id: 'p1', name: 'Test', industry: 'Tech',
          driver_count: 0, formula_count: 0, benchmark_count: 0, workflow_count: 0,
          status: 'active', scope, updated_at: '2024-01-01T00:00:00Z',
        },
        `ValuePack (scope=${scope})`
      );
    }
  });

  it('rejects unknown status', () => {
    assertSchemaRejects(
      ValuePackSchema,
      {
        id: 'p1', pack_id: 'p1', name: 'Test', industry: 'Tech',
        driver_count: 0, formula_count: 0, benchmark_count: 0, workflow_count: 0,
        status: 'retired', scope: 'global', updated_at: '2024-01-01T00:00:00Z',
      },
      'ValuePack with unknown status'
    );
  });

  it('rejects negative driver_count', () => {
    assertSchemaRejects(
      ValuePackSchema,
      {
        id: 'p1', pack_id: 'p1', name: 'Test', industry: 'Tech',
        driver_count: -1, formula_count: 0, benchmark_count: 0, workflow_count: 0,
        status: 'active', scope: 'global', updated_at: '2024-01-01T00:00:00Z',
      },
      'ValuePack with negative driver_count'
    );
  });
});

// ── GET /v1/packs with filters ────────────────────────────────────────────────

describe('Contract: GET /v1/packs — filter query params', () => {
  it('documents valid filter parameters', () => {
    // These are the query params the frontend sends; validated here as a
    // living contract document rather than runtime schema.
    const validFilters = {
      industry: 'Technology',
      status: 'active',
      scope: 'global',
      category: 'cost-reduction',
      search: 'SaaS',
    };
    // All values are strings — no coercion needed
    for (const [key, value] of Object.entries(validFilters)) {
      expect(typeof value).toBe('string');
      expect(key).toBeTruthy();
    }
  });
});

// ── POST /v1/packs/{pack_id}/apply ────────────────────────────────────────────

describe('Contract: POST /v1/packs/{pack_id}/apply', () => {
  it('successful apply response has success=true', () => {
    const resp = assertSchema(
      ApplyValuePackResponseSchema,
      {
        success: true,
        message: 'Applied value pack: SaaS Value Pack',
        appliedAt: '2024-01-15T10:00:00Z',
        pack_id: 'pack-saas-001',
        entity_id: 'entity-001',
      },
      'ApplyValuePackResponse (success)'
    );
    expect(resp.success).toBe(true);
  });

  it('failed apply response has success=false', () => {
    const resp = assertSchema(
      ApplyValuePackResponseSchema,
      { success: false, message: 'Pack already applied to this entity' },
      'ApplyValuePackResponse (failure)'
    );
    expect(resp.success).toBe(false);
  });

  it('minimal apply response (only success field) is valid', () => {
    assertSchema(
      ApplyValuePackResponseSchema,
      { success: true },
      'ApplyValuePackResponse (minimal)'
    );
  });
});

// ── POST /v1/packs/{pack_id}/fork ─────────────────────────────────────────────

describe('Contract: POST /v1/packs/{pack_id}/fork', () => {
  it('fork response has new pack_id and forked_from reference', () => {
    const resp = assertSchema(
      ForkValuePackResponseSchema,
      {
        pack_id: 'pack-saas-001-fork',
        name: 'SaaS Value Pack (fork)',
        forked_from: 'pack-saas-001',
        status: 'draft',
      },
      'ForkValuePackResponse'
    );
    expect(resp.forked_from).toBe('pack-saas-001');
    expect(resp.status).toBe('draft');
  });
});

// ── Pagination ────────────────────────────────────────────────────────────────

describe('Contract: GET /v1/packs — pagination', () => {
  it('empty result set is valid', () => {
    const PaginatedPacksSchema = z.object({
      items: z.array(ValuePackSchema),
      total: z.number().int().nonnegative(),
      page: z.number().int().positive(),
      page_size: z.number().int().positive(),
      has_more: z.boolean(),
    });

    const resp = assertSchema(
      PaginatedPacksSchema,
      { items: [], total: 0, page: 1, page_size: 20, has_more: false },
      'PaginatedPacks (empty)'
    );
    expect(resp.has_more).toBe(false);
    expect(resp.total).toBe(0);
  });
});

// ── Tenant context ────────────────────────────────────────────────────────────

describe('Contract: value pack tenant context', () => {
  it('tenant-scoped value pack includes tenant_id', () => {
    const TenantScopedPackSchema = ValuePackSchema.extend({
      tenant_id: z.string().uuid().nullable(),
    });
    const pack = assertSchema(
      TenantScopedPackSchema,
      {
        id: 'pack-saas-001',
        pack_id: 'pack-saas-001',
        name: 'SaaS Value Pack',
        industry: 'Technology',
        description: 'Pre-built value drivers for SaaS companies',
        driver_count: 12,
        formula_count: 8,
        benchmark_count: 5,
        workflow_count: 3,
        status: 'active',
        scope: 'tenant',
        updated_at: '2024-01-15T10:00:00Z',
        version: '2.1.0',
        tenant_id: '550e8400-e29b-41d4-a716-446655440000',
      },
      'TenantScopedValuePack'
    );
    expect(pack.tenant_id).toBe('550e8400-e29b-41d4-a716-446655440000');
    expect(pack.scope).toBe('tenant');
  });
});

// ── Auth failures ─────────────────────────────────────────────────────────────

describe('Contract: value pack auth failures', () => {
  it('401 matches ApiError shape', () => {
    assertSchema(
      ApiErrorSchema,
      { error: { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', request_id: 'trace-pack-401' } },
      'ApiError (401)'
    );
  });

  it('403 cross-tenant pack access matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Value pack does not belong to your tenant', code: 'AUTHORIZATION_ERROR', request_id: 'trace-pack-403' } },
      'ApiError (403 cross-tenant)'
    );
    expect(err.error.code).toBe('AUTHORIZATION_ERROR');
    expect(err.error.request_id).toBeTruthy();
  });

  it('pack not found 404 matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Value pack not found', code: 'NOT_FOUND', request_id: 'trace-pack-404' } },
      'ApiError (404)'
    );
    expect(err.error.code).toBe('NOT_FOUND');
  });
});
