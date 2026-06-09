/**
 * Admin Pages — Behavior Test Suite
 *
 * Covers all admin governance pages with smoke + behavior tests:
 * - FormulaGovernance
 * - BenchmarkPolicies
 * - VariableRegistry
 * - PackManagement
 * - PermissionsAdmin
 * - PlatformSettings
 * - HealthMonitor
 * - SuperAdminConsole
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createWrapper, renderWithRouter } from '../../test-utils';

// Static imports avoid per-test dynamic import overhead
import FormulaGovernance from './FormulaGovernance';
import BenchmarkPolicies from './BenchmarkPolicies';
import VariableRegistry from './VariableRegistry';
import PackManagement from './PackManagement';
import PermissionsAdmin from './PermissionsAdmin';
import PlatformSettings from './PlatformSettings';
import HealthMonitor from './HealthMonitor';
import SuperAdminConsole from './SuperAdminConsole';

// ── Mock factories ───────────────────────────────────────────────────────────

import {
  makeUseFormulas,
  makeUseFormulaApprovals,
  makeUseApproveFormula,
  makeUseSubmitFormula,
  makeUseBenchmarks,
  makeUseBenchmarkPolicies,
  makeUseValuePacks,
  makeUseVariables,
  makeUseSourceBindings,
  makeUseVariableStats,
  makeUseValidateVariable,
  makeUseTestVariableBinding,
  makeUseUsers,
  makeUseApiKeys,
  makeUseRevokeApiKey,
  makeUseInviteUser,
  makeUsePlatformSettings,
  makeUseUpdatePlatformSettings,
  makeUseSystemHealth,
  makeUseHealthAlerts,
  makeUseSuperAdminOverview,
} from './__mocks__/adminMocks';

let mockUseFormulas = makeUseFormulas();
let mockUseFormulaApprovals = makeUseFormulaApprovals();
let mockUseApproveFormula = makeUseApproveFormula();
let mockUseSubmitFormula = makeUseSubmitFormula();
let mockUseBenchmarks = makeUseBenchmarks();
let mockUseBenchmarkPolicies = makeUseBenchmarkPolicies();
let mockUseValuePacks = makeUseValuePacks();
let mockUseVariables = makeUseVariables();
let mockUseSourceBindings = makeUseSourceBindings();
let mockUseVariableStats = makeUseVariableStats();
let mockUseValidateVariable = makeUseValidateVariable();
let mockUseTestVariableBinding = makeUseTestVariableBinding();
let mockUseUsers = makeUseUsers();
let mockUseApiKeys = makeUseApiKeys();
let mockUseRevokeApiKey = makeUseRevokeApiKey();
let mockUseInviteUser = makeUseInviteUser();
let mockUsePlatformSettings = makeUsePlatformSettings();
let mockUseUpdatePlatformSettings = makeUseUpdatePlatformSettings();
let mockUseSystemHealth = makeUseSystemHealth();
let mockUseHealthAlerts = makeUseHealthAlerts();
let mockUseSuperAdminOverview = makeUseSuperAdminOverview();
import BillingAdmin from './BillingAdmin';

vi.mock('@/hooks/useFormulas', () => ({
  useFormulas: (...a: unknown[]) => mockUseFormulas(...a),
  useFormulaApprovals: () => mockUseFormulaApprovals(),
  useApproveFormula: () => mockUseApproveFormula(),
  useSubmitFormula: () => mockUseSubmitFormula(),
}));

vi.mock('@/hooks/useBenchmarks', () => ({
  useBenchmarks: (...a: unknown[]) => mockUseBenchmarks(...a),
  useBenchmarkPolicies: () => mockUseBenchmarkPolicies(),
}));

vi.mock('@/hooks/useValuePacks', () => ({
  useValuePacks: (...a: unknown[]) => mockUseValuePacks(...a),
}));

vi.mock('@/hooks/useVariables', () => ({
  useVariables: (...a: unknown[]) => mockUseVariables(...a),
  useSourceBindings: () => mockUseSourceBindings(),
  useVariableStats: () => mockUseVariableStats(),
  useValidateVariable: () => mockUseValidateVariable(),
  useTestVariableBinding: () => mockUseTestVariableBinding(),
}));

vi.mock('@/hooks/useGovernance', () => ({
  useUsers: () => mockUseUsers(),
  useApiKeys: () => mockUseApiKeys(),
  useRevokeApiKey: () => mockUseRevokeApiKey(),
  useInviteUser: () => mockUseInviteUser(),
}));

vi.mock('@/hooks/usePlatformSettings', () => ({
  usePlatformSettings: () => mockUsePlatformSettings(),
  useUpdatePlatformSettings: () => mockUseUpdatePlatformSettings(),
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuthContext: () => ({
    user: {
      id: 'u-1',
      email: 'admin@example.com',
      role: 'admin',
      tenantId: 't-1',
      tenantSlug: 'demo',
    },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

vi.mock('@/hooks/useHealthMonitor', () => ({
  useSystemHealth: () => mockUseSystemHealth(),
  useHealthAlerts: () => mockUseHealthAlerts(),
}));

vi.mock('@/hooks/useSuperAdminOverview', () => ({
  useSuperAdminOverview: (...a: unknown[]) => mockUseSuperAdminOverview(...a),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockUseFormulas = makeUseFormulas();
  mockUseFormulaApprovals = makeUseFormulaApprovals();
  mockUseApproveFormula = makeUseApproveFormula();
  mockUseSubmitFormula = makeUseSubmitFormula();
  mockUseBenchmarks = makeUseBenchmarks();
  mockUseBenchmarkPolicies = makeUseBenchmarkPolicies();
  mockUseValuePacks = makeUseValuePacks();
  mockUseVariables = makeUseVariables();
  mockUseSourceBindings = makeUseSourceBindings();
  mockUseVariableStats = makeUseVariableStats();
  mockUseValidateVariable = makeUseValidateVariable();
  mockUseTestVariableBinding = makeUseTestVariableBinding();
  mockUseUsers = makeUseUsers();
  mockUseApiKeys = makeUseApiKeys();
  mockUseRevokeApiKey = makeUseRevokeApiKey();
  mockUseInviteUser = makeUseInviteUser();
  mockUsePlatformSettings = makeUsePlatformSettings();
  mockUseUpdatePlatformSettings = makeUseUpdatePlatformSettings();
  mockUseSystemHealth = makeUseSystemHealth();
  mockUseHealthAlerts = makeUseHealthAlerts();
  mockUseSuperAdminOverview = makeUseSuperAdminOverview();
});

// ═════════════════════════════════════════════════════════════════════════════
vi.mock('@/hooks/useBilling', () => ({
  useBilling: () => ({
    subscription: {
      id: 'sub-1',
      plan_id: 'pro',
      status: 'active',
      current_period_start: '2026-01-01T00:00:00Z',
      current_period_end: '2026-02-01T00:00:00Z',
      cancel_at_period_end: false,
    },
    isLoading: false,
    error: null,
    openCustomerPortal: vi.fn(),
    isOpeningPortal: false,
    checkoutError: null,
    portalError: null,
    clearErrors: vi.fn(),
    subscribe: vi.fn(),
    isSubscribing: false,
  }),
  useEntitlements: () => ({
    data: {
      plan_id: 'pro',
      plan_name: 'Pro Plan',
      features: {
        advanced_analytics: { enabled: true, name: 'Advanced Analytics', description: 'Custom dashboards and deep insights' },
        ai_assistant: { enabled: true, name: 'AI Assistant', description: 'AI-powered suggestions' },
        custom_integrations: { enabled: false, name: 'Custom Integrations', description: 'Build custom API integrations' },
      },
    },
    isLoading: false,
    error: null,
  }),
}));

vi.mock('@/hooks/useInvoices', () => ({
  useInvoices: () => ({
    invoices: [
      {
        id: 'inv-1',
        invoice_number: 'INV-001',
        customer_id: 'cust-1',
        status: 'paid',
        currency: 'usd',
        subtotal_cents: 9900,
        tax_cents: 0,
        total_cents: 9900,
        total_dollars: 99,
        amount_paid_cents: 9900,
        amount_due_cents: 0,
        amount_due_dollars: 0,
        balance_cents: 0,
        period_start: '2026-01-01T00:00:00Z',
        period_end: '2026-01-31T00:00:00Z',
        due_date: '2026-01-15T00:00:00Z',
        paid_at: '2026-01-05T00:00:00Z',
        voided_at: null,
        created_at: '2026-01-01T00:00:00Z',
        description: null,
        hosted_invoice_url: null,
        invoice_pdf_url: 'https://example.com/inv-1.pdf',
        item_count: 2,
      },
    ],
    charges: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('@/hooks/useUsage', () => ({
  useUsage: () => ({
    metrics: [
      {
        metric: 'api_calls',
        total_quantity: 45000,
        limit: 50000,
        unit: 'calls',
        warning_threshold: 80,
        overage_rate: 0.001,
        percentage: 90,
      },
      {
        metric: 'storage',
        total_quantity: 320,
        limit: 500,
        unit: 'GB',
        warning_threshold: 80,
        overage_rate: 0.1,
        percentage: 64,
      },
    ],
    limits: [],
    events: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    checkLimits: vi.fn(),
    overageStatus: null,
    isChecking: false,
  }),
}));

// FormulaGovernance
// ═════════════════════════════════════════════════════════════════════════════

describe('FormulaGovernance', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<FormulaGovernance />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Formula Governance')).toBeInTheDocument();
    });
  }, 20_000);

  it('switches between registry, versions, and approvals tabs', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<FormulaGovernance />, { wrapper });

    await waitFor(() => screen.getByRole('tab', { name: /^Version History/i }));
    await user.click(screen.getByRole('tab', { name: /^Version History/i }));
    await waitFor(() => expect(screen.getByText(/Formula version history will be available/i)).toBeInTheDocument());

    await user.click(screen.getByRole('tab', { name: /^Approval Queue/i }));
    await waitFor(() => expect(screen.getByText(/Pending Approvals/i)).toBeInTheDocument());

    await user.click(screen.getByRole('tab', { name: /^Formula Registry/i }));
    await waitFor(() => expect(screen.getAllByText('Test Formula').length).toBeGreaterThan(0));
  }, 20_000);

  it('filters formulas by status chip', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<FormulaGovernance />, { wrapper });

    await waitFor(() => expect(screen.getAllByText('Test Formula').length).toBeGreaterThan(0));
    await user.click(screen.getByRole('button', { name: /^Draft$/i }));

    await waitFor(() => {
      const calls = mockUseFormulas.mock.calls;
      const lastCall = calls[calls.length - 1][0] as { status?: string };
      expect(lastCall?.status).toBe('draft');
    });
  }, 20_000);

  it('shows empty state when no formulas', async () => {
    mockUseFormulas = makeUseFormulas({ data: [] });
    const wrapper = createWrapper();
    render(<FormulaGovernance />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText(/No formulas match your filters/i)).toBeInTheDocument();
    });
  }, 20_000);
});

// ═════════════════════════════════════════════════════════════════════════════
// BenchmarkPolicies
// ═════════════════════════════════════════════════════════════════════════════

describe('BenchmarkPolicies', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<BenchmarkPolicies />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Benchmark Policies')).toBeInTheDocument();
    });
  }, 10_000);

  it('filters benchmarks by confidence level', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<BenchmarkPolicies />, { wrapper });

    await waitFor(() => screen.getByText('Test Benchmark'));
    await user.click(screen.getAllByRole('combobox')[0]);
    await user.click(screen.getByRole('option', { name: 'High' }));

    await waitFor(() => {
      const calls = mockUseBenchmarks.mock.calls;
      const lastCall = calls[calls.length - 1][0] as { confidence?: string };
      expect(lastCall?.confidence).toBe('High');
    });
  }, 10_000);
});

// ═════════════════════════════════════════════════════════════════════════════
// VariableRegistry
// ═════════════════════════════════════════════════════════════════════════════

describe('VariableRegistry', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<VariableRegistry />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Variable Registry')).toBeInTheDocument();
    });
  }, 10_000);

  it('switches between catalog and bindings tabs', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<VariableRegistry />, { wrapper });

    await waitFor(() => screen.getByRole('tab', { name: /^Source Bindings/i }));
    await user.click(screen.getByRole('tab', { name: /^Source Bindings/i }));
    await waitFor(() => expect(screen.getByText('Connected Data Sources')).toBeInTheDocument());

    await user.click(screen.getByRole('tab', { name: /^Variable Catalog/i }));
    await waitFor(() => expect(screen.getByText('contract_value')).toBeInTheDocument());
  }, 10_000);

  it('expands variable row to show details', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<VariableRegistry />, { wrapper });

    await waitFor(() => screen.getByText('contract_value'));
    await user.click(screen.getByText('contract_value'));
    await waitFor(() => {
      expect(screen.getByText(/Description/i)).toBeInTheDocument();
    });
  }, 10_000);

  it('shows tenant-scoped confirmation before deleting variable', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<VariableRegistry />, { wrapper });

    await waitFor(() => screen.getByText('contract_value'));
    const deleteBtns = screen.getAllByLabelText('Delete variable');
    await user.click(deleteBtns[0]);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Delete Variable' })).toBeInTheDocument();
      expect(screen.getByText(/Tenant scope/i)).toBeInTheDocument();
    });
  }, 10_000);
});

// ═════════════════════════════════════════════════════════════════════════════
// PackManagement
// ═════════════════════════════════════════════════════════════════════════════

describe('PackManagement', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<PackManagement />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Pack Management')).toBeInTheDocument();
    });
  }, 10_000);

  it('filters packs by status chip', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<PackManagement />, { wrapper });

    await waitFor(() => screen.getByText('Test Pack'));
    await user.click(screen.getByRole('button', { name: /^Draft$/i }));

    await waitFor(() => {
      const calls = mockUseValuePacks.mock.calls;
      const lastCall = calls[calls.length - 1][0] as { status?: string };
      expect(lastCall?.status).toBe('draft');
    });
  }, 10_000);
});

// ═════════════════════════════════════════════════════════════════════════════
// PermissionsAdmin
// ═════════════════════════════════════════════════════════════════════════════

describe('PermissionsAdmin', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<PermissionsAdmin />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Permissions & Access')).toBeInTheDocument();
    });
  }, 10_000);

  it('sets API Keys as the active tab for /settings/access/keys', async () => {
    renderWithRouter(<PermissionsAdmin />, { path: '/settings/access/keys' });
    await waitFor(() => {
      const apiKeysTab = screen.getByRole('tab', { name: /^API Keys/i });
      const usersTab = screen.getByRole('tab', { name: /^Users/i });
      expect(apiKeysTab).toHaveClass('text-primary');
      expect(usersTab).not.toHaveClass('text-primary');
    });
  }, 10_000);

  it('keeps Users as the active tab for /settings/access/roles', async () => {
    renderWithRouter(<PermissionsAdmin />, { path: '/settings/access/roles' });
    await waitFor(() => {
      const usersTab = screen.getByRole('tab', { name: /^Users/i });
      const apiKeysTab = screen.getByRole('tab', { name: /^API Keys/i });
      expect(usersTab).toHaveClass('text-primary');
      expect(apiKeysTab).not.toHaveClass('text-primary');
    });
  }, 10_000);

  it('switches between Users and API Keys tabs', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<PermissionsAdmin />, { wrapper });

    await waitFor(() => screen.getByRole('tab', { name: /^API Keys/i }));
    await user.click(screen.getByRole('tab', { name: /^API Keys/i }));
    await waitFor(() => expect(screen.getByText('Primary Key')).toBeInTheDocument());

    await user.click(screen.getByRole('tab', { name: /^Users/i }));
    await waitFor(() => expect(screen.getByText('admin@example.com')).toBeInTheDocument());
  }, 10_000);

  it('filters users by search input', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<PermissionsAdmin />, { wrapper });

    await waitFor(() => screen.getByPlaceholderText(/Search users/i));
    await user.type(screen.getByPlaceholderText(/Search users/i), 'admin');
    await waitFor(() => expect(screen.getByText('admin@example.com')).toBeInTheDocument());
  }, 10_000);

  it('opens invite dialog when Invite User clicked', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<PermissionsAdmin />, { wrapper });

    await waitFor(() => screen.getByText('Permissions & Access'));
    await user.click(screen.getByRole('button', { name: /Invite User/i }));
    await waitFor(() => expect(screen.getByText('Send an invitation to join this tenant.')).toBeInTheDocument());
  }, 10_000);

  it('shows tenant-scoped confirmation before revoking API key', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<PermissionsAdmin />, { wrapper });

    await waitFor(() => screen.getByRole('tab', { name: /^API Keys/i }));
    await user.click(screen.getByRole('tab', { name: /^API Keys/i }));
    await waitFor(() => screen.getByText('Primary Key'));
    const revokeBtn = screen.getByLabelText('Revoke API key');
    await user.click(revokeBtn);
    await waitFor(() => {
      expect(screen.getByText('Revoke API Key')).toBeInTheDocument();
      expect(screen.getByText(/Tenant scope/i)).toBeInTheDocument();
    });
  }, 10_000);
});

// ═════════════════════════════════════════════════════════════════════════════
// PlatformSettings
// ═════════════════════════════════════════════════════════════════════════════

describe('PlatformSettings', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<PlatformSettings />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Platform Settings')).toBeInTheDocument();
    });
  }, 10_000);

  it('switches between feature tabs', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<PlatformSettings />, { wrapper });

    await waitFor(() => screen.getByRole('tab', { name: /^Notifications/i }));
    await user.click(screen.getByRole('tab', { name: /^Notifications/i }));
    await waitFor(() => expect(screen.getByText('Email Alerts')).toBeInTheDocument());

    await user.click(screen.getByRole('tab', { name: /^Security/i }));
    await waitFor(() => expect(screen.getByText('Require Two-Factor Auth')).toBeInTheDocument());
  }, 10_000);
});

// ═════════════════════════════════════════════════════════════════════════════
// HealthMonitor
// ═════════════════════════════════════════════════════════════════════════════

describe('HealthMonitor', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<HealthMonitor />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('System Health')).toBeInTheDocument();
    });
  }, 10_000);

  it('shows overall status banner', async () => {
    const wrapper = createWrapper();
    render(<HealthMonitor />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText(/System Healthy/i)).toBeInTheDocument();
    });
  }, 10_000);

  it('filters services by status', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<HealthMonitor />, { wrapper });

    await waitFor(() => screen.getByText('l1 ingestion'));
    await user.click(screen.getAllByRole('combobox')[0]);
    await user.click(screen.getByRole('option', { name: 'Degraded' }));

    await waitFor(() => {
      expect(screen.queryByText('l1 ingestion')).not.toBeInTheDocument();
      expect(screen.getByText('l2 extraction')).toBeInTheDocument();
    });
  }, 10_000);

  it('refresh button triggers refetch without crashing', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<HealthMonitor />, { wrapper });

    await waitFor(() => screen.getByRole('button', { name: /Refresh/i }));
    await user.click(screen.getByRole('button', { name: /Refresh/i }));

    // After refresh, the page should still render normally
    await waitFor(() => expect(screen.getByText('System Health')).toBeInTheDocument());
  }, 10_000);
});

// ═════════════════════════════════════════════════════════════════════════════
// SuperAdminConsole
// ═════════════════════════════════════════════════════════════════════════════

describe('SuperAdminConsole', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<SuperAdminConsole />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Super Admin Console')).toBeInTheDocument();
    });
  }, 10_000);

  it('renders tenant stats row', async () => {
    const wrapper = createWrapper();
    render(<SuperAdminConsole />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Total Tenants')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  }, 10_000);

  it('renders tenant table rows', async () => {
    const wrapper = createWrapper();
    render(<SuperAdminConsole />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('Beta Inc')).toBeInTheDocument();
    });
  }, 10_000);
});

// BillingAdmin
describe('BillingAdmin', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<BillingAdmin />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Billing & Subscription')).toBeInTheDocument();
    });
  }, 10_000);

  it('displays invoice list', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<BillingAdmin />, { wrapper });

    await waitFor(() => screen.getByRole('tab', { name: /^Invoices/i }));
    await user.click(screen.getByRole('tab', { name: /^Invoices/i }));

    await waitFor(() => {
      expect(screen.getByText('INV-001')).toBeInTheDocument();
    });
  }, 10_000);

  it('switches to usage tab', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<BillingAdmin />, { wrapper });

    await waitFor(() => screen.getByRole('tab', { name: /^Usage/i }));
    await user.click(screen.getByRole('tab', { name: /^Usage/i }));

    await waitFor(() => {
      expect(screen.getByText('Usage Metrics')).toBeInTheDocument();
    });
  }, 10_000);
});
