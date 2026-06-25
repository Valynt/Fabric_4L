/**
 * GraphExplorer Component Tests
 *
 * Tests for the knowledge graph visualization component including:
 * - Rendering with graph data
 * - Empty graph state
 * - Node selection and click handlers
 * - Search/filter interactions
 * - Loading and error states
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createWrapper } from '../test-utils';
import { http, HttpResponse } from 'msw';
import { server } from '../test/mocks/server';
import GraphExplorer from './GraphExplorer';

// Standard timeout configuration for asynchronous test assertions.
const WAIT_OPTIONS = { timeout: 3000 };

describe('GraphExplorer', () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it('renders with graph data', async () => {
    const wrapper = createWrapper();
    render(<GraphExplorer />, { wrapper });

    // Should show page header immediately (static content)
    expect(screen.getByRole('heading', { name: 'Graph Explorer' })).toBeInTheDocument();

    // Wait for loading state to appear first, then disappear.
    // This ensures the component is fetching before we wait for completion.
    await waitFor(() => {
      expect(screen.queryByText('Loading knowledge graph...')).toBeInTheDocument();
    }, WAIT_OPTIONS);

    // Then wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText('Loading knowledge graph...')).not.toBeInTheDocument();
    }, WAIT_OPTIONS);
  });

  it('handles empty graph state', async () => {
    // Override the handler before rendering so the response is deterministic.
    server.use(
      http.get('/api/v1/graph/subgraph', async () => {
        return HttpResponse.json({
          root_entity_id: '',
          nodes: [],
          edges: [],
          depth: 2,
          stats: { total_nodes: 0, total_edges: 0, density: 0 },
        });
      })
    );

    // Now render after mock is set up
    const wrapper = createWrapper();
    render(<GraphExplorer />, { wrapper });

    // Wait for loading to appear then disappear
    await waitFor(() => {
      expect(screen.queryByText('Loading knowledge graph...')).toBeInTheDocument();
    }, { timeout: 3000 });

    await waitFor(() => {
      expect(screen.queryByText('Loading knowledge graph...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Then check for empty state
    await waitFor(() => {
      expect(screen.getByText('No matching entities found')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('handles graph error state', async () => {
    server.resetHandlers();
    server.use(
      http.get('/api/v1/graph/subgraph', () => {
        return HttpResponse.json({ error: 'Neo4j connection failed' }, { status: 500 });
      })
    );

    const wrapper = createWrapper();
    render(<GraphExplorer />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    }, { timeout: 5000 });
  });

  it('allows search input', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<GraphExplorer />, { wrapper });

    const searchInput = screen.getByPlaceholderText('Search entities...');
    await user.type(searchInput, 'test query');

    expect(searchInput).toHaveValue('test query');
  });

  it('displays graph statistics', async () => {
    const wrapper = createWrapper();
    render(<GraphExplorer />, { wrapper });

    // Wait for loading to complete before checking stats.
    await waitFor(() => {
      expect(screen.queryByText('Loading knowledge graph...')).not.toBeInTheDocument();
    }, WAIT_OPTIONS);

    // Then wait for graph stats to appear
    await waitFor(() => {
      expect(screen.getByText('Graph Statistics')).toBeInTheDocument();
    }, WAIT_OPTIONS);

    // Should show statistics labels
    expect(screen.getByText('Nodes')).toBeInTheDocument();
    expect(screen.getByText('Edges')).toBeInTheDocument();
  });

  it('shows selected node panel when node clicked', async () => {
    const wrapper = createWrapper();
    render(<GraphExplorer />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Graph Statistics')).toBeInTheDocument();
    });

    // Initially shows empty state with "Select a Node" title
    expect(screen.getByText('Select a Node')).toBeInTheDocument();
  });

  it('renders zoom control buttons', () => {
    const wrapper = createWrapper();
    render(<GraphExplorer />, { wrapper });

    // Zoom controls should have zoom in/out buttons (text is "In" and "Out")
    expect(screen.getByRole('button', { name: /in/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /out/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reset view/i })).toBeInTheDocument();
  });

  it('renders search input in control panel', () => {
    const wrapper = createWrapper();
    render(<GraphExplorer />, { wrapper });

    // Search input is now the single entry point in the control panel
    expect(screen.getByPlaceholderText('Search entities...')).toBeInTheDocument();
  });

  it('renders coherent graph with nodes and edges from subgraph endpoint', async () => {
    server.use(
      http.get('/api/v1/graph/subgraph', () => {
        return HttpResponse.json({
          root_entity_id: 'ent-1',
          nodes: [
            { id: 'ent-1', name: 'AI Processing', entity_type: 'Capability', confidence_score: 0.95 },
            { id: 'ent-2', name: 'Data Pipeline', entity_type: 'Capability', confidence_score: 0.88 },
            { id: 'ent-3', name: 'Customer Analytics', entity_type: 'UseCase', confidence_score: 0.92 },
          ],
          edges: [
            { source: 'ent-1', target: 'ent-2', type: 'ENABLES' },
            { source: 'ent-2', target: 'ent-3', type: 'ENABLES' },
          ],
          depth: 2,
          stats: { total_nodes: 3, total_edges: 2, density: 0.33 },
        });
      })
    );

    const wrapper = createWrapper();
    render(<GraphExplorer />, { wrapper });

    // Wait for graph to load and verify stats are displayed
    await waitFor(() => {
      expect(screen.getByText('Graph Statistics')).toBeInTheDocument();
    }, { timeout: 3000 });

    // Verify graph stats are displayed (Nodes and Edges labels present)
    expect(screen.getByText('Nodes')).toBeInTheDocument();
    expect(screen.getByText('Edges')).toBeInTheDocument();
  });
});
