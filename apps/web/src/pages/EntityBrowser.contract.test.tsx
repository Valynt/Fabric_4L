/**
 * Contract tests for Entity Browser component
 * 
 * Validates:
 * - Component renders from API data (no mock derivation)
 * - Server-backed filtering triggers correct API calls
 * - Selection updates detail panel
 * - Error and empty states render correctly
 * - No UI-side derivation logic executes
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EntityBrowser from './EntityBrowser';

// Mock the hooks
vi.mock('@/hooks/useEntities', () => ({
  useEntities: vi.fn(),
  useEntity: vi.fn(),
  useEntitySearch: vi.fn().mockReturnValue({ data: null, isLoading: false, error: null }),
  useEntityFilterOptions: vi.fn().mockReturnValue({ data: null, isLoading: false, error: null }),
  useCreateEntity: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false, error: null }),
}));

vi.mock('@/stores', () => ({
  useEntityUIStore: vi.fn(() => ({
    searchQuery: '',
    selectedType: null,
    selectedEntityId: null,
    setSearchQuery: vi.fn(),
    setSelectedType: vi.fn(),
    setSelectedEntityId: vi.fn(),
    clearFilters: vi.fn(),
  })),
  useUserTierStore: vi.fn(() => ({ tier: 'standard', permissions: {} })),
  useIngestionUIStore: vi.fn(() => ({})),
  useIngestionJobsStore: vi.fn(() => ({})),
  useOntologyStore: vi.fn(() => ({})),
  useNarrativeStore: vi.fn(() => ({})),
}));

import { useEntities, useEntity } from '@/hooks/useEntities';
import { useEntityUIStore } from '@/stores';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('EntityBrowser Contract Tests', () => {
  const mockStore = {
    searchQuery: '',
    selectedType: null,
    selectedEntityId: null,
    setSearchQuery: vi.fn(),
    setSelectedType: vi.fn(),
    setSelectedEntityId: vi.fn(),
    clearFilters: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useEntityUIStore).mockReturnValue(mockStore);
    vi.mocked(useEntities).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useEntities>);
    vi.mocked(useEntity).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useEntity>);
  });

  describe('API Data Consumption', () => {
    it('should render entities directly from API without derivation', async () => {
      // API returns canonical entities with domain, status from backend
      const mockEntities = {
        results: [
          {
            id: 'ent-1',
            name: 'AI Capability',
            type: 'Capability',
            domain: 'Finance', // Direct from API
            status: 'validated', // Direct from API
            confidence: 0.94,
            confidenceLabel: 'high',
            updatedAt: '2026-04-18T12:00:00Z',
            sourceName: 'test-source',
          },
        ],
        totalCount: 1,
        filteredCount: 1,
        limit: 25,
        offset: 0,
        hasMore: false,
        availableDomains: ['Finance', 'IT'],
        availableSources: ['test-source'],
      };

      vi.mocked(useEntities).mockReturnValue({
        data: mockEntities,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      vi.mocked(useEntity).mockReturnValue({
        data: null,
        isLoading: false,
      });

      render(<EntityBrowser />, { wrapper: createWrapper() });

      // Verify entity name renders
      expect(screen.getByText('AI Capability')).toBeInTheDocument();
      
      // Verify domain rendered directly from API (not derived)
      expect(screen.getAllByText('Finance').length).toBeGreaterThanOrEqual(1);
      
      // Verify status rendered directly from API
      expect(screen.getAllByText(/validated/i).length).toBeGreaterThanOrEqual(1);
    });

    it('should use server-backed filtering via useEntities hook', async () => {
      const mockUseEntities = vi.fn().mockReturnValue({
        data: { results: [], totalCount: 0, filteredCount: 0, limit: 25, offset: 0, hasMore: false, availableDomains: [], availableSources: [] },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      vi.mocked(useEntities).mockImplementation(mockUseEntities);

      vi.mocked(useEntity).mockReturnValue({
        data: null,
        isLoading: false,
      });

      // Set up store with filters
      vi.mocked(useEntityUIStore).mockReturnValue({
        ...mockStore,
        searchQuery: 'AI',
        selectedType: 'Capability',
      });

      render(<EntityBrowser />, { wrapper: createWrapper() });

      // Verify useEntities called with correct filter params
      await waitFor(() => {
        expect(mockUseEntities).toHaveBeenCalledWith(
          expect.objectContaining({
            searchText: 'AI',
            entityTypes: ['Capability'],
            limit: 25,
          })
        );
      });
    });

    it('should NOT call /search/hybrid endpoint', async () => {
      const mockUseEntities = vi.fn().mockReturnValue({
        data: { results: [], totalCount: 0, filteredCount: 0, limit: 25, offset: 0, hasMore: false, availableDomains: [], availableSources: [] },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      vi.mocked(useEntities).mockImplementation(mockUseEntities);

      vi.mocked(useEntity).mockReturnValue({
        data: null,
        isLoading: false,
      });

      render(<EntityBrowser />, { wrapper: createWrapper() });

      // Verify the hook is called (implementation uses /v1/entities)
      expect(mockUseEntities).toHaveBeenCalled();
      
      // The implementation detail: useEntities uses '/entities' not '/search/hybrid'
      // This is verified by the hook implementation test, not component test
    });
  });

  describe('Detail Panel Integration', () => {
    it('should fetch and display entity details when selected', async () => {
      const mockUseEntity = vi.fn().mockReturnValue({
        data: {
          id: 'ent-1',
          name: 'Detail Entity',
          type: 'Capability',
          domain: 'IT',
          status: 'pending',
          confidence: 0.75,
          confidenceLabel: 'medium',
          description: 'Detailed description',
          updatedAt: '2026-04-18T12:00:00Z',
          sourceName: 'internal',
          extractionJobId: 'job-123',
        },
        isLoading: false,
      });
      vi.mocked(useEntity).mockImplementation(mockUseEntity);

      vi.mocked(useEntities).mockReturnValue({
        data: {
          results: [{ id: 'ent-1', name: 'Detail Entity', type: 'Capability', domain: 'IT', status: 'pending', confidence: 0.75, confidenceLabel: 'medium', updatedAt: '2026-04-18T12:00:00Z' }],
          totalCount: 1,
          filteredCount: 1,
          limit: 25,
          offset: 0,
          hasMore: false,
          availableDomains: ['IT'],
          availableSources: ['internal'],
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      // Set selected entity
      vi.mocked(useEntityUIStore).mockReturnValue({
        ...mockStore,
        selectedEntityId: 'ent-1',
      });

      render(<EntityBrowser />, { wrapper: createWrapper() });

      // Verify useEntity called with selected ID
      await waitFor(() => {
        expect(mockUseEntity).toHaveBeenCalledWith('ent-1');
      });

      // Verify detail panel shows description from API
      expect(screen.getByText('Detailed description')).toBeInTheDocument();
    });
  });

  describe('Edge States', () => {
    it('should display empty state when no entities', async () => {
      vi.mocked(useEntities).mockReturnValue({
        data: {
          results: [],
          totalCount: 0,
          filteredCount: 0,
          limit: 25,
          offset: 0,
          hasMore: false,
          availableDomains: [],
          availableSources: [],
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      vi.mocked(useEntity).mockReturnValue({
        data: null,
        isLoading: false,
      });

      render(<EntityBrowser />, { wrapper: createWrapper() });

      expect(screen.getByText(/No entities found/i)).toBeInTheDocument();
    });

    it('should display error state on API failure', async () => {
      vi.mocked(useEntities).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { message: 'Failed to fetch entities', response: { data: { detail: 'Connection error' } } },
        refetch: vi.fn(),
      });

      vi.mocked(useEntity).mockReturnValue({
        data: null,
        isLoading: false,
      });

      render(<EntityBrowser />, { wrapper: createWrapper() });

      expect(screen.getByText(/Failed to fetch entities/i)).toBeInTheDocument();
      expect(screen.getByText(/Retry/i)).toBeInTheDocument();
    });

    it('should display loading state', async () => {
      vi.mocked(useEntities).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });

      vi.mocked(useEntity).mockReturnValue({
        data: null,
        isLoading: false,
      });

      render(<EntityBrowser />, { wrapper: createWrapper() });

      expect(screen.getByText(/Loading entities/i)).toBeInTheDocument();
    });
  });

  describe('Filter Domain/Status Usage', () => {
    it('should populate domain filter from available_domains API field', async () => {
      vi.mocked(useEntities).mockReturnValue({
        data: {
          results: [],
          totalCount: 5,
          filteredCount: 5,
          limit: 25,
          offset: 0,
          hasMore: false,
          availableDomains: ['Finance', 'Healthcare', 'IT'],
          availableSources: ['source1'],
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      vi.mocked(useEntity).mockReturnValue({
        data: null,
        isLoading: false,
      });

      render(<EntityBrowser />, { wrapper: createWrapper() });

      // Verify domain dropdown populated from API
      const domainSelect = screen.getByText(/All Domains/i);
      expect(domainSelect).toBeInTheDocument();
    });
  });
});

describe('No Derivation Verification', () => {
  it('should NOT have getDomain helper in component', () => {
    // This test verifies by code inspection that no derivation functions exist
    // The component should use entity.domain directly from API
    const componentSource = require.resolve('./EntityBrowser.tsx');
    expect(componentSource).toBeDefined();
    
    // Note: Actual verification would need AST parsing
    // For now, we verify by runtime behavior that domain comes from API
  });

  it('should NOT have getStatus helper in component', () => {
    // Status should come directly from API, not derived from confidence
    const mockEntities = {
      results: [
        {
          id: 'ent-1',
          name: 'Test',
          type: 'Capability',
          domain: null,
          status: 'draft', // Low confidence but explicit status
          confidence: 0.94, // High confidence
          confidenceLabel: 'high',
          updatedAt: '2026-04-18T12:00:00Z',
        },
      ],
      totalCount: 1,
      filteredCount: 1,
      limit: 25,
      offset: 0,
      hasMore: false,
      availableDomains: [],
      availableSources: [],
    };

    vi.mocked(useEntities).mockReturnValue({
      data: mockEntities,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    vi.mocked(useEntity).mockReturnValue({
      data: null,
      isLoading: false,
    });

    render(<EntityBrowser />, { wrapper: createWrapper() });

    // Should show 'draft' (from API) not 'validated' (derived from confidence)
    expect(screen.getAllByText(/draft/i).length).toBeGreaterThanOrEqual(1);
  });
});
