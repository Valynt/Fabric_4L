import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import {
  validateOrThrow,
  validateOrNull,
  validateObject,
  ValidationError,
  EntitySchema,
  EntityListResponseSchema,
  GraphNodeSchema,
  GraphEdgeSchema,
  SubgraphResponseSchema,
  GraphQueryResponseSchema,
  EntityContextResponseSchema,
  EntityTraversalResponseSchema,
} from './schemas';
import { FormulaSchema } from '@/lib/schemas/formula';
import { ExtractedEntitySchema, ExtractionResultsResponseSchema } from '@/api/protocol/extraction';

// ── ValidationError ──────────────────────────────────────────────────────────

describe('ValidationError', () => {
  it('is an instance of Error', () => {
    const err = new ValidationError('test message', 'test-context');
    expect(err).toBeInstanceOf(Error);
  });

  it('has name "ValidationError"', () => {
    const err = new ValidationError('msg', 'ctx');
    expect(err.name).toBe('ValidationError');
  });

  it('exposes context property', () => {
    const err = new ValidationError('msg', 'my-context');
    expect(err.context).toBe('my-context');
  });

  it('exposes issues property when provided', () => {
    const issues: z.ZodIssue[] = [
      { code: 'custom', message: 'bad', path: ['field'] },
    ];
    const err = new ValidationError('msg', 'ctx', issues);
    expect(err.issues).toEqual(issues);
  });

  it('has undefined issues when not provided', () => {
    const err = new ValidationError('msg', 'ctx');
    expect(err.issues).toBeUndefined();
  });
});

// ── validateOrThrow ───────────────────────────────────────────────────────────

describe('validateOrThrow', () => {
  const SimpleSchema = z.object({ name: z.string(), age: z.number() });

  it('returns validated data when input is valid', () => {
    const result = validateOrThrow(SimpleSchema, { name: 'Alice', age: 30 }, 'user');
    expect(result).toEqual({ name: 'Alice', age: 30 });
  });

  it('throws ValidationError when input is invalid', () => {
    expect(() =>
      validateOrThrow(SimpleSchema, { name: 123, age: 'bad' }, 'user')
    ).toThrowError(ValidationError);
  });

  it('includes context in error message', () => {
    let caught: ValidationError | undefined;
    try {
      validateOrThrow(SimpleSchema, {}, 'my-context');
    } catch (e) {
      caught = e as ValidationError;
    }
    expect(caught?.message).toContain('my-context');
  });

  it('includes field paths in error message', () => {
    let caught: ValidationError | undefined;
    try {
      validateOrThrow(SimpleSchema, { name: 123, age: 'bad' }, 'user');
    } catch (e) {
      caught = e as ValidationError;
    }
    expect(caught?.message).toContain('name');
  });

  it('includes ZodIssue[] on thrown error', () => {
    let caught: ValidationError | undefined;
    try {
      validateOrThrow(SimpleSchema, {}, 'ctx');
    } catch (e) {
      caught = e as ValidationError;
    }
    expect(Array.isArray(caught?.issues)).toBe(true);
    expect(caught!.issues!.length).toBeGreaterThan(0);
  });
});

// ── validateOrNull ────────────────────────────────────────────────────────────

describe('validateOrNull', () => {
  const SimpleSchema = z.object({ value: z.string() });

  it('returns validated data when input is valid', () => {
    expect(validateOrNull(SimpleSchema, { value: 'ok' })).toEqual({ value: 'ok' });
  });

  it('returns null when input is invalid', () => {
    expect(validateOrNull(SimpleSchema, { value: 42 })).toBeNull();
  });

  it('returns null for null input', () => {
    expect(validateOrNull(SimpleSchema, null)).toBeNull();
  });

  it('returns null for undefined input', () => {
    expect(validateOrNull(SimpleSchema, undefined)).toBeNull();
  });
});

// ── validateObject ────────────────────────────────────────────────────────────

describe('validateObject', () => {
  it('returns the value when it is a plain object', () => {
    const obj = { a: 1, b: 'two' };
    expect(validateObject(obj, 'ctx')).toBe(obj);
  });

  it('throws ValidationError for null', () => {
    expect(() => validateObject(null, 'ctx')).toThrowError(ValidationError);
  });

  it('throws ValidationError for arrays', () => {
    expect(() => validateObject([1, 2, 3], 'ctx')).toThrowError(ValidationError);
  });

  it('throws ValidationError for strings', () => {
    expect(() => validateObject('string', 'ctx')).toThrowError(ValidationError);
  });

  it('throws ValidationError for numbers', () => {
    expect(() => validateObject(42, 'ctx')).toThrowError(ValidationError);
  });

  it('includes context in the error message', () => {
    let caught: ValidationError | undefined;
    try {
      validateObject(null, 'my-object-ctx');
    } catch (e) {
      caught = e as ValidationError;
    }
    expect(caught?.message).toContain('my-object-ctx');
  });
});

// ── EntitySchema ─────────────────────────────────────────────────────────────

describe('EntitySchema', () => {
  const validEntity = {
    id: 'ent-1',
    name: 'Test Entity',
    entity_type: 'capability',
    status: 'validated' as const,
    confidence: 0.9,
    confidence_label: 'high' as const,
    updated_at: '2024-01-01T00:00:00Z',
  };

  it('parses a valid entity', () => {
    const result = EntitySchema.safeParse(validEntity);
    expect(result.success).toBe(true);
  });

  it('applies default status of "draft"', () => {
    const { status: _, ...withoutStatus } = validEntity;
    const result = EntitySchema.safeParse(withoutStatus);
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.status).toBe('draft');
  });

  it('applies default confidence of 0', () => {
    const { confidence: _, ...withoutConfidence } = validEntity;
    const result = EntitySchema.safeParse(withoutConfidence);
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.confidence).toBe(0);
  });

  it('rejects invalid status', () => {
    const result = EntitySchema.safeParse({ ...validEntity, status: 'unknown' });
    expect(result.success).toBe(false);
  });

  it('rejects confidence outside [0, 1]', () => {
    const result = EntitySchema.safeParse({ ...validEntity, confidence: 1.5 });
    expect(result.success).toBe(false);
  });
});

// ── EntityListResponseSchema ──────────────────────────────────────────────────

describe('EntityListResponseSchema', () => {
  it('parses a valid entity list response', () => {
    const result = EntityListResponseSchema.safeParse({
      results: [],
      total_count: 0,
      filtered_count: 0,
      limit: 50,
      offset: 0,
      has_more: false,
      available_domains: [],
      available_sources: [],
    });
    expect(result.success).toBe(true);
  });

  it('applies defaults for missing optional fields', () => {
    const result = EntityListResponseSchema.safeParse({ results: [] });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.total_count).toBe(0);
      expect(result.data.has_more).toBe(false);
      expect(result.data.available_domains).toEqual([]);
    }
  });
});

// ── GraphNodeSchema ───────────────────────────────────────────────────────────

describe('GraphNodeSchema', () => {
  it('parses a valid graph node', () => {
    const result = GraphNodeSchema.safeParse({
      id: 'n1',
      name: 'Node 1',
      entity_type: 'capability',
    });
    expect(result.success).toBe(true);
  });

  it('applies default confidence_score of 0.8', () => {
    const result = GraphNodeSchema.safeParse({
      id: 'n1',
      name: 'Node 1',
      entity_type: 'capability',
    });
    if (result.success) expect(result.data.confidence_score).toBe(0.8);
  });

  it('rejects nodes without required fields', () => {
    expect(GraphNodeSchema.safeParse({ name: 'Node 1' }).success).toBe(false);
    expect(GraphNodeSchema.safeParse({ id: 'n1' }).success).toBe(false);
  });
});

// ── GraphEdgeSchema ───────────────────────────────────────────────────────────

describe('GraphEdgeSchema', () => {
  it('parses a valid graph edge', () => {
    const result = GraphEdgeSchema.safeParse({
      source: 'n1',
      target: 'n2',
      type: 'RELATES_TO',
    });
    expect(result.success).toBe(true);
  });

  it('rejects edges without required fields', () => {
    expect(GraphEdgeSchema.safeParse({ source: 'n1', target: 'n2' }).success).toBe(false);
  });
});

// ── SubgraphResponseSchema ────────────────────────────────────────────────────

describe('SubgraphResponseSchema', () => {
  it('parses a valid subgraph response', () => {
    const result = SubgraphResponseSchema.safeParse({
      root_entity_id: 'n1',
      nodes: [],
      edges: [],
      depth: 2,
      stats: { total_nodes: 0, total_edges: 0, density: 0 },
    });
    expect(result.success).toBe(true);
  });
});

// ── GraphQueryResponseSchema ──────────────────────────────────────────────────

describe('GraphQueryResponseSchema', () => {
  it('parses a minimal valid graph query response', () => {
    const result = GraphQueryResponseSchema.safeParse({ query: 'test query' });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.entities).toEqual([]);
      expect(result.data.confidence_score).toBe(0);
    }
  });
});

// ── EntityContextResponseSchema ───────────────────────────────────────────────

describe('EntityContextResponseSchema', () => {
  const center = { id: 'n1', name: 'Center', entity_type: 'capability', confidence_score: 0.8 };

  it('parses a valid entity context response', () => {
    const result = EntityContextResponseSchema.safeParse({
      entity_id: 'n1',
      center,
      neighbors: [],
      relationships: [],
      entity_count: 1,
      relationship_count: 0,
    });
    expect(result.success).toBe(true);
  });
});

// ── EntityTraversalResponseSchema ─────────────────────────────────────────────

describe('EntityTraversalResponseSchema', () => {
  it('parses a valid traversal response', () => {
    const result = EntityTraversalResponseSchema.safeParse({
      start_entity_id: 'n1',
      direction: 'outbound',
      paths: [],
      path_count: 0,
    });
    expect(result.success).toBe(true);
  });

  it('applies default empty paths array', () => {
    const result = EntityTraversalResponseSchema.safeParse({
      start_entity_id: 'n1',
      direction: 'outbound',
    });
    expect(result.success).toBe(true);
    if (result.success) expect(result.data.paths).toEqual([]);
  });
});

// ── FormulaSchema (lib/schemas/formula.ts) ──────────────────────────────────

describe('FormulaSchema variables shape', () => {
  const baseFormula = {
    id: 'formula-1',
    name: 'ROI',
  };

  it('accepts array variables used by formula creation/list consumers', () => {
    const result = FormulaSchema.safeParse({ ...baseFormula, variables: ['revenue', 'cost'] });
    expect(result.success).toBe(true);
  });

  it('accepts object variables used by evaluation/scenario contract payloads', () => {
    const result = FormulaSchema.safeParse({
      ...baseFormula,
      variables: { annual_savings: 500000, implementation_cost: 200000 },
    });
    expect(result.success).toBe(true);
  });

  it('rejects invalid scalar variables payload', () => {
    const result = FormulaSchema.safeParse({ ...baseFormula, variables: 42 });
    expect(result.success).toBe(false);
  });
});

// ── Extraction protocol entity/result schema tightening ─────────────────────

describe('ExtractedEntitySchema attributes shape', () => {
  const baseEntity = {
    entity_id: 'e-1',
    type: 'organization',
    name: 'Acme',
    confidence: 0.91,
  };

  it('accepts flexible attribute object values', () => {
    const result = ExtractedEntitySchema.safeParse({
      ...baseEntity,
      attributes: {
        revenue: 1000000,
        tags: ['finance', 'public'],
        metadata: { source: '10-k' },
        nullable: null,
      },
    });
    expect(result.success).toBe(true);
  });

  it('rejects non-object attributes payloads', () => {
    const result = ExtractedEntitySchema.safeParse({ ...baseEntity, attributes: 'bad-shape' });
    expect(result.success).toBe(false);
  });
});

describe('ExtractionResultsResponseSchema', () => {
  it('accepts valid extraction results response payload', () => {
    const result = ExtractionResultsResponseSchema.safeParse({
      summary: {
        job_id: 'job-1',
        total_entities: 3,
        returned_entities: 3,
        page: 1,
        page_size: 50,
        total_pages: 1,
        mode: 'full',
      },
      entities: [
        {
          entity_id: 'e-1',
          type: 'organization',
          name: 'Acme',
          confidence: 0.91,
          attributes: { sector: 'manufacturing' },
        },
      ],
    });
    expect(result.success).toBe(true);
  });

  it('rejects entities with malformed attributes', () => {
    const result = ExtractionResultsResponseSchema.safeParse({
      summary: {
        job_id: 'job-1',
        total_entities: 1,
        returned_entities: 1,
        page: 1,
        page_size: 50,
        total_pages: 1,
        mode: 'summary',
      },
      entities: [
        {
          entity_id: 'e-1',
          type: 'organization',
          name: 'Acme',
          confidence: 0.91,
          attributes: 999,
        },
      ],
    });
    expect(result.success).toBe(false);
  });
});
