/**
 * OpenAPI Drift Detection Suite
 *
 * Validates that every hand-written Zod schema in _helpers.ts stays in sync
 * with its canonical checked-in OpenAPI JSON Schema definition. If a Zod
 * schema becomes looser or stricter than the OpenAPI contract, this suite
 * surfaces the mismatch with field-level detail.
 *
 * Run: pnpm run test:contracts
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  OPENAPI_SCHEMA_MAP,
  DRIFT_TRACKED_SCHEMAS,
  assertOpenApiSchema,
  assertOpenApiSchemaRejects,
} from './openapi-validator';
import {
  ExtractResponseSchema,
  ExtractionStatusSchema,
  GraphNodeSchema,
  SubgraphResponseSchema,
  FormulaEvaluateResponseSchema,
  PackSummarySchema,
  WorkflowCreateResponseSchema,
  WorkflowStatusResponseSchema,
  TenantModelSchema,
  FeatureFlagResponseSchema,
  TruthObjectResponseSchema,
  TruthObjectListResponseSchema,
  ApiErrorSchema,
  fixtures,
  assertCanonicalSchema,
  assertSchema,
  assertSchemaRejects,
} from './_helpers';



// ---------------------------------------------------------------------------
// Drift detection — every tracked schema must accept its canonical fixture
// ---------------------------------------------------------------------------

describe('OpenAPI drift: tracked schemas have canonical mappings', () => {
  it('every entry in OPENAPI_SCHEMA_MAP resolves to a real schema file', () => {
    for (const [name, mapping] of Object.entries(OPENAPI_SCHEMA_MAP)) {
      expect(mapping.specFile).toMatch(/\.json$/);
      expect(mapping.ref).toMatch(/^#\/components\/schemas\//);
      expect(mapping.description).toBeTruthy();
    }
  });

  it('DRIFT_TRACKED_SCHEMAS matches OPENAPI_SCHEMA_MAP keys', () => {
    const mapKeys = Object.keys(OPENAPI_SCHEMA_MAP).sort();
    const tracked = [...DRIFT_TRACKED_SCHEMAS].sort();
    expect(tracked).toEqual(mapKeys);
  });

  it('checked-in OpenAPI fixtures keep expected base-path version prefixes', () => {
    const expectedPrefixes: Record<string, Array<`/${string}`>> = {
      'layer1-ingestion.json': ['/api/v1', '/api', '/v1', '/health', '/ready', '/metrics'],
      'layer2-extraction.json': ['/v1', '/health', '/ready', '/metrics'],
      'layer3-knowledge.json': ['/v1', '/health', '/ready', '/metrics', '/graph', '/entities'],
      'layer4-agents.json': ['/v1', '/', '/health', '/ready', '/metrics', '/auth'],
      'layer5-ground-truth.json': ['/api/v1', '/health', '/ready', '/metrics'],
      // Layer 6 keeps a temporary deprecated readiness alias for backward compatibility.
      'layer6-benchmarks.json': ['/v1', '/health', '/ready', '/readiness', '/metrics'],
    };

    for (const [specFile, allowedPrefixes] of Object.entries(expectedPrefixes)) {
      const absolutePath = resolve(CONTRACTS_OPENAPI_DIR, specFile);
      const spec = JSON.parse(readFileSync(absolutePath, 'utf-8')) as { paths: Record<string, unknown> };
      const paths = Object.keys(spec.paths ?? {});
      expect(paths.length).toBeGreaterThan(0);

      for (const routePath of paths) {
        const allowed = allowedPrefixes.some((prefix) => (
          prefix === '/'
            ? routePath === '/'
            : routePath === prefix || routePath.startsWith(`${prefix}/`)
        ));
        expect(allowed, `${specFile} path ${routePath} must match one of: ${allowedPrefixes.join(', ')}`).toBe(true);
      }
    }
  });
});

// ---------------------------------------------------------------------------
// L2 Extraction fixtures against OpenAPI
// ---------------------------------------------------------------------------

describe('OpenAPI drift: L2 Extraction', () => {
  it('ExtractResponse fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer2-extraction.json',
      '#/components/schemas/ExtractResponse',
      fixtures.extractResponse(),
      'ExtractResponse'
    );
  });

  it('ExtractionStatus (completed) fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer2-extraction.json',
      '#/components/schemas/ExtractionStatusResponse',
      fixtures.extractionStatus(),
      'ExtractionStatus (completed)'
    );
  });

  it('ExtractionStatus (failed) fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer2-extraction.json',
      '#/components/schemas/ExtractionStatusResponse',
      fixtures.extractionStatus({
        overall_status: 'failed',
        extraction_status: 'failed',
        ingestion_status: 'skipped',
        last_error: 'timeout',
      }),
      'ExtractionStatus (failed)'
    );
  });
});

// ---------------------------------------------------------------------------
// L3 Knowledge Graph fixtures against OpenAPI
// ---------------------------------------------------------------------------

describe('OpenAPI drift: L3 Knowledge Graph', () => {
  it('GraphNode fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer3-knowledge.json',
      '#/components/schemas/GraphNode',
      fixtures.graphNode(),
      'GraphNode'
    );
  });

  it('SubgraphResponse fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer3-knowledge.json',
      '#/components/schemas/SubgraphResponse',
      {
        root_entity_id: 'node-001',
        nodes: [fixtures.graphNode()],
        edges: [],
        depth: 2,
        stats: { total_nodes: 1, total_edges: 0, density: 0 },
      },
      'SubgraphResponse'
    );
  });

  it('FormulaEvaluateResponse fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer3-knowledge.json',
      '#/components/schemas/FormulaEvaluateResponse',
      {
        result: 150,
        unit: 'percent',
        confidence: 0.92,
        calculation_steps: [
          { step: 1, operation: 'a+b', result: '150' },
        ],
        formula_used: 'roi_v2',
      },
      'FormulaEvaluateResponse'
    );
  });

  it('PackSummary fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer3-knowledge.json',
      '#/components/schemas/PackSummary',
      fixtures.packSummary(),
      'PackSummary'
    );
  });
});

// ---------------------------------------------------------------------------
// L4 Agents / Workflows / Governance fixtures against OpenAPI
// ---------------------------------------------------------------------------

describe('OpenAPI drift: L4 Agents', () => {
  it('WorkflowCreateResponse fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer4-agents.json',
      '#/components/schemas/WorkflowCreateResponse',
      fixtures.workflowCreateResponse(),
      'WorkflowCreateResponse'
    );
  });

  it('WorkflowStatusResponse (running) fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer4-agents.json',
      '#/components/schemas/WorkflowStatusResponse',
      fixtures.workflowStatus(),
      'WorkflowStatusResponse (running)'
    );
  });

  it('TenantModel fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer4-agents.json',
      '#/components/schemas/TenantModel',
      fixtures.tenant(),
      'TenantModel'
    );
  });

  it('FeatureFlagResponse fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer4-agents.json',
      '#/components/schemas/FeatureFlagResponse',
      fixtures.featureFlag(),
      'FeatureFlagResponse'
    );
  });
});

// ---------------------------------------------------------------------------
// L5 Ground Truth fixtures against OpenAPI
// ---------------------------------------------------------------------------

describe('OpenAPI drift: L5 Ground Truth', () => {
  it('TruthObjectResponse fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer5-ground-truth.json',
      '#/components/schemas/TruthObjectResponse',
      fixtures.truthObject(),
      'TruthObjectResponse'
    );
  });

  it('TruthObjectListResponse fixture passes canonical OpenAPI schema', () => {
    assertOpenApiSchema(
      'layer5-ground-truth.json',
      '#/components/schemas/TruthObjectListResponse',
      {
        items: [fixtures.truthObjectSummary()],
        total: 1,
        limit: 20,
        offset: 0,
        has_more: false,
      },
      'TruthObjectListResponse'
    );
  });
});

// ---------------------------------------------------------------------------
// Negative-path drift: Zod must be at least as strict as OpenAPI
// ---------------------------------------------------------------------------

describe('OpenAPI drift: negative-path consistency', () => {
  it('Zod rejects invalid UUID where OpenAPI also rejects it', () => {
    const bad = { ...fixtures.tenant(), id: 'not-a-uuid' };
    assertSchemaRejects(TenantModelSchema, bad, 'TenantModel bad UUID');
    assertOpenApiSchemaRejects(
      'layer4-agents.json',
      '#/components/schemas/TenantModel',
      bad,
      'TenantModel bad UUID (OpenAPI)'
    );
  });

  it('Zod and OpenAPI both reject out-of-range confidence', () => {
    const bad = { ...fixtures.truthObject(), confidence: 1.5 };
    assertSchemaRejects(TruthObjectResponseSchema, bad, 'TruthObject confidence > 1');
    assertOpenApiSchemaRejects(
      'layer5-ground-truth.json',
      '#/components/schemas/TruthObjectResponse',
      bad,
      'TruthObject confidence > 1 (OpenAPI)'
    );
  });

  it('Zod and OpenAPI both reject unknown workflow status', () => {
    const bad = fixtures.workflowStatus({ status: 'bogus' as 'running' });
    assertSchemaRejects(WorkflowStatusResponseSchema, bad, 'WorkflowStatus unknown enum');
    assertOpenApiSchemaRejects(
      'layer4-agents.json',
      '#/components/schemas/WorkflowStatusResponse',
      bad,
      'WorkflowStatus unknown enum (OpenAPI)'
    );
  });
});

// ---------------------------------------------------------------------------
// Common error shapes
// ── Auth failures ─────────────────────────────────────────────────────────────

describe('Contract: drift-detection auth failures', () => {
  it('401 matches ApiError shape', () => {
    assertSchema(ApiErrorSchema, { error: { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', request_id: 'trace-drift-401' } }, 'ApiError (401)');
  });

  it('403 forbidden matches ApiError shape', () => {
    assertSchema(ApiErrorSchema, { error: { message: 'Access denied', code: 'AUTHORIZATION_ERROR', request_id: 'trace-drift-403' } }, 'ApiError (403)');
  });
});

// ── Common error shapes ───────────────────────────────────────────────────────

describe('OpenAPI drift: common error shapes', () => {
  it('ApiError fixture is compatible with canonical ErrorResponse', () => {
    const frontendError = { error: { message: 'Bad request', code: 'VALIDATION_ERROR', request_id: 'abc' } };
    // layer2-extraction.json defines the canonical ErrorEnvelope that matches frontend ApiErrorSchema.
    assertCanonicalSchema(ApiErrorSchema, 'layer2-extraction.json', '#/components/schemas/ErrorResponse', frontendError, 'frontend ApiError');
  });
});
const CONTRACTS_OPENAPI_DIR = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../../../../../contracts/openapi'
);
const LAYER4_ROUTE_CONTRACT_MATRIX_PATH = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../../../../../contracts/layer4-route-contract-matrix.json'
);

describe('OpenAPI drift: layer4 route contract matrix coverage', () => {
  it('covers launched intelligence and workspace flows with backend route ownership', () => {
    const matrix = JSON.parse(readFileSync(LAYER4_ROUTE_CONTRACT_MATRIX_PATH, 'utf-8')) as {
      entries: Array<{
        openapi_path: string;
        method: string;
        backend_route_files?: string[];
      }>;
    };

    const expectedRoutes = [
      { method: 'GET', path: '/v1/intelligence/account/{account_id}/briefing' },
      { method: 'GET', path: '/v1/intelligence/account/{account_id}/deal-readiness' },
      { method: 'GET', path: '/v1/intelligence/pipeline-summary' },
      { method: 'GET', path: '/v1/cases/{case_id}/workspace/evidence' },
      { method: 'GET', path: '/v1/cases/{case_id}/workspace/{tab_key}' },
      { method: 'PUT', path: '/v1/cases/{case_id}/workspace/{tab_key}' },
      { method: 'POST', path: '/v1/cases/{case_id}/workspace/generate' },
    ] as const;

    for (const route of expectedRoutes) {
      const entry = matrix.entries.find((candidate) => (
        candidate.method === route.method && candidate.openapi_path === route.path
      ));
      expect(entry, `Missing matrix entry for ${route.method} ${route.path}`).toBeTruthy();
      expect(
        entry?.backend_route_files?.length ?? 0,
        `Missing backend route ownership for ${route.method} ${route.path}`
      ).toBeGreaterThan(0);
    }
  });
});
