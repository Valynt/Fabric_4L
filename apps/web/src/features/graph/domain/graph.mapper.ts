/**
 * graph.mapper.ts — DTO-to-Domain mapper for L3 graph responses
 *
 * Maps snake_case / legacy-field DTOs into camelCase domain models.
 * Handles:
 *   - Field name normalization (label → name, type → entityType, etc.)
 *   - Missing optional metadata (degrades safely)
 *   - Inconsistent graph topology (logs warnings, does not crash)
 *
 * This is the **only** place where generated DTO types may be imported
 * into the graph feature domain layer.
 */

import { createFeatureLogger } from '@/lib/telemetry';
import type { components } from '@/api/generated/l3';
import {
  validateGraphTopology,
  type GraphNodeDto,
  type GraphEdgeDto,
  type GraphSubgraphResponseDto,
  type GraphQueryResponseDto,
  type EntityContextResponseDto,
} from './graph.schemas';
import type {
  GraphNode,
  GraphEdge,
  GraphSubgraph,
  GraphStats,
  GraphQueryResult,
  EntityContext,
} from './graph.model';

const log = createFeatureLogger('graph.mapper');

// ── Constants ───────────────────────────────────────────────────────────────────

const DEFAULT_CONFidence = 0.8;
const DEFAULT_ENTITY_TYPE = 'Unknown';
const DEFAULT_RELATIONSHIP_TYPE = 'RELATED_TO';

// ── Helpers ──────────────────────────────────────────────────────────────────

function normalizeNodeId(id: unknown): string {
  if (typeof id === 'string' && id.length > 0) return id;
  throw new Error(`Invalid node id: ${String(id)}`);
}

function extractName(dto: GraphNodeDto | Record<string, unknown>): string {
  // Prefer canonical 'label', fall back to legacy 'name'
  if ('label' in dto && typeof dto.label === 'string' && dto.label.length > 0) {
    return dto.label;
  }
  if ('name' in dto && typeof dto.name === 'string' && dto.name.length > 0) {
    return dto.name;
  }
  return normalizeNodeId(dto.id);
}

function extractEntityType(dto: GraphNodeDto | Record<string, unknown>): string {
  // Prefer canonical 'type', fall back to legacy 'entity_type'
  if ('type' in dto && typeof dto.type === 'string' && dto.type.length > 0) {
    return dto.type;
  }
  if ('entity_type' in dto && typeof dto.entity_type === 'string' && dto.entity_type.length > 0) {
    return dto.entity_type;
  }
  return DEFAULT_ENTITY_TYPE;
}

function extractConfidence(dto: GraphNodeDto | Record<string, unknown>): number {
  if ('confidence' in dto && typeof dto.confidence === 'number') {
    return dto.confidence;
  }
  if ('confidence_score' in dto && typeof dto.confidence_score === 'number') {
    return dto.confidence_score;
  }
  return DEFAULT_CONFidence;
}

function extractRelationshipType(dto: GraphEdgeDto | Record<string, unknown>): string {
  if ('type' in dto && typeof dto.type === 'string' && dto.type.length > 0) {
    return dto.type;
  }
  if ('relationship_type' in dto && typeof dto.relationship_type === 'string') {
    return dto.relationship_type;
  }
  return DEFAULT_RELATIONSHIP_TYPE;
}

// ── Node / Edge Mappers ──────────────────────────────────────────────────────

export function mapGraphNodeDtoToDomain(dto: unknown): GraphNode {
  const d = dto as Record<string, unknown>;
  return {
    id: normalizeNodeId(d.id),
    name: extractName(d),
    entityType: extractEntityType(d),
    confidenceScore: extractConfidence(d),
    description:
      'description' in d && typeof d.description === 'string'
        ? d.description
        : undefined,
    properties:
      'properties' in d && d.properties && typeof d.properties === 'object'
        ? (d.properties as Record<string, unknown>)
        : undefined,
  };
}

export function mapGraphEdgeDtoToDomain(dto: unknown): GraphEdge {
  const d = dto as Record<string, unknown>;
  return {
    sourceId: normalizeNodeId(d.source),
    targetId: normalizeNodeId(d.target),
    relationshipType: extractRelationshipType(d),
    weight: typeof d.weight === 'number' ? d.weight : 1.0,
    properties:
      'properties' in d && d.properties && typeof d.properties === 'object'
        ? (d.properties as Record<string, unknown>)
        : undefined,
  };
}

// ── Response Mappers ─────────────────────────────────────────────────────────

export function mapSubgraphResponseDtoToDomain(
  dto: GraphSubgraphResponseDto | Record<string, unknown>
): GraphSubgraph {
  const raw = dto as Record<string, unknown>;
  const nodes = ((raw.nodes as unknown[]) || []).map(mapGraphNodeDtoToDomain);
  const edges = ((raw.edges as unknown[]) || []).map(mapGraphEdgeDtoToDomain);

  // Warn about topology issues but do not crash
  const topology = validateGraphTopology(nodes, edges);
  if (!topology.valid) {
    log.warn(
      `Subgraph topology has ${topology.orphanedEdges.length} orphaned edge(s)`,
      { orphanedEdges: topology.orphanedEdges.length }
    );
  }

  const stats = raw.stats as Record<string, unknown> | undefined;

  return {
    rootEntityId: String(raw.root_entity_id || ''),
    nodes,
    edges,
    depth: Number(raw.depth ?? 0),
    stats: stats
      ? {
          totalNodes: Number(stats.total_nodes ?? 0),
          totalEdges: Number(stats.total_edges ?? 0),
          nodeTypes: (stats.node_types as Record<string, number>) || {},
          communities: Number(stats.communities ?? 0),
          density: Number(stats.density ?? 0),
        }
      : { totalNodes: 0, totalEdges: 0, nodeTypes: {}, communities: 0, density: 0 },
  };
}

export function mapGraphQueryResponseDtoToDomain(
  dto: GraphQueryResponseDto | Record<string, unknown>
): GraphQueryResult {
  const raw = dto as Record<string, unknown>;
  const entities = ((raw.entities as unknown[]) || []).map(mapGraphNodeDtoToDomain);
  const relationships = ((raw.relationships as unknown[]) || []).map(mapGraphEdgeDtoToDomain);

  const topology = validateGraphTopology(entities, relationships);
  if (!topology.valid) {
    log.warn(
      `Query result topology has ${topology.orphanedEdges.length} orphaned edge(s)`,
      { orphanedEdges: topology.orphanedEdges.length }
    );
  }

  const contextGraph = raw.context_graph as Record<string, unknown> | undefined;

  return {
    query: String(raw.query || ''),
    entities,
    relationships,
    contextGraph: contextGraph
      ? {
          nodes: ((contextGraph.nodes as unknown[]) || []).map(mapGraphNodeDtoToDomain),
          edges: ((contextGraph.edges as unknown[]) || []).map(mapGraphEdgeDtoToDomain),
        }
      : undefined,
    confidenceScore: Number(raw.confidence_score ?? 0),
    sources: Array.isArray(raw.sources) ? (raw.sources as string[]) : undefined,
    processingTimeMs: typeof raw.processing_time_ms === 'number' ? raw.processing_time_ms : undefined,
    answer: typeof raw.answer === 'string' ? raw.answer : undefined,
  };
}

export function mapEntityContextResponseDtoToDomain(
  dto: EntityContextResponseDto | Record<string, unknown>
): EntityContext {
  const raw = dto as Record<string, unknown>;
  const center = mapGraphNodeDtoToDomain(raw.center as Record<string, unknown>);
  const neighbors = ((raw.neighbors as unknown[]) || []).map(mapGraphNodeDtoToDomain);
  const relationships = ((raw.relationships as unknown[]) || []).map(mapGraphEdgeDtoToDomain);

  const allNodes = [center, ...neighbors];
  const topology = validateGraphTopology(allNodes, relationships);
  if (!topology.valid) {
    log.warn(
      `Entity context topology has ${topology.orphanedEdges.length} orphaned edge(s)`,
      { orphanedEdges: topology.orphanedEdges.length }
    );
  }

  return {
    entityId: String(raw.entity_id || ''),
    center,
    neighbors,
    relationships,
    entityCount: Number(raw.entity_count ?? 0),
    relationshipCount: Number(raw.relationship_count ?? 0),
  };
}

function mapGraphStatsDtoToDomain(
  dto: Record<string, unknown>
): GraphStats {
  return {
    totalNodes: Number(dto.total_nodes ?? 0),
    totalEdges: Number(dto.total_edges ?? 0),
    nodeTypes: (dto.node_types as Record<string, number>) || {},
    communities: Number(dto.communities ?? 0),
    density: Number(dto.density ?? 0),
  };
}

// ── Convenience: Map from generated OpenAPI types ────────────────────────────

/**
 * Maps the raw L3 SubgraphResponse OpenAPI type to domain model.
 * Use this when you have the generated type but haven't run Zod validation yet.
 */
export function mapGeneratedSubgraphToDomain(
  raw: components['schemas']['SubgraphResponse']
): GraphSubgraph {
  return mapSubgraphResponseDtoToDomain(raw as unknown as GraphSubgraphResponseDto);
}

/**
 * Maps the raw L3 GraphRAGResponse OpenAPI type to domain model.
 */
export function mapGeneratedQueryResultToDomain(
  raw: components['schemas']['GraphRAGResponse']
): GraphQueryResult {
  return mapGraphQueryResponseDtoToDomain(raw as unknown as GraphQueryResponseDto);
}

/**
 * Maps the raw L3 EntityContextResponse OpenAPI type to domain model.
 */
export function mapGeneratedEntityContextToDomain(
  raw: unknown
): EntityContext {
  return mapEntityContextResponseDtoToDomain(raw as unknown as EntityContextResponseDto);
}
