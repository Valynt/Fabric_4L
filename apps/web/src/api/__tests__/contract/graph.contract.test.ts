/**
 * Contract tests: Knowledge Graph (L3)
 *
 * Validates request/response shapes against contracts/openapi/layer3-knowledge.json.
 * Covers: GET /v1/value-trees/{entity_id}, GET /v1/value-trees/{entity_id}/paths,
 * and the entity/subgraph shapes used by the graph visualisation.
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";
import {
  GraphNodeSchema,
  ApiErrorSchema,
  assertSchema,
  assertSchemaRejects,
  fixtures,
} from "./_helpers";

// ── Value Tree schemas ────────────────────────────────────────────────────────

const ValueTreeNodeSchema: z.ZodType<{
  id: string;
  label: string;
  type: string;
  layer: number;
  confidence: number;
  properties: Record<string, unknown>;
  children?: unknown[];
}> = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  type: z.string().min(1),
  layer: z.number().int().min(1).max(4),
  confidence: z.number().min(0).max(1),
  properties: z.record(z.string(), z.unknown()),
  children: z.lazy(() => z.array(ValueTreeNodeSchema)).optional(),
});

const ValueTreeEdgeSchema = z.object({
  source: z.string().min(1),
  target: z.string().min(1),
  type: z.enum(["ENABLES", "BENEFITS", "DRIVES"]),
  weight: z.number().min(0).max(1),
});

const ValueTreeResponseSchema = z.object({
  root_entity_id: z.string().min(1),
  direction: z.enum(["upward", "downward"]),
  nodes: z.array(ValueTreeNodeSchema),
  edges: z.array(ValueTreeEdgeSchema),
  paths: z.array(
    z.object({
      length: z.number().int().positive(),
      nodes: z.array(z.string()),
    })
  ),
  stats: z.object({
    total_nodes: z.number().int().nonnegative(),
    total_edges: z.number().int().nonnegative(),
    by_layer: z.record(z.string(), z.number()),
    max_depth: z.number().int().nonnegative(),
  }),
});

const ValueTreePathSchema = z.object({
  nodes: z.array(
    z.object({
      id: z.string().min(1),
      name: z.string().min(1),
      type: z.string().min(1),
    })
  ),
  length: z.number().int().positive(),
});

// ── GET /v1/value-trees/{entity_id} ──────────────────────────────────────────

describe("Contract: GET /v1/value-trees/{entity_id}", () => {
  it("upward tree response has root_entity_id and nodes", () => {
    const resp = assertSchema(
      ValueTreeResponseSchema,
      {
        root_entity_id: "cap-001",
        direction: "upward",
        nodes: [
          {
            id: "cap-001",
            label: "Cloud Migration",
            type: "Capability",
            layer: 1,
            confidence: 0.95,
            properties: {},
          },
          {
            id: "vd-001",
            label: "Cost Reduction",
            type: "ValueDriver",
            layer: 4,
            confidence: 0.88,
            properties: {},
          },
        ],
        edges: [
          { source: "cap-001", target: "vd-001", type: "ENABLES", weight: 0.8 },
        ],
        paths: [{ length: 2, nodes: ["cap-001", "vd-001"] }],
        stats: {
          total_nodes: 2,
          total_edges: 1,
          by_layer: { "1": 1, "4": 1 },
          max_depth: 2,
        },
      },
      "ValueTreeResponse (upward)"
    );
    expect(resp.root_entity_id).toBe("cap-001");
    expect(resp.direction).toBe("upward");
    expect(resp.nodes).toHaveLength(2);
  });

  it("layer values are constrained to 1–4", () => {
    assertSchemaRejects(
      ValueTreeNodeSchema,
      {
        id: "n1",
        label: "Test",
        type: "Capability",
        layer: 5,
        confidence: 0.9,
        properties: {},
      },
      "ValueTreeNode with layer > 4"
    );
  });

  it("edge type must be one of ENABLES, BENEFITS, DRIVES", () => {
    assertSchemaRejects(
      ValueTreeEdgeSchema,
      { source: "n1", target: "n2", type: "RELATES_TO", weight: 0.5 },
      "ValueTreeEdge with unknown type"
    );
  });

  it("confidence is in [0,1]", () => {
    assertSchemaRejects(
      ValueTreeNodeSchema,
      {
        id: "n1",
        label: "Test",
        type: "Capability",
        layer: 1,
        confidence: 1.5,
        properties: {},
      },
      "ValueTreeNode with confidence > 1"
    );
  });

  it("empty tree (no nodes) is valid", () => {
    assertSchema(
      ValueTreeResponseSchema,
      {
        root_entity_id: "cap-999",
        direction: "downward",
        nodes: [],
        edges: [],
        paths: [],
        stats: { total_nodes: 0, total_edges: 0, by_layer: {}, max_depth: 0 },
      },
      "ValueTreeResponse (empty)"
    );
  });
});

// ── GET /v1/value-trees/{entity_id}/paths ────────────────────────────────────

describe("Contract: GET /v1/value-trees/{entity_id}/paths", () => {
  it("path list has nodes with id, name, type", () => {
    const paths = z.array(ValueTreePathSchema);
    const resp = assertSchema(
      paths,
      [
        {
          nodes: [
            { id: "cap-001", name: "Cloud Migration", type: "Capability" },
            { id: "uc-001", name: "Cost Optimisation", type: "UseCase" },
            { id: "vd-001", name: "Cost Reduction", type: "ValueDriver" },
          ],
          length: 3,
        },
      ],
      "ValueTreePathList"
    );
    expect(resp[0].length).toBe(3);
    expect(resp[0].nodes).toHaveLength(3);
  });

  it("path length must be positive", () => {
    assertSchemaRejects(
      ValueTreePathSchema,
      { nodes: [{ id: "n1", name: "Node", type: "Capability" }], length: 0 },
      "ValueTreePath with length 0"
    );
  });
});

// ── Subgraph / entity shapes ──────────────────────────────────────────────────

describe("Contract: subgraph and entity shapes", () => {
  it("graph node has required id, name, entity_type", () => {
    const node = assertSchema(
      GraphNodeSchema,
      fixtures.graphNode(),
      "GraphNode"
    );
    expect(node.id).toBeTruthy();
    expect(node.name).toBeTruthy();
    expect(node.entity_type).toBeTruthy();
  });
});

// ── Tenant context ────────────────────────────────────────────────────────────

describe("Contract: graph tenant context", () => {
  it("graph node can carry tenant_id for isolation", () => {
    const TenantScopedGraphNodeSchema = GraphNodeSchema.extend({
      tenant_id: z.uuid(),
    });
    const node = assertSchema(
      TenantScopedGraphNodeSchema,
      {
        id: "node-001",
        name: "Cloud Migration",
        entity_type: "capability",
        label: "Cloud Migration",
        type: "capability",
        tenant_id: "550e8400-e29b-41d4-a716-446655440000",
      },
      "TenantScopedGraphNode"
    );
    expect(node.tenant_id).toBe("550e8400-e29b-41d4-a716-446655440000");
  });
});

// ── Pagination ────────────────────────────────────────────────────────────────

describe("Contract: graph entity list pagination", () => {
  it("paginated entity list has required pagination fields", () => {
    const PaginatedGraphNodesSchema = z.object({
      items: z.array(GraphNodeSchema),
      total: z.number().int().nonnegative(),
      page: z.number().int().positive(),
      page_size: z.number().int().positive(),
      has_more: z.boolean(),
    });

    const resp = assertSchema(
      PaginatedGraphNodesSchema,
      { items: [], total: 0, page: 1, page_size: 20, has_more: false },
      "PaginatedGraphNodes (empty)"
    );
    expect(resp.has_more).toBe(false);
  });
});

// ── Auth failures ─────────────────────────────────────────────────────────────

describe("Contract: graph auth failures", () => {
  it("401 matches ApiError shape", () => {
    assertSchema(
      ApiErrorSchema,
      {
        error: {
          message: "Authentication required",
          code: "AUTHENTICATION_ERROR",
          request_id: "trace-graph-401",
        },
      },
      "ApiError (401)"
    );
  });

  it("403 cross-tenant entity access matches ApiError shape", () => {
    const err = assertSchema(
      ApiErrorSchema,
      {
        error: {
          message: "Entity belongs to a different tenant",
          code: "AUTHORIZATION_ERROR",
          request_id: "trace-graph-403",
        },
      },
      "ApiError (403 cross-tenant)"
    );
    expect(err.error.code).toBe("AUTHORIZATION_ERROR");
    expect(err.error.request_id).toBeTruthy();
  });

  it("entity not found 404 matches ApiError shape", () => {
    const err = assertSchema(
      ApiErrorSchema,
      {
        error: {
          message: "Entity not found",
          code: "NOT_FOUND",
          request_id: "trace-graph-404",
        },
      },
      "ApiError (404)"
    );
    expect(err.error.code).toBe("NOT_FOUND");
  });
});
