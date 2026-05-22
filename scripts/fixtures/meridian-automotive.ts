/**
 * Meridian Automotive — Canonical E2E Fixture
 *
 * This fixture contains all deterministic test data for the primary E2E
 * journey account. Every ID, timestamp, and value is fixed so that
 * Playwright assertions can match exact strings.
 *
 * Industry: Manufacturing / Automotive Supplier
 * Scenario: Mid-market supplier evaluating operational efficiency platform
 */

// ---------------------------------------------------------------------------
// Stable IDs — never change these across runs
// ---------------------------------------------------------------------------

const ACCOUNT_ID = 'acct-meridian-001';
const CASE_ID = 'case-meridian-e2e-001';
const TENANT_ID = process.env.BACKEND_E2E_TENANT_ID || '00000000-0000-4000-e2e0-000000000001';

// ---------------------------------------------------------------------------
// Account Profile
// ---------------------------------------------------------------------------

const account = {
  id: ACCOUNT_ID,
  provider: 'manual' as const,
  name: 'Meridian Automotive',
  domain: 'meridian-auto.com',
  industry: 'Manufacturing',
  region: 'North America',
  company_size: 2400,
  owner_name: 'Sarah Chen',
  stage: 'Discovery',
  segment: 'Mid-Market',
  sync_status: 'synced' as const,
  annual_revenue: 380_000_000,
  employee_count: 2400,
  description:
    'Tier-2 automotive parts supplier specializing in precision-machined drivetrain components for OEMs across North America.',
  enrichment_status: 'complete' as const,
  opportunities: [
    {
      provider_opportunity_id: 'opp-meridian-001',
      name: 'Operational Efficiency Platform',
      stage: 'Discovery',
      value: 450_000,
      probability: 0.35,
      close_date: '2026-09-30',
      last_synced_at: '2026-04-01T00:00:00Z',
    },
  ],
  contacts: [
    {
      provider_contact_id: 'contact-meridian-001',
      name: 'James Whitfield',
      title: 'VP Operations',
      email: 'j.whitfield@meridian-auto.com',
      phone: '+1-555-0101',
      is_primary: true,
      last_synced_at: '2026-04-01T00:00:00Z',
    },
    {
      provider_contact_id: 'contact-meridian-002',
      name: 'Lisa Park',
      title: 'Director of IT',
      email: 'l.park@meridian-auto.com',
      phone: '+1-555-0102',
      is_primary: false,
      last_synced_at: '2026-04-01T00:00:00Z',
    },
    {
      provider_contact_id: 'contact-meridian-003',
      name: 'Robert Tanaka',
      title: 'CFO',
      email: 'r.tanaka@meridian-auto.com',
      phone: '+1-555-0103',
      is_primary: false,
      last_synced_at: '2026-04-01T00:00:00Z',
    },
  ],
};

// ---------------------------------------------------------------------------
// Case / Workspace
// ---------------------------------------------------------------------------

const caseData = {
  case_id: CASE_ID,
  account_id: ACCOUNT_ID,
  title: 'Meridian Automotive — Operational Efficiency Assessment',
  status: 'active',
};

// ---------------------------------------------------------------------------
// Intelligence Workspace Tabs
// ---------------------------------------------------------------------------

const signals = [
  {
    id: 'sig-001',
    text: 'Manual approval routing causes 3-day average delays in purchase orders',
    category: 'process_inefficiency',
    severity: 'high',
    confidence: 0.92,
    source: 'Discovery call transcript — 2026-03-15',
    detected_at: '2026-03-15T14:30:00Z',
  },
  {
    id: 'sig-002',
    text: 'Quality inspection data is siloed in 4 separate spreadsheet systems',
    category: 'data_fragmentation',
    severity: 'high',
    confidence: 0.88,
    source: 'IT assessment document',
    detected_at: '2026-03-16T09:00:00Z',
  },
  {
    id: 'sig-003',
    text: 'Supplier scorecards updated quarterly instead of real-time, causing delayed risk detection',
    category: 'visibility_gap',
    severity: 'medium',
    confidence: 0.85,
    source: 'Operations review deck — Q1 2026',
    detected_at: '2026-03-17T11:15:00Z',
  },
  {
    id: 'sig-004',
    text: 'Production line changeover takes 45 minutes vs. industry benchmark of 20 minutes',
    category: 'operational_bottleneck',
    severity: 'high',
    confidence: 0.91,
    source: 'Plant tour observation notes',
    detected_at: '2026-03-18T16:00:00Z',
  },
  {
    id: 'sig-005',
    text: 'Customer complaints about delivery variance increased 18% YoY',
    category: 'customer_impact',
    severity: 'medium',
    confidence: 0.79,
    source: 'Annual report FY2025',
    detected_at: '2026-03-19T08:45:00Z',
  },
];

const drivers = [
  {
    id: 'drv-001',
    name: 'Manual process overhead',
    description:
      'Purchase order approvals, quality sign-offs, and supplier evaluations all require manual routing through email and spreadsheets.',
    impact: 'high',
    signals: ['sig-001', 'sig-004'],
    quantified_cost: '$1.8M annually in labor and delay costs',
  },
  {
    id: 'drv-002',
    name: 'Fragmented data systems',
    description:
      'Quality, procurement, and production data lives in disconnected spreadsheets and legacy systems with no single source of truth.',
    impact: 'high',
    signals: ['sig-002', 'sig-003'],
    quantified_cost: '$620K annually in reconciliation and error correction',
  },
  {
    id: 'drv-003',
    name: 'Lack of real-time operational visibility',
    description:
      'Management relies on quarterly reports and manual dashboards, preventing proactive intervention on emerging issues.',
    impact: 'medium',
    signals: ['sig-003', 'sig-005'],
    quantified_cost: '$340K annually in reactive firefighting',
  },
];

const evidence = [
  {
    id: 'evi-001',
    claim: 'Purchase order approval cycle averages 3 business days',
    source: 'Discovery call transcript — James Whitfield, VP Operations',
    source_date: '2026-03-15',
    confidence: 0.92,
    validation_status: 'validated',
    linked_signals: ['sig-001'],
  },
  {
    id: 'evi-002',
    claim: 'Quality data exists in 4 separate spreadsheet systems across 3 plants',
    source: 'IT infrastructure assessment — Lisa Park, Director of IT',
    source_date: '2026-03-16',
    confidence: 0.88,
    validation_status: 'validated',
    linked_signals: ['sig-002'],
  },
  {
    id: 'evi-003',
    claim: 'Changeover time is 2.25x the industry benchmark',
    source: 'Plant tour observation — Meridian Dayton facility',
    source_date: '2026-03-18',
    confidence: 0.91,
    validation_status: 'validated',
    linked_signals: ['sig-004'],
  },
  {
    id: 'evi-004',
    claim: 'Delivery variance complaints up 18% year-over-year',
    source: 'Meridian Automotive FY2025 Annual Report, p.34',
    source_date: '2026-02-28',
    confidence: 0.95,
    validation_status: 'validated',
    linked_signals: ['sig-005'],
  },
];

const stakeholders = [
  {
    id: 'sth-001',
    name: 'James Whitfield',
    title: 'VP Operations',
    role: 'Champion',
    influence: 'high',
    concerns: ['Reducing manual overhead', 'Improving changeover time'],
    engagement_status: 'active',
  },
  {
    id: 'sth-002',
    name: 'Lisa Park',
    title: 'Director of IT',
    role: 'Technical Evaluator',
    influence: 'high',
    concerns: ['Integration with existing ERP', 'Data migration complexity'],
    engagement_status: 'active',
  },
  {
    id: 'sth-003',
    name: 'Robert Tanaka',
    title: 'CFO',
    role: 'Economic Buyer',
    influence: 'high',
    concerns: ['ROI timeline', 'Total cost of ownership'],
    engagement_status: 'pending',
  },
  {
    id: 'sth-004',
    name: 'Maria Santos',
    title: 'Plant Manager — Dayton',
    role: 'End User',
    influence: 'medium',
    concerns: ['Disruption to production schedule', 'Training requirements'],
    engagement_status: 'active',
  },
];

// ---------------------------------------------------------------------------
// Value Studio Workspace Tabs
// ---------------------------------------------------------------------------

const valueModel = [
  {
    id: 'vm-001',
    category: 'Cost Reduction',
    line_item: 'Automated approval workflows',
    current_cost: 1_800_000,
    projected_savings: 1_260_000,
    confidence: 0.85,
    horizon: 'Year 1',
    assumptions: ['70% of approvals automated', '30% reduction in cycle time'],
  },
  {
    id: 'vm-002',
    category: 'Cost Reduction',
    line_item: 'Unified quality data platform',
    current_cost: 620_000,
    projected_savings: 434_000,
    confidence: 0.80,
    horizon: 'Year 1-2',
    assumptions: ['Single source of truth', 'Eliminate 70% of manual reconciliation'],
  },
  {
    id: 'vm-003',
    category: 'Revenue Protection',
    line_item: 'Real-time supplier risk detection',
    current_cost: 340_000,
    projected_savings: 238_000,
    confidence: 0.75,
    horizon: 'Year 1',
    assumptions: ['Quarterly to real-time monitoring', 'Early intervention on 60% of issues'],
  },
  {
    id: 'vm-004',
    category: 'Productivity',
    line_item: 'Reduced changeover time',
    current_cost: 0,
    projected_savings: 520_000,
    confidence: 0.70,
    horizon: 'Year 2',
    assumptions: ['45min to 25min changeover', '3 production lines'],
  },
];

const narrative = [
  {
    id: 'nar-001',
    section: 'Executive Summary',
    content:
      'Meridian Automotive faces $2.76M in annual operational inefficiency driven by manual processes, fragmented data systems, and lack of real-time visibility. Our platform addresses all three root causes with a projected $2.45M in first-year value.',
  },
  {
    id: 'nar-002',
    section: 'Current State',
    content:
      'As a Tier-2 automotive supplier with 2,400 employees across 3 plants, Meridian relies on manual approval routing (3-day average delays), siloed quality data (4 separate spreadsheet systems), and quarterly supplier scorecards that prevent proactive risk management.',
  },
  {
    id: 'nar-003',
    section: 'Recommended Approach',
    content:
      'A phased implementation starting with workflow automation (Q2), followed by data unification (Q3), and real-time analytics (Q4) minimizes disruption while delivering measurable value within 90 days of deployment.',
  },
];

const actionPlan = [
  {
    id: 'ap-001',
    phase: 'Phase 1 — Quick Wins',
    timeline: 'Q2 2026',
    actions: [
      'Deploy automated PO approval workflow',
      'Configure real-time supplier scorecard feeds',
      'Train operations team on new dashboard',
    ],
    expected_value: '$1.26M annualized',
    owner: 'James Whitfield',
  },
  {
    id: 'ap-002',
    phase: 'Phase 2 — Data Unification',
    timeline: 'Q3 2026',
    actions: [
      'Migrate quality data from 4 spreadsheet systems',
      'Integrate with existing ERP (SAP)',
      'Establish single source of truth for quality metrics',
    ],
    expected_value: '$434K annualized',
    owner: 'Lisa Park',
  },
  {
    id: 'ap-003',
    phase: 'Phase 3 — Advanced Analytics',
    timeline: 'Q4 2026',
    actions: [
      'Deploy real-time production analytics',
      'Implement predictive changeover optimization',
      'Launch executive visibility dashboard',
    ],
    expected_value: '$758K annualized',
    owner: 'James Whitfield',
  },
];

// ---------------------------------------------------------------------------
// Platform Settings (Governance)
// ---------------------------------------------------------------------------

const settings = {
  features: {
    value_studio: true,
    intelligence_workspace: true,
    agent_stream: true,
    governance_dashboard: true,
    benchmark_policies: true,
    health_monitoring: true,
    api_keys: true,
    team_management: true,
  },
  notifications: {
    email: true,
    slack: false,
    webhook_url: '',
  },
  branding: {
    company_name: 'Fabric 4L E2E',
    logo_url: '',
    primary_color: '#1a56db',
  },
  security: {
    mfa_required: false,
    session_timeout_minutes: 60,
    ip_allowlist: [],
  },
};

// ---------------------------------------------------------------------------
// Ingestion Jobs (for Command Center / J1)
// ---------------------------------------------------------------------------

const ingestionJobs = [
  {
    id: 'job-meridian-001',
    domain: 'meridian-auto.com',
    status: 'COMPLETED',
    pages_crawled: 47,
    pages_total: 47,
    created_at: '2026-03-14T10:00:00Z',
    completed_at: '2026-03-14T10:12:34Z',
    content_blocks: 312,
  },
  {
    id: 'job-meridian-002',
    domain: 'meridian-auto.com/careers',
    status: 'COMPLETED',
    pages_crawled: 12,
    pages_total: 12,
    created_at: '2026-03-14T11:00:00Z',
    completed_at: '2026-03-14T11:03:22Z',
    content_blocks: 89,
  },
];

// ---------------------------------------------------------------------------
// Value Tree (for J1 Step 5)
// ---------------------------------------------------------------------------

const valueTree = {
  root_entity_id: 'cap-meridian-001',
  direction: 'upward' as const,
  nodes: [
    {
      id: 'cap-meridian-001',
      label: 'Workflow Automation',
      type: 'Capability',
      layer: 1,
      confidence: 0.92,
      properties: { domain: 'meridian-auto.com' },
    },
    {
      id: 'uc-meridian-001',
      label: 'Automated PO Approval',
      type: 'UseCase',
      layer: 2,
      confidence: 0.88,
      properties: {},
    },
    {
      id: 'per-meridian-001',
      label: 'Operations Manager',
      type: 'Persona',
      layer: 3,
      confidence: 0.85,
      properties: {},
    },
    {
      id: 'vd-meridian-001',
      label: 'Reduce Manual Overhead',
      type: 'ValueDriver',
      layer: 4,
      confidence: 0.90,
      properties: { annual_value: 1_260_000 },
    },
  ],
  edges: [
    { source: 'cap-meridian-001', target: 'uc-meridian-001', type: 'ENABLES', weight: 0.92 },
    { source: 'uc-meridian-001', target: 'per-meridian-001', type: 'BENEFITS', weight: 0.88 },
    { source: 'per-meridian-001', target: 'vd-meridian-001', type: 'DRIVES', weight: 0.90 },
  ],
  paths: [
    { length: 3, nodes: ['cap-meridian-001', 'uc-meridian-001', 'per-meridian-001', 'vd-meridian-001'] },
  ],
  stats: {
    total_nodes: 4,
    total_edges: 3,
    by_layer: { '1': 1, '2': 1, '3': 1, '4': 1 },
    max_depth: 4,
  },
};

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

export const MERIDIAN_FIXTURE = {
  tenantId: TENANT_ID,
  account,
  case: caseData,
  workspace: {
    signals,
    drivers,
    evidence,
    stakeholders,
    valueModel: valueModel,
    narrative,
    actionPlan: actionPlan,
  },
  settings,
  ingestionJobs,
  valueTree,
} as const;

// Re-export IDs for direct use in tests
export { ACCOUNT_ID, CASE_ID, TENANT_ID };
