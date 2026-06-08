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
import { createWrapper, renderWithRouter } from '../../test-utils';

// Static imports avoid per-test dynamic import overhead that causes timeouts
import FormulaGovernance from './FormulaGovernance';
import BenchmarkPolicies from './BenchmarkPolicies';
import VariableRegistry from './VariableRegistry';
import PackManagement from './PackManagement';
import PermissionsAdmin from './PermissionsAdmin';
import PlatformSettings from './PlatformSettings';
import HealthMonitor from './HealthMonitor';

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
