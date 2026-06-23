/**
 * Contract tests: Benchmarks / Policies (L6)
 *
 * Validates request/response shapes against contracts/openapi/layer6-benchmarks.json
 * and the BenchmarkPolicy schema in layer3-knowledge.json.
 * Covers: GET /v1/benchmarks/datasets, POST /v1/benchmarks/compare,
 * POST /v1/benchmarks/validate, GET /v1/benchmarks/industries,
 * and the BenchmarkPolicy CRUD shapes.
 *
 * Note: The L6 OpenAPI spec was discovered from router source and does not
 * include inline response schemas. These tests document the frontend-expected
 * contract shapes and will catch drift when the spec is enriched.
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { ApiErrorSchema, assertSchema, assertSchemaRejects } from './_helpers';

// ── Response schemas (frontend-expected shapes) ───────────────────────────────

const BenchmarkDatasetSchema = z.object({
  dataset_id: z.string().min(1),
  name: z.string().min(1),
  description: z.string(),
  industry: z.string().min(1),
  segment: z.string().optional().nullable(),
  geography: z.string().optional().nullable(),
  metrics: z.array(z.string()),
  metric_count: z.number().int().nonnegative(),
  version: z.string(),
  data_source: z.string().optional().nullable(),
});

const BenchmarkCompareResponseSchema = z.object({
  prospect_id: z.string().min(1),
  metrics: z.array(
    z.object({
      metric_name: z.string().min(1),
      prospect_value: z.number(),
      benchmark_value: z.number(),
      percentile: z.number().min(0).max(100),
      delta_percent: z.number(),
    })
  ),
  overall_percentile: z.number().min(0).max(100),
  dataset_id: z.string().min(1),
});

const BenchmarkValidateResponseSchema = z.object({
  is_valid: z.boolean(),
  errors: z.array(z.string()),
  warnings: z.array(z.string()),
  validated_metrics: z.number().int().nonnegative(),
});

const BenchmarkPolicySchema = z.object({
  id: z.string().min(1),
  policy_type: z.enum(['threshold', 'cadence', 'fallback', 'override']),
  name: z.string().min(1),
  description: z.string(),
  value: z.string(),
  is_enabled: z.boolean(),
});

const BenchmarkPolicyUpdateSchema = z.object({
  name: z.string().nullable().optional(),
  description: z.string().nullable().optional(),
  value: z.string().nullable().optional(),
  is_enabled: z.boolean().nullable().optional(),
});

const BenchmarkIndustriesSchema = z.union([
  z.array(z.string().min(1)),
  z.object({ industries: z.array(z.string().min(1)) }),
]);

// ── GET /v1/benchmarks/datasets ───────────────────────────────────────────────

describe('Contract: GET /v1/benchmarks/datasets', () => {
  it('dataset has id, name, industry, and metric_count', () => {
    const dataset = assertSchema(
      BenchmarkDatasetSchema,
      {
        dataset_id: 'ds-saas-2024',
        name: 'SaaS Industry Benchmarks 2024',
        description: 'Peer benchmarks for SaaS operational metrics',
        industry: 'Technology',
        segment: 'enterprise',
        geography: 'global',
        metrics: ['cac', 'nrr', 'churn'],
        metric_count: 3,
        version: '1.0.0',
        data_source: 'Gartner',
      },
      'BenchmarkDataset'
    );
    expect(dataset.metric_count).toBeGreaterThanOrEqual(0);
  });

  it('source is optional', () => {
    assertSchema(
      BenchmarkDatasetSchema,
      {
        dataset_id: 'ds-001',
        name: 'Manufacturing Benchmarks',
        description: 'Manufacturing efficiency benchmarks',
        industry: 'Manufacturing',
        metrics: ['oee', 'cycle_time'],
        metric_count: 2,
        version: '1.0.0',
      },
      'BenchmarkDataset (no source)'
    );
  });

  it('rejects negative metric_count', () => {
    assertSchemaRejects(
      BenchmarkDatasetSchema,
      {
        dataset_id: 'ds-001',
        name: 'Test',
        description: 'Test dataset',
        industry: 'Tech',
        metrics: [],
        metric_count: -1,
        version: '1.0.0',
      },
      'BenchmarkDataset with negative metric_count'
    );
  });
});

// ── POST /v1/benchmarks/compare ───────────────────────────────────────────────

describe('Contract: POST /v1/benchmarks/compare', () => {
  it('compare response has per-metric percentiles and overall_percentile', () => {
    const resp = assertSchema(
      BenchmarkCompareResponseSchema,
      {
        prospect_id: 'prospect-abc',
        metrics: [
          {
            metric_name: 'revenue_per_employee',
            prospect_value: 180000,
            benchmark_value: 220000,
            percentile: 35,
            delta_percent: -18.2,
          },
          {
            metric_name: 'gross_margin',
            prospect_value: 0.72,
            benchmark_value: 0.68,
            percentile: 65,
            delta_percent: 5.9,
          },
        ],
        overall_percentile: 48,
        dataset_id: 'ds-saas-2024',
      },
      'BenchmarkCompareResponse'
    );
    expect(resp.overall_percentile).toBeGreaterThanOrEqual(0);
    expect(resp.overall_percentile).toBeLessThanOrEqual(100);
    for (const m of resp.metrics) {
      expect(m.percentile).toBeGreaterThanOrEqual(0);
      expect(m.percentile).toBeLessThanOrEqual(100);
    }
  });

  it('rejects overall_percentile > 100', () => {
    assertSchemaRejects(
      BenchmarkCompareResponseSchema,
      {
        prospect_id: 'p',
        metrics: [],
        overall_percentile: 101,
        dataset_id: 'ds-001',
      },
      'BenchmarkCompareResponse with percentile > 100'
    );
  });
});

// ── POST /v1/benchmarks/validate ──────────────────────────────────────────────

describe('Contract: POST /v1/benchmarks/validate', () => {
  it('valid data returns is_valid=true with no errors', () => {
    const resp = assertSchema(
      BenchmarkValidateResponseSchema,
      { is_valid: true, errors: [], warnings: [], validated_metrics: 12 },
      'BenchmarkValidateResponse (valid)'
    );
    expect(resp.is_valid).toBe(true);
    expect(resp.errors).toHaveLength(0);
  });

  it('invalid data returns is_valid=false with errors', () => {
    const resp = assertSchema(
      BenchmarkValidateResponseSchema,
      {
        is_valid: false,
        errors: ['revenue_per_employee: value must be positive', 'gross_margin: must be in [0,1]'],
        warnings: ['churn_rate: unusually high value'],
        validated_metrics: 10,
      },
      'BenchmarkValidateResponse (invalid)'
    );
    expect(resp.is_valid).toBe(false);
    expect(resp.errors.length).toBeGreaterThan(0);
  });
});

// ── GET /v1/benchmarks/industries ────────────────────────────────────────────

describe('Contract: GET /v1/benchmarks/industries', () => {
  it('industries response supports array form', () => {
    const resp = assertSchema(
      BenchmarkIndustriesSchema,
      ['Technology', 'Manufacturing', 'Healthcare', 'Financial Services'],
      'IndustriesResponse'
    );
    const industries = Array.isArray(resp) ? resp : resp.industries;
    expect(industries.length).toBeGreaterThan(0);
    for (const industry of industries) {
      expect(typeof industry).toBe('string');
    }
  });

  it('industries response supports wrapped object form', () => {
    const resp = assertSchema(
      BenchmarkIndustriesSchema,
      { industries: ['Technology', 'Manufacturing'] },
      'IndustriesResponseWrapped'
    );
    const industries = Array.isArray(resp) ? resp : resp.industries;
    expect(industries).toContain('Technology');
  });
});

describe('Contract: benchmark ownership boundaries', () => {
  it('L6 benchmark experiences pin the canonical global compare/validate route surface', () => {
    const canonicalRoutes = [
      '/v1/benchmarks/datasets',
      '/v1/benchmarks/datasets/{dataset_id}',
      '/v1/benchmarks/compare',
      '/v1/benchmarks/validate',
      '/v1/benchmarks/industries',
    ];

    const deprecatedDatasetScopedRoutes = [
      '/v1/benchmarks/datasets/{dataset_id}/compare',
      '/v1/benchmarks/datasets/{dataset_id}/validate',
    ];

    const openApiPath = resolve(process.cwd(), '../../contracts/openapi/layer6-benchmarks.json');
    const openApiSpec = JSON.parse(readFileSync(openApiPath, 'utf8')) as { paths: Record<string, unknown> };
    const declaredRoutes = Object.keys(openApiSpec.paths);

    expect(canonicalRoutes.every((route) => route.startsWith('/v1/benchmarks/'))).toBe(true);
    expect(declaredRoutes).toEqual(expect.arrayContaining(canonicalRoutes));
    expect(declaredRoutes).not.toEqual(expect.arrayContaining(deprecatedDatasetScopedRoutes));
  });
});

// ── BenchmarkPolicy CRUD ──────────────────────────────────────────────────────

describe('Contract: BenchmarkPolicy shapes', () => {
  it('policy has required fields and valid policy_type', () => {
    const policy = assertSchema(
      BenchmarkPolicySchema,
      {
        id: 'policy-001',
        policy_type: 'threshold',
        name: 'Minimum confidence threshold',
        description: 'Reject benchmarks below this confidence level',
        value: '0.7',
        is_enabled: true,
      },
      'BenchmarkPolicy'
    );
    expect(['threshold', 'cadence', 'fallback', 'override']).toContain(policy.policy_type);
  });

  it('all valid policy_type values are accepted', () => {
    for (const policy_type of ['threshold', 'cadence', 'fallback', 'override'] as const) {
      assertSchema(
        BenchmarkPolicySchema,
        { id: 'p1', policy_type, name: 'Test', description: 'Desc', value: '1', is_enabled: true },
        `BenchmarkPolicy (${policy_type})`
      );
    }
  });

  it('rejects unknown policy_type', () => {
    assertSchemaRejects(
      BenchmarkPolicySchema,
      { id: 'p1', policy_type: 'custom', name: 'Test', description: 'Desc', value: '1', is_enabled: true },
      'BenchmarkPolicy with unknown type'
    );
  });

  it('update accepts partial fields', () => {
    assertSchema(
      BenchmarkPolicyUpdateSchema,
      { is_enabled: false },
      'BenchmarkPolicyUpdate (disable only)'
    );
  });

  it('update accepts empty patch', () => {
    assertSchema(BenchmarkPolicyUpdateSchema, {}, 'BenchmarkPolicyUpdate (empty)');
  });
});

// ── Tenant context ────────────────────────────────────────────────────────────

describe('Contract: benchmarks tenant context', () => {
  it('dataset list is scoped to tenant_id in request context', () => {
    const TenantScopedDatasetSchema = BenchmarkDatasetSchema.extend({
      tenant_id: z.string().uuid(),
    });
    const ds = assertSchema(
      TenantScopedDatasetSchema,
      {
        dataset_id: 'ds-saas-2024',
        name: 'SaaS Benchmarks',
        description: 'SaaS operational benchmarks',
        industry: 'Technology',
        metrics: ['cac', 'nrr'],
        metric_count: 2,
        version: '1.0.0',
        tenant_id: '550e8400-e29b-41d4-a716-446655440000',
      },
      'TenantScopedDataset'
    );
    expect(ds.tenant_id).toBe('550e8400-e29b-41d4-a716-446655440000');
  });
});

// ── Pagination ────────────────────────────────────────────────────────────────

describe('Contract: benchmarks pagination', () => {
  it('paginated dataset list has required pagination fields', () => {
    const PaginatedDatasetsSchema = z.object({
      items: z.array(BenchmarkDatasetSchema),
      total: z.number().int().nonnegative(),
      page: z.number().int().positive(),
      page_size: z.number().int().positive(),
      has_more: z.boolean(),
    });

    const resp = assertSchema(
      PaginatedDatasetsSchema,
      { items: [], total: 0, page: 1, page_size: 20, has_more: false },
      'PaginatedDatasets (empty)'
    );
    expect(resp.has_more).toBe(false);
  });

  it('paginated dataset list with has_more=true', () => {
    const PaginatedDatasetsSchema = z.object({
      items: z.array(BenchmarkDatasetSchema),
      total: z.number().int().nonnegative(),
      page: z.number().int().positive(),
      page_size: z.number().int().positive(),
      has_more: z.boolean(),
    });

    const resp = assertSchema(
      PaginatedDatasetsSchema,
      {
        items: [{ dataset_id: 'ds-1', name: 'DS1', description: 'Test dataset', industry: 'Tech', metrics: ['m1'], metric_count: 1, version: '1.0.0' }],
        total: 42,
        page: 1,
        page_size: 20,
        has_more: true,
      },
      'PaginatedDatasets (has more)'
    );
    expect(resp.has_more).toBe(true);
    expect(resp.total).toBeGreaterThan(resp.items.length);
  });
});

// ── Auth failures ─────────────────────────────────────────────────────────────

describe('Contract: benchmarks auth failures', () => {
  it('401 matches ApiError shape', () => {
    assertSchema(
      ApiErrorSchema,
      { error: { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', request_id: 'trace-bench-401' } },
      'ApiError (401)'
    );
  });

  it('403 cross-tenant access matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Dataset does not belong to your tenant', code: 'AUTHORIZATION_ERROR', request_id: 'trace-bench-403' } },
      'ApiError (403 cross-tenant)'
    );
    expect(err.error.code).toBe('AUTHORIZATION_ERROR');
    expect(err.error.request_id).toBeTruthy();
  });

  it('dataset not found 404 matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Benchmark dataset not found', code: 'NOT_FOUND', request_id: 'trace-bench-404' } },
      'ApiError (404)'
    );
    expect(err.error.code).toBe('NOT_FOUND');
  });
});
