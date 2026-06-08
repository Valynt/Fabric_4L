/**
 * Admin Pages — Test Suite
 *
 * Tests for all admin governance pages:
 * - FormulaGovernance
 * - BenchmarkPolicies
 * - VariableRegistry
 * - PackManagement
 * - PermissionsAdmin
 * - PlatformSettings
 * - HealthMonitor
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createWrapper, renderWithRouter } from '../../test-utils';

// Static imports avoid per-test dynamic import overhead that causes timeouts
import FormulaGovernance from './FormulaGovernance';
import BenchmarkPolicies from './BenchmarkPolicies';
import VariableRegistry from './VariableRegistry';
import PackManagement from './PackManagement';
import PermissionsAdmin from './PermissionsAdmin';
import PlatformSettings from './PlatformSettings';
import HealthMonitor from './HealthMonitor';
import BillingAdmin from './BillingAdmin';

// Mock the hooks to avoid backend dependencies
vi.mock('@/hooks/useFormulas', () => ({
  useFormulas: () => ({
    data: [
      { id: '1', formula_id: 'f-001', name: 'Test Formula', version: '1.0.0', status: 'active' },
    ],
    isLoading: false,
    error: null,
  }),
  useFormulaApprovals: () => ({
    data: [],
    isLoading: false,
    error: null,
  }),
  useApproveFormula: () => ({
    mutate: () => {},
    mutateAsync: async () => {},
    isPending: false,
  }),
  useSubmitFormula: () => ({
    mutate: () => {},
    mutateAsync: async () => {},
    isPending: false,
  }),
}));

vi.mock('@/hooks/useBenchmarks', () => ({
  useBenchmarks: () => ({
    data: [],
    isLoading: false,
    error: null,
  }),
  useBenchmarkPolicies: () => ({
    data: [],
    isLoading: false,
    error: null,
  }),
}));

vi.mock('@/hooks/useValuePacks', () => ({
  useValuePacks: () => ({
    data: [],
    isLoading: false,
    error: null,
  }),
}));

vi.mock('@/hooks/useVariables', () => ({
  useVariables: () => ({
    data: [
      {
        variable_id: 'var-1',
        name: 'contract_value',
        display_name: 'Contract Value',
        description: 'Total signed contract value.',
        type: 'currency',
        unit: 'USD',
        source: 'CRM',
        binding: 'opportunity.amount',
        binding_path: 'crm.opportunity.amount',
        used_in_count: 3,
        validation_status: 'validated',
        version: '1.0.0',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      },
    ],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useSourceBindings: () => ({
    data: [
      {
        id: 'binding-1',
        name: 'Salesforce CRM',
        source: 'CRM',
        status: 'connected',
        variables_bound: 1,
        connection_string: 'salesforce://tenant/test',
        last_sync: '2026-01-02T00:00:00Z',
      },
    ],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useVariableStats: () => ({
    data: {
      total: 1,
      validated: 1,
      pending: 0,
      failed: 0,
      avg_usage: 3,
    },
    isLoading: false,
    error: null,
  }),
  useValidateVariable: () => ({
    mutate: vi.fn(),
    mutateAsync: async () => ({}),
    isPending: false,
  }),
  useTestVariableBinding: () => ({
    mutate: vi.fn(),
    mutateAsync: async () => ({ success: true }),
    isPending: false,
  }),
}));

vi.mock('@/hooks/useGovernance', () => ({
  useUsers: () => ({
    data: [
      {
        id: 'u-1',
        email: 'admin@example.com',
        display_name: 'Admin User',
        role: 'tenant_admin',
        status: 'active',
        tenant_id: 't-1',
        created_at: '2026-01-01T00:00:00Z',
        last_login_at: '2026-01-02T00:00:00Z',
      },
    ],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useApiKeys: () => ({
    data: [
      {
        id: 'k-1',
        name: 'Primary Key',
        prefix: 'pk_live_',
        tenant_id: 't-1',
        is_enabled: true,
        created_at: '2026-01-01T00:00:00Z',
        last_used_at: '2026-01-03T00:00:00Z',
      },
    ],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useRevokeApiKey: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useInviteUser: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

vi.mock('@/hooks/usePlatformSettings', () => ({
  usePlatformSettings: () => ({
    data: {
      tenant_id: 't-1',
      tenant_name: 'Test Tenant',
      features: {
        advanced_analytics: true,
        custom_integrations: false,
        ai_assistant: true,
        audit_trail: false,
      },
      limits: {
        max_users: 100,
        max_api_calls_per_day: 50000,
        storage_gb: 500,
      },
      notifications: {
        email_alerts: true,
      },
      security: {
        require_2fa: false,
        session_timeout_minutes: 60,
        ip_allowlist: [],
      },
      updated_at: '2026-01-01T00:00:00Z',
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useUpdatePlatformSettings: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
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
  useSystemHealth: () => ({
    data: {
      overall_status: 'healthy',
      checked_at: '2026-01-01T00:00:00Z',
      services: [
        {
          name: 'l1-ingestion',
          status: 'healthy',
          version: '1.0.0',
          uptime_seconds: 3600,
          last_check_at: '2026-01-01T00:00:00Z',
          response_time_ms: 45,
        },
      ],
      summary: {
        healthy: 1,
        degraded: 0,
        unhealthy: 0,
        unknown: 0,
        total: 1,
      },
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useHealthAlerts: () => ({
    data: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

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
describe('FormulaGovernance', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<FormulaGovernance />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Formula Governance')).toBeInTheDocument();
    });
  }, 20_000);
});

// BenchmarkPolicies
describe('BenchmarkPolicies', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<BenchmarkPolicies />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Benchmark Policies')).toBeInTheDocument();
    });
  }, 10_000);
});

// VariableRegistry
describe('VariableRegistry', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<VariableRegistry />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Variable Registry')).toBeInTheDocument();
    });
  }, 10_000);
});

// PackManagement
describe('PackManagement', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<PackManagement />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Pack Management')).toBeInTheDocument();
    });
  }, 10_000);
});

// PermissionsAdmin
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
});

// PlatformSettings
describe('PlatformSettings', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<PlatformSettings />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Platform Settings')).toBeInTheDocument();
    });
  }, 10_000);
});

// HealthMonitor
describe('HealthMonitor', () => {
  it('renders without crashing', async () => {
    const wrapper = createWrapper();
    render(<HealthMonitor />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('System Health')).toBeInTheDocument();
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
    const wrapper = createWrapper();
    render(<BillingAdmin />, { wrapper });

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
