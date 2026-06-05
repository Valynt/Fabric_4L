/**
 * OpenAPI-backed runtime schema validator for frontend contract tests.
 *
 * Loads the canonical checked-in OpenAPI JSON specs from contracts/openapi/
 * and compiles component schemas into AJV validators. This provides a
 * single source of truth guard: if the hand-written Zod schemas in
 * _helpers.ts drift from the OpenAPI contracts, the drift-detection suite
 * will surface the mismatch with field-level detail.
 */

import { readFileSync } from 'fs';
import { resolve } from 'path';
import { fileURLToPath } from 'url';
import Ajv, { ErrorObject, ValidateFunction } from 'ajv';
import addFormats from 'ajv-formats';

const __filename = fileURLToPath(import.meta.url);
const __dirname = resolve(__filename, '..');

// ---------------------------------------------------------------------------
// AJV setup
// ---------------------------------------------------------------------------

const ajv = new Ajv({
  strict: false,
  allErrors: true,
  coerceTypes: false,
  validateFormats: true,
});
addFormats(ajv);

// ---------------------------------------------------------------------------
// Spec loading + schema compilation cache
// ---------------------------------------------------------------------------

const specCache = new Map<string, Record<string, unknown>>();
const validatorCache = new Map<string, ValidateFunction>();

function loadSpec(specFile: string): Record<string, unknown> {
  if (specCache.has(specFile)) {
    return specCache.get(specFile)!;
  }

  const root = resolve(__dirname, '..', '..', '..', '..', '..', '..');
  const specPath = resolve(root, 'contracts', 'openapi', specFile);
  const raw = readFileSync(specPath, 'utf-8');
  const spec = JSON.parse(raw) as Record<string, unknown>;
  specCache.set(specFile, spec);
  return spec;
}

function getComponentSchema(spec: Record<string, unknown>, ref: string): unknown {
  // ref formats supported:
  //   "#/components/schemas/Foo"
  //   "#/definitions/Foo"
  const parts = ref.replace(/^#\//, '').split('/');
  let current: unknown = spec;
  for (const part of parts) {
    if (current && typeof current === 'object' && part in current) {
      current = (current as Record<string, unknown>)[part];
    } else {
      throw new Error(`Cannot resolve ${ref} in OpenAPI spec — missing segment "${part}"`);
    }
  }
  return current;
}

function buildValidator(specFile: string, ref: string): ValidateFunction {
  const cacheKey = `${specFile}::${ref}`;
  if (validatorCache.has(cacheKey)) {
    return validatorCache.get(cacheKey)!;
  }

  const spec = loadSpec(specFile);
  const schema = getComponentSchema(spec, ref);

  // Inline all $ref definitions from the spec so AJV can resolve them
  const inlined = {
    ...spec,
    $ref: ref,
  };

  const validate = ajv.compile(inlined);
  validatorCache.set(cacheKey, validate);
  return validate;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Assert that `data` satisfies the canonical JSON Schema component `ref`
 * inside `specFile`. Throws a descriptive, field-level error on mismatch.
 */
export function assertOpenApiSchema(
  specFile: string,
  ref: string,
  data: unknown,
  label: string
): void {
  const validate = buildValidator(specFile, ref);
  const valid = validate(data);

  if (!valid) {
    const issues = (validate.errors || [])
      .map((e: ErrorObject) => `  ${e.instancePath || '(root)'}: ${e.message}`)
      .join('\n');
    throw new Error(`OpenAPI contract violation for ${label} (${specFile} ${ref}):\n${issues}`);
  }
}

/**
 * Assert that `data` **fails** the canonical JSON Schema component `ref`.
 * Useful for negative-path (drift) tests.
 */
export function assertOpenApiSchemaRejects(
  specFile: string,
  ref: string,
  data: unknown,
  label: string
): void {
  const validate = buildValidator(specFile, ref);
  const valid = validate(data);

  if (valid) {
    throw new Error(
      `Expected ${label} to fail OpenAPI schema validation (${specFile} ${ref}), but it passed`
    );
  }
}

/**
 * Map from our hand-written schema names to their canonical OpenAPI homes.
 * Used by the drift-detection suite to know which spec+ref to validate
 * against for each fixture.
 */
export const OPENAPI_SCHEMA_MAP: Record<
  string,
  { specFile: string; ref: string; description: string }
> = {
  // L2 Extraction / signal lifecycle
  OperationalSignalLifecycleRecordSchema: {
    specFile: 'layer2-extraction.json',
    ref: '#/components/schemas/OperationalSignalLifecycleRecord',
    description: 'L2 operational signal lifecycle record',
  },

  // L3 Knowledge Graph
  GraphNodeSchema: {
    specFile: 'layer3-knowledge.json',
    ref: '#/components/schemas/GraphNode',
    description: 'L3 graph node shape',
  },
  GraphEdgeSchema: {
    specFile: 'layer3-knowledge.json',
    ref: '#/components/schemas/GraphEdge',
    description: 'L3 graph edge shape',
  },
  SubgraphResponseSchema: {
    specFile: 'layer3-knowledge.json',
    ref: '#/components/schemas/SubgraphResponse',
    description: 'L3 subgraph response',
  },
  FormulaEvaluateResponseSchema: {
    specFile: 'layer3-knowledge.json',
    ref: '#/components/schemas/FormulaEvaluateResponse',
    description: 'L3 POST /v1/formulas/evaluate response',
  },
  PackSummarySchema: {
    specFile: 'layer3-knowledge.json',
    ref: '#/components/schemas/PackSummary',
    description: 'L3 value pack summary',
  },

  // L4 Agents / Workflows / Governance
  WorkflowCreateResponseSchema: {
    specFile: 'layer4-agents.json',
    ref: '#/components/schemas/WorkflowCreateResponse',
    description: 'L4 POST /v1/workflows response',
  },
  WorkflowStatusResponseSchema: {
    specFile: 'layer4-agents.json',
    ref: '#/components/schemas/WorkflowStatusResponse',
    description: 'L4 GET /v1/workflows/{workflow_id} response',
  },
  WorkflowResumeResponseSchema: {
    specFile: 'layer4-agents.json',
    ref: '#/components/schemas/WorkflowResumeResponse',
    description: 'L4 workflow resume response',
  },
  TenantModelSchema: {
    specFile: 'layer4-agents.json',
    ref: '#/components/schemas/TenantModel',
    description: 'L4 tenant model',
  },
  FeatureFlagResponseSchema: {
    specFile: 'layer4-agents.json',
    ref: '#/components/schemas/FeatureFlagResponse',
    description: 'L4 feature flag response',
  },

  // L5 Ground Truth
  TruthObjectResponseSchema: {
    specFile: 'layer5-ground-truth.json',
    ref: '#/components/schemas/TruthObjectResponse',
    description: 'L5 GET /api/v1/truths/{truth_id} response',
  },
  TruthObjectListResponseSchema: {
    specFile: 'layer5-ground-truth.json',
    ref: '#/components/schemas/TruthObjectListResponse',
    description: 'L5 paginated truth list',
  },
  ValidateResponseSchema: {
    specFile: 'layer5-ground-truth.json',
    ref: '#/components/schemas/ValidateResponse',
    description: 'L5 validate response',
  },

  // Common
  ApiErrorSchema: {
    specFile: 'fabric-4l-api.json',
    ref: '#/components/schemas/ErrorEnvelope',
    description: 'Canonical shared API error envelope',
  },
};

/** All drift-tracked schema names exported from _helpers.ts. */
export const DRIFT_TRACKED_SCHEMAS = Object.keys(OPENAPI_SCHEMA_MAP);
