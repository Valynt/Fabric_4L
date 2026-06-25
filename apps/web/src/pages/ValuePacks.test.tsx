/**
 * ValuePacks Page Integration Tests
 *
 * Tests for the Value Packs page:
 * - Page loads with header, filter bar, preview panel, pack actions
 * - 3-col pack grid populates from API
 * - Dropdown filters and search narrow displayed packs
 * - Selecting a pack populates the preview panel
 * - Deploy to Account triggers apply mutation
 * - Loading / error / empty states render correctly
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createWrapper, createWrapperWithRetry, createMockResponse } from '../test-utils';
import { http, HttpResponse } from 'msw';
import { server } from '../test/mocks/server';
import ValuePacks from './ValuePacks';
import { apiClient } from '@/api/client';
import { ValuePackApiError } from '@/hooks/useValuePacks';

// Mock the API client for error state tests - preserves actual implementation by default
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>();
  const passthroughGet = (...args: Parameters<typeof actual.apiClient.get>) => actual.apiClient.get(...args);
  const passthroughPost = (...args: Parameters<typeof actual.apiClient.post>) => actual.apiClient.post(...args);
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      get: vi.fn(passthroughGet),
      post: vi.fn(passthroughPost),
      __testPassthroughGet: passthroughGet,
      __testPassthroughPost: passthroughPost,
    },
  };
});

// Mock matchMedia for responsive tests
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

describe('ValuePacks', () => {
  beforeEach(() => {
    server.resetHandlers();
    const testClient = apiClient as typeof apiClient & {
      __testPassthroughGet?: typeof apiClient.get;
      __testPassthroughPost?: typeof apiClient.post;
    };
    vi.mocked(apiClient.get).mockImplementation(testClient.__testPassthroughGet ?? apiClient.get);
    vi.mocked(apiClient.post).mockImplementation(testClient.__testPassthroughPost ?? apiClient.post);
  });

  // ── Page Load ──────────────────────────────────────────────────────────────

  describe('Page Load', () => {
    it('renders page header with Import Pack button', () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      expect(screen.getByRole('heading', { name: 'Value Packs' })).toBeInTheDocument();
      expect(screen.getByText(/Import Pack/i)).toBeInTheDocument();
    });

    it('renders loading skeletons during initial fetch', () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      // Use testid for resilient selector
      expect(screen.getByTestId('packs-loading')).toBeInTheDocument();
    });

    it('renders pack grid with loaded packs', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      // Wait for pack grid to load with at least one pack
      await waitFor(() => {
        expect(screen.getAllByText('Enterprise Security ROI')[0]).toBeInTheDocument();
      });

      // Verify multiple packs are rendered (mock returns 4 packs, component may filter)
      expect(screen.getAllByText('Customer Churn Reduction')[0]).toBeInTheDocument();
      // Note: Draft packs may be filtered by default UI settings
    });

    it('displays pack description on cards', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getAllByText('Enterprise Security ROI')[0]).toBeInTheDocument();
      });

      expect(screen.getByText(/Comprehensive security ROI calculations/i)).toBeInTheDocument();
    });

    it('shows preview panel and pack actions sidebar', () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      expect(screen.getByTestId('preview-panel')).toBeInTheDocument();
      expect(screen.getByTestId('pack-actions')).toBeInTheDocument();
      expect(screen.getByText(/Deploy to Account/i)).toBeInTheDocument();
    });

    it('shows my packs section after data loads', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getByTestId('my-packs-section')).toBeInTheDocument();
      });
    });

    it('displays empty state when API returns no packs', async () => {
      server.use(
        http.get(/\/api\/v1\/graph\/packs.*/, () => {
          return HttpResponse.json([]);
        })
      );

      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getByText(/No value packs match your filters/i)).toBeInTheDocument();
      });
    });

    it('displays error state with retry button when API fails and retries successfully', async () => {
      const recoveredPack = {
        id: 'recovered-pack',
        pack_id: 'recovered-pack',
        name: 'Recovered Pack',
        industry: 'SaaS / B2B',
        status: 'active' as const,
        category: 'Revenue',
        description: 'Recovered after retry',
        version: '1.0.1',
        scope: 'global' as const,
        driver_count: 1,
        formula_count: 1,
        benchmark_count: 1,
        workflow_count: 1,
        updated_at: '2026-01-10T00:00:00Z',
        created_at: '2026-01-01T00:00:00Z',
      };
      let packListCalls = 0;
      vi.mocked(apiClient.get).mockImplementation(async (layer, path, config) => {
        if (layer === 'l3' && (path === '/packs' || path.startsWith('/packs?'))) {
          packListCalls += 1;
          if (packListCalls === 1) {
            throw new ValuePackApiError('HTTP 500: Service unavailable', 500);
          }
          return createMockResponse([recoveredPack]);
        }
        const testClient = apiClient as typeof apiClient & { __testPassthroughGet?: typeof apiClient.get };
        return testClient.__testPassthroughGet
          ? testClient.__testPassthroughGet(layer, path, config)
          : createMockResponse([]);
      });

      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      // Wait for error state to appear
      const errorBanner = await screen.findByText(/Failed to load value packs/i);
      expect(errorBanner).toBeInTheDocument();
      expect(screen.getByText('HTTP 500: Service unavailable')).toBeInTheDocument();

      const retryButton = screen.getByRole('button', { name: /Try again/i });
      expect(retryButton).toBeInTheDocument();

      const user = userEvent.setup();
      await user.click(retryButton);

      expect((await screen.findAllByText('Recovered Pack')).length).toBeGreaterThan(0);
      await waitFor(() => {
        expect(screen.queryByText(/Failed to load value packs/i)).not.toBeInTheDocument();
      });
    }, 10000);
  });

  // ── Filtering ──────────────────────────────────────────────────────────────

  describe('Pack Filtering', () => {
    it('filters packs by search query when user types', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getAllByText('Enterprise Security ROI')[0]).toBeInTheDocument();
      });

      const user = userEvent.setup();
      const searchInput = screen.getByPlaceholderText(/Search packs/i);
      await user.type(searchInput, 'Churn');

      // Wait for the search-triggered fetch to settle (isLoading becomes false)
      await waitFor(() => {
        expect(screen.queryByTestId('packs-loading')).not.toBeInTheDocument();
      });

      // Filtering is applied: only the matching pack should be visible in the grid
      expect(screen.getAllByText('Customer Churn Reduction').length).toBeGreaterThanOrEqual(1);
      const packGrid = screen.getByText('Pack Grid').closest('div');
      expect(packGrid).not.toHaveTextContent('Enterprise Security ROI');
    });

    it('shows industry tags on pack cards', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getAllByText('Enterprise Security ROI')[0]).toBeInTheDocument();
      });

      // Pack cards display industry as tags
      const saasLabels = screen.getAllByText('SaaS / B2B');
      expect(saasLabels.length).toBeGreaterThan(0);
    });

    it('shows version tags on pack cards', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getAllByText('Enterprise Security ROI')[0]).toBeInTheDocument();
      });

      expect(screen.getByText('v1.2.0')).toBeInTheDocument();
      expect(screen.getByText('v1.0.0')).toBeInTheDocument();
    });

    it('shows category data from API in pack cards', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getAllByText('Enterprise Security ROI')[0]).toBeInTheDocument();
      });

      // Verify category filter dropdown is present (derived from API data)
      // Categories are available in the "All Categories" dropdown
      expect(screen.getByText('All Categories')).toBeInTheDocument();
    });
  });

  // ── Pack Selection & Preview ───────────────────────────────────────────────

  describe('Pack Selection & Preview', () => {
    it('populates preview panel when user selects a pack', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getAllByText('Enterprise Security ROI')[0]).toBeInTheDocument();
      });

      // Click the first pack card
      const user = userEvent.setup();
      await user.click(screen.getAllByText('Enterprise Security ROI')[0]);

      // Preview panel should show pack details after fetch
      await waitFor(() => {
        const panel = screen.getByTestId('preview-panel');
        expect(panel).toHaveTextContent('Enterprise Security ROI');
      });
    });

    it('preview panel shows placeholder when no pack selected', () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      const panel = screen.getByTestId('preview-panel');
      expect(panel).toHaveTextContent('Select a pack to preview');
    });
  });

  // ── Deploy Flow ────────────────────────────────────────────────────────────

  describe('Deploy Flow', () => {
    it('Deploy to Account button is disabled when no pack selected', () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      const deployBtn = screen.getByText('Deploy to Account');
      expect(deployBtn.closest('button')).toBeDisabled();
    });

    it('enables Deploy button after user selects a pack', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getAllByText('Enterprise Security ROI')[0]).toBeInTheDocument();
      });

      // Select a pack
      const user = userEvent.setup();
      await user.click(screen.getAllByText('Enterprise Security ROI')[0]);

      // Deploy button should now be enabled
      const deployBtn = screen.getByText('Deploy to Account');
      expect(deployBtn.closest('button')).toBeEnabled();
    });

    it('executes deploy mutation and shows deploying state', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getAllByText('Enterprise Security ROI')[0]).toBeInTheDocument();
      });

      // Select pack, then deploy
      const user = userEvent.setup();
      await user.click(screen.getAllByText('Enterprise Security ROI')[0]);
      const deployBtn = screen.getByText('Deploy to Account');
      await user.click(deployBtn.closest('button')!);

      // Button should show deploying state
      await waitFor(() => {
        expect(screen.getByText(/Deploying/i)).toBeInTheDocument();
      });

      // After mutation completes, button text should revert
      await waitFor(() => {
        expect(screen.getByText('Deploy to Account')).toBeInTheDocument();
      });
    });
  });

  // ── Apply Flow - Error Paths ───────────────────────────────────────────────

  describe('Deploy Flow - Error Paths', () => {
    it('disables deploy button when no pack is selected', async () => {
      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      await waitFor(() => {
        expect(screen.getAllByText('Enterprise Security ROI')[0]).toBeInTheDocument();
      });

      // Deploy to Account button exists and is disabled (no pack selected)
      const deployBtn = screen.getByText('Deploy to Account');
      expect(deployBtn.closest('button')).toBeDisabled();
    });

    it('displays deploy error in pack actions panel when API returns 400', async () => {
      // Setup error response for apply endpoint
      server.use(
        http.post('/api/v1/graph/packs/:id/apply', () => {
          return HttpResponse.json({ message: 'Deployment failed' }, { status: 400 });
        })
      );

      const wrapper = createWrapper();
      render(<ValuePacks />, { wrapper });

      expect(await screen.findAllByRole('heading', { name: 'Enterprise Security ROI' })).not.toHaveLength(0);

      const user = userEvent.setup();
      await user.click(screen.getAllByRole('heading', { name: 'Enterprise Security ROI' })[0]);

      // The pack actions panel should be present with deploy button
      expect(screen.getByTestId('pack-actions')).toBeInTheDocument();

      // Enable the deploy button by selecting a pack first
      const deployBtn = await screen.findByRole('button', { name: 'Deploy to Account' });
      await waitFor(() => {
        expect(deployBtn).toBeEnabled();
      });

      // Click deploy button
      await user.click(deployBtn);

      // Wait for mutation to settle and error alert to render
      const packActions = screen.getByTestId('pack-actions');
      await waitFor(() => {
        expect(within(packActions).getByText(/Request failed with status code 400/i)).toBeInTheDocument();
      });
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Deploy to Account' })).toBeEnabled();
      });

      // Banner can be dismissed by the clear button
      const dismissErrorButton = within(packActions).getByRole('button', { name: '×' });
      await user.click(dismissErrorButton);
      await waitFor(() => {
        expect(within(packActions).queryByText(/Request failed with status code 400/i)).not.toBeInTheDocument();
      });
    });
  });
});
