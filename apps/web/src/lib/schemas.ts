/**
 * Runtime validation schemas for API responses
 *
 * Uses Zod for type-safe parsing of external data at trust boundaries.
 * All schemas should match the OpenAPI contracts in /contracts/openapi/
 */
import { z } from 'zod';
import { createFeatureLogger } from '@/lib/telemetry';

const log = createFeatureLogger('api-schemas');

// ===== Shared Base Schemas =====

export const EntityTypeSchema = z.enum([
  'capability',
  'usecase',
  'persona',
  'outcome',
  'value_driver',
  'kpi',
  'Unknown',
]);

export const GraphNodeSchema = z.object({
  id: z.string(),
  name: z.string(),
  entity_type: z.union([EntityTypeSchema, z.string()]),
  confidence_score: z.number().min(0).max(1),
  description: z.string().optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
});

export const GraphRelationshipSchema = z.object({
  source: z.string(),
  target: z.string(),
  type: z.string(),
  confidence: z.number().min(0).max(1).optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
});

// ===== Formula Schemas (High Risk) =====

export const FormulaVariableSchema = z.object({
  name: z.string(),
  type: z.enum(['currency', 'percentage', 'integer', 'float', 'string']),
  unit: z.string().optional(),
  default_value: z.union([z.string(), z.number()]).optional(),
  description: z.string().optional(),
});

export const FormulaSchema = z.object({
  id: z.string(),
  formula_id: z.string(),
  name: z.string().min(1),
  expression: z.string().min(1),
  version: z.string().regex(/^\d+\.\d+\.\d+$/),
  status: z.enum(['draft', 'pending', 'approved', 'active', 'archived']),
  owner: z.email(),
  updated_at: z.iso.datetime(),
  created_at: z.iso.datetime(),
  used_in_count: z.number().int().min(0),
  governance_score: z.number().min(0).max(1),
  variables: z.array(z.string()),
  description: z.string().optional(),
});

export const FormulaEvaluationResultSchema = z.object({
  result: z.number(),
  unit: z.string(),
  confidence: z.number().min(0).max(1),
  calculation_steps: z.array(
    z.object({
      step: z.number().int(),
      operation: z.string(),
      result: z.string(),
    })
  ),
  formula_used: z.string(),
});

export const FormulaApprovalRequestSchema = z.object({
  id: z.string(),
  formula_id: z.string(),
  formula_name: z.string(),
  submitted_by: z.email(),
  submitted_at: z.iso.datetime(),
  change_summary: z.string(),
  previous_version: z.string(),
  status: z.enum(['pending', 'approved', 'rejected']),
});

// ===== Graph Query Schemas (High Risk) =====

export const GraphQueryRequestSchema = z.object({
  query: z.string().min(1),
  entity_type: z.string().optional(),
  max_hops: z.number().int().min(1).max(5).optional(),
  max_results: z.number().int().min(1).max(100).optional(),
});

export const GraphQueryResponseSchema = z.object({
  query: z.string(),
  entities: z.array(GraphNodeSchema),
  relationships: z.array(GraphRelationshipSchema),
  context_graph: z
    .object({
      nodes: z.array(GraphNodeSchema),
      relationships: z.array(GraphRelationshipSchema),
    })
    .optional(),
  confidence_score: z.number().min(0).max(1),
  sources: z.array(z.string()).optional(),
  processing_time_ms: z.number().positive(),
});

export const EntityContextResponseSchema = z.object({
  entity_id: z.string(),
  center: GraphNodeSchema,
  neighbors: z.array(GraphNodeSchema),
  relationships: z.array(GraphRelationshipSchema),
  entity_count: z.number().int().nonnegative(),
  relationship_count: z.number().int().nonnegative(),
});

export const EntityTraversalResponseSchema = z.object({
  start_entity_id: z.string(),
  direction: z.enum(['up', 'down', 'both']),
  paths: z.array(
    z.object({
      nodes: z.array(GraphNodeSchema),
      relationships: z.array(GraphRelationshipSchema),
      value_score: z.number().optional(),
    })
  ),
  path_count: z.number().int().nonnegative(),
});

// ===== Value Pack Schemas =====

export const ValuePackSchema = z.object({
  id: z.string(),
  pack_id: z.string(),
  name: z.string().min(1),
  industry: z.string(),
  description: z.string().optional(),
  driver_count: z.number().int().nonnegative(),
  formula_count: z.number().int().nonnegative(),
  benchmark_count: z.number().int().nonnegative(),
  workflow_count: z.number().int().nonnegative(),
  status: z.enum(['active', 'draft', 'archived', 'published']),
  scope: z.enum(['global', 'tenant']),
  updated_at: z.iso.datetime(),
  created_at: z.iso.datetime().optional(),
  version: z.string().optional(),
  owner: z.string().optional(),
});

// ===== Value Tree Schemas (High Risk) =====

export const ValueTreeNodeSchema = z.object({
  id: z.string(),
  label: z.string(),
  type: z.enum(['Capability', 'UseCase', 'Persona', 'ValueDriver', 'Outcome', 'KPI']),
  layer: z.number().int().min(1).max(4),
  confidence: z.number().min(0).max(1),
  properties: z.record(z.string(), z.unknown()).default({}),
});

export const ValueTreeEdgeSchema = z.object({
  source: z.string(),
  target: z.string(),
  type: z.enum(['ENABLES', 'BENEFITS', 'DRIVES', 'REQUIRES', 'RELATED_TO']),
  weight: z.number().min(0).max(1),
});

export const ValueTreeStatsSchema = z.object({
  total_nodes: z.number().int().nonnegative(),
  total_edges: z.number().int().nonnegative(),
  by_layer: z.record(z.string(), z.number().int().nonnegative()),
  max_depth: z.number().int().min(1).max(4),
});

export const ValueTreeResponseSchema = z.object({
  root_entity_id: z.string(),
  direction: z.enum(['upward', 'downward']),
  nodes: z.array(ValueTreeNodeSchema),
  edges: z.array(ValueTreeEdgeSchema),
  paths: z.array(
    z.object({
      length: z.number().int().positive(),
      nodes: z.array(z.string()),
    })
  ),
  stats: ValueTreeStatsSchema,
});

export const ValueTreePathNodeSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.string(),
});

export const ValueTreePathSchema = z.object({
  nodes: z.array(ValueTreePathNodeSchema),
  length: z.number().int().positive(),
});

export const ValueTreePathListSchema = z.array(ValueTreePathSchema);

export const CreateValueTreeRequestSchema = z.object({
  entity_id: z.string().min(1),
  direction: z.enum(['upward', 'downward']).optional(),
  initialize_root: z.boolean().optional(),
});

export const ImportValueTreeRequestSchema = z.object({
  entity_id: z.string().min(1),
  tree: ValueTreeResponseSchema,
});

// ===== Validation Helpers =====

/**
 * Safely parse API response with Zod schema
 * Logs validation errors in development but returns null instead of throwing
 */
export function safeParseResponse<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  endpoint: string
): T | null {
  const result = schema.safeParse(data);
  if (!result.success) {
    log.error(`API Validation Error: ${endpoint}`);
    return null;
  }
  return result.data;
}

/**
 * Parse API response or throw error for critical paths
 */
export function parseResponseOrThrow<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  endpoint: string
): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    log.error(`API Validation Error: ${endpoint}`);
    throw new Error(`Invalid API response from ${endpoint}`);
  }
  return result.data;
}
