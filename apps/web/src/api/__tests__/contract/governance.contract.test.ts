/**
 * Contract tests: Governance / Admin / Settings (L4)
 *
 * Validates shapes for tenant management and feature-flag endpoints against
 * contracts/openapi/layer4-agents.json (TenantModel, TenantCreateRequest,
 * FeatureFlagResponse, FeatureFlagUpsertRequest).
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import {
  TenantModelSchema,
  FeatureFlagResponseSchema,
  ApiErrorSchema,
  assertSchema,
  assertSchemaRejects,
  fixtures,
} from './_helpers';

// ── Local request schemas ────────────────────────────────────────────────────

const TenantCreateRequestSchema = z.object({
  name: z.string().min(1).max(200),
  slug: z.string().min(1).max(63).regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
  settings: z.record(z.string(), z.unknown()).optional(),
});

const TenantUpdateRequestSchema = z.object({
  name: z.string().min(1).max(200).nullable().optional(),
  status: z.enum(['active', 'suspended', 'deleted']).nullable().optional(),
});

const FeatureFlagUpsertRequestSchema = z.object({
  enabled: z.boolean(),
  rollout_percentage: z.number().int().min(0).max(100),
  description: z.string().nullable().optional(),
  metadata: z.record(z.string(), z.unknown()).nullable().optional(),
});


const ComplianceStatusEnumSchema = z.enum(["compliant", "in_progress", "non_compliant", "expired", "not_applicable"]);

const ComplianceFrameworkStatusSchema = z.object({
  framework: z.string().min(1),
  status: ComplianceStatusEnumSchema,
  control_coverage_percent: z.number().min(0).max(100),
  exceptions_count: z.number().int().nonnegative(),
  effective_date: z.string().datetime().optional(),
  next_review_date: z.string().datetime().optional(),
  attestation_expires_at: z.string().datetime().optional(),
  owner: z.string().min(1).optional(),
  evidence_references: z.array(
    z.object({
      id: z.string().min(1).optional(),
      label: z.string().min(1),
      url: z.string().url().optional(),
    })
  ),
});

const ComplianceStatusResponseSchema = z.object({
  items: z.array(ComplianceFrameworkStatusSchema),
  updated_at: z.string().datetime().optional(),
  updated_by: z.string().min(1).optional(),
});
// ── POST /v1/tenants ─────────────────────────────────────────────────────────

describe('Contract: POST /v1/tenants', () => {
  it('accepts a valid create request', () => {
    assertSchema(
      TenantCreateRequestSchema,
      { name: 'Acme Corp', slug: 'acme-corp' },
      'TenantCreateRequest'
    );
  });

  it('accepts optional settings object', () => {
    assertSchema(
      TenantCreateRequestSchema,
      { name: 'Acme Corp', slug: 'acme-corp', settings: { timezone: 'UTC', locale: 'en-US' } },
      'TenantCreateRequest (with settings)'
    );
  });

  it('rejects slug with uppercase letters', () => {
    assertSchemaRejects(
      TenantCreateRequestSchema,
      { name: 'Acme', slug: 'Acme-Corp' },
      'TenantCreateRequest with uppercase slug'
    );
  });

  it('rejects slug with spaces', () => {
    assertSchemaRejects(
      TenantCreateRequestSchema,
      { name: 'Acme', slug: 'acme corp' },
      'TenantCreateRequest with space in slug'
    );
  });

  it('rejects name exceeding 200 characters', () => {
    assertSchemaRejects(
      TenantCreateRequestSchema,
      { name: 'a'.repeat(201), slug: 'acme' },
      'TenantCreateRequest with name > 200 chars'
    );
  });
});

// ── GET /v1/tenants/{tenant_id} ──────────────────────────────────────────────

describe('Contract: GET /v1/tenants/{tenant_id}', () => {
  it('response matches TenantModel shape', () => {
    const tenant = assertSchema(TenantModelSchema, fixtures.tenant(), 'TenantModel');
    expect(tenant.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
    expect(tenant.slug).toMatch(/^[a-z0-9]+(?:-[a-z0-9]+)*$/);
  });

  it('all valid status values are accepted', () => {
    for (const status of ['active', 'suspended', 'deleted'] as const) {
      assertSchema(
        TenantModelSchema,
        { ...fixtures.tenant(), status },
        `TenantModel (${status})`
      );
    }
  });

  it('rejects unknown status', () => {
    assertSchemaRejects(
      TenantModelSchema,
      { ...fixtures.tenant(), status: 'pending' },
      'TenantModel with unknown status'
    );
  });

  it('rejects invalid UUID for id', () => {
    assertSchemaRejects(
      TenantModelSchema,
      { ...fixtures.tenant(), id: 'not-a-uuid' },
      'TenantModel with non-UUID id'
    );
  });
});

// ── PATCH /v1/tenants/{tenant_id} ────────────────────────────────────────────

describe('Contract: PATCH /v1/tenants/{tenant_id}', () => {
  it('accepts partial update with name only', () => {
    assertSchema(
      TenantUpdateRequestSchema,
      { name: 'Acme Corporation' },
      'TenantUpdateRequest (name only)'
    );
  });

  it('accepts status change to suspended', () => {
    assertSchema(
      TenantUpdateRequestSchema,
      { status: 'suspended' },
      'TenantUpdateRequest (suspend)'
    );
  });

  it('accepts empty patch (no-op)', () => {
    assertSchema(TenantUpdateRequestSchema, {}, 'TenantUpdateRequest (empty)');
  });
});

// ── GET /v1/feature-flags ────────────────────────────────────────────────────

describe('Contract: GET /v1/feature-flags', () => {
  it('individual flag matches FeatureFlagResponse shape', () => {
    const flag = assertSchema(
      FeatureFlagResponseSchema,
      fixtures.featureFlag(),
      'FeatureFlagResponse'
    );
    expect(flag.flag_key).toBeTruthy();
    expect(typeof flag.enabled).toBe('boolean');
    expect(flag.rollout_percentage).toBeGreaterThanOrEqual(0);
    expect(flag.rollout_percentage).toBeLessThanOrEqual(100);
  });

  it('global flag has null tenant_id', () => {
    const flag = assertSchema(
      FeatureFlagResponseSchema,
      { ...fixtures.featureFlag(), tenant_id: null },
      'FeatureFlagResponse (global)'
    );
    expect(flag.tenant_id).toBeNull();
  });

  it('rejects rollout_percentage > 100', () => {
    assertSchemaRejects(
      FeatureFlagResponseSchema,
      { ...fixtures.featureFlag(), rollout_percentage: 101 },
      'FeatureFlagResponse with rollout > 100'
    );
  });

  it('rejects rollout_percentage < 0', () => {
    assertSchemaRejects(
      FeatureFlagResponseSchema,
      { ...fixtures.featureFlag(), rollout_percentage: -1 },
      'FeatureFlagResponse with rollout < 0'
    );
  });
});

// ── PUT /v1/feature-flags/{flag_key} ─────────────────────────────────────────

describe('Contract: PUT /v1/feature-flags/{flag_key}', () => {
  it('accepts a valid upsert request', () => {
    assertSchema(
      FeatureFlagUpsertRequestSchema,
      { enabled: true, rollout_percentage: 50, description: 'Gradual rollout' },
      'FeatureFlagUpsertRequest'
    );
  });

  it('accepts minimal upsert (no description)', () => {
    assertSchema(
      FeatureFlagUpsertRequestSchema,
      { enabled: false, rollout_percentage: 0 },
      'FeatureFlagUpsertRequest (minimal)'
    );
  });

  it('rejects non-integer rollout_percentage', () => {
    assertSchemaRejects(
      FeatureFlagUpsertRequestSchema,
      { enabled: true, rollout_percentage: 50.5 },
      'FeatureFlagUpsertRequest with float percentage'
    );
  });
});


// ── GET /v1/governance/compliance/status ─────────────────────────────────────

describe('Contract: GET /v1/governance/compliance/status', () => {
  it('accepts a typed compliance status payload', () => {
    const payload = assertSchema(
      ComplianceStatusResponseSchema,
      {
        items: [
          {
            framework: 'SOC 2 Type II',
            status: 'compliant',
            control_coverage_percent: 98.4,
            exceptions_count: 2,
            effective_date: '2026-01-10T00:00:00Z',
            next_review_date: '2026-07-10T00:00:00Z',
            attestation_expires_at: '2027-01-10T00:00:00Z',
            owner: 'governance@acme.com',
            evidence_references: [{ id: 'att-2026', label: 'SOC2 report', url: 'https://evidence.example/soc2' }],
          },
        ],
        updated_at: '2026-05-22T16:00:00Z',
        updated_by: 'governance-agent',
      },
      'ComplianceStatusResponse'
    );

    expect(payload.items[0].framework).toBe('SOC 2 Type II');
  });

  it('rejects out-of-range control coverage percent', () => {
    assertSchemaRejects(
      ComplianceStatusResponseSchema,
      {
        items: [{
          framework: 'HIPAA',
          status: 'in_progress',
          control_coverage_percent: 120,
          exceptions_count: 0,
          evidence_references: [],
        }],
      },
      'ComplianceStatusResponse with invalid coverage'
    );
  });
});

// ── Tenant context ────────────────────────────────────────────────────────────

describe('Contract: governance tenant context', () => {
  it('tenant model includes tenant_id as UUID', () => {
    const tenant = assertSchema(TenantModelSchema, fixtures.tenant(), 'TenantModel');
    expect(tenant.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    );
  });

  it('feature flag tenant_id can be null for global flags', () => {
    const flag = assertSchema(
      FeatureFlagResponseSchema,
      { ...fixtures.featureFlag(), tenant_id: null },
      'FeatureFlagResponse (global)'
    );
    expect(flag.tenant_id).toBeNull();
  });

  it('cross-tenant tenant fetch is rejected', () => {
    assertSchemaRejects(
      TenantModelSchema,
      { ...fixtures.tenant(), id: 'not-a-uuid' },
      'TenantModel with invalid UUID'
    );
  });
});

// ── Pagination ────────────────────────────────────────────────────────────────

describe('Contract: tenant list pagination', () => {
  it('paginated tenant list has required pagination fields', () => {
    const PaginatedTenantSchema = z.object({
      items: z.array(TenantModelSchema),
      total: z.number().int().nonnegative(),
      page: z.number().int().positive(),
      page_size: z.number().int().positive(),
      has_more: z.boolean(),
    });

    const resp = assertSchema(
      PaginatedTenantSchema,
      { items: [], total: 0, page: 1, page_size: 20, has_more: false },
      'PaginatedTenants (empty)'
    );
    expect(resp.has_more).toBe(false);
  });
});

// ── Auth failures ─────────────────────────────────────────────────────────────

describe('Contract: governance auth failures', () => {
  it('401 matches ApiError shape', () => {
    assertSchema(
      ApiErrorSchema,
      { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', trace_id: 'trace-gov-401' },
      'ApiError (401 governance)'
    );
  });

  it('non-admin 403 matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { message: 'super_admin role required', code: 'AUTHORIZATION_ERROR', trace_id: 'trace-gov-403' },
      'ApiError (403 governance)'
    );
    expect(err.code).toBe('AUTHORIZATION_ERROR');
    expect(err.trace_id).toBeTruthy();
  });

  it('tenant not found 404 matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { message: 'Tenant not found', code: 'NOT_FOUND', trace_id: 'trace-gov-404' },
      'ApiError (404 tenant)'
    );
    expect(err.message).toBeTruthy();
  });
});
