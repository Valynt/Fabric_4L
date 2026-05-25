/**
 * MSW (Mock Service Worker) handlers for API mocking in tests.
 * Provides consistent, deterministic responses for all API endpoints.
 */

import { http, HttpResponse, delay } from 'msw';

// Helper to generate fake IDs
const generateId = (prefix: string) => `${prefix}-${Math.random().toString(36).substr(2, 9)}`;

// Mock entity data
const mockEntities = [
  { id: 'entity-001', name: 'Cloud Migration', type: 'capability', confidence: 0.95 },
  { id: 'entity-002', name: 'Cost Reduction', type: 'usecase', confidence: 0.88 },
  { id: 'entity-003', name: 'CIO', type: 'persona', confidence: 0.92 },
  { id: 'entity-004', name: 'Revenue Growth', type: 'valuedriver', confidence: 0.85 },
];

// Mock value packs
const mockValuePacks = [
  {
    id: 'pack-001',
    name: 'Digital Transformation',
    description: 'Complete digital transformation framework',
    status: 'published',
    formulas: [{ id: 'f1', name: 'ROI Formula' }],
  },
  {
    id: 'pack-002',
    name: 'Cost Optimization',
    description: 'Cost reduction strategies and formulas',
    status: 'draft',
    formulas: [],
  },
];


const mockCurrentValuePacks = [
  {
    id: 'pack-001',
    pack_id: 'pack-001',
    name: 'Enterprise Security ROI',
    industry: 'SaaS / B2B',
    description: 'Comprehensive security ROI calculations and risk-reduction value modeling.',
    driver_count: 4,
    formula_count: 3,
    benchmark_count: 2,
    workflow_count: 1,
    status: 'active',
    scope: 'global',
    updated_at: '2024-01-15T10:00:00Z',
    created_at: '2024-01-01T00:00:00Z',
    version: '1.2.0',
    owner: 'value-fabric@example.com',
    category: 'Security',
  },
  {
    id: 'pack-002',
    pack_id: 'pack-002',
    name: 'Customer Churn Reduction',
    industry: 'SaaS / B2B',
    description: 'Improves retention through usage, support, and renewal signals.',
    driver_count: 5,
    formula_count: 4,
    benchmark_count: 3,
    workflow_count: 2,
    status: 'published',
    scope: 'tenant',
    updated_at: '2024-02-20T12:00:00Z',
    created_at: '2024-02-01T00:00:00Z',
    version: '1.0.0',
    owner: 'tenant-admin@example.com',
    category: 'Revenue',
  },
];

const mockCurrentFormulas = [
  {
    id: 'formula-1',
    formula_id: 'formula-1',
    name: 'ROI Calculator',
    description: 'Calculates return on investment from benefits and costs.',
    domain: 'Finance',
    formula_type: 'simple',
    pack_id: 'pack-001',
    pack_name: 'Enterprise Security ROI',
    version: '1.0.0',
    status: 'active',
    owner: 'finance@example.com',
    updated_at: '2024-01-15T10:00:00Z',
    created_at: '2024-01-01T00:00:00Z',
    used_in_count: 3,
    governance_score: 0.97,
    last_reviewed: '2024-01-20T00:00:00Z',
    reviewers: ['approver@example.com'],
    expression: '(benefits - costs) / costs',
    variables: ['benefits', 'costs'],
  },
  {
    id: 'formula-2',
    formula_id: 'formula-2',
    name: 'TCO Analysis',
    description: 'Total cost of ownership over a planning horizon.',
    domain: 'Finance',
    formula_type: 'composite',
    pack_id: 'pack-002',
    pack_name: 'Customer Churn Reduction',
    version: '1.2.0',
    status: 'pending',
    owner: 'ops@example.com',
    updated_at: '2024-02-10T10:00:00Z',
    created_at: '2024-02-01T00:00:00Z',
    used_in_count: 1,
    governance_score: 0.84,
    last_reviewed: '2024-02-14T00:00:00Z',
    reviewers: ['reviewer@example.com'],
    expression: 'capex + opex',
    variables: ['capex', 'opex'],
  },
];

const mockCurrentApproval = {
  id: '11111111-1111-4111-8111-111111111111',
  formula_id: 'formula-2',
  formula_name: 'TCO Analysis',
  submitted_by: 'submitter@example.com',
  submitted_at: '2024-02-15T10:00:00.000Z',
  change_summary: 'Updated cost inputs and versioned calculation evidence.',
  previous_version: '1.1.0',
  status: 'pending',
};

const mockFrameworkValuePacks = [
  {
    industry_id: 'saas-b2b',
    display_name: 'SaaS / B2B',
    tier: 1,
    description: 'Pre-wired SaaS growth, retention, and security value framework.',
    driver_count: 4,
    formula_count: 3,
    updated_at: '2024-01-15T10:00:00Z',
    primary_value_drivers: [
      {
        id: 'driver-security-risk',
        name: 'Security Risk Reduction',
        description: 'Quantifies reduced breach exposure and control automation.',
        typical_impact: '10-25% lower expected annual loss',
        measurement_approach: 'Expected loss avoided and control labor reduction',
      },
    ],
    core_use_cases: [
      {
        id: 'usecase-retention',
        name: 'Retention Expansion',
        description: 'Connect product usage and support signals to renewal value.',
        target_persona: 'Customer Success',
        business_problem: 'Reducing churn across strategic accounts',
      },
    ],
    economic_model_types: [
      {
        id: 'model-roi',
        name: 'ROI Model',
        formula_shape: '(benefits - costs) / costs',
        inputs: ['benefits', 'costs'],
        output_unit: 'ratio',
      },
    ],
    why_it_wins: [
      {
        statement: 'Links operational evidence to board-level value metrics.',
        differentiation: 'Combines graph-grounded variables with governed formulas.',
        proof_point: 'Approved formulas and evidence-backed variables are shipped together.',
      },
    ],
    composable_model_templates: [
      {
        template_id: 'template-roi',
        template_name: 'ROI Calculator',
        formula_pattern: '(benefits - costs) / costs',
        applicable_industries: ['SaaS / B2B'],
        example_calculation: '(400000 - 100000) / 100000 = 3.0',
      },
    ],
    pre_wired_ontology_tags: [
      { tag: 'security', category: 'value_driver', related_tags: ['risk', 'compliance'] },
    ],
    metadata: {
      deal_size_range: '$50k-$500k',
      sales_cycle_length: '60-120 days',
      switching_cost: 'medium',
      data_richness: 'high',
      feedback_loop_speed: 'fast',
    },
    completeness_score: 0.95,
    proof_requirements: [
      { id: 'proof-1', requirement: 'Approved ROI formula evidence', evidence_type: 'formula' },
    ],
  },
  {
    industry_id: 'industrial-iot',
    display_name: 'Industrial IoT',
    tier: 2,
    description: 'Operational reliability and predictive-maintenance value framework.',
    driver_count: 3,
    formula_count: 2,
    updated_at: '2024-02-20T12:00:00Z',
    primary_value_drivers: [],
    core_use_cases: [],
    economic_model_types: [],
    why_it_wins: [],
    composable_model_templates: [],
    pre_wired_ontology_tags: [{ tag: 'reliability', category: 'value_driver', related_tags: ['uptime'] }],
    metadata: {
      deal_size_range: '$250k-$2M',
      sales_cycle_length: '120-240 days',
      switching_cost: 'high',
      data_richness: 'medium',
      feedback_loop_speed: 'medium',
    },
    completeness_score: 0.88,
    proof_requirements: [],
  },
];

const mockCurrentVariables = [
  {
    id: 'var-001',
    variable_id: 'benefits',
    name: 'benefits',
    display_name: 'Annual Benefits',
    description: 'Projected annual quantified benefits.',
    type: 'currency',
    unit: 'USD',
    source: 'CRM',
    binding: 'crm.opportunity.annual_benefits',
    binding_path: '$.opportunity.annual_benefits',
    default_value: '100000',
    valid_range: { min: 0, max: 10000000 },
    used_in_count: 7,
    validation_status: 'validated',
    validation_message: 'Validated against source evidence.',
    tags: ['finance', 'roi'],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    version: '1.0.0',
  },
  {
    id: 'var-002',
    variable_id: 'costs',
    name: 'costs',
    display_name: 'Implementation Costs',
    description: 'One-time and recurring implementation costs.',
    type: 'currency',
    unit: 'USD',
    source: 'ERP',
    binding: 'erp.project.total_cost',
    binding_path: '$.project.total_cost',
    default_value: '25000',
    valid_range: { min: 0, max: 5000000 },
    used_in_count: 5,
    validation_status: 'pending',
    validation_message: 'Awaiting next ERP sync.',
    tags: ['finance', 'cost'],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-16T00:00:00Z',
    version: '1.0.0',
  },
];

const mockCurrentBindings = [
  {
    id: 'binding-001',
    name: 'CRM Opportunity',
    source_type: 'CRM',
    connection_string: 'salesforce://tenant/opportunity',
    status: 'connected',
    last_sync: '2024-01-15T00:00:00Z',
    variables_bound: 4,
  },
  {
    id: 'binding-002',
    name: 'ERP Project Ledger',
    source_type: 'ERP',
    connection_string: 'erp://tenant/project-ledger',
    status: 'connected',
    last_sync: '2024-01-16T00:00:00Z',
    variables_bound: 3,
  },
];

const mockGraphNodes = [
  {
    id: 'entity-001',
    name: 'Cloud Migration',
    entity_type: 'capability',
    confidence_score: 0.95,
    description: 'Cloud migration capability with quantified value impact.',
    properties: { domain: 'infrastructure' },
  },
  {
    id: 'entity-002',
    name: 'Cost Reduction',
    entity_type: 'value_driver',
    confidence_score: 0.88,
    description: 'Cost reduction value driver linked to cloud modernization.',
    properties: { domain: 'finance' },
  },
  {
    id: 'entity-003',
    name: 'CIO',
    entity_type: 'persona',
    confidence_score: 0.92,
    description: 'Executive buyer persona accountable for modernization outcomes.',
    properties: { seniority: 'executive' },
  },
];

const mockGraphRelationships = [
  { source: 'entity-001', target: 'entity-002', type: 'enables', confidence: 0.91 },
  { source: 'entity-003', target: 'entity-001', type: 'owns', confidence: 0.86 },
];

const mockSubgraphNodes = mockGraphNodes.slice(0, 2);
const mockSubgraphRelationships = mockGraphRelationships.slice(0, 1);

const mockBusinessCase = {
  case_id: 'case-001',
  title: 'Test Business Case',
  summary: 'Modernize infrastructure to reduce operating cost and improve deployment velocity.',
  total_value: 1200000,
  implementation_cost: 300000,
  roi_ratio: 4.0,
  payback_months: 12,
  confidence_score: 0.92,
  recommendations: [
    'Implement solution within Q2',
    'Focus on high-value customer segments',
    'Monitor metrics monthly',
  ],
  status: 'completed',
  created_at: '2024-03-01T00:00:00Z',
  updated_at: '2024-03-02T00:00:00Z',
  document_url: '/exports/case-001.pdf',
  page_count: 12,
  file_size_bytes: 524288,
  truth_references: ['truth-001'],
  remediation_items: [],
  case_metadata: { owner: 'value-team@example.com' },
};

const mockTruthItems = [
  {
    id: 'truth-001',
    truth_id: 'truth-001',
    claim: 'Cloud migration reduces annual infrastructure cost by 20%.',
    status: 'validated',
    maturity_level: 4,
    confidence: 0.93,
    freshness: 'fresh',
    is_stale: false,
    source_count: 3,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-03-01T00:00:00Z',
  },
  {
    id: 'truth-002',
    truth_id: 'truth-002',
    claim: 'Legacy renewal benchmark requires quarterly refresh.',
    status: 'pending',
    maturity_level: 2,
    confidence: 0.64,
    freshness: 'stale',
    is_stale: true,
    source_count: 1,
    created_at: '2024-01-15T00:00:00Z',
    updated_at: '2024-01-20T00:00:00Z',
  },
];

const mockMaturityLadder = {
  levels: [
    { level: 1, name: 'Claim Captured', required_status: 'draft', count: 0 },
    { level: 2, name: 'Source Attached', required_status: 'pending', count: 1 },
    { level: 3, name: 'Evidence Reviewed', required_status: 'validated', count: 0 },
    { level: 4, name: 'Production Approved', required_status: 'validated', count: 1 },
  ],
};

// Mock user
const mockUser = {
  id: 'user-001',
  email: 'test@example.com',
  name: 'Test User',
  tenant_id: 'tenant-001',
  role: 'editor',
  tier: 'advanced',
};

export const handlers = [


  // Current L3 value-pack routes
  http.get('/api/v1/graph/packs', ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get('search')?.toLowerCase() ?? '';
    const packs = search
      ? mockCurrentValuePacks.filter((pack) =>
          pack.name.toLowerCase().includes(search) ||
          pack.description.toLowerCase().includes(search) ||
          pack.industry.toLowerCase().includes(search)
        )
      : mockCurrentValuePacks;
    return HttpResponse.json(packs);
  }),

  http.get('/api/v1/graph/packs/:id', ({ params }) => {
    const pack = mockCurrentValuePacks.find((item) => item.id === params.id || item.pack_id === params.id);
    if (!pack) return HttpResponse.json({ detail: 'Pack not found' }, { status: 404 });
    return HttpResponse.json(pack);
  }),

  http.post('/api/v1/graph/packs/:id/apply', async ({ params }) => {
    const pack = mockCurrentValuePacks.find((item) => item.id === params.id || item.pack_id === params.id);
    if (!pack) return HttpResponse.json({ detail: 'Pack not found' }, { status: 404 });
    await delay(100);
    return HttpResponse.json({
      success: true,
      message: `Applied value pack: ${pack.name}`,
      pack_id: pack.pack_id,
      appliedAt: '2024-03-01T00:00:00Z',
    });
  }),

  // Current L3 framework value-pack routes
  http.get('/api/v1/graph/valuepacks/ontology-map', () => {
    return HttpResponse.json({
      shared_drivers: [
        { id: 'driver-security-risk', name: 'Security Risk Reduction', industries: ['saas-b2b'], count: 1 },
        { id: 'driver-reliability', name: 'Reliability Improvement', industries: ['industrial-iot'], count: 1 },
      ],
      shared_model_types: [
        { id: 'model-roi', name: 'ROI Model', industries: ['saas-b2b', 'industrial-iot'], count: 2 },
      ],
      shared_proof_patterns: [
        { id: 'proof-approved-formula', requirement: 'Approved formula evidence', industries: ['saas-b2b'], count: 1 },
      ],
      cross_reference_matrix: {
        'saas-b2b': { 'industrial-iot': 1 },
        'industrial-iot': { 'saas-b2b': 1 },
      },
    });
  }),

  http.get('/api/v1/graph/valuepacks/composable-templates', () => {
    const templates = mockFrameworkValuePacks.flatMap((pack) => pack.composable_model_templates);
    return HttpResponse.json({
      templates,
      template_usage: templates.reduce<Record<string, string[]>>((acc, template) => {
        acc[template.template_id] = template.applicable_industries;
        return acc;
      }, {}),
    });
  }),

  http.post('/api/v1/graph/valuepacks/compare', async ({ request }) => {
    const body = await request.json() as { industry_ids?: string[] };
    const requested = new Set(body.industry_ids ?? mockFrameworkValuePacks.map((pack) => pack.industry_id));
    const valuepacks = mockFrameworkValuePacks.filter((pack) => requested.has(pack.industry_id));
    return HttpResponse.json({
      valuepacks,
      comparison_matrix: {
        completeness: Object.fromEntries(valuepacks.map((pack) => [pack.industry_id, String(pack.completeness_score ?? 0)])),
        tier: Object.fromEntries(valuepacks.map((pack) => [pack.industry_id, String(pack.tier)])),
      },
      shared_templates: ['template-roi'],
      differentiation_analysis: Object.fromEntries(valuepacks.map((pack) => [pack.industry_id, pack.description])),
    });
  }),

  http.get('/api/v1/graph/valuepacks/:industryId', ({ params }) => {
    const pack = mockFrameworkValuePacks.find((item) => item.industry_id === params.industryId);
    if (!pack) return HttpResponse.json({ detail: 'Value pack framework not found' }, { status: 404 });
    return HttpResponse.json(pack);
  }),

  http.get('/api/v1/graph/valuepacks', ({ request }) => {
    const url = new URL(request.url);
    const tier = url.searchParams.get('tier');
    const search = url.searchParams.get('search')?.toLowerCase() ?? '';
    let items = [...mockFrameworkValuePacks];
    if (tier) items = items.filter((pack) => String(pack.tier) === tier);
    if (search) {
      items = items.filter((pack) =>
        pack.display_name.toLowerCase().includes(search) ||
        pack.description.toLowerCase().includes(search) ||
        pack.industry_id.toLowerCase().includes(search)
      );
    }
    return HttpResponse.json({ items, total: items.length });
  }),

  // Current L3 formula governance routes
  http.get('/api/v1/graph/formulas/approvals/pending', () => {
    return HttpResponse.json([mockCurrentApproval]);
  }),

  http.get('/api/v1/graph/formulas/:id', ({ params }) => {
    const formula = mockCurrentFormulas.find((item) => item.id === params.id || item.formula_id === params.id);
    if (!formula) return HttpResponse.json({ detail: 'Formula not found' }, { status: 404 });
    return HttpResponse.json(formula);
  }),

  http.get('/api/v1/graph/formulas', ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const search = url.searchParams.get('search')?.toLowerCase();
    let formulas = [...mockCurrentFormulas];
    if (status) formulas = formulas.filter((formula) => formula.status === status);
    if (search) formulas = formulas.filter((formula) => formula.name.toLowerCase().includes(search));
    return HttpResponse.json({ formulas, total: formulas.length });
  }),

  http.post('/api/v1/graph/formulas', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      ...mockCurrentFormulas[0],
      id: generateId('formula'),
      formula_id: generateId('formula'),
      name: String(body.name ?? 'New Formula'),
      description: typeof body.description === 'string' ? body.description : undefined,
      expression: String(body.expression ?? 'x + y'),
      variables: Array.isArray(body.variables) ? body.variables : [],
      status: 'draft',
      created_at: '2024-03-01T00:00:00Z',
      updated_at: '2024-03-01T00:00:00Z',
    }, { status: 201 });
  }),

  http.patch('/api/v1/graph/formulas/:id', async ({ params, request }) => {
    const formula = mockCurrentFormulas.find((item) => item.id === params.id || item.formula_id === params.id);
    if (!formula) return HttpResponse.json({ detail: 'Formula not found' }, { status: 404 });
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      ...formula,
      ...body,
      version: '1.0.1',
      updated_at: '2024-03-02T00:00:00Z',
    });
  }),

  http.delete('/api/v1/graph/formulas/:id', ({ params }) => {
    const formula = mockCurrentFormulas.find((item) => item.id === params.id || item.formula_id === params.id);
    if (!formula) return HttpResponse.json({ detail: 'Formula not found' }, { status: 404 });
    return HttpResponse.json({ success: true, formula_id: formula.formula_id });
  }),

  http.post('/api/v1/graph/formulas/:id/approve', ({ params }) => {
    const formula = mockCurrentFormulas.find((item) => item.id === params.id || item.formula_id === params.id);
    if (!formula) return HttpResponse.json({ detail: 'Formula not found' }, { status: 404 });
    return HttpResponse.json({ formula_id: formula.formula_id, status: 'approved' });
  }),

  http.post('/api/v1/graph/formulas/:id/submit', ({ params }) => {
    const formula = mockCurrentFormulas.find((item) => item.id === params.id || item.formula_id === params.id);
    if (!formula && params.id !== 'formula-draft') {
      return HttpResponse.json({ detail: 'Formula not found' }, { status: 404 });
    }
    return HttpResponse.json({ formula_id: String(params.id), status: 'pending_approval' });
  }),

  http.post('/api/v1/graph/formulas/evaluate', () => {
    return HttpResponse.json({
      result: 3,
      unit: 'ratio',
      confidence: 0.95,
      calculation_steps: [{ step: 1, operation: 'Evaluate benefits minus costs divided by costs', result: '3' }],
      formula_used: 'ROI Calculator',
    });
  }),

  // Current L3 variable registry routes
  http.get('/api/v1/graph/variables/stats', () => {
    return HttpResponse.json({ total: 2, validated: 1, pending: 1, failed: 0, manual_sources: 0, avg_usage: 6 });
  }),

  http.get('/api/v1/graph/variables/bindings', () => {
    return HttpResponse.json(mockCurrentBindings);
  }),

  http.get('/api/v1/graph/variables/:id', ({ params }) => {
    const requestedId = String(params.id ?? '');
    const aliases: Record<string, string> = { 'var-1': 'benefits', 'var-2': 'costs' };
    const canonicalId = aliases[requestedId] ?? requestedId;
    const variable = mockCurrentVariables.find(
      (item) => item.id === requestedId || item.variable_id === requestedId || item.id === canonicalId || item.variable_id === canonicalId
    );
    if (!variable) return HttpResponse.json({ detail: 'Variable not found' }, { status: 404 });
    return HttpResponse.json({ ...variable, id: requestedId.startsWith('var-') ? requestedId : variable.id });
  }),

  http.get('/api/v1/graph/variables', ({ request }) => {
    const url = new URL(request.url);
    const query = url.searchParams.get('search')?.toLowerCase() ?? '';
    const type = url.searchParams.get('type');
    const source = url.searchParams.get('source');
    const status = url.searchParams.get('status');
    const variables = mockCurrentVariables.filter((variable) => {
      const matchesQuery = !query ||
        variable.name.toLowerCase().includes(query) ||
        variable.display_name.toLowerCase().includes(query);
      const matchesType = !type || variable.type === type;
      const matchesSource = !source || variable.source === source;
      const matchesStatus = !status || variable.validation_status === status;
      return matchesQuery && matchesType && matchesSource && matchesStatus;
    });
    return HttpResponse.json(variables);
  }),

  http.post('/api/v1/graph/variables/:id/validate', ({ params }) => {
    const requestedId = String(params.id ?? '');
    const aliases: Record<string, string> = { 'var-1': 'benefits', 'var-2': 'costs' };
    const canonicalId = aliases[requestedId] ?? requestedId;
    const variable = mockCurrentVariables.find(
      (item) => item.id === requestedId || item.variable_id === requestedId || item.id === canonicalId || item.variable_id === canonicalId
    );
    if (!variable && requestedId !== 'bad-var') return HttpResponse.json({ detail: 'Variable not found' }, { status: 404 });
    return HttpResponse.json({
      ...(variable ?? {}),
      variable_id: requestedId,
      validation_status: requestedId === 'bad-var' ? 'failed' : 'validated',
      validation_message: requestedId === 'bad-var' ? 'Invalid binding path' : 'Validated by test mock.',
      validated_at: '2024-03-01T12:00:00Z',
    });
  }),

  // Current L3 graph query routes
  http.post('/api/v1/graph/query/graph', async ({ request }) => {
    const body = await request.json() as { query?: string; max_results?: number };
    const entities = mockGraphNodes.slice(0, body.max_results ?? mockGraphNodes.length);
    return HttpResponse.json({
      query: body.query ?? 'cloud migration',
      entities,
      relationships: mockGraphRelationships,
      context_graph: { nodes: entities, relationships: mockGraphRelationships },
      confidence_score: 0.91,
      sources: ['mock-graph-evidence'],
      processing_time_ms: 42,
    });
  }),

  http.get('/api/v1/graph/entity/:id/context', ({ params }) => {
    const center = mockGraphNodes.find((node) => node.id === params.id) ?? mockGraphNodes[0];
    const neighbors = mockGraphNodes.filter((node) => node.id !== center.id);
    return HttpResponse.json({
      entity_id: center.id,
      center,
      neighbors,
      relationships: mockGraphRelationships,
      entity_count: neighbors.length + 1,
      relationship_count: mockGraphRelationships.length,
    });
  }),

  http.post('/api/v1/graph/entity/traverse', async ({ request }) => {
    const body = await request.json() as { entity_id?: string; direction?: string };
    return HttpResponse.json({
      start_entity_id: body.entity_id ?? 'entity-001',
      direction: body.direction ?? 'both',
      paths: [
        {
          nodes: mockGraphNodes,
          relationships: mockGraphRelationships,
          value_score: 0.89,
        },
      ],
      path_count: 1,
    });
  }),

  http.get('/api/v1/graph/subgraph', ({ request }) => {
    const url = new URL(request.url);
    const centerEntityId = url.searchParams.get('center_entity_id') ?? mockGraphNodes[0].id;
    const depth = Number(url.searchParams.get('depth') ?? '2');
    return HttpResponse.json({
      root_entity_id: centerEntityId,
      nodes: mockSubgraphNodes,
      edges: mockSubgraphRelationships,
      relationships: mockSubgraphRelationships,
      depth,
      stats: {
        total_nodes: mockSubgraphNodes.length,
        total_edges: mockSubgraphRelationships.length,
        density: 0.5,
      },
    });
  }),

  http.get('/api/v1/graph/graph/subgraph', ({ request }) => {
    const url = new URL(request.url);
    const centerEntityId = url.searchParams.get('center_entity_id') ?? mockGraphNodes[0].id;
    const depth = Number(url.searchParams.get('depth') ?? '2');
    return HttpResponse.json({
      root_entity_id: centerEntityId,
      nodes: mockSubgraphNodes,
      edges: mockSubgraphRelationships,
      relationships: mockSubgraphRelationships,
      depth,
      stats: {
        total_nodes: mockSubgraphNodes.length,
        total_edges: mockSubgraphRelationships.length,
        density: 0.5,
      },
    });
  }),

  // Current L4 business-case and ground-truth governance routes
  http.get('/api/v1/agents/cases/:caseId', ({ params }) => {
    if (params.caseId === 'missing' || params.caseId === 'not-found') {
      return HttpResponse.json({ detail: 'Business case not found' }, { status: 404 });
    }
    return HttpResponse.json({ ...mockBusinessCase, case_id: String(params.caseId) });
  }),

  http.post('/api/v1/agents/cases/:caseId/export', ({ params }) => {
    return HttpResponse.json({
      download_ready: true,
      document_url: `/exports/${String(params.caseId)}.pdf`,
      truth_references: ['truth-001'],
      remediation_items: [],
      manifest: { case_id: String(params.caseId), generated_at: '2024-03-02T00:00:00Z' },
    });
  }),

  http.get('/api/v1/agents/ground-truth/truths/freshness-summary', () => {
    return HttpResponse.json({ tenant_id: 'tenant-demo', timestamp: '2026-01-02T00:00:00Z', summary: { fresh: 1, stale: 1, expiring_soon: 0, total: mockTruthItems.length }, warning_threshold_days: 14 });
  }),

  http.get('/api/v1/agents/ground-truth/truths/stale', () => {
    return HttpResponse.json({ items: mockTruthItems.filter((truth) => truth.is_stale), total: 1 });
  }),

  http.get('/api/v1/agents/ground-truth/truths/:truthId/audit', ({ params }) => {
    return HttpResponse.json({
      items: [
        {
          id: 'audit-001',
          truth_id: String(params.truthId),
          action: 'validated',
          actor: 'reviewer@example.com',
          timestamp: '2024-03-01T00:00:00Z',
          details: 'Validated against approved source evidence.',
        },
      ],
      total: 1,
    });
  }),

  http.get('/api/v1/agents/ground-truth/truths', () => {
    return HttpResponse.json({ items: mockTruthItems, total: mockTruthItems.length, limit: 100, offset: 0, has_more: false });
  }),

  http.get('/api/v1/agents/ground-truth/maturity-ladder', () => {
    return HttpResponse.json(mockMaturityLadder);
  }),

  // Compatibility aliases for direct governance tests and legacy fetch hooks
  http.get('/api/v1/truths/freshness-summary', () => {
    return HttpResponse.json({ tenant_id: 'tenant-demo', timestamp: '2026-01-02T00:00:00Z', summary: { fresh: 1, stale: 1, expiring_soon: 0, total: mockTruthItems.length }, warning_threshold_days: 14 });
  }),

  http.get('/api/v1/truths/stale', () => {
    return HttpResponse.json({ items: mockTruthItems.filter((truth) => truth.is_stale), total: 1 });
  }),

  http.get('/api/v1/truths/:truthId/audit', ({ params }) => {
    return HttpResponse.json({ items: [{ id: 'audit-001', truth_id: String(params.truthId), action: 'validated', actor: 'reviewer@example.com', timestamp: '2024-03-01T00:00:00Z' }], total: 1 });
  }),

  http.get('/api/v1/truths', () => {
    return HttpResponse.json({ items: mockTruthItems, total: mockTruthItems.length, limit: 100, offset: 0, has_more: false });
  }),

  http.get('/api/v1/maturity-ladder', () => {
    return HttpResponse.json(mockMaturityLadder);
  }),

  // Current L1/L2/L4 smoke routes used by hooks and page tests
  http.get('/api/v1/ingest/jobs', () => {
    return HttpResponse.json({ jobs: [{ id: 'job-001', status: 'completed', source_type: 'document', progress: 100 }], total: 1 });
  }),

  http.get('/api/v1/extract/jobs/:id', ({ params }) => {
    return HttpResponse.json({ id: params.id, status: 'completed', progress: 100, extracted_entities: 5 });
  }),

  http.get('/api/v1/agents/workflows/:id/result', ({ params }) => {
    const workflowId = String(params.id);

    return HttpResponse.json({
      workflow_id: workflowId,
      workflow_type: 'business_case',
      status: 'completed',
      output: {
        title: 'Test Business Case',
        company_name: 'Test Company',
        executive_summary: 'Comprehensive analysis for the requested business case',
        total_investment: 300000,
        total_benefit: 1200000,
        net_present_value: 900000,
        roi_percentage: 300,
        payback_period_months: 18,
        recommendations: [
          'Proceed with phased implementation',
          'Establish baseline KPIs before rollout',
        ],
      },
      steps: [
        { id: 'step-1', agent_name: 'Value Architect', status: 'completed' },
        { id: 'step-2', agent_name: 'Business Case Analyst', status: 'completed' },
      ],
      completed_at: '2024-01-15T10:00:00Z',
    });
  }),

  http.get('/api/v1/agents/workflows', () => {
    return HttpResponse.json({
      items: [
        {
          workflow_instance_id: 'workflow-bc-1',
          workflow_type: 'business_case',
          status: 'completed',
          current_state: null,
          current_node: null,
          progress_percentage: 100,
          started_at: '2024-01-15T09:00:00Z',
          completed_at: '2024-01-15T10:00:00Z',
          error_count: 0,
          has_output: true,
          results: {
            title: 'Test Business Case',
            company_name: 'Test Company',
            total_investment: 300000,
            total_benefit: 1200000,
            roi_percentage: 300,
          },
          tenant_id: 'tenant-001',
          user_id: 'user-001',
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
      has_more: false,
    });
  }),

  http.get('/api/v1/agents/workflows/active', () => {
    const items = [
      { id: 'wf-1', name: 'Market Analysis Workflow', status: 'running', progress: 65 },
      { id: 'wf-2', name: 'Extraction Pipeline', status: 'pending', progress: 15 },
      { id: 'wf-3', name: 'Completed Workflow', status: 'completed', progress: 100 },
    ];
    return HttpResponse.json({ items, total: items.length, limit: 50, offset: 0, has_more: false });
  }),

  http.post('/api/v1/agents/workflows', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      workflow_instance_id: 'wf-created',
      status: 'pending',
      estimated_duration_seconds: 300,
    }, { status: 201 });
  }),

  http.delete('/api/v1/agents/workflows/:id', ({ params }) => {
    return HttpResponse.json({ success: true, workflow_id: String(params.id), status: 'cancelled' });
  }),

  http.get('/api/v1/agents/workflows/:id', ({ params }) => {
    return HttpResponse.json({
      workflow_instance_id: String(params.id),
      workflow_type: 'business_case',
      status: 'running',
      current_state: 'data_collection',
      current_node: 'collect_metrics',
      progress_percentage: 80,
      started_at: '2024-01-15T10:00:00Z',
      completed_at: null,
      error_count: 0,
      has_output: false,
      results: null,
      tenant_id: 'tenant-001',
      user_id: 'user-001',
      priority: 5,
      scheduler_status: 'scheduled',
      progress: {
        step_id: 'collect_metrics',
        status: 'running',
        percent: 80,
        message: 'Collecting metrics',
        started_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:05:00Z',
        completed_at: null,
        actionable_next_state: {
          can_retry: false,
          can_resume: false,
          can_cancel: true,
          requires_user_action: false,
          next_action: 'wait',
        },
      },
    });
  }),

  // Health check
  http.get('/api/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
    });
  }),

  // Billing - Entitlements
  http.get('/api/billing/entitlements', () => {
    return HttpResponse.json([
      { featureId: 'messages', hasAccess: true, usageLimit: 100, currentUsage: 42 },
      { featureId: 'pro_models', hasAccess: true },
      { featureId: 'advanced_mode', hasAccess: true },
      { featureId: 'api_access', hasAccess: false },
    ]);
  }),

  // Billing - Subscription
  http.get('/api/billing/subscription', () => {
    return HttpResponse.json({
      id: 'sub-test-001',
      planId: 'pro',
      status: 'active',
      currentPeriodStart: new Date().toISOString(),
      currentPeriodEnd: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    });
  }),

  // Billing - Report usage
  http.post('/api/billing/report-usage', async () => {
    await delay(100);
    return HttpResponse.json({ success: true });
  }),

  // Entities - List
  http.get('/api/entities', ({ request }) => {
    const url = new URL(request.url);
    const type = url.searchParams.get('type');
    const query = url.searchParams.get('q')?.toLowerCase();
    
    let entities = [...mockEntities];
    
    if (type) {
      entities = entities.filter(e => e.type === type);
    }
    
    if (query) {
      entities = entities.filter(e => 
        e.name.toLowerCase().includes(query) ||
        e.type.toLowerCase().includes(query)
      );
    }
    
    return HttpResponse.json({
      items: entities,
      total: entities.length,
      page: 1,
      pageSize: 20,
    });
  }),

  // Entities - Get single
  http.get('/api/entities/:id', ({ params }) => {
    const entity = mockEntities.find(e => e.id === params.id);
    if (!entity) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(entity);
  }),

  // Entities - Create
  http.post('/api/entities', async ({ request }) => {
    const body = await request.json() as { name: string; type: string };
    const newEntity = {
      id: generateId('entity'),
      name: body.name,
      type: body.type,
      confidence: 0.8,
      created_at: new Date().toISOString(),
    };
    return HttpResponse.json(newEntity, { status: 201 });
  }),

  // Entities - Update
  http.patch('/api/entities/:id', async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>;
    const entity = mockEntities.find(e => e.id === params.id);
    if (!entity) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({ ...entity, ...body, updated_at: new Date().toISOString() });
  }),

  // Entities - Delete
  http.delete('/api/entities/:id', ({ params }) => {
    const entity = mockEntities.find(e => e.id === params.id);
    if (!entity) {
      return new HttpResponse(null, { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  }),

  // Value Packs - List (matches apiClient.get('l3', '/packs'))
  http.get('/packs', () => {
    return HttpResponse.json(mockValuePacks);
  }),

  // Value Packs - Get single
  http.get('/packs/:id', ({ params }) => {
    const pack = mockValuePacks.find(p => p.id === params.id);
    if (!pack) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(pack);
  }),

  // Value Packs - Apply
  http.post('/packs/:id/apply', async ({ params }) => {
    await delay(500);
    const pack = mockValuePacks.find(p => p.id === params.id);
    if (!pack) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json({
      success: true,
      message: `Applied value pack: ${pack.name}`,
      appliedAt: new Date().toISOString(),
    });
  }),

  // Formulas - List
  http.get('/api/formulas', () => {
    return HttpResponse.json({
      items: [
        { id: 'formula-001', name: 'ROI Calculator', status: 'approved', version: 3 },
        { id: 'formula-002', name: 'TCO Analysis', status: 'draft', version: 1 },
      ],
      total: 2,
    });
  }),

  // Formulas - Create
  http.post('/api/formulas', async ({ request }) => {
    const body = await request.json() as { name: string };
    await delay(200);
    return HttpResponse.json({
      id: generateId('formula'),
      name: body.name,
      status: 'draft',
      version: 1,
      created_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // Search - Hybrid
  http.post('/api/search/hybrid', async ({ request }) => {
    const body = await request.json() as { query: string; limit?: number };
    await delay(300);
    
    return HttpResponse.json({
      results: mockEntities
        .filter(e => e.name.toLowerCase().includes(body.query.toLowerCase()))
        .slice(0, body.limit || 10),
      total: mockEntities.length,
      query: body.query,
    });
  }),

  // Graph - Full graph
  http.get('/api/graph/full', () => {
    return HttpResponse.json({
      nodes: mockEntities.map(e => ({
        id: e.id,
        label: e.name,
        type: e.type,
        confidence: e.confidence,
      })),
      edges: [
        { source: 'entity-001', target: 'entity-002', type: 'enables' },
        { source: 'entity-002', target: 'entity-003', type: 'requires' },
      ],
    });
  }),

  // Ingestion - Jobs
  http.get('/api/ingestion/jobs', () => {
    return HttpResponse.json({
      items: [
        { id: 'job-001', status: 'completed', source_type: 'document', entities_extracted: 5 },
        { id: 'job-002', status: 'processing', source_type: 'url', progress: 45 },
      ],
      total: 2,
    });
  }),

  // Ingestion - Create job
  http.post('/api/ingestion/jobs', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    await delay(100);
    return HttpResponse.json({
      id: generateId('job'),
      status: 'pending',
      ...body,
      created_at: new Date().toISOString(),
    }, { status: 202 });
  }),

  // Workflows - List
  http.get('/api/workflows', () => {
    return HttpResponse.json({
      items: [
        { id: 'wf-001', name: 'Extraction Pipeline', status: 'active', last_run: new Date().toISOString() },
        { id: 'wf-002', name: 'Validation Workflow', status: 'paused' },
      ],
    });
  }),

  // Agent - Query
  http.post('/api/agent/query', async ({ request }) => {
    const body = await request.json() as { query: string };
    await delay(2000); // Simulate LLM processing
    
    return HttpResponse.json({
      response: `Based on your query "${body.query}", I found relevant information about cloud capabilities.`,
      referenced_entities: mockEntities.slice(0, 2),
      confidence: 0.87,
    });
  }),

  // Evidence - Traces
  http.get('/api/evidence/traces', () => {
    return HttpResponse.json({
      items: [
        {
          id: 'trace-001',
          timestamp: new Date().toISOString(),
          action: 'entity_created',
          actor: 'user-001',
          resource_id: 'entity-001',
        },
      ],
      total: 1,
    });
  }),

  // Business Cases
  http.get('/api/business-cases', () => {
    return HttpResponse.json({
      items: [
        {
          id: 'case-001',
          title: 'Test Business Case',
          status: 'draft',
          roi_percent: 150,
          payback_months: 18,
        },
      ],
    });
  }),

  // Accounts
  http.get('/api/accounts', () => {
    return HttpResponse.json({
      items: [
        { id: 'acc-001', name: 'Acme Corporation', industry: 'Technology' },
        { id: 'acc-002', name: 'Global Industries', industry: 'Manufacturing' },
      ],
    });
  }),

  // ── Layer 1 — Scraping Targets ────────────────────────────────────────────
  // Response shapes match ApiTargetListResponse / ScrapingTargetDetail /
  // TargetStatsResponse as defined in useTargets.ts.

  http.get('/api/v1/ingest/targets', () => {
    return HttpResponse.json({
      data: [
        {
          id: 'target-1',
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
        },
      ],
      pagination: { page: 1, limit: 25, total: 1, total_pages: 1 },
    });
  }),

  http.get('/api/v1/ingest/targets/stats', () => {
    return HttpResponse.json({
      total: 5,
      connected: 3,
      disconnected: 1,
      error: 1,
      total_records: 500,
      average_health_score: 85,
    });
  }),

  http.get('/api/v1/ingest/targets/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      name: 'Acme Corp',
      url: 'https://acme.com',
      target_type: 'SPIDER',
      source_category: 'CRM',
      status: 'ACTIVE',
      tags: ['prospect'],
      tenant_id: 'tenant-1',
      description: 'Acme Corp target',
      url_pattern: null,
      crawl_path: 'browser',
      extraction_config: { method: 'llm' },
      browser_config: {},
      schedule: { enabled: false },
      rate_limit: { requests_per_second: 1 },
      compliance: { respect_robots_txt: true },
      success_count: 10,
      error_count: 1,
      average_execution_time_ms: 1200,
      last_success_at: '2024-01-15T10:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-15T10:00:00Z',
    });
  }),

  http.get('/api/v1/ingest/jobs', () => {
    return HttpResponse.json({
      data: [],
      pagination: { page: 1, limit: 10, total: 0, total_pages: 0 },
    });
  }),

  http.post('/api/v1/ingest/targets', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      id: 'new-target',
      name: body.name ?? 'New Target',
      url: body.url ?? 'https://example.com',
      target_type: body.target_type ?? 'SPIDER',
      source_category: body.source_category ?? 'CRM',
      status: 'ACTIVE',
      tags: [],
      tenant_id: 'tenant-1',
      description: null,
      url_pattern: null,
      crawl_path: 'browser',
      extraction_config: {},
      browser_config: {},
      schedule: null,
      rate_limit: {},
      compliance: {},
      success_count: 0,
      error_count: 0,
      average_execution_time_ms: 0,
      last_success_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  http.put('/api/v1/ingest/targets/:id', async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      id: params.id,
      name: body.name ?? 'Updated Target',
      url: body.url ?? 'https://example.com',
      target_type: body.target_type ?? 'SPIDER',
      source_category: 'CRM',
      status: 'ACTIVE',
      tags: [],
      tenant_id: 'tenant-1',
      description: null,
      url_pattern: null,
      crawl_path: 'browser',
      extraction_config: {},
      browser_config: {},
      schedule: null,
      rate_limit: {},
      compliance: {},
      success_count: 10,
      error_count: 1,
      average_execution_time_ms: 1200,
      last_success_at: '2024-01-15T10:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: new Date().toISOString(),
    });
  }),

  http.patch('/api/v1/ingest/targets/:id/status', async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>;
    return HttpResponse.json({
      id: params.id,
      name: 'Acme Corp',
      url: 'https://acme.com',
      target_type: 'SPIDER',
      source_category: 'CRM',
      status: body.status ?? 'ACTIVE',
      tags: ['prospect'],
      tenant_id: 'tenant-1',
      description: null,
      url_pattern: null,
      crawl_path: 'browser',
      extraction_config: {},
      browser_config: {},
      schedule: null,
      rate_limit: {},
      compliance: {},
      success_count: 10,
      error_count: 1,
      average_execution_time_ms: 1200,
      last_success_at: '2024-01-15T10:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: new Date().toISOString(),
    });
  }),

  http.post('/api/v1/ingest/targets/batch', async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    const ids = (body.target_ids as string[]) ?? [];
    return HttpResponse.json({
      succeeded: ids,
      failed: [],
      operation: body.operation,
    });
  }),

  http.post('/api/v1/ingest/targets/:id/execute', ({ params }) => {
    return HttpResponse.json({
      job_id: `job-${String(params.id)}`,
      target_id: params.id,
      status: 'QUEUED',
      created_at: new Date().toISOString(),
    }, { status: 202 });
  }),

  http.post('/api/v1/ingest/targets/:id/validate', ({ params }) => {
    return HttpResponse.json({
      target_id: params.id,
      valid: true,
      errors: [],
      warnings: [],
    });
  }),

  http.delete('/api/v1/ingest/targets/:id', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // ── Layer 4 — Harness runs (MSW fallback for tests that don't mock apiClient) ─

  http.get('/api/v1/agents/harness/runs', () => {
    return HttpResponse.json({
      items: [],
      total: 0,
    });
  }),

  // ── Layer 3 — Value Signals ───────────────────────────────────────────────

  http.get('/api/v1/signals', () => {
    return HttpResponse.json({
      items: [],
      total: 0,
    });
  }),

  // ── Global Search ───────────────────────────────────────────────────────────

  http.get('/api/v1/search', ({ request }) => {
    const url = new URL(request.url);
    const query = url.searchParams.get('q');
    
    if (!query) {
      return HttpResponse.json({
        query: '',
        scope: 'tenant',
        tenant_id: 'acme',
        results: {},
        total_by_type: {},
        processing_time_ms: 0,
      });
    }
    
    // Import mock search data
    const { createMockSearchResponse } = require('./searchMocks');
    const response = createMockSearchResponse(query);
    
    return HttpResponse.json(response);
  }),
];
