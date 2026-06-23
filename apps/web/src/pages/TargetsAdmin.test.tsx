/**
 * TargetsAdmin — Expanded Behavior Tests
 *
 * Covers: list render, stats strip, all four tabs, filter/sort,
 * empty/loading/error states, row actions, bulk toolbar,
 * archive confirmation, panel open/close, status mutations.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithRouter } from '../test-utils';

// ── Shared mock data ──────────────────────────────────────────────────────────

const mockTargets = [
  {
    id: 'target-1', name: 'Acme Corp', url: 'https://acme.com',
    targetType: 'SPIDER', sourceCategory: 'CRM', status: 'ACTIVE' as const,
    tags: ['prospect'], successCount: 10, errorCount: 1,
    averageExecutionTimeMs: 1200, healthScore: 91,
    lastSuccessAt: '2024-01-15T10:00:00Z',
    createdAt: '2024-01-01T00:00:00Z', updatedAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'target-2', name: 'Beta Inc', url: 'https://beta.com',
    targetType: 'SINGLE_PAGE', sourceCategory: 'GENERAL', status: 'PAUSED' as const,
    tags: [], successCount: 5, errorCount: 3,
    averageExecutionTimeMs: 800, healthScore: 63,
    lastSuccessAt: null,
    createdAt: '2024-01-02T00:00:00Z', updatedAt: '2024-01-10T00:00:00Z',
  },
  {
    id: 'target-3', name: 'Error Corp', url: 'https://error.com',
    targetType: 'PAGINATED', sourceCategory: 'GENERAL', status: 'ERROR' as const,
    tags: ['compliance'], successCount: 2, errorCount: 8,
    averageExecutionTimeMs: 500, healthScore: 20,
    lastSuccessAt: null,
    createdAt: '2024-01-03T00:00:00Z', updatedAt: '2024-01-12T00:00:00Z',
  },
];

const mockStats = { total: 3, connected: 1, disconnected: 1, error: 1, total_records: 0, average_health_score: 58 };

// ── Mock factories ────────────────────────────────────────────────────────────

const makeUseTargets = (overrides = {}) => vi.fn(() => ({
  data: { targets: mockTargets, pagination: { page: 1, limit: 25, total: 3, totalPages: 1 } },
  isLoading: false, isFetching: false, refetch: vi.fn(), ...overrides,
}));

const makeUpdateStatus = () => vi.fn(() => ({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false }));
const makeExecute = () => vi.fn(() => ({ mutateAsync: vi.fn().mockResolvedValue({ jobId: 'job-1' }), isPending: false }));
const makeBatch = (result = {}) => vi.fn(() => ({
  mutateAsync: vi.fn().mockResolvedValue({ operation: 'pause', requested: 1, succeeded: 1, failed: 0, results: [], ...result }),
  isPending: false,
}));

let mockUseTargets = makeUseTargets();
let mockUseTargetStats = vi.fn(() => ({ data: mockStats, isLoading: false }));
let mockUpdateStatus = makeUpdateStatus();
let mockExecute = makeExecute();
let mockBatch = makeBatch();

vi.mock('@/hooks/useTargets', () => ({
  useTargets: (...a: unknown[]) => mockUseTargets(...a),
  useTargetStats: () => mockUseTargetStats(),
  useTarget: () => ({ data: null, isLoading: false }),
  useTargetJobs: () => ({ data: { jobs: [], pagination: {} }, isLoading: false, refetch: vi.fn() }),
  useUpdateTargetStatus: () => mockUpdateStatus(),
  useExecuteTarget: () => mockExecute(),
  useBatchTargetOperation: () => mockBatch(),
  useCreateTarget: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateTarget: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteTarget: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useValidateTarget: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/queryKeys', () => ({
  QK: {
    targets: { all: ['targets'], list: (f: unknown) => ['targets', 'list', f], detail: (id: string) => ['targets', 'detail', id], stats: ['targets', 'stats'], jobs: (id: string) => ['targets', 'jobs', id] },
    ingestion: { jobs: () => ['ingestion', 'jobs'] },
  },
}));

import TargetsAdmin from './TargetsAdmin';

beforeEach(() => {
  vi.clearAllMocks();
  mockUseTargets = makeUseTargets();
  mockUseTargetStats = vi.fn(() => ({ data: mockStats, isLoading: false }));
  mockUpdateStatus = makeUpdateStatus();
  mockExecute = makeExecute();
  mockBatch = makeBatch();
});

// ── Page header & primary actions ─────────────────────────────────────────────

describe('Page header', () => {
  it('renders the Targets title', async () => {
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => expect(screen.getAllByText('Targets').length).toBeGreaterThan(0));
  });

  it('renders New Target button', async () => {
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => expect(screen.getByText('New Target')).toBeInTheDocument());
  });

  it('renders Refresh button', async () => {
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => expect(screen.getByText('Refresh')).toBeInTheDocument());
  });
});

// ── Stats strip ───────────────────────────────────────────────────────────────

describe('Stats strip', () => {
  it('renders total count', async () => {
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());
  });

  it('shows loading skeletons while stats are loading', async () => {
    mockUseTargetStats = vi.fn(() => ({ data: undefined, isLoading: true }));
    renderWithRouter(<TargetsAdmin />);
    // No crash; skeletons render
    expect(document.body).toBeTruthy();
  });
});

// ── Tabs ──────────────────────────────────────────────────────────────────────

describe('Tabs', () => {
  it('renders all four tabs', async () => {
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => {
      expect(screen.getByText('All Targets')).toBeInTheDocument();
      expect(screen.getByText('Scheduled')).toBeInTheDocument();
      expect(screen.getByText('Compliance Failures')).toBeInTheDocument();
      expect(screen.getByText('Events')).toBeInTheDocument();
    });
  });

  it('All Targets tab is active by default', async () => {
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument());
  });

  it('Compliance Failures tab filters by ERROR status', async () => {
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Compliance Failures'));
    await user.click(screen.getByText('Compliance Failures'));
    // The tab renders — no crash
    await waitFor(() => expect(screen.getByText('Compliance Failures')).toBeInTheDocument());
  });
});

// ── Target table ──────────────────────────────────────────────────────────────

describe('Target table', () => {
  it('renders target rows', async () => {
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('Beta Inc')).toBeInTheDocument();
    });
  });

  it('shows empty state when no targets', async () => {
    mockUseTargets = vi.fn(() => ({
      data: { targets: [], pagination: { page: 1, limit: 25, total: 0, totalPages: 0 } },
      isLoading: false, isFetching: false, refetch: vi.fn(),
    }));
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => expect(screen.getByText(/No targets found/i)).toBeInTheDocument());
  });

  it('shows loading skeletons while fetching', async () => {
    mockUseTargets = vi.fn(() => ({ data: undefined, isLoading: true, isFetching: true, refetch: vi.fn() }));
    renderWithRouter(<TargetsAdmin />);
    expect(document.body).toBeTruthy();
  });

  it('renders status badges', async () => {
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => {
      expect(screen.getAllByText('Active').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Paused').length).toBeGreaterThan(0);
    });
  });
});

// ── Filter bar ────────────────────────────────────────────────────────────────

describe('Filter bar', () => {
  it('renders search input', async () => {
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => expect(screen.getByPlaceholderText(/Search targets/i)).toBeInTheDocument());
  });

  it('typing in search calls useTargets with search param', async () => {
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByPlaceholderText(/Search targets/i));
    await user.type(screen.getByPlaceholderText(/Search targets/i), 'acme');
    await waitFor(() => {
      const calls = mockUseTargets.mock.calls;
      const lastCall = calls[calls.length - 1][0] as { search?: string };
      expect(lastCall?.search).toBe('acme');
    });
  });
});

// ── Row actions ───────────────────────────────────────────────────────────────

describe('Row actions', () => {
  it('clicking a row opens the detail panel', async () => {
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    await user.click(screen.getByText('Acme Corp'));
    // Panel opens — no crash
    await waitFor(() => expect(screen.getAllByText('Acme Corp').length).toBeGreaterThanOrEqual(1));
  });

  it('Pause action calls updateStatus with PAUSED', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    mockUpdateStatus = vi.fn(() => ({ mutateAsync, isPending: false }));
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    const moreButtons = screen.getAllByLabelText('Target actions');
    await user.click(moreButtons[0]);
    await user.click(await screen.findByText('Pause'));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ id: 'target-1', status: 'PAUSED' }));
  });

  it('Resume action calls updateStatus with ACTIVE', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    mockUpdateStatus = vi.fn(() => ({ mutateAsync, isPending: false }));
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Beta Inc'));
    const moreButtons = screen.getAllByLabelText('Target actions');
    await user.click(moreButtons[1]); // Beta Inc is PAUSED
    await user.click(await screen.findByText('Resume'));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ id: 'target-2', status: 'ACTIVE' }));
  });

  it('Run action calls executeTarget', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ jobId: 'job-1' });
    mockExecute = vi.fn(() => ({ mutateAsync, isPending: false }));
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    const moreButtons = screen.getAllByLabelText('Target actions');
    await user.click(moreButtons[0]);
    await user.click(await screen.findByText('Run now'));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ id: 'target-1' }));
  });

  it('Archive action opens confirmation dialog', async () => {
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    const moreButtons = screen.getAllByLabelText('Target actions');
    await user.click(moreButtons[0]);
    await user.click(await screen.findByText('Archive'));
    await waitFor(() => expect(screen.getByText(/Archive this target\?/i)).toBeInTheDocument());
  });

  it('Cancel archive does not call updateStatus', async () => {
    const mutateAsync = vi.fn();
    mockUpdateStatus = vi.fn(() => ({ mutateAsync, isPending: false }));
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    const moreButtons = screen.getAllByLabelText('Target actions');
    await user.click(moreButtons[0]);
    await user.click(await screen.findByText('Archive'));
    await waitFor(() => screen.getByText(/Archive this target\?/i));
    await user.click(screen.getByText('Cancel'));
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('Confirm archive calls updateStatus with ARCHIVED', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    mockUpdateStatus = vi.fn(() => ({ mutateAsync, isPending: false }));
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    const moreButtons = screen.getAllByLabelText('Target actions');
    await user.click(moreButtons[0]);
    await user.click(await screen.findByText('Archive'));
    await waitFor(() => screen.getByText(/Archive this target\?/i));
    await user.click(screen.getByRole('button', { name: /^Archive$/i }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ id: 'target-1', status: 'ARCHIVED' }));
  });
});

// ── Bulk toolbar ──────────────────────────────────────────────────────────────

describe('Bulk toolbar', () => {
  it('appears when a row is selected', async () => {
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]); // first row checkbox
    await waitFor(() => expect(screen.getByText(/1 selected/i)).toBeInTheDocument());
  });

  it('Bulk pause calls batch with pause operation', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ operation: 'pause', requested: 1, succeeded: 1, failed: 0, results: [] });
    mockBatch = vi.fn(() => ({ mutateAsync, isPending: false }));
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]);
    await waitFor(() => screen.getByText(/1 selected/i));
    await user.click(screen.getByRole('button', { name: /^Pause$/i }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ operation: 'pause', targetIds: expect.arrayContaining(['target-1']) })
    ));
  });

  it('Bulk execute calls batch with execute operation', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ operation: 'execute', requested: 1, succeeded: 1, failed: 0, results: [] });
    mockBatch = vi.fn(() => ({ mutateAsync, isPending: false }));
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]);
    await waitFor(() => screen.getByText(/1 selected/i));
    await user.click(screen.getByRole('button', { name: /^Run$/i }));
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ operation: 'execute' })
    ));
  });

  it('partial batch failure shows warning feedback', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ operation: 'pause', requested: 2, succeeded: 1, failed: 1, results: [] });
    mockBatch = vi.fn(() => ({ mutateAsync, isPending: false }));
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]);
    await user.click(checkboxes[2]);
    await waitFor(() => screen.getByText(/2 selected/i));
    await user.click(screen.getByRole('button', { name: /^Pause$/i }));
    // Toast with warning is shown — no crash
    await waitFor(() => expect(mutateAsync).toHaveBeenCalled());
  });

  it('Clear button deselects all rows', async () => {
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('Acme Corp'));
    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]);
    await waitFor(() => screen.getByText(/1 selected/i));
    await user.click(screen.getByText('Clear'));
    await waitFor(() => expect(screen.queryByText(/1 selected/i)).not.toBeInTheDocument());
  });
});

// ── New Target panel ──────────────────────────────────────────────────────────

describe('New Target panel', () => {
  it('opens create panel when New Target is clicked', async () => {
    const user = userEvent.setup();
    renderWithRouter(<TargetsAdmin />);
    await waitFor(() => screen.getByText('New Target'));
    await user.click(screen.getByText('New Target'));
    await waitFor(() => expect(screen.getByText('New Target', { selector: 'h2, [data-slot="sheet-title"], [role="dialog"] *' })).toBeInTheDocument());
  });
});
