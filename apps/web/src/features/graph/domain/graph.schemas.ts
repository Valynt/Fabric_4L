/**
 * graph.schemas.ts — Zod validation schemas for L3 Graph DTOs
 *
 * Validates graph API responses before they reach the domain layer.
 * Enforces:
 *   - Edge endpoints reference existing node IDs
 *   - Confidence values are in [0, 1]
 *   - Tenant-scoped IDs are non-empty strings
 *   - Optional visualization metadata degrades safely
 *
 * These schemas mirror the cleaned OpenAPI DTOs (GraphNode, GraphEdge,
 * SubgraphResponse, GraphRAGResponse) and are the single source of truth
 * for runtime graph validation.
 */

import { z } from 'zod';

// ── Primitives ───────────────────────────────────────────────────────────────

export const EntityIdSchema = z.string().min(1).max(255);

export const ConfidenceSchema = z.number().min(0).max(1);

export const RelationshipTypeSchema = z.string().min(1).max(100);

// ── GraphNodeDto ─────────────────────────────────────────────────────────────

export const GraphNodeDtoSchema = z.object({
  id: EntityIdSchema.describe('Unique node identifier'),
  label: z.string().min(1).describe('Display label (canonical field)'),
  type: z.string().min(1).describe('Node type (canonical field)'),
  confidence: ConfidenceSchema.default(0.8).describe('Confidence score'),
  properties: z.record(z.string(), z.unknown()).optional(),
});

export type GraphNodeDto = z.infer<typeof GraphNodeDtoSchema>;

// ── GraphEdgeDto ─────────────────────────────────────────────────────────────

export const GraphEdgeDtoSchema = z.object({
  source: EntityIdSchema.describe('Source node ID'),
  target: EntityIdSchema.describe('Target node ID'),
  type: RelationshipTypeSchema.describe('Relationship type/label'),
  weight: z.number().min(0).default(1.0).describe('Edge weight/strength'),
  properties: z.record(z.string(), z.unknown()).optional(),
});

export type GraphEdgeDto = z.infer<typeof GraphEdgeDtoSchema>;

// ── GraphSubgraphResponseDto ─────────────────────────────────────────────────

export const GraphSubgraphResponseDtoSchema = z.object({
  root_entity_id: EntityIdSchema.describe('ID of the central entity'),
  nodes: z.array(GraphNodeDtoSchema).min(1).describe('Connected nodes including root'),
  edges: z.array(GraphEdgeDtoSchema).describe('Edges between returned nodes'),
  depth: z.number().int().min(1).max(5).describe('Traversal depth used'),
  stats: z.object({
    total_nodes: z.number().int().nonnegative(),
    total_edges: z.number().int().nonnegative(),
    node_types: z.record(z.string(), z.number().int().nonnegative()).default({}),
    communities: z.number().int().nonnegative().default(0),
    density: z.number().min(0).default(0),
  }),
});

export type GraphSubgraphResponseDto = z.infer<typeof GraphSubgraphResponseDtoSchema>;

// ── GraphQueryResponseDto ────────────────────────────────────────────────────

export const GraphQueryResponseDtoSchema = z.object({
  query: z.string().min(1).describe('Original query'),
  entities: z.array(GraphNodeDtoSchema).describe('Relevant entities found'),
  relationships: z.array(GraphEdgeDtoSchema).describe('Relevant relationships found'),
  context_graph: z
    .object({
      nodes: z.array(GraphNodeDtoSchema),
      edges: z.array(GraphEdgeDtoSchema),
    })
    .optional()
    .describe('Context graph structure'),
  confidence_score: ConfidenceSchema.describe('Overall confidence score'),
  sources: z.array(z.string()).optional().describe('Source entities/IDs'),
  processing_time_ms: z.number().nonnegative().optional().describe('Processing time in milliseconds'),
  answer: z.string().optional().describe('Generated answer'),
});

export type GraphQueryResponseDto = z.infer<typeof GraphQueryResponseDtoSchema>;

// ── EntityContextResponseDto ─────────────────────────────────────────────────

export const EntityContextResponseDtoSchema = z.object({
  entity_id: EntityIdSchema,
  center: GraphNodeDtoSchema.describe('Center entity'),
  neighbors: z.array(GraphNodeDtoSchema).describe('Neighbor entities'),
  relationships: z.array(GraphEdgeDtoSchema).describe('Relationships'),
  entity_count: z.number().int().nonnegative(),
  relationship_count: z.number().int().nonnegative(),
  pagination: z
    .object({
      has_more: z.boolean().optional(),
      next_cursor: z.string().optional(),
      returned_count: z.number().int().nonnegative().optional(),
    })
    .optional(),
});

export type EntityContextResponseDto = z.infer<typeof EntityContextResponseDtoSchema>;

// ── Topology Validation ──────────────────────────────────────────────────────

/**
 * Validates that every edge in a graph references existing node IDs.
 * Returns an array of orphaned edge indices (empty if valid).
 */
export function validateGraphTopology<
  N extends { id: string },
  E extends { source: string; target: string } | { sourceId: string; targetId: string }
>(
  nodes: readonly N[],
  edges: readonly E[]
): { valid: boolean; orphanedEdges: number[] } {
  const nodeIds = new Set(nodes.map((n) => n.id));
  const orphanedEdges: number[] = [];

  edges.forEach((edge, idx) => {
    const source = 'sourceId' in edge ? edge.sourceId : edge.source;
    const target = 'targetId' in edge ? edge.targetId : edge.target;
    if (!nodeIds.has(source) || !nodeIds.has(target)) {
      orphanedEdges.push(idx);
    }
  });

  return {
    valid: orphanedEdges.length === 0,
    orphanedEdges,
  };
}

/**
 * Validates an entire subgraph DTO including topology.
 * Throws a descriptive error if invalid.
 */
export function validateSubgraphTopology(dto: GraphSubgraphResponseDto): void {
  const topology = validateGraphTopology(dto.nodes, dto.edges);
  if (!topology.valid) {
    const badEdges = topology.orphanedEdges.map((i) => dto.edges[i]);
    throw new Error(
      `Subgraph topology invalid: ${topology.orphanedEdges.length} orphaned edge(s). ` +
        `Examples: ${badEdges.map((e) => `${e.source}->${e.target}`).join(', ')}`
    );
  }
}
