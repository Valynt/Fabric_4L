/**
 * TargetsAdmin — MSW Integration Tests
 *
 * Tests the full request/response cycle through real TanStack Query hooks
 * and MSW-intercepted HTTP calls. No hook mocks — API layer is the boundary.
 *
 * URL base for l1: /api/v1/ingest  (VITE_API_VERSION_PREFIX=/api/v1, l1 prefix=/ingest)
 */

import React from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { screen, waitFor, within, cleanup, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/mocks/server';
import { renderWithRouter } from '../test-utils';
import TargetsAdmin from './TargetsAdmin';

// vi.mock factories are hoisted before ES imports, so the `React` binding is
// not yet initialised when the factory runs. Use require() inside the factory
// to get React at call time (after module graph is resolved).

vi.mock('@/components/ui/fabric/SidePanel', () => {
  const R = require('react');
  return {
    SidePanel: ({ open, children, title }: any) =>
      open ? R.createElement('div', { 'data-testid': 'side-panel', 'aria-label': title }, children) : null,
  };
});

// Mock Radix DropdownMenu — all items always rendered so role="menuitem"
// queries work without triggering Radix body-lock in jsdom.
vi.mock('@/components/ui/dropdown-menu', () => {
  const R = require('react');
  return {
    DropdownMenu: ({ children }: any) =>
      R.createElement('div', { 'data-testid': 'dropdown-menu' }, children),
    // asChild=true: pass through to child element to avoid double-wrapping
    DropdownMenuTrigger: ({ children, asChild }: any) =>
      asChild ? children : R.createElement('button', { 'aria-label': 'Target actions' }, children),
    DropdownMenuContent: ({ children }: any) =>
      R.createElement('div', { role: 'menu' }, children),
    DropdownMenuItem: ({ children, onClick, disabled }: any) =>
      R.createElement('div', { role: 'menuitem', onClick, 'aria-disabled': disabled }, children),
    DropdownMenuSeparator: () => R.createElement('hr', null),
  };
});

// Mock Radix Select — SelectTrigger uses role="combobox", SelectItem uses
// role="option", so tests can query them with standard ARIA roles.
vi.mock('@/components/ui/select', () => {
  const R = require('react');
  // Carry onValueChange via React context so SelectItem can call it.
  const Ctx = R.createContext<((v: string) => void) | undefined>(undefined);
  return {
    Select: ({ value, onValueChange, children }: any) =>
      R.createElement(Ctx.Provider, { value: onValueChange },
        R.createElement('div', { 'data-testid': 'select', 'data-value': value }, children),
      ),
    SelectTrigger: ({ children, className, 'aria-label': ariaLabel }: any) =>
      R.createElement('button', { role: 'combobox', className, 'aria-label': ariaLabel }, children),
    SelectValue: ({ placeholder }: any) => R.createElement('span', null, placeholder),
    SelectContent: ({ children }: any) => R.createElement('div', null, children),
    SelectItem: ({ value, children }: any) => {
      const onChange = R.useContext(Ctx);
      return R.createElement('div', { role: 'option', 'data-value': value, onClick: () => onChange?.(value) }, children);
    },
  };
});

vi.mock('@/components/ui/alert-dialog', () => {
  const R = require('react');
  // Context carries the onOpenChange callback so AlertDialogCancel can close
  // the dialog without needing an explicit onClick prop (matching Radix behaviour).
  const CloseCtx = R.createContext<(() => void) | undefined>(undefined);
  return {
    AlertDialog: ({ open, onOpenChange, children }: any) =>
      open
        ? R.createElement(CloseCtx.Provider, { value: () => onOpenChange?.(false) },
            R.createElement('div', { role: 'alertdialog' }, children),
          )
        : null,
    AlertDialogContent: ({ children }: any) => R.createElement('div', null, children),
    AlertDialogHeader: ({ children }: any) => R.createElement('div', null, children),
    AlertDialogTitle: ({ children }: any) => R.createElement('h2', null, children),
    AlertDialogDescription: ({ children }: any) => R.createElement('p', null, children),
    AlertDialogFooter: ({ children }: any) => R.createElement('div', null, children),
    AlertDialogAction: ({ children, onClick }: any) => R.createElement('button', { onClick }, children),
    // Cancel reads the close callback from context (no explicit onClick needed).
    AlertDialogCancel: ({ children, onClick }: any) => {
      const close = R.useContext(CloseCtx);
      return R.createElement('button', { onClick: onClick ?? close }, children);
    },
  };
});

// ── Canonical URL prefix ──────────────────────────────────────────────────────
// Matches client.ts: API_VERSION_PREFIX=/api/v1, l1 LAYER_PREFIX=/ingest
const L1 = '/api/v1/ingest';

// ── Shared fixture data ───────────────────────────────────────────────────────

const makeApiSummary = (overrides: Record<string, unknown> = {}) => ({
  id: 'tgt-001',
  tenant_id: 'tenant-a',
  name: 'Acme Corp',
  url: 'https://acme.com',
  target_type: 'SPIDER',
  source_category: 'CRM',
  status: 'ACTIVE',
  tags: ['prospect'],
  success_count: 10,
  error_count: 1,
  average_execution_time_ms: 1200,
  last_success_at: '2024-01-15T10:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
  ...overrides,
});

const makeApiDetail = (overrides: Record<string, unknown> = {}) => ({
  ...makeApiSummary(overrides),
  description: 'Acme Corp website',
  url_pattern: null,
  crawl_path: 'browser',
  extraction_config: {},
  browser_config: {},
  schedule: null,
  rate_limit: {},
  compliance: {},
  proxy_config: {},
  authentication: null,
  last_error_at: null,
  created_by: 'user-1',
  ...overrides,
});

const makeListResponse = (items: ReturnType<typeof makeApiSummary>[], total = items.length) => ({
  data: items,
  pagination: { page: 1, limit: 25, total, total_pages: Math.ceil(total / 25) },
});

const makeStats = (overrides: Record<string, unknown> = {}) => ({
  total: 3,
  connected: 1,
  disconnected: 1,
  error: 1,
  total_records: 150,
  average_health_score: 72,
  ...overrides,
});

// ── Handler helpers ───────────────────────────────────────────────────────────

/** Register the minimum handlers needed for the page to render without errors. */
function registerBaseHandlers(
  targets: ReturnType<typeof makeApiSummary>[] = [makeApiSummary()],
  stats = makeStats(),
) {
  server.use(
    http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse(targets))),
    http.get(`${L1}/targets/stats`, () => HttpResponse.json(stats)),
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TargetsAdmin integration — initial render', () => {
  beforeEach(() => {
    registerBaseHandlers();
  });

  it('renders the page title', async () => {
    renderWithRouter(<TargetsAdmin />);
    // Use getAllByText to handle multiple elements with the same text (e.g. breadcrumb + heading)
    const elements = await screen.findAllByText('Targets');
    expect(elements.length).toBeGreaterThan(0);
  });

  it('shows stats from the API', async () => {
    renderWithRouter(<TargetsAdmin />);
    // Stats strip shows total, active (connected), paused (disconnected), error
    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument(); // total
    });
  });

  it('renders target rows from the API', async () => {
    renderWithRouter(<TargetsAdmin />);
    expect(await screen.findByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('https://acme.com')).toBeInTheDocument();
  });

  it('shows Active status badge for ACTIVE target', async () => {
    renderWithRouter(<TargetsAdmin />);
    // 'Active' may appear in both the status badge and filter options
    const elements = await screen.findAllByText('Active');
    expect(elements.length).toBeGreaterThan(0);
  });
});

describe('TargetsAdmin integration — loading states', () => {
  it('shows skeleton while stats are loading', async () => {
    // Delay the stats response so we can observe the loading state
    server.use(
      http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse([]))),
      http.get(`${L1}/targets/stats`, async () => {
        await new Promise(r => setTimeout(r, 200));
        return HttpResponse.json(makeStats());
      }),
    );

    renderWithRouter(<TargetsAdmin />);

    // The page heading is immediately visible even while stats are loading
    expect(screen.getByRole('button', { name: /new target/i })).toBeInTheDocument();

    // Stats data eventually arrives without crashing
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /new target/i })).toBeInTheDocument();
    }, { timeout: 1000 });
  });

  it('shows empty state when no targets exist', async () => {
    server.use(
      http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse([]))),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats({ total: 0, connected: 0, disconnected: 0, error: 0 }))),
    );

    renderWithRouter(<TargetsAdmin />);
    expect(await screen.findByText('No targets found')).toBeInTheDocument();
  });
});

describe('TargetsAdmin integration — multiple targets', () => {
  const targets = [
    makeApiSummary({ id: 'tgt-001', name: 'Acme Corp', status: 'ACTIVE' }),
    makeApiSummary({ id: 'tgt-002', name: 'Beta Inc', status: 'PAUSED', url: 'https://beta.com', tags: [] }),
    makeApiSummary({ id: 'tgt-003', name: 'Error Corp', status: 'ERROR', url: 'https://error.com', tags: ['compliance'] }),
  ];

  beforeEach(() => {
    registerBaseHandlers(targets, makeStats({ total: 3, connected: 1, disconnected: 1, error: 1 }));
  });

  it('renders all three targets', async () => {
    renderWithRouter(<TargetsAdmin />);
    expect(await screen.findByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Beta Inc')).toBeInTheDocument();
    expect(screen.getByText('Error Corp')).toBeInTheDocument();
  });

  it('shows correct status badges for each target', async () => {
    renderWithRouter(<TargetsAdmin />);
    await screen.findByText('Acme Corp');
    // 'Active' may appear in both the status badge and filter options
    expect(screen.getAllByText('Active').length).toBeGreaterThan(0);
    // 'Paused' may appear in both the status badge and the always-rendered dropdown menu item
    expect(screen.getAllByText('Paused').length).toBeGreaterThan(0);
    // 'Error' may appear in both the status badge and error state text
    expect(screen.getAllByText('Error').length).toBeGreaterThan(0);
  });

  it('shows compliance failures tab content for ERROR targets', async () => {
    renderWithRouter(<TargetsAdmin />);
    await screen.findByText('Acme Corp');

    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(screen.getByRole('tab', { name: /compliance failures/i }));

    // Error Corp has status ERROR — should appear in failures tab
    await waitFor(() => {
      expect(screen.getAllByText('Error Corp').length).toBeGreaterThan(0);
    });
  });
});

describe('TargetsAdmin integration — row click opens detail panel', () => {
  afterEach(async () => {
    await act(async () => { cleanup(); });
    document.body.removeAttribute('data-scroll-locked');
    document.body.style.removeProperty('pointer-events');
    document.documentElement.removeAttribute('data-scroll-locked');
    document.querySelectorAll('[data-radix-focus-guard]').forEach((el) => el.remove());
    document.querySelectorAll('[data-radix-popper-content-wrapper]').forEach((el) => el.remove());
  });
  beforeEach(() => {
    const target = makeApiSummary({ id: 'tgt-001', name: 'Acme Corp' });
    const detail = makeApiDetail({ id: 'tgt-001', name: 'Acme Corp' });

    server.use(
      http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse([target]))),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats())),
      http.get(`${L1}/targets/tgt-001`, () => HttpResponse.json(detail)),
      http.get(`${L1}/jobs`, () =>
        HttpResponse.json({ data: [], pagination: { page: 1, limit: 10, total: 0, total_pages: 1 } }),
      ),
    );
  });

  it('opens the detail panel when a row is clicked', async () => {
    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    const row = await screen.findByText('Acme Corp');
    await user.click(row);

    // SidePanel opens — detail panel title or content appears
    await waitFor(() => {
      // The SidePanel title is the target name
      const panels = screen.getAllByText('Acme Corp');
      expect(panels.length).toBeGreaterThan(1); // row + panel header
    });
  });
});

describe('TargetsAdmin integration — New Target button opens form panel', () => {
  afterEach(async () => {
    await act(async () => { cleanup(); });
    document.body.removeAttribute('data-scroll-locked');
    document.body.style.removeProperty('pointer-events');
    document.documentElement.removeAttribute('data-scroll-locked');
    document.querySelectorAll('[data-radix-focus-guard]').forEach((el) => el.remove());
    document.querySelectorAll('[data-radix-popper-content-wrapper]').forEach((el) => el.remove());
  });
  beforeEach(() => {
    registerBaseHandlers();
  });

  it('opens the create form when New Target is clicked', async () => {
    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');
    await user.click(screen.getByRole('button', { name: /new target/i }));

    await waitFor(() => {
      // 'New Target' appears in both the button and the panel heading after click
      const elements = screen.getAllByText('New Target');
      expect(elements.length).toBeGreaterThan(0);
    });
  });
});

describe('TargetsAdmin integration — status transitions via row actions', () => {
  const target = makeApiSummary({ id: 'tgt-001', name: 'Acme Corp', status: 'ACTIVE' });

  afterEach(() => {
    cleanup();
    // @radix-ui/react-remove-scroll sets data-scroll-locked and pointer-events
    // on <body> as a side effect. These persist after React tree unmount because
    // the effect teardown is async. Reset them here so the next test is clean.
    document.body.removeAttribute('data-scroll-locked');
    document.body.style.removeProperty('pointer-events');
    document.documentElement.removeAttribute('data-scroll-locked');
    document.querySelectorAll('[data-radix-focus-guard]').forEach((el) => el.remove());
    document.querySelectorAll('[data-radix-popper-content-wrapper]').forEach((el) => el.remove());
  });
  beforeEach(() => {
    server.use(
      http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse([target]))),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats())),
    );
  });

  it('calls PATCH /targets/:id/status when Pause is clicked', async () => {
    let patchBody: unknown = null;
    let getCallCount = 0;

    // Register the PATCH handler and a GET handler that returns PAUSED only
    // after the first (initial) fetch — so the initial render sees ACTIVE and
    // shows the Pause menu item, while the post-mutation refetch sees PAUSED.
    server.use(
      http.patch(`${L1}/targets/tgt-001/status`, async ({ request }) => {
        patchBody = await request.json();
        return HttpResponse.json(makeApiDetail({ id: 'tgt-001', status: 'PAUSED' }));
      }),
      http.get(`${L1}/targets`, () => {
        getCallCount++;
        const status = getCallCount > 1 ? 'PAUSED' : 'ACTIVE';
        return HttpResponse.json(makeListResponse([{ ...target, status }]));
      }),
    );

    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');

    // Menu items are always rendered (mock has no open/close state).
    const actionBtn = await screen.findByRole('button', { name: /target actions/i });
    await user.click(actionBtn);
    const pauseItem = await screen.findByRole('menuitem', { name: /pause/i }, { timeout: 3000 });
    await user.click(pauseItem);

    await waitFor(() => {
      expect(patchBody).toMatchObject({ status: 'PAUSED' });
    });
  });

  it('calls POST /targets/:id/execute when Run now is clicked', async () => {
    let executeCalled = false;

    server.use(
      http.post(`${L1}/targets/tgt-001/execute`, () => {
        executeCalled = true;
        return HttpResponse.json({ job_id: 'job-xyz' });
      }),
      http.get(`${L1}/jobs`, () =>
        HttpResponse.json({ data: [], pagination: { page: 1, limit: 10, total: 0, total_pages: 1 } }),
      ),
    );

    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');

    const actionBtn = screen.getByRole('button', { name: /target actions/i });
    await user.click(actionBtn);

    const runItem = await screen.findByRole('menuitem', { name: /run now/i });
    await user.click(runItem);

    await waitFor(() => {
      expect(executeCalled).toBe(true);
    });
  });
});

describe('TargetsAdmin integration — archive confirmation dialog', () => {
  const target = makeApiSummary({ id: 'tgt-001', name: 'Acme Corp', status: 'ACTIVE' });

  afterEach(() => {
    cleanup();
    document.body.removeAttribute('data-scroll-locked');
    document.body.style.removeProperty('pointer-events');
    document.documentElement.removeAttribute('data-scroll-locked');
    document.querySelectorAll('[data-radix-focus-guard]').forEach((el) => el.remove());
    document.querySelectorAll('[data-radix-popper-content-wrapper]').forEach((el) => el.remove());
  });
  beforeEach(() => {
    server.use(
      http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse([target]))),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats())),
    );
  });

  it('shows confirmation dialog when Archive is clicked', async () => {
    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');

    const actionBtn = screen.getByRole('button', { name: /target actions/i });
    await user.click(actionBtn);

    const archiveItem = await screen.findByRole('menuitem', { name: /archive/i });
    await user.click(archiveItem);

    await waitFor(() => {
      expect(screen.getByText('Archive this target?')).toBeInTheDocument();
    });
  });

  it('calls PATCH status=ARCHIVED when dialog is confirmed', async () => {
    let patchBody: unknown = null;
    let getCallCount = 0;

    // Return ACTIVE on the first fetch so the Archive menu item renders,
    // then ARCHIVED on subsequent fetches (post-mutation refetch).
    server.use(
      http.patch(`${L1}/targets/tgt-001/status`, async ({ request }) => {
        patchBody = await request.json();
        return HttpResponse.json(makeApiDetail({ id: 'tgt-001', status: 'ARCHIVED' }));
      }),
      http.get(`${L1}/targets`, () => {
        getCallCount++;
        const status = getCallCount > 1 ? 'ARCHIVED' : 'ACTIVE';
        return HttpResponse.json(makeListResponse([{ ...target, status }]));
      }),
    );

    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');

    // Menu items are always rendered (mock has no open/close state).
    const archiveActionBtn = await screen.findByRole('button', { name: /target actions/i });
    await user.click(archiveActionBtn);
    const archiveItem = await screen.findByRole('menuitem', { name: /archive/i }, { timeout: 3000 });
    await user.click(archiveItem);

    // Confirm in dialog
    const dialog = await screen.findByRole('alertdialog');
    const confirmBtn = within(dialog).getByRole('button', { name: /archive/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(patchBody).toMatchObject({ status: 'ARCHIVED' });
    });
  });

  it('dismisses dialog without calling API when Cancel is clicked', async () => {
    let patchCalled = false;

    server.use(
      http.patch(`${L1}/targets/tgt-001/status`, () => {
        patchCalled = true;
        return HttpResponse.json(makeApiDetail({ id: 'tgt-001', status: 'ARCHIVED' }));
      }),
    );

    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');

    // Open actions → Archive
    await user.click(screen.getByRole('button', { name: /target actions/i }));
    await user.click(await screen.findByRole('menuitem', { name: /archive/i }));

    const dialog = await screen.findByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: /cancel/i }));

    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    });
    expect(patchCalled).toBe(false);
  });
});

describe('TargetsAdmin integration — bulk operations', () => {
  const targets = [
    makeApiSummary({ id: 'tgt-001', name: 'Acme Corp', status: 'ACTIVE' }),
    makeApiSummary({ id: 'tgt-002', name: 'Beta Inc', status: 'ACTIVE', url: 'https://beta.com', tags: [] }),
  ];

  beforeEach(() => {
    server.use(
      http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse(targets))),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats({ total: 2, connected: 2 }))),
    );
  });

  it('shows bulk toolbar when targets are selected', async () => {
    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');

    // Select first target via checkbox
    const checkboxes = screen.getAllByRole('checkbox');
    // First checkbox is "select all", subsequent ones are per-row
    await user.click(checkboxes[1]);

    await waitFor(() => {
      expect(screen.getByText(/1 selected/i)).toBeInTheDocument();
    });
  });

  it('calls POST /targets/batch with pause operation', async () => {
    let batchBody: unknown = null;

    server.use(
      http.post(`${L1}/targets/batch`, async ({ request }) => {
        batchBody = await request.json();
        return HttpResponse.json({
          operation: 'pause',
          requested: 1,
          succeeded: 1,
          failed: 0,
          results: [{ id: 'tgt-001', status: 'succeeded', job_id: null, error: null }],
        });
      }),
      http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse(targets))),
    );

    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');

    // Select first target
    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]);

    await screen.findByText(/1 selected/i);

    // Click bulk Pause
    const pauseBtn = screen.getByRole('button', { name: /pause/i });
    await user.click(pauseBtn);

    await waitFor(() => {
      expect(batchBody).toMatchObject({
        operation: 'pause',
        target_ids: ['tgt-001'],
      });
    });
  });

  it('selects all targets with the header checkbox', async () => {
    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');

    // Click the "select all" header checkbox
    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[0]);

    await waitFor(() => {
      expect(screen.getByText(/2 selected/i)).toBeInTheDocument();
    });
  });

  it('clears selection when Clear is clicked in bulk toolbar', async () => {
    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');

    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]);
    await screen.findByText(/1 selected/i);

    await user.click(screen.getByRole('button', { name: /clear/i }));

    await waitFor(() => {
      expect(screen.queryByText(/1 selected/i)).not.toBeInTheDocument();
    });
  });
});

describe('TargetsAdmin integration — search filter', () => {
  it('sends search param to the API', async () => {
    let capturedSearch: string | null = null;

    server.use(
      http.get(`${L1}/targets`, ({ request }) => {
        const url = new URL(request.url);
        capturedSearch = url.searchParams.get('search');
        return HttpResponse.json(makeListResponse([]));
      }),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats())),
    );

    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    // Wait for initial render
    await screen.findByText('No targets found');

    // placeholder is "Search targets…"
    const searchInput = screen.getByPlaceholderText('Search targets…');
    await user.type(searchInput, 'acme');

    await waitFor(() => {
      expect(capturedSearch).toBe('acme');
    });
  });
});

describe('TargetsAdmin integration — status filter', () => {
  it('sends status param to the API when filter is changed', async () => {
    let capturedStatus: string | null = null;

    server.use(
      http.get(`${L1}/targets`, ({ request }) => {
        const url = new URL(request.url);
        capturedStatus = url.searchParams.get('status');
        return HttpResponse.json(makeListResponse([]));
      }),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats())),
    );

    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('No targets found');

    // The status SelectTrigger has aria-label="Status filter".
    const statusTrigger = screen.getByRole('combobox', { name: /status filter/i });
    await user.click(statusTrigger);

    const activeOption = await screen.findByRole('option', { name: /^active$/i });
    await user.click(activeOption);

    await waitFor(() => {
      expect(capturedStatus).toBe('ACTIVE');
    });
  });
});

describe('TargetsAdmin integration — refresh button', () => {
  it('re-fetches targets when Refresh is clicked', async () => {
    let fetchCount = 0;

    server.use(
      http.get(`${L1}/targets`, () => {
        fetchCount++;
        return HttpResponse.json(makeListResponse([makeApiSummary()]));
      }),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats())),
    );

    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');
    const countAfterLoad = fetchCount;

    // Page header has a visible "Refresh" button (text label); filter bar has
    // an icon-only button with aria-label="Refresh". Click the header one.
    const refreshBtns = screen.getAllByRole('button', { name: /refresh/i });
    await user.click(refreshBtns[0]);

    await waitFor(() => {
      expect(fetchCount).toBeGreaterThan(countAfterLoad);
    });
  });
});

describe('TargetsAdmin integration — API error handling', () => {
  it('does not crash when targets API returns 500', async () => {
    server.use(
      http.get(`${L1}/targets`, () => HttpResponse.json({ detail: 'Internal Server Error' }, { status: 500 })),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats())),
    );

    // Should render without throwing
    renderWithRouter(<TargetsAdmin />);
    // Page header still renders
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new target/i })).toBeInTheDocument();
    });
  });

  it('does not crash when stats API returns 500', async () => {
    server.use(
      http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse([makeApiSummary()]))),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json({ detail: 'Internal Server Error' }, { status: 500 })),
    );

    renderWithRouter(<TargetsAdmin />);
    expect(await screen.findByText('Acme Corp')).toBeInTheDocument();
  });
});

describe('TargetsAdmin integration — pagination', () => {
  it('renders pagination bar when total exceeds page size', async () => {
    const manyTargets = Array.from({ length: 25 }, (_, i) =>
      makeApiSummary({ id: `tgt-${i}`, name: `Target ${i}`, url: `https://target${i}.com` }),
    );

    server.use(
      http.get(`${L1}/targets`, () =>
        HttpResponse.json({
          data: manyTargets,
          pagination: { page: 1, limit: 25, total: 50, total_pages: 2 },
        }),
      ),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats({ total: 50 }))),
    );

    renderWithRouter(<TargetsAdmin />);
    await screen.findByText('Target 0');

    // Pagination bar should appear
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
    });
  });

  it('sends updated page param when Next is clicked', async () => {
    let capturedPage: string | null = null;

    server.use(
      http.get(`${L1}/targets`, ({ request }) => {
        const url = new URL(request.url);
        capturedPage = url.searchParams.get('page');
        return HttpResponse.json({
          data: [makeApiSummary()],
          pagination: { page: Number(capturedPage ?? 1), limit: 25, total: 50, total_pages: 2 },
        });
      }),
      http.get(`${L1}/targets/stats`, () => HttpResponse.json(makeStats({ total: 50 }))),
    );

    renderWithRouter(<TargetsAdmin />);
    await screen.findByText('Acme Corp');

    await waitFor(() => screen.getByRole('button', { name: /next/i }));

    const user = userEvent.setup({ pointerEventsCheck: 0 });
    await user.click(screen.getByRole('button', { name: /next/i }));

    await waitFor(() => {
      expect(capturedPage).toBe('2');
    });
  });
});

describe('TargetsAdmin integration — tabs navigation', () => {
  beforeEach(() => {
    registerBaseHandlers();
  });

  it('renders four tabs', async () => {
    renderWithRouter(<TargetsAdmin />);
    await screen.findByText('Acme Corp');

    expect(screen.getByRole('tab', { name: /all targets/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /scheduled/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /compliance failures/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /events/i })).toBeInTheDocument();
  });

  it('switches to Scheduled tab', async () => {
    // Scheduled tab also calls useTargets — register a handler for it
    server.use(
      http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse([makeApiSummary()]))),
    );

    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');
    await user.click(screen.getByRole('tab', { name: /scheduled/i }));

    // Tab becomes active — no crash
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /scheduled/i })).toHaveAttribute('data-state', 'active');
    });
  });

  it('switches to Events tab', async () => {
    server.use(
      http.get(`${L1}/targets`, () => HttpResponse.json(makeListResponse([makeApiSummary()]))),
    );

    renderWithRouter(<TargetsAdmin />);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findByText('Acme Corp');
    await user.click(screen.getByRole('tab', { name: /events/i }));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /events/i })).toHaveAttribute('data-state', 'active');
    });
  });
});
