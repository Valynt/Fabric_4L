import { describe, it, expect } from "vitest";
import {
  GraphNodeSchema,
  GraphEdgeSchema,
  SubgraphResponseSchema,
  EntitySchema,
  EntityListResponseSchema,
  ValueTreeNodeSchema,
  ValueTreeSchema,
  ValidationError,
  validate,
  validateWithFallback,
} from "./validation";

describe("GraphNodeSchema", () => {
  it("accepts valid node", () => {
    const node = { id: "n1", name: "Node", type: "account", properties: {}, confidence_score: 0.5 };
    expect(GraphNodeSchema.parse(node)).toEqual(node);
  });

  it("rejects node without id", () => {
    expect(() => GraphNodeSchema.parse({ name: "Node", type: "account" })).toThrow();
  });

  it("rejects node without name", () => {
    expect(() => GraphNodeSchema.parse({ id: "n1", type: "account" })).toThrow();
  });
});

describe("GraphEdgeSchema", () => {
  it("accepts valid edge", () => {
    const edge = { source: "a", target: "b", relationship: "DRIVES" };
    expect(GraphEdgeSchema.parse(edge)).toEqual(edge);
  });

  it("rejects edge without source", () => {
    expect(() => GraphEdgeSchema.parse({ target: "b", relationship: "DRIVES" })).toThrow();
  });
});

describe("SubgraphResponseSchema", () => {
  it("accepts valid response", () => {
    const data = {
      root_entity_id: "e1",
      nodes: [{ id: "n1", name: "Node", type: "account" }],
      edges: [{ source: "n1", target: "n2", relationship: "DRIVES" }],
      depth: 2,
      stats: { total_nodes: 1, total_edges: 1, density: 0.5 },
    };
    expect(SubgraphResponseSchema.parse(data)).toEqual(data);
  });

  it("rejects missing stats", () => {
    expect(() =>
      SubgraphResponseSchema.parse({
        root_entity_id: "e1",
        nodes: [],
        edges: [],
        depth: 0,
      })
    ).toThrow();
  });
});

describe("EntitySchema", () => {
  it("accepts valid entity", () => {
    const entity = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "Entity",
      type: "account",
      domain: "example.com",
      status: "validated",
      properties: {},
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    };
    expect(EntitySchema.parse(entity)).toEqual(entity);
  });

  it("rejects invalid status", () => {
    expect(() =>
      EntitySchema.parse({
        id: "550e8400-e29b-41d4-a716-446655440000",
        name: "Entity",
        type: "account",
        status: "invalid",
        properties: {},
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      })
    ).toThrow();
  });
});

describe("EntityListResponseSchema", () => {
  it("accepts valid list", () => {
    const data = {
      results: [],
      total: 0,
      page: 1,
    };
    expect(EntityListResponseSchema.parse(data)).toEqual(data);
  });
});

describe("ValueTreeNodeSchema", () => {
  it("accepts valid tree node", () => {
    const node = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "Root",
      value: 100,
      confidence: 0.9,
    };
    expect(ValueTreeNodeSchema.parse(node)).toEqual(node);
  });

  it("accepts nested children", () => {
    const node = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      name: "Root",
      value: 100,
      confidence: 0.9,
      children: [
        {
          id: "550e8400-e29b-41d4-a716-446655440001",
          name: "Child",
          value: 50,
          confidence: 0.8,
        },
      ],
    };
    expect(ValueTreeNodeSchema.parse(node)).toEqual(node);
  });
});

describe("ValueTreeSchema", () => {
  it("accepts valid tree", () => {
    const tree = {
      id: "550e8400-e29b-41d4-a716-446655440000",
      entity_id: "550e8400-e29b-41d4-a716-446655440001",
      root_node: {
        id: "550e8400-e29b-41d4-a716-446655440002",
        name: "Root",
        value: 100,
        confidence: 0.9,
      },
      total_value: 100,
      currency: "USD",
      confidence: 0.9,
    };
    expect(ValueTreeSchema.parse(tree)).toEqual(tree);
  });
});

describe("validate", () => {
  it("returns data on success", () => {
    const data = { id: "n1", name: "Node", type: "account" };
    expect(validate(GraphNodeSchema, data, "node")).toEqual(data);
  });

  it("throws ValidationError on failure", () => {
    expect(() => validate(GraphNodeSchema, {}, "node")).toThrow(ValidationError);
  });
});

describe("validateWithFallback", () => {
  it("returns data on success", () => {
    const data = { id: "n1", name: "Node", type: "account" };
    expect(validateWithFallback(GraphNodeSchema, data, { id: "f", name: "F", type: "t" })).toEqual(data);
  });

  it("returns fallback on failure", () => {
    const fallback = { id: "f", name: "F", type: "t" };
    expect(validateWithFallback(GraphNodeSchema, {}, fallback)).toEqual(fallback);
  });
});
