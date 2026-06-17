/**
 * Admin Mock Factories
 *
 * Shared mock factories for all admin page tests.
 * Pattern follows TargetsAdmin.test.tsx — each factory returns a vi.fn()
 * that can be overridden per test.
 */

import { vi } from 'vitest';

// ── useFormulas ──────────────────────────────────────────────────────────────

export const DEFAULT_FORMULAS = [
  {
    id: 'f-001',
    formula_id: 'f-001',
    name: 'Test Formula',
    version: '1.0.0',
    status: 'active',
    pack_name: 'Test Pack',
    description: 'A test formula',
    owner: 'admin@example.com',
    governance_score: 85,
    used_in_count: 3,
    updated_at: '2026-01-01T00:00:00Z',
  },
];

export const DEFAULT_APPROVALS = [
  {
    id: 'a-001',
    formula_id: 'f-001',
    formula_name: 'Test Formula',
    change_summary: 'Updated driver mapping',
    submitted_by: 'user@example.com',
    submitted_at: '2026-01-02T00:00:00Z',
    previous_version: '1.0.0',
  },
];

export const makeUseFormulas = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_FORMULAS,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));

export const makeUseFormulaApprovals = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_APPROVALS,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));

export const makeUseApproveFormula = (overrides = {}) =>
  vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
    ...overrides,
  }));

export const makeUseSubmitFormula = (overrides = {}) =>
  vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
    ...overrides,
  }));

// ── useBenchmarks ────────────────────────────────────────────────────────────

export const DEFAULT_BENCHMARKS = [
  {
    id: 'b-001',
    name: 'Test Benchmark',
    industry: 'Software',
    vertical: 'SaaS',
    value_range: '10-50%',
    confidence: 'High',
    source: 'Industry Report',
    year: 2025,
    status: 'active',
    usage_count: 5,
    tags: ['revenue', 'growth'],
    last_verified: '2026-01-01T00:00:00Z',
  },
];

export const makeUseBenchmarks = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_BENCHMARKS,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));

export const makeUseBenchmarkPolicies = (overrides = {}) =>
  vi.fn(() => ({
    data: [],
    isLoading: false,
    error: null,
    ...overrides,
  }));

// ── useValuePacks ────────────────────────────────────────────────────────────

export const DEFAULT_VALUE_PACKS = [
  {
    id: 'vp-001',
    name: 'Test Pack',
    description: 'A test value pack',
    industry: 'Software',
    status: 'published',
    driver_count: 3,
    formula_count: 5,
    benchmark_count: 2,
    version: '1.0.0',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

export const makeUseValuePacks = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_VALUE_PACKS,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));

// ── useVariables ─────────────────────────────────────────────────────────────

export const DEFAULT_VARIABLES = [
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
    validation_message: '',
    version: '1.0.0',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    default_value: null,
    valid_range: { min: 0, max: 1000000 },
  },
  {
    variable_id: 'var-2',
    name: 'lead_score',
    display_name: 'Lead Score',
    description: 'ML-derived lead quality score.',
    type: 'float',
    unit: 'points',
    source: 'Model',
    binding: 'ml.lead_score',
    binding_path: 'ml.lead_score',
    used_in_count: 1,
    validation_status: 'pending',
    validation_message: '',
    version: '1.0.0',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    default_value: '0.0',
    valid_range: null,
  },
];

export const DEFAULT_SOURCE_BINDINGS = [
  {
    id: 'binding-1',
    name: 'Salesforce CRM',
    source: 'CRM',
    status: 'connected',
    variables_bound: 1,
    connection_string: 'salesforce://tenant/test',
    last_sync: '2026-01-02T00:00:00Z',
    error_message: '',
  },
];

export const DEFAULT_VARIABLE_STATS = {
  total: 2,
  validated: 1,
  pending: 1,
  failed: 0,
  avg_usage: 2,
};

export const makeUseVariables = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_VARIABLES,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));

export const makeUseSourceBindings = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_SOURCE_BINDINGS,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));

export const makeUseVariableStats = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_VARIABLE_STATS,
    isLoading: false,
    error: null,
    ...overrides,
  }));

export const makeUseValidateVariable = (overrides = {}) =>
  vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
    ...overrides,
  }));

export const makeUseTestVariableBinding = (overrides = {}) =>
  vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({
      pass: true,
      evaluated_value: 12345,
      failure_class: null,
      source_trace: { source: 'CRM', binding: 'opportunity.amount', resolved_path: 'crm.opportunity.amount' },
      diagnostics: [],
    }),
    isPending: false,
    ...overrides,
  }));

// ── useGovernance ────────────────────────────────────────────────────────────

export const DEFAULT_USERS = [
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
  {
    id: 'u-2',
    email: 'member@example.com',
    display_name: 'Member User',
    role: 'member',
    status: 'active',
    tenant_id: 't-1',
    created_at: '2026-01-01T00:00:00Z',
    last_login_at: '2026-01-02T00:00:00Z',
  },
];

export const DEFAULT_API_KEYS = [
  {
    key_id: 'vf_00000000000000000000000000000001',
    name: 'Primary Key',
    prefix: 'pk_live_',
    tenant_id: 't-1',
    role: 'analyst',
    enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    expires_at: undefined,
    last_used_at: '2026-01-03T00:00:00Z',
  },
  {
    key_id: 'vf_00000000000000000000000000000002',
    name: 'Revoked Key',
    prefix: 'pk_rev_',
    tenant_id: 't-1',
    role: 'read_only',
    enabled: false,
    revoked_at: '2026-01-04T00:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
    expires_at: undefined,
    last_used_at: undefined,
  },
];

export const DEFAULT_CREATED_API_KEY = {
  key_id: 'vf_00000000000000000000000000000003',
  name: 'New Key',
  prefix: 'pk_new_',
  tenant_id: 't-1',
  role: 'analyst',
  permissions: ['read:health'],
  api_key: 'vf_testsecretvalue_12345',
  expires_at: undefined,
  created_at: '2026-01-05T00:00:00Z',
};

export const makeUseUsers = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_USERS,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));

export const makeUseApiKeys = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_API_KEYS,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));

export const makeUseCreateApiKey = (overrides = {}) =>
  vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue(DEFAULT_CREATED_API_KEY),
    isPending: false,
    reset: vi.fn(),
    ...overrides,
  }));

export const makeUseRevokeApiKey = (overrides = {}) =>
  vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
    ...overrides,
  }));

export const makeUseInviteUser = (overrides = {}) =>
  vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
    ...overrides,
  }));

// ── usePlatformSettings ──────────────────────────────────────────────────────

export const DEFAULT_PLATFORM_SETTINGS = {
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
    webhook_url: '',
    slack_webhook: '',
  },
  security: {
    require_2fa: false,
    session_timeout_minutes: 60,
    ip_allowlist: [],
  },
  branding: {
    logo_url: '',
    primary_color: '#2563eb',
    favicon_url: '',
  },
  updated_at: '2026-01-01T00:00:00Z',
};

export const makeUsePlatformSettings = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_PLATFORM_SETTINGS,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));

export const makeUseUpdatePlatformSettings = (overrides = {}) =>
  vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
    ...overrides,
  }));

// ── useHealthMonitor ─────────────────────────────────────────────────────────

export const DEFAULT_SYSTEM_HEALTH = {
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
      error_message: '',
    },
    {
      name: 'l2-extraction',
      status: 'degraded',
      version: '1.0.1',
      uptime_seconds: 1800,
      last_check_at: '2026-01-01T00:00:00Z',
      response_time_ms: 1200,
      error_message: 'High memory usage',
    },
  ],
  summary: {
    healthy: 1,
    degraded: 1,
    unhealthy: 0,
    unknown: 0,
    total: 2,
  },
};

export const DEFAULT_HEALTH_ALERTS = [
  {
    id: 'alert-1',
    service_name: 'l2-extraction',
    severity: 'warning',
    message: 'Response time elevated',
    started_at: '2026-01-01T00:00:00Z',
    resolved_at: null,
  },
];

export const makeUseSystemHealth = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_SYSTEM_HEALTH,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    dataUpdatedAt: Date.now(),
    ...overrides,
  }));

export const makeUseHealthAlerts = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_HEALTH_ALERTS,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));

// ── useSuperAdminOverview ────────────────────────────────────────────────────

export const DEFAULT_TENANT_OVERVIEW = {
  items: [
    {
      id: 'tenant-1',
      name: 'Acme Corp',
      slug: 'acme',
      status: 'active',
      tier_id: 'enterprise',
      user_count: 42,
      active_workflow_count: 5,
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'tenant-2',
      name: 'Beta Inc',
      slug: 'beta',
      status: 'pending',
      tier_id: 'team',
      user_count: 8,
      active_workflow_count: 1,
      created_at: '2026-01-01T00:00:00Z',
    },
  ],
  total: 2,
};

export const makeUseSuperAdminOverview = (overrides = {}) =>
  vi.fn(() => ({
    data: DEFAULT_TENANT_OVERVIEW,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  }));
