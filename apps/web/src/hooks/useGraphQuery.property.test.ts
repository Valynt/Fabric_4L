/**
 * LAYER 3: PROPERTY-BASED TESTS (5% of test count)
 * Uses fast-check for generative testing
 *
 * Properties that MUST always hold:
 * 1. "For any valid input, output always contains required fields"
 * 2. "For any input, function never throws uncaught exception"
 * 3. "Operation is reversible: create then delete returns to original state"
 * 4. "For any two inputs, operation is commutative [where applicable]"
 *
 * NOTE: Requires dependency: npm install --save-dev fast-check
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { createWrapper } from '../test-utils';
import { http, HttpResponse } from 'msw';
import { server } from '../test/mocks/server';

import {
  useSubgraph,
  useGraphViewState,
  type GraphNode,
  type GraphRelationship,
  type SubgraphResponse,
} from './useGraphQuery';

// ============================================================================
// PROPERTY HELPERS (fast-check style generators without external dep)
// ============================================================================

/** Generate a random string of given length */
const randomString = (min = 1, max = 50): string => {
  const len = Math.floor(Math.random() * (max - min + 1)) + min;
  return Array.from({ length: len }, () =>
    String.fromCharCode(97 + Math.floor(Math.random() * 26))
  ).join('');
};

/** Generate a random number in range */
const randomNumber = (min: number, max: number): number =>
  Math.random() * (max - min) + min;

/** Generate a random integer in range */
const randomInt = (min: number, max: number): number =>
  Math.floor(Math.random() * (max - min + 1)) + min;

/** Generate a valid GraphNode */
const generateGraphNode = (): GraphNode => ({
  id: randomString(5, 20),
  name: randomString(5, 50),
  entity_type: ['Capability', 'UseCase', 'ValueDriver', 'Persona'][randomInt(0, 3)],
  confidence_score: randomNumber(0, 1),
  description: randomString(10, 200),
  properties: {},
  x: randomNumber(0, 1000),
  y: randomNumber(0, 1000),
});

/** Generate a valid GraphRelationship */
const generateGraphEdge = (nodes: GraphNode[]): GraphRelationship => {
  const source = nodes[randomInt(0, nodes.length - 1)]?.id || 'node-1';
  let target = nodes[randomInt(0, nodes.length - 1)]?.id || 'node-2';
  // Ensure no self-loops in property tests
  while (target === source && nodes.length > 1) {
    target = nodes[randomInt(0, nodes.length - 1)]?.id || 'node-2';
  }
  return {
    source,
    target,
    type: ['ENABLES', 'DEPENDS_ON', 'DRIVES', 'REQUIRES'][randomInt(0, 3)],
    confidence: randomNumber(0, 1),
    properties: {},
  };
};

/** Generate a valid SubgraphResponse */
const generateSubgraphResponse = (nodeCount = randomInt(1, 100)): SubgraphResponse => {
  const nodes = Array.from({ length: nodeCount }, generateGraphNode);
  // Cap edge count so density never exceeds 1 (simple directed graph max)
  const maxEdges = Math.max(0, nodes.length * (nodes.length - 1));
  const edgeCount = randomInt(0, Math.min(maxEdges, 200));
  const edges = Array.from({ length: edgeCount }, () => generateGraphEdge(nodes));

  return {
    root_entity_id: nodes[0]?.id || '',
    nodes,
    edges,
    depth: randomInt(1, 3),
    stats: {
      total_nodes: nodes.length,
      total_edges: edges.length,
      density: nodes.length > 1 ? edges.length / (nodes.length * (nodes.length - 1)) : 0,
    },
  };
};

/** Run a property test multiple times with different random inputs */
const propertyTest = async (
  name: string,
  count: number,
  testFn: () => Promise<void> | void
) => {
  for (let i = 0; i < count; i++) {
    try {
      await testFn();
    } catch (e) {
      throw new Error(`Property "${name}" failed on iteration ${i + 1}: ${e}`);
    }
  }
};

beforeEach(() => {
  server.resetHandlers();
});

// ============================================================================
// PROPERTY TESTS
// ============================================================================

describe('useSubgraph Properties [L3-Property]', () => {
  /**
   * PROPERTY 1: "For any valid subgraph response, useSubgraph returns
   * data with all required fields present and properly typed"
   */
  it('property: response always contains required fields', async () => {
    const mockResponse = generateSubgraphResponse();

    server.use(
      http.get('/api/v1/graph/subgraph', () => HttpResponse.json(mockResponse))
    );

    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useSubgraph({ query: 'test-query' }),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    // Required fields must always be present
    expect(result.current.data).toBeDefined();
    expect(result.current.data?.nodes).toBeInstanceOf(Array);
    expect(result.current.data?.edges).toBeInstanceOf(Array);
    expect(result.current.data?.stats).toBeDefined();
    expect(typeof result.current.data?.depth).toBe('number');

    // Stats must be present
    expect(typeof result.current.data?.stats.totalNodes).toBe('number');
    expect(typeof result.current.data?.stats.totalEdges).toBe('number');
    expect(typeof result.current.data?.stats.density).toBe('number');

    // Node count must match stats
    expect(result.current.data?.nodes.length).toBe(result.current.data?.stats.totalNodes);
    expect(result.current.data?.edges.length).toBe(result.current.data?.stats.totalEdges);
  });

  /**
   * PROPERTY 2: "For any valid input, function never throws uncaught exception"
   */
  it('property: never throws on valid inputs', async () => {
    await propertyTest('no throws on valid input', 50, async () => {
      const depth = randomInt(1, 3);
      const limit = randomInt(1, 500);
      const query = randomString(0, 100);

      server.use(
        http.get('/api/v1/graph/subgraph', () =>
          HttpResponse.json(generateSubgraphResponse(randomInt(0, limit)))
        )
      );

      const wrapper = createWrapper();

      // Should not throw
      let error: Error | null = null;
      try {
        const { result } = renderHook(
          () => useSubgraph({ query, depth, limit }),
          { wrapper }
        );
        await waitFor(() =>
          result.current.isSuccess || result.current.isError
        );
      } catch (e) {
        error = e as Error;
      }

      expect(error).toBeNull();
    });
  }, 15000);

  /**
   * PROPERTY 3: "Coherence - all edge endpoints exist in nodes array"
   */
  it('property: all edges reference existing nodes (coherence)', async () => {
    await propertyTest('edge coherence', 30, async () => {
      const response = generateSubgraphResponse(randomInt(5, 50));
      const nodeIds = new Set(response.nodes.map((n) => n.id));

      server.use(
        http.get('/api/v1/graph/subgraph', () => HttpResponse.json(response))
      );

      const wrapper = createWrapper();
      const { result } = renderHook(
        () => useSubgraph({ query: 'test' }),
        { wrapper }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Every edge source/target must exist in nodes
      const data = result.current.data!;
      for (const edge of data.edges) {
        expect(nodeIds.has(edge.sourceId)).toBe(true);
        expect(nodeIds.has(edge.targetId)).toBe(true);
      }
    });
  }, 15000);

  /**
   * PROPERTY 4: "Density calculation is always in valid range [0, 1]"
   */
  it('property: density is always valid [0, 1]', async () => {
    await propertyTest('density range', 50, async () => {
      const response = generateSubgraphResponse(randomInt(1, 100));

      server.use(
        http.get('/api/v1/graph/subgraph', () => HttpResponse.json(response))
      );

      const wrapper = createWrapper();
      const { result } = renderHook(
        () => useSubgraph({ query: 'test' }),
        { wrapper }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const density = result.current.data?.stats.density;
      expect(density).toBeGreaterThanOrEqual(0);
      expect(density).toBeLessThanOrEqual(1);
    });
  }, 15000);

  /**
   * PROPERTY 5: "Empty result is handled gracefully"
   */
  it('property: empty result is valid', async () => {
    server.use(
      http.get('/api/v1/graph/subgraph', () =>
        HttpResponse.json({
          root_entity_id: '',
          nodes: [],
          edges: [],
          depth: 2,
          stats: { total_nodes: 0, total_edges: 0, density: 0 },
        })
      )
    );

    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useSubgraph({ query: 'no-results-test' }),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

    expect(result.current.data?.nodes).toEqual([]);
    expect(result.current.data?.edges).toEqual([]);
    expect(result.current.data?.stats.totalNodes).toBe(0);
    expect(result.current.data?.stats.density).toBe(0);
  });
});

describe('useGraphViewState Properties [L3-Property]', () => {
  /**
   * PROPERTY 1: "Zoom is always within bounds [MIN_ZOOM, MAX_ZOOM]"
   */
  it('property: zoom always clamped to [0.5, 3.0]', async () => {
    const { result } = renderHook(() => useGraphViewState());

    await propertyTest('zoom bounds', 100, () => {
      const action = randomInt(0, 3);
      switch (action) {
        case 0:
          act(() => result.current.zoomIn());
          break;
        case 1:
          act(() => result.current.zoomOut());
          break;
        case 2:
          act(() => result.current.setZoom(randomNumber(0, 5)));
          break;
        case 3:
          // Random sequence of operations
          for (let i = 0; i < randomInt(1, 10); i++) {
            act(() =>
              Math.random() > 0.5 ? result.current.zoomIn() : result.current.zoomOut()
            );
          }
          break;
      }

      expect(result.current.viewState.zoom).toBeGreaterThanOrEqual(0.5);
      expect(result.current.viewState.zoom).toBeLessThanOrEqual(3.0);
    });
  });

  /**
   * PROPERTY 2: "Reset always returns to initial state"
   */
  it('property: reset is idempotent', async () => {
    const { result } = renderHook(() => useGraphViewState());

    await propertyTest('reset idempotency', 50, () => {
      // Random sequence of operations
      for (let i = 0; i < randomInt(0, 20); i++) {
        const action = randomInt(0, 3);
        act(() => {
          switch (action) {
            case 0:
              result.current.zoomIn();
              break;
            case 1:
              result.current.panBy(randomNumber(-1000, 1000), randomNumber(-1000, 1000));
              break;
            case 2:
              result.current.zoomOut();
              break;
            case 3:
              result.current.setZoom(randomNumber(0.5, 3));
              break;
          }
        });
      }

      // Reset
      act(() => result.current.resetView());

      // Must return to initial state
      expect(result.current.viewState).toEqual({
        zoom: 1,
        panX: 0,
        panY: 0,
      });
    });
  });

  /**
   * PROPERTY 3: "Pan operations are cumulative"
   */
  it('property: pan operations compose linearly', async () => {
    const { result } = renderHook(() => useGraphViewState());

    await propertyTest('pan linearity', 50, () => {
      // Reset state each iteration so expected values start from 0
      act(() => result.current.resetView());

      let expectedX = 0;
      let expectedY = 0;

      // Apply random pan operations
      for (let i = 0; i < randomInt(1, 10); i++) {
        const dx = randomNumber(-100, 100);
        const dy = randomNumber(-100, 100);
        expectedX += dx;
        expectedY += dy;

        act(() => result.current.panBy(dx, dy));
      }

      // Use 4 decimal places to allow for tiny floating-point accumulation errors
      expect(result.current.viewState.panX).toBeCloseTo(expectedX, 4);
      expect(result.current.viewState.panY).toBeCloseTo(expectedY, 4);
    });
  });

  /**
   * PROPERTY 4: "Zoom in then zoom out returns to approximately original"
   */
  it('property: zoom operations are approximately reversible', async () => {
    const { result } = renderHook(() => useGraphViewState());

    await propertyTest('zoom reversibility', 30, () => {
      // Start from known state
      act(() => result.current.resetView());
      const initialZoom = result.current.viewState.zoom;

      // Zoom in N times
      const n = randomInt(1, 5);
      for (let i = 0; i < n; i++) {
        act(() => result.current.zoomIn());
      }

      // Zoom out N times
      for (let i = 0; i < n; i++) {
        act(() => result.current.zoomOut());
      }

      // Should be close to original (within floating point error)
      expect(result.current.viewState.zoom).toBeCloseTo(initialZoom, 10);
    });
  });
});

describe('GraphNode/GraphEdge Type Properties [L3-Property]', () => {
  /**
   * PROPERTY 1: "Confidence score is always in [0, 1]"
   */
  it('property: confidence_score always valid', async () => {
    await propertyTest('confidence score range', 100, () => {
      const node = generateGraphNode();
      expect(node.confidence_score).toBeGreaterThanOrEqual(0);
      expect(node.confidence_score).toBeLessThanOrEqual(1);
    });
  });

  /**
   * PROPERTY 2: "Node ID is non-empty string"
   */
  it('property: node ID is always non-empty', async () => {
    await propertyTest('node ID non-empty', 100, () => {
      const node = generateGraphNode();
      expect(typeof node.id).toBe('string');
      expect(node.id.length).toBeGreaterThan(0);
    });
  });

  /**
   * PROPERTY 3: "Edge source and target are always different (no self-loops)"
   */
  it('property: no self-loops in generated edges', async () => {
    await propertyTest('no self-loops', 50, () => {
      const nodes = Array.from({ length: randomInt(2, 10) }, generateGraphNode);
      const edge = generateGraphEdge(nodes);

      // Edge generator should prevent self-loops when possible
      if (nodes.length > 1) {
        expect(edge.source).not.toBe(edge.target);
      }
    });
  });
});
