/**
 * Shared helpers for frontend contract tests.
 *
 * Provides Zod schemas derived from checked-in OpenAPI contracts and
 * fixture factories that produce minimal-valid objects for each shape.
 * Tests import from here rather than re-declaring schemas inline.
 */

import { z } from 'zod';
import {
  assertOpenApiSchema,
  assertOpenApiSchemaRejects,
} from './openapi-validator';

// ---------------------------------------------------------------------------
// Common
// ---------------------------------------------------------------------------

export const ApiErrorSchema = z.object({
  error: z.object({
    code: z.string().min(1),
    message: z.string(),
    request_id: z.string().min(1),
    details: z.record(z.string(), z.unknown()).nullable().optional(),
  }),
});

export const PaginatedSchema = <T extends z.ZodType>(item: T) =>
  z.object({
    items: z.array(item),
    total: z.number().int().nonnegative(),
    limit: z.number().int().positive(),
    offset: z.number().int().nonnegative(),
    has_more: z.boolean(),
  });

// Tenant context helpers
export const TenantContextSchema = z.object({
  tenant_id: z.uuid(),
});

export const CrossTenantErrorSchema = z.object({
  error: z.object({
    code: z.literal('AUTHORIZATION_ERROR'),
    message: z.string().min(1),
    request_id: z.string().min(1),
    details: z.record(z.string(), z.unknown()).nullable().optional(),
  }),
});

// ---------------------------------------------------------------------------
// L2 Extraction  (contracts/openapi/layer2-extraction.json)
// ---------------------------------------------------------------------------

export const ExtractResponseSchema = z.object({
  extraction_job_id: z.string().min(1),
  status: z.string().min(1),
  message: z.string(),
});

export const ExtractionStatusSchema = z.object({
  job_id: z.string().min(1),
  overall_status: z.string().min(1),
  extraction_status: z.string().min(1),
  ingestion_status: z.string().min(1),
  entities_extracted: z.number().int().nonnegative(),
  relationships_extracted: z.number().int().nonnegative(),
  retry_count: z.number().int().nonnegative().default(0),
  last_error: z.string().nullable().optional(),
  next_retry_at: z.string().nullable().optional(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
});

export const SignalLifecycleStatusSchema = z.enum([
  'active',
  'superseded',
  'merged',
]);

export const SignalLifecycleActorSchema = z.object({
  actor_id: z.string().min(1),
  account_id: z.string().min(1),
});

export const SignalLineageSchema = z.object({
  supersedes: z.array(z.string()).optional(),
  superseded_by: z.array(z.string()).optional(),
  merged_into: z.string().nullable().optional(),
});

export const SignalLifecycleMetadataSchema = z.object({
  created_by: SignalLifecycleActorSchema,
  created_at: z.string().optional(),
  updated_by: SignalLifecycleActorSchema,
  updated_at: z.string().optional(),
});

export const OperationalSignalLifecycleRecordSchema = z.object({
  signal_id: z.string().min(1),
  tenant_id: z.string().min(1),
  account_id: z.string().min(1),
  status: SignalLifecycleStatusSchema.default('active'),
  lineage: SignalLineageSchema.optional(),
  lifecycle: SignalLifecycleMetadataSchema,
});

// ---------------------------------------------------------------------------
// L3 Knowledge Graph  (contracts/openapi/layer3-knowledge.json)
// ---------------------------------------------------------------------------

export const GraphNodeSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  entity_type: z.string().min(1),
  label: z.string().min(1).optional(),
  type: z.string().min(1).optional(),
  confidence: z.number().min(0).max(1).optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
  confidence_score: z.number().min(0).max(1).optional(),
});

export const GraphEdgeSchema = z.object({
  source: z.string().min(1),
  target: z.string().min(1),
  type: z.string().min(1),
  relationship_type: z.string().min(1).optional(),
  weight: z.number().nullable().optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
});

export const SubgraphResponseSchema = z.object({
  root_entity_id: z.string(),
  nodes: z.array(GraphNodeSchema),
  edges: z.array(GraphEdgeSchema),
  depth: z.number().int().nonnegative(),
  stats: z.object({
    total_nodes: z.number().int(),
    total_edges: z.number().int(),
    density: z.number(),
  }),
});

export const FormulaEvaluateResponseSchema = z.object({
  result: z.number(),
  unit: z.string(),
  confidence: z.number().min(0).max(1),
  calculation_steps: z.array(
    z.object({
      step: z.number().int().positive(),
      operation: z.string(),
      result: z.string(),
    })
  ),
  formula_used: z.string(),
});

export const PackSummarySchema = z.object({
  pack_id: z.string().min(1),
  name: z.string().min(1),
  industry: z.string(),
  segment: z.string().nullable(),
  status: z.string(),
  version: z.string().min(1),
  driver_count: z.number().int().nonnegative(),
  formula_count: z.number().int().nonnegative(),
  benchmark_count: z.number().int().nonnegative(),
});

// ---------------------------------------------------------------------------
// L4 Agents  (contracts/openapi/layer4-agents.json)
// ---------------------------------------------------------------------------

export const WorkflowStatusEnum = z.enum([
  'pending', 'running', 'completed', 'failed', 'cancelled', 'paused', 'interrupted',
]);

export const WorkflowCreateResponseSchema = z.object({
  workflow_instance_id: z.string().min(1),
  status: z.string().min(1),
  estimated_duration_seconds: z.number().int().nonnegative(),
});

export const WorkflowStatusResponseSchema = z.object({
  id: z.string().min(1),
  workflow_instance_id: z.string().min(1),
  workflow_type: z.string().min(1),
  status: WorkflowStatusEnum,
  current_state: z.string().nullable(),
  current_node: z.string().nullable(),
  progress_percentage: z.number().min(0).max(100),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  error_count: z.number().int().nonnegative(),
  has_output: z.boolean(),
  results: z.record(z.string(), z.unknown()).nullable(),
  tenant_id: z.string().nullable(),
  user_id: z.string().nullable(),
  priority: z.number().nullable().optional(),
  scheduler_status: z.string().nullable().optional(),
  progress: z.object({
    step_id: z.string().nullable(),
    status: z.enum(['pending', 'running', 'paused', 'completed', 'failed', 'cancelled', 'unknown']),
    percent: z.number().min(0).max(100),
    message: z.string(),
    started_at: z.string().nullable().optional(),
    updated_at: z.string(),
    completed_at: z.string().nullable().optional(),
    actionable_next_state: z.object({
      can_retry: z.boolean(),
      can_resume: z.boolean(),
      can_cancel: z.boolean(),
      requires_user_action: z.boolean(),
      next_action: z.string().nullable(),
    }),
  }).nullable().optional(),
});

export const WorkflowResultResponseSchema = z.object({
  workflow_id: z.string().min(1),
  status: z.string().min(1),
  output: z.record(z.string(), z.unknown()).nullable(),
  errors: z.array(z.string()),
  completed_at: z.string().nullable(),
});

export const WorkflowResumeResponseSchema = z.object({
  workflow_instance_id: z.string().min(1),
  status: z.string().min(1),
  resumed_from_node: z.string().nullable(),
  message: z.string(),
  estimated_completion_seconds: z.number().int().nonnegative(),
});

export const C1MessageSchema = z.object({
  role: z.string().min(1),
  content: z.string().min(1),
});

export const TenantModelSchema = z.object({
  id: z.uuid(),
  name: z.string().min(1).max(200),
  slug: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
  status: z.enum(['active', 'suspended', 'deleted']),
});

export const FeatureFlagResponseSchema = z.object({
  id: z.uuid(),
  tenant_id: z.uuid().nullable(),
  flag_key: z.string().min(1),
  enabled: z.boolean(),
  rollout_percentage: z.number().int().min(0).max(100),
  description: z.string().nullable().optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  created_at: z.string(),
  updated_at: z.string(),
  updated_by: z.uuid().nullable(),
});


export const WorkspaceTabKeySchema = z.enum([
  'signals',
  'drivers',
  'evidence',
  'stakeholders',
  'action-plan',
  'value-model',
  'narrative',
]);

export const WorkspaceSignalSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  category: z.string().min(1),
  confidence: z.number().min(0).max(100),
  impact: z.string().min(1),
  trend: z.string().min(1).optional(),
});

export const WorkspaceDriverSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  contribution: z.number(),
  parentSignal: z.string().min(1).optional(),
  subDrivers: z.array(z.string().min(1)).optional(),
});

export const WorkspaceEvidenceSchema = z.object({
  id: z.string().min(1),
  source: z.string().min(1),
  claim: z.string().min(1),
  confidence: z.number().min(0).max(100),
  type: z.string().min(1).optional(),
});

export const WorkspaceStakeholderSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  role: z.string().min(1),
  priority: z.string().min(1).optional(),
  engagement: z.string().min(1).optional(),
});

export const WorkspaceActionPlanItemSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  priority: z.string().min(1),
  projectedValue: z.string().min(1).optional(),
  confidence: z.string().min(1).optional(),
  horizon: z.string().min(1).optional(),
});

export const WorkspaceValueModelItemSchema = z.object({
  id: z.string().min(1),
  driver: z.string().min(1),
  category: z.string().min(1),
  conservative: z.number(),
  expected: z.number(),
  optimistic: z.number(),
});

export const WorkspaceNarrativeItemSchema = z.object({
  id: z.string().min(1),
  stakeholder: z.string().min(1),
  role: z.string().min(1),
  status: z.string().min(1),
  headline: z.string().min(1),
  summary: z.string().min(1),
});

export const WorkspaceTabResponseSchema = z.object({
  signals: z.array(WorkspaceSignalSchema).optional(),
  drivers: z.array(WorkspaceDriverSchema).optional(),
  evidence: z.array(WorkspaceEvidenceSchema).optional(),
  stakeholders: z.array(WorkspaceStakeholderSchema).optional(),
  'action-plan': z.array(WorkspaceActionPlanItemSchema).optional(),
  'value-model': z.array(WorkspaceValueModelItemSchema).optional(),
  narrative: z.array(WorkspaceNarrativeItemSchema).optional(),
}).superRefine((value, ctx) => {
  const presentKeys = Object.keys(value).filter((key) => value[key as keyof typeof value] !== undefined);
  if (presentKeys.length !== 1) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Workspace tab response must contain exactly one tab payload key',
    });
  }
});

export const WorkspaceUpdateResponseSchema = z.object({
  case_id: z.string().min(1),
  tab: WorkspaceTabKeySchema,
  updated: z.literal(true),
});

export const WorkspaceGenerateResponseSchema = z.object({
  account_id: z.string().min(1),
  case_id: z.string().min(1),
  generated: z.literal(true),
  stats: z.object({
    signals: z.number().int().nonnegative(),
    drivers: z.number().int().nonnegative(),
    evidence: z.number().int().nonnegative(),
    stakeholders: z.number().int().nonnegative(),
  }),
});

// ---------------------------------------------------------------------------
// L5 Ground Truth  (contracts/openapi/layer5-ground-truth.json)
// ---------------------------------------------------------------------------

export const TruthStatusEnum = z.enum([
  'proposed', 'validated', 'disputed', 'rejected', 'superseded', 'expired',
]);

export const TruthObjectResponseSchema = z.object({
  id: z.uuid(),
  tenant_id: z.uuid(),
  organization_id: z.uuid(),
  claim: z.string().min(1),
  claim_type: z.string(),
  confidence: z.number().min(0).max(1),
  status: z.string(),
  maturity_level: z.number().int().nonnegative(),
  freshness: z.string(),
  is_stale: z.boolean(),
  applies_to: z.record(z.string(), z.unknown()).nullable().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export const TruthObjectSummarySchema = z.object({
  id: z.uuid(),
  claim: z.string().min(1),
  claim_type: z.string(),
  confidence: z.number(),
  status: z.string(),
  maturity_level: z.number().int().nonnegative(),
  is_stale: z.boolean(),
  source_count: z.number().int().nonnegative().default(0),
  validated_by: z.string().nullable(),
  freshness: z.string(),
  created_at: z.string(),
});

export const TruthObjectListResponseSchema = z.object({
  items: z.array(TruthObjectSummarySchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().nonnegative(),
  offset: z.number().int().nonnegative(),
  has_more: z.boolean(),
});

export const ValidateResponseSchema = z.object({
  truth_id: z.uuid(),
  previous_status: z.string(),
  new_status: z.string(),
  maturity_level: z.number().int().nonnegative(),
});

// ---------------------------------------------------------------------------
// Fixture factories — produce minimal-valid objects for each schema
// ---------------------------------------------------------------------------

export const fixtures = {
  extractResponse: (): z.infer<typeof ExtractResponseSchema> => ({
    extraction_job_id: 'job-abc123',
    status: 'pending',
    message: 'Extraction job queued',
  }),

  extractionStatus: (overrides?: Partial<z.infer<typeof ExtractionStatusSchema>>): z.infer<typeof ExtractionStatusSchema> => ({
    job_id: 'job-abc123',
    overall_status: 'completed',
    extraction_status: 'completed',
    ingestion_status: 'completed',
    entities_extracted: 12,
    relationships_extracted: 8,
    retry_count: 0,
    last_error: null,
    next_retry_at: null,
    started_at: '2024-01-15T10:00:00Z',
    completed_at: '2024-01-15T10:01:30Z',
    ...overrides,
  }),

  operationalSignalLifecycleRecord: (
    overrides?: Partial<z.infer<typeof OperationalSignalLifecycleRecordSchema>>
  ): z.infer<typeof OperationalSignalLifecycleRecordSchema> => ({
    signal_id: 'signal-001',
    tenant_id: 'tenant-001',
    account_id: 'account-001',
    status: 'active',
    lineage: {
      supersedes: [],
      superseded_by: [],
      merged_into: null,
    },
    lifecycle: {
      created_by: {
        actor_id: 'user-001',
        account_id: 'account-001',
      },
      created_at: '2024-01-15T10:00:00Z',
      updated_by: {
        actor_id: 'user-001',
        account_id: 'account-001',
      },
      updated_at: '2024-01-15T10:00:00Z',
    },
    ...overrides,
  }),

  workflowCreateResponse: (): z.infer<typeof WorkflowCreateResponseSchema> => ({
    workflow_instance_id: 'wf-inst-001',
    status: 'pending',
    estimated_duration_seconds: 300,
  }),

  workflowStatus: (overrides?: Partial<z.infer<typeof WorkflowStatusResponseSchema>>): z.infer<typeof WorkflowStatusResponseSchema> => ({
    id: 'wf-inst-001',
    workflow_instance_id: 'wf-inst-001',
    workflow_type: 'roi_calculator',
    status: 'running',
    current_state: 'data_collection',
    current_node: 'collect_metrics',
    progress_percentage: 45,
    started_at: '2024-01-15T10:00:00Z',
    completed_at: null,
    error_count: 0,
    has_output: false,
    results: null,
    tenant_id: 'tenant-001',
    user_id: 'user-001',
    ...overrides,
  }),

  workflowResult: (): z.infer<typeof WorkflowResultResponseSchema> => ({
    workflow_id: 'wf-inst-001',
    status: 'completed',
    output: { roi_percent: 142, payback_months: 18 },
    errors: [],
    completed_at: '2024-01-15T10:05:00Z',
  }),

  tenant: (): z.infer<typeof TenantModelSchema> => ({
    id: '550e8400-e29b-41d4-a716-446655440000',
    name: 'Acme Corp',
    slug: 'acme-corp',
    status: 'active',
  }),

  featureFlag: (): z.infer<typeof FeatureFlagResponseSchema> => ({
    id: '550e8400-e29b-41d4-a716-446655440001',
    tenant_id: '550e8400-e29b-41d4-a716-446655440000',
    flag_key: 'advanced_analytics',
    enabled: true,
    rollout_percentage: 100,
    description: 'Enable advanced analytics dashboard',
    metadata: { region: 'us-east-1' },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    updated_by: '550e8400-e29b-41d4-a716-446655440000',
  }),


  workspaceSignal: (): z.infer<typeof WorkspaceSignalSchema> => ({
    id: 'sig-001',
    name: 'Operational inefficiency in Manufacturing',
    category: 'Operational',
    confidence: 85,
    impact: 'High',
    trend: 'Increasing',
  }),

  workspaceDriver: (): z.infer<typeof WorkspaceDriverSchema> => ({
    id: 'drv-001',
    name: 'Manual process overhead',
    contribution: 35,
    parentSignal: 'Operational inefficiency in Manufacturing',
    subDrivers: ['Data entry', 'Approval delays'],
  }),

  workspaceEvidence: (): z.infer<typeof WorkspaceEvidenceSchema> => ({
    id: 'ev-001',
    source: 'Industry Report 2024',
    claim: 'Sector averages 23% efficiency gap',
    confidence: 88,
    type: 'benchmark',
  }),

  workspaceStakeholder: (): z.infer<typeof WorkspaceStakeholderSchema> => ({
    id: 'st-001',
    name: 'CFO',
    role: 'Economic Buyer',
    priority: 'High',
    engagement: 'Active',
  }),

  workspaceActionPlanItem: (): z.infer<typeof WorkspaceActionPlanItemSchema> => ({
    id: 'rec-001',
    title: 'Automate manual approval workflows',
    priority: 'critical',
    projectedValue: '$2.4M annually',
    confidence: 'high',
    horizon: 'Q2-Q3',
  }),

  workspaceValueModelItem: (): z.infer<typeof WorkspaceValueModelItemSchema> => ({
    id: 'val-001',
    driver: 'Labor cost reduction',
    category: 'hard',
    conservative: 800000,
    expected: 1200000,
    optimistic: 1600000,
  }),

  workspaceNarrativeItem: (): z.infer<typeof WorkspaceNarrativeItemSchema> => ({
    id: 'nar-001',
    stakeholder: 'CFO',
    role: 'Economic Buyer',
    status: 'ready',
    headline: '$5.2M projected ROI over 3 years',
    summary: 'Financial analysis shows a compelling return profile.',
  }),

  truthObject: (overrides?: Partial<z.infer<typeof TruthObjectResponseSchema>>): z.infer<typeof TruthObjectResponseSchema> => ({
    id: '550e8400-e29b-41d4-a716-446655440002',
    tenant_id: '550e8400-e29b-41d4-a716-446655440000',
    organization_id: '550e8400-e29b-41d4-a716-446655440000',
    claim: 'Manual reporting costs 12 hours/week per analyst',
    claim_type: 'quantitative',
    confidence: 0.82,
    status: 'validated',
    maturity_level: 4,
    freshness: '2024-01-15T10:00:00Z',
    is_stale: false,
    applies_to: { account_id: 'acct-456' },
    created_at: '2024-01-10T08:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    ...overrides,
  }),

  truthObjectSummary: (overrides?: Partial<z.infer<typeof TruthObjectSummarySchema>>): z.infer<typeof TruthObjectSummarySchema> => ({
    id: '550e8400-e29b-41d4-a716-446655440002',
    claim: 'Manual reporting costs 12 hours/week per analyst',
    claim_type: 'quantitative',
    confidence: 0.82,
    status: 'validated',
    maturity_level: 4,
    is_stale: false,
    source_count: 3,
    validated_by: 'admin@example.com',
    freshness: '2024-01-15T10:00:00Z',
    created_at: '2024-01-10T08:00:00Z',
    ...overrides,
  }),

  paginatedSignals: (offset = 0, hasMore = false): z.infer<ReturnType<typeof PaginatedSchema>> => ({
    items: [],
    total: 0,
    limit: 50,
    offset,
    has_more: hasMore,
  }),

  graphNode: (): z.infer<typeof GraphNodeSchema> => ({
    id: 'node-001',
    name: 'Cloud Migration',
    entity_type: 'capability',
    label: 'Cloud Migration',
    type: 'capability',
    confidence_score: 0.95,
    confidence: 0.95,
  }),

  packSummary: (): z.infer<typeof PackSummarySchema> => ({
    pack_id: 'pack-saas-001',
    name: 'SaaS Value Pack',
    industry: 'Technology',
    segment: 'saas',
    status: 'active',
    version: '2.1.0',
    driver_count: 12,
    formula_count: 8,
    benchmark_count: 5,
  }),
};

// ---------------------------------------------------------------------------
// Assertion helpers
// ---------------------------------------------------------------------------

/**
 * Assert that `data` satisfies `schema` and return the parsed value.
 * Throws a descriptive error on mismatch — surfaces field-level issues.
 */
export function assertSchema<T extends z.ZodType>(
  schema: T,
  data: unknown,
  label: string
): z.infer<T> {
  const result = schema.safeParse(data);
  if (!result.success) {
    const issues = result.error.issues
      .map((i) => `  ${i.path.join('.')}: ${i.message}`)
      .join('\n');
    throw new Error(`Contract violation for ${label}:\n${issues}`);
  }
  return result.data;
}

/**
 * Assert that `data` fails `schema` validation (for negative-path tests).
 */
export function assertSchemaRejects(
  schema: z.ZodType,
  data: unknown,
  label: string
): void {
  const result = schema.safeParse(data);
  if (result.success) {
    throw new Error(
      `Expected ${label} to fail schema validation, but it passed`
    );
  }
}

// ---------------------------------------------------------------------------
// Dual-validation helpers (Zod + canonical OpenAPI JSON Schema)
// ---------------------------------------------------------------------------

/**
 * Assert that `data` satisfies both the hand-written Zod `schema`
 * and the canonical OpenAPI JSON Schema component `ref` in `specFile`.
 * Returns the Zod-parsed value for downstream assertions.
 */
export function assertCanonicalSchema<T extends z.ZodType>(
  schema: T,
  specFile: string,
  ref: string,
  data: unknown,
  label: string
): z.infer<T> {
  const parsed = assertSchema(schema, data, label);
  assertOpenApiSchema(specFile, ref, data, label);
  return parsed;
}

/**
 * Assert that `data` fails both the Zod `schema` and the canonical
 * OpenAPI JSON Schema component `ref` in `specFile`.
 */
export function assertCanonicalSchemaRejects(
  schema: z.ZodType,
  specFile: string,
  ref: string,
  data: unknown,
  label: string
): void {
  assertSchemaRejects(schema, data, label);
  assertOpenApiSchemaRejects(specFile, ref, data, label);
}
