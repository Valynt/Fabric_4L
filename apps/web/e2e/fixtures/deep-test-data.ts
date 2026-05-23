/**
 * Rich mock data factories for deep validation tests.
 *
 * These factories provide complete, realistic data payloads for testing
 * multi-step workflows with state transitions, form interactions, and
 * business-logic validation.
 */
import type { MockEndpoint } from '../helpers/api-harness';

// ── Identifiers ──────────────────────────────────────────────────────────────

export const DEEP_ACCOUNT_ID = 'acct-deep-meridian-001';
export const DEEP_CASE_APPROVED_ID = 'case-deep-approved-001';
export const DEEP_CASE_DRAFT_ID = 'case-deep-draft-001';
export const DEEP_TENANT_ID = 'tenant-e2e-001';
export const DEEP_FOREIGN_TENANT_ID = 'tenant-foreign-999';
export const DEEP_FOREIGN_ACCOUNT_ID = 'acct-foreign-globex-999';

// ── Full Account Payloads ────────────────────────────────────────────────────

export function createFullAccountPayload(overrides?: Record<string, unknown>) {
  return {
    id: DEEP_ACCOUNT_ID,
    name: 'Meridian Health Group',
    domain: 'meridian.example',
    website: 'https://meridian.example',
    industry: 'Healthcare',
    company_size: 'enterprise',
    annual_revenue: 85000000,
    employee_count: 1200,
    tier: 'enterprise',
    stage: 'prospect',
    owner: 'Avery Stone',
    readiness: 78,
    value_pack: 'Healthcare Operations',
    created_at: '2026-04-01T12:00:00Z',
    updated_at: '2026-05-01T12:00:00Z',
    audit_events: [
      { event: 'account_created', actor: 'Avery Stone', timestamp: '2026-04-01T12:00:00Z' },
      { event: 'value_pack_assigned', actor: 'Avery Stone', timestamp: '2026-04-02T09:00:00Z' },
      { event: 'ingestion_completed', actor: 'system', timestamp: '2026-04-03T14:00:00Z' },
    ],
    ...overrides,
  };
}

// ── Business Case Payloads ───────────────────────────────────────────────────

export function createApprovedBusinessCase(overrides?: Record<string, unknown>) {
  return {
    case_id: DEEP_CASE_APPROVED_ID,
    id: DEEP_CASE_APPROVED_ID,
    title: 'Meridian Automation Business Case',
    status: 'approved',
    document_url: '/exports/meridian-business-case.pdf',
    roi_ratio: 2.87,
    payback_months: 9,
    total_value: 2100000,
    summary: 'Approved case with verified evidence lineage and three-scenario ROI.',
    executive_summary: 'Approved case with verified evidence lineage and three-scenario ROI.',
    confidence_score: 0.91,
    implementation_cost: 180000,
    page_count: 12,
    file_size_bytes: 245760,
    recommendations: [
      'Proceed with Phase 1 automation rollout.',
      'Assign metric owners for realization tracking.',
    ],
    truth_references: [
      { id: 'ref-001', claim: 'Manual reconciliation costs $420K annually', source: 'Discovery call transcript', evidence_id: 'ev-001', type: 'evidence' },
      { id: 'ref-002', claim: 'Automation reduces cycle time by 18-27%', source: 'Industry Benchmark DB', benchmark_id: 'bench-001', type: 'benchmark' },
      { id: 'ref-003', claim: 'Finance team validates baseline hours', source: 'Internal assumption', type: 'assumption', approved: true },
    ],
    case_metadata: {
      account_id: DEEP_ACCOUNT_ID,
      account_route_id: DEEP_ACCOUNT_ID,
      external_account_id: DEEP_ACCOUNT_ID,
      crm_ready: true,
      realization_ready: true,
    },
    approval_history: [
      { action: 'submitted', actor: 'Avery Stone', timestamp: '2026-04-28T10:00:00Z' },
      { action: 'approved', actor: 'Value Engineering Lead', timestamp: '2026-04-29T15:30:00Z' },
    ],
    created_at: '2026-04-28T10:00:00Z',
    ...overrides,
  };
}

export function createDraftBusinessCase(overrides?: Record<string, unknown>) {
  return {
    case_id: DEEP_CASE_DRAFT_ID,
    id: DEEP_CASE_DRAFT_ID,
    title: 'Draft Meridian Business Case',
    status: 'draft',
    document_url: null,
    roi_ratio: 1.1,
    payback_months: 18,
    total_value: 450000,
    summary: 'Draft case pending evidence approval and reviewer sign-off.',
    executive_summary: 'Draft case pending evidence approval and reviewer sign-off.',
    confidence_score: 0.45,
    implementation_cost: 180000,
    page_count: 0,
    file_size_bytes: 0,
    recommendations: ['Resolve missing evidence before export.'],
    truth_references: [],
    case_metadata: {
      account_id: DEEP_ACCOUNT_ID,
      account_route_id: DEEP_ACCOUNT_ID,
    },
    approval_history: [],
    created_at: '2026-05-01T10:00:00Z',
    ...overrides,
  };
}

// ── Signal Set ───────────────────────────────────────────────────────────────

export function createSignalSet() {
  return {
    status: 'ready',
    generated_at: '2026-05-01T12:00:00Z',
    content: {
      signals: [
        { id: 'sig-001', name: 'Manual reconciliation burden', confidence: 0.92, confidence_display: '92%', source: 'Discovery call transcript', source_type: 'customer_data', status: 'approved' },
        { id: 'sig-002', name: 'Supply chain visibility gaps', confidence: 0.87, confidence_display: '87%', source: 'Q3 earnings call', source_type: 'earnings_call', status: 'pending_review' },
        { id: 'sig-003', name: 'Regulatory compliance overhead', confidence: 0.65, confidence_display: '65%', source: 'Industry report', source_type: 'industry_report', status: 'pending_review' },
        { id: 'sig-004', name: 'Customer churn from manual processes', confidence: 0.44, confidence_display: '44%', source: 'Internal estimate', source_type: 'estimate', status: 'low_confidence' },
      ],
    },
  };
}

// ── Value Driver Tree ────────────────────────────────────────────────────────

export function createValueDriverTree() {
  return {
    status: 'ready',
    generated_at: '2026-05-01T12:00:00Z',
    content: {
      drivers: [
        {
          id: 'driver-001', name: 'Operational Efficiency', weight: 0.4,
          children: [
            { id: 'driver-001a', name: 'Reconciliation Automation', weight: 0.6, evidence_ids: ['ev-001'] },
            { id: 'driver-001b', name: 'Cycle Time Reduction', weight: 0.4, evidence_ids: ['ev-002'] },
          ],
        },
        {
          id: 'driver-002', name: 'Revenue Growth', weight: 0.35,
          children: [
            { id: 'driver-002a', name: 'Faster Time to Market', weight: 1.0, evidence_ids: [] },
          ],
        },
        {
          id: 'driver-003', name: 'Risk Reduction', weight: 0.25,
          children: [
            { id: 'driver-003a', name: 'Compliance Automation', weight: 1.0, evidence_ids: ['ev-003'] },
          ],
        },
      ],
    },
  };
}

// ── Evidence Set ─────────────────────────────────────────────────────────────

export function createEvidenceSet() {
  return {
    status: 'ready',
    generated_at: '2026-05-01T12:00:00Z',
    content: {
      evidence: [
        { id: 'ev-001', title: 'Manual reconciliation baseline', source: 'Discovery Notes', confidence: 0.91, type: 'customer_data' },
        { id: 'ev-002', title: 'Cycle time benchmark data', source: 'Industry Benchmark DB', confidence: 0.85, type: 'benchmark' },
        { id: 'ev-003', title: 'Compliance audit findings', source: 'Internal Audit Report', confidence: 0.78, type: 'customer_data' },
      ],
    },
  };
}

// ── ROI Scenarios ────────────────────────────────────────────────────────────

export function createROIScenarios() {
  return {
    conservative: { roi_ratio: 1.8, total_value: 1200000, payback_months: 14, annual_savings: 340000, currency: 'USD' },
    expected: { roi_ratio: 2.87, total_value: 2100000, payback_months: 9, annual_savings: 700000, currency: 'USD' },
    optimistic: { roi_ratio: 4.2, total_value: 3400000, payback_months: 6, annual_savings: 1130000, currency: 'USD' },
  };
}

export function createROICalculatorMock() {
  const scenarios = createROIScenarios();
  return {
    account_id: DEEP_ACCOUNT_ID,
    scenarios,
    active_scenario: 'expected',
    formula_inputs: [
      { id: 'input-hours', name: 'Manual Hours per Week', value: 120, unit: 'hours', required: true },
      { id: 'input-rate', name: 'Fully Loaded Hourly Rate', value: 85, unit: 'USD/hour', required: true },
      { id: 'input-reduction', name: 'Automation Reduction %', value: 0.65, unit: '%', required: true },
      { id: 'input-license', name: 'Annual License Cost', value: 180000, unit: 'USD', required: false },
    ],
    version: 3,
    last_updated: '2026-05-01T12:00:00Z',
  };
}

// ── Approval Workflow ────────────────────────────────────────────────────────

export function createApprovalWorkflow(state: 'pending_review' | 'changes_requested' | 'approved' | 'rejected' = 'pending_review') {
  return {
    id: 'approval-deep-001',
    case_id: DEEP_CASE_DRAFT_ID,
    state,
    reviewer: 'Value Engineering Lead',
    submitted_by: 'Avery Stone',
    submitted_at: '2026-04-28T10:00:00Z',
    comments: state === 'changes_requested'
      ? [{ author: 'Value Engineering Lead', text: 'Missing evidence for claim #2. Please attach benchmark data.', timestamp: '2026-04-28T14:00:00Z' }]
      : [],
    resolved_at: state === 'approved' ? '2026-04-29T15:30:00Z' : null,
  };
}

// ── Ingestion Jobs ───────────────────────────────────────────────────────────

export function createIngestionJobs() {
  return [
    {
      id: 'job-complete-001',
      status: 'completed',
      progress_percent_complete: 100,
      progress_processed_pages: 42,
      created_at: '2026-05-01T10:00:00Z',
      updated_at: '2026-05-01T10:05:00Z',
      configuration: { url: 'https://meridian.example' },
    },
    {
      id: 'job-failed-001',
      status: 'failed',
      progress_percent_complete: 33,
      progress_processed_pages: 3,
      created_at: '2026-05-01T09:00:00Z',
      updated_at: '2026-05-01T09:02:00Z',
      configuration: { url: 'https://duplicate.example' },
    },
    {
      id: 'job-running-001',
      status: 'processing',
      progress_percent_complete: 67,
      progress_processed_pages: 13,
      created_at: '2026-05-01T08:00:00Z',
      updated_at: '2026-05-01T08:30:00Z',
      configuration: { url: 'https://newclient.example' },
    },
  ];
}

// ── Agent Responses ──────────────────────────────────────────────────────────

export function createGroundedAgentResponse() {
  return {
    content: 'Based on the Discovery call transcript (ev-001), manual reconciliation costs approximately $420K annually. **Assumption:** Finance team confirms baseline hours of 120/week. **Inference:** At 65% automation rate, projected annual savings are $273K. Note: This claim requires customer validation of the hourly rate assumption.',
    metadata: {
      citations: ['ev-001: Discovery call transcript', 'bench-001: Industry benchmark'],
      grounding: 'evidence_backed',
      assumptions: ['Finance team validates baseline hours of 120/week', 'Hourly rate of $85 is fully loaded'],
      confidence: 0.87,
      trace_id: 'trace-deep-001',
      audit_event_id: 'audit-deep-001',
    },
  };
}

export function createRefusalAgentResponse() {
  return {
    content: '**I cannot support this claim.** The requested ROI figure of 500% has no supporting evidence in the current evidence set. Available evidence supports a conservative range of 1.8x–4.2x ROI. Please provide additional customer data or benchmark references before making this claim.',
    metadata: {
      grounding: 'refusal',
      reason: 'unsupported_claim',
      trace_id: 'trace-deep-002',
      audit_event_id: 'audit-deep-002',
    },
  };
}

export function createPromptInjectionAttempt() {
  return {
    content: 'The uploaded document contained embedded instructions that were identified and ignored. Document processing continued normally, extracting 3 valid entities and 0 injected directives.',
    metadata: {
      grounding: 'sanitized',
      injection_detected: true,
      trace_id: 'trace-deep-003',
    },
  };
}

// ── Benchmark Data ───────────────────────────────────────────────────────────

export function createBenchmarkDatasets() {
  return [
    {
      id: 'bench-001', benchmark_id: 'bench-manual-hours-saved', name: 'Manual Hours Saved',
      industry: 'Healthcare', vertical: 'Operations', value_range: '18-27%',
      confidence: 'High', source: 'Validated customer outcomes', year: 2026,
      status: 'active', tags: [], last_verified: '2026-05-01T12:00:00Z', usage_count: 14,
      description: 'Active benchmark with high confidence.',
    },
    {
      id: 'bench-002', benchmark_id: 'bench-cycle-time', name: 'Cycle Time Reduction',
      industry: 'Healthcare', vertical: 'Operations', value_range: '12-20%',
      confidence: 'Medium', source: 'Peer-reviewed study', year: 2024,
      status: 'active', tags: ['stale-warning'], last_verified: '2024-06-15T12:00:00Z', usage_count: 7,
      description: 'Stale benchmark — last verified over 12 months ago.',
    },
  ];
}

// ── Ground Truth ─────────────────────────────────────────────────────────────

export function createGroundTruthSet() {
  return {
    truths: [
      { id: 'truth-001', truth_id: 'truth-001', claim: 'CFO validates baseline reconciliation hours at 120/week.', status: 'validated', maturity: 'approved', confidence: 0.91, stale: false, freshness: 'current', source: 'CFO discovery note' },
      { id: 'truth-002', truth_id: 'truth-002', claim: 'Hourly rate of $85 is fully loaded including benefits.', status: 'pending', maturity: 'unverified', confidence: 0.6, stale: false, freshness: 'current', source: 'HR estimate' },
      { id: 'truth-003', truth_id: 'truth-003', claim: 'Competitor pricing has decreased 15% YoY.', status: 'rejected', maturity: 'disputed', confidence: 0.3, stale: true, freshness: 'stale', source: 'Market report 2024' },
    ],
    total: 3,
  };
}

// ── CRM Integration ──────────────────────────────────────────────────────────

export function createCRMIntegration(status: 'idle' | 'syncing' | 'error' = 'idle') {
  return {
    integrations: [{
      id: 'int-sf-deep-001', tenant_id: DEEP_TENANT_ID, provider: 'salesforce',
      enabled: true, instance_url: 'https://meridian.my.salesforce.com',
      sync_interval_minutes: 60, sync_batch_size: 250,
      last_sync_at: '2026-05-01T12:00:00Z',
      last_successful_sync_at: status === 'error' ? null : '2026-05-01T12:00:00Z',
      records_synced: status === 'error' ? 0 : 128,
      records_updated: status === 'error' ? 0 : 9,
      records_failed: status === 'error' ? 7 : 0,
      status,
      last_error_message: status === 'error' ? 'Authentication token expired. Re-authorize.' : null,
      has_refresh_token: true,
      created_at: '2026-04-01T12:00:00Z',
      updated_at: '2026-05-01T12:00:00Z',
    }],
  };
}

// ── Stakeholder Data ─────────────────────────────────────────────────────────

export function createStakeholderSet() {
  return {
    status: 'ready',
    generated_at: '2026-05-01T12:00:00Z',
    content: {
      stakeholders: [
        { id: 'sh-001', name: 'Dr. Sarah Chen', title: 'Chief Financial Officer', department: 'Finance', influence: 'high', buying_role: 'economic_buyer', pains: ['sig-001'], initiatives: ['initiative-cost-reduction'], value_drivers: ['driver-001'], evidence_sources: ['ev-001'] },
        { id: 'sh-002', name: 'Marcus Rivera', title: 'VP of Operations', department: 'Operations', influence: 'medium', buying_role: 'technical_buyer', pains: ['sig-002'], initiatives: ['initiative-automation'], value_drivers: ['driver-001a'], evidence_sources: ['ev-002'] },
        { id: 'sh-003', name: 'Priya Kapoor', title: 'Director of IT', department: 'Information Technology', influence: 'medium', buying_role: 'champion', pains: ['sig-003'], initiatives: ['initiative-compliance'], value_drivers: ['driver-003a'], evidence_sources: ['ev-003'] },
        { id: 'sh-004', name: 'Tom Walsh', title: 'Head of Procurement', department: 'Finance', influence: 'low', buying_role: 'blocker', pains: [], initiatives: [], value_drivers: [], evidence_sources: [] },
      ],
    },
  };
}

export function createStakeholderDetail(id = 'sh-001') {
  const set = createStakeholderSet();
  return set.content.stakeholders.find((s) => s.id === id) ?? set.content.stakeholders[0];
}

// ── Value Pack Data ──────────────────────────────────────────────────────────

export function createValuePackList() {
  return [
    {
      id: 'pack-healthcare-001', name: 'Healthcare Operations', version: '3.1.0', status: 'active',
      industries: ['Healthcare'], description: 'Formulas, benchmarks, and personas for healthcare operational efficiency.',
      formulas: ['formula-reconciliation', 'formula-claim-processing'],
      benchmarks: ['bench-001', 'bench-002'],
      personas: ['persona-cfo', 'persona-coo'],
      ontology_terms: ['manual-reconciliation', 'claim-cycle-time', 'compliance-overhead'],
      evidence_requirements: ['customer_data', 'audit_report'],
      published_by: 'Platform Admin',
      published_at: '2026-03-01T12:00:00Z',
    },
    {
      id: 'pack-saas-001', name: 'SaaS Growth', version: '2.4.0', status: 'active',
      industries: ['Technology', 'SaaS'], description: 'ARR growth, churn reduction, and expansion revenue drivers.',
      formulas: ['formula-arr-uplift', 'formula-churn-reduction'],
      benchmarks: ['bench-saas-001'],
      personas: ['persona-cro', 'persona-cmo'],
      ontology_terms: ['annual-recurring-revenue', 'net-revenue-retention', 'expansion-rate'],
      evidence_requirements: ['customer_data', 'crm_data'],
      published_by: 'Platform Admin',
      published_at: '2026-01-15T12:00:00Z',
    },
    {
      id: 'pack-deprecated-001', name: 'Legacy ERP', version: '1.0.0', status: 'deprecated',
      industries: ['Manufacturing'], description: 'Deprecated ERP value drivers — use Manufacturing Operations v2 instead.',
      formulas: [],
      benchmarks: [],
      personas: [],
      ontology_terms: [],
      evidence_requirements: [],
      published_by: 'Platform Admin',
      published_at: '2024-01-01T12:00:00Z',
      deprecated_at: '2025-06-01T12:00:00Z',
      deprecation_note: 'Superseded by Manufacturing Operations v2.0.0.',
    },
  ];
}

// ── Narrative Versions Data ──────────────────────────────────────────────────

export function createNarrativeVersions() {
  return {
    current_version: 3,
    versions: [
      { version: 3, created_at: '2026-05-01T14:00:00Z', created_by: 'Avery Stone', summary: 'Added CFO-specific ROI framing and tightened cycle time claims.' },
      { version: 2, created_at: '2026-04-30T10:00:00Z', created_by: 'Avery Stone', summary: 'Removed unsupported 500% ROI claim. Evidence citations added to all value claims.' },
      { version: 1, created_at: '2026-04-28T09:00:00Z', created_by: 'system', summary: 'Initial AI-generated narrative.' },
    ],
    narrative_types: ['executive_summary', 'discovery_recap', 'executive_email', 'mutual_action_plan', 'renewal_narrative', 'expansion_narrative', 'proposal_section'],
  };
}

export function createNarrativeContent(type = 'executive_email') {
  const contents: Record<string, string> = {
    executive_email: 'Subject: Meridian Health Group — Projected $700K in Annual Operational Savings\n\nDear Dr. Chen,\n\nBased on our discovery conversations and your Q3 reconciliation data, we have modeled three outcome scenarios...',
    executive_summary: 'Meridian Health Group can recapture $700K in annual operational costs by automating its manual reconciliation workflow. This case is grounded in customer-validated baseline hours and industry benchmark data...',
    discovery_recap: 'Key findings from our April 28 discovery session with the Meridian Finance and Operations teams...',
    mutual_action_plan: 'Shared success milestones and owner assignments for the Meridian automation initiative...',
    renewal_narrative: 'In Year 1, Meridian achieved $640K in realized savings against a projected $700K target. The variance is attributable to...',
    expansion_narrative: 'With reconciliation automation stabilized, Meridian is positioned to extend the platform to its four regional billing centers...',
    proposal_section: 'Section 3: Financial Impact Analysis — Conservative, Expected, and Optimistic outcomes based on validated assumptions...',
  };
  return {
    status: 'ready',
    generated_at: '2026-05-01T12:00:00Z',
    content: {
      type,
      text: contents[type] ?? 'Generated narrative content.',
      grounding_score: 0.91,
      unsupported_claims: [],
      citations: ['ev-001: Discovery call transcript', 'bench-001: Industry benchmark'],
    },
  };
}

// ── Collaboration Data ────────────────────────────────────────────────────────

export function createCollaborationData() {
  return {
    team_members: [
      { id: 'user-001', name: 'Avery Stone', email: 'avery@valuefabric.test', role: 'owner', access: 'full' },
      { id: 'user-002', name: 'Jordan Lee', email: 'jordan@valuefabric.test', role: 'reviewer', access: 'read_write' },
      { id: 'user-003', name: 'Sam Taylor', email: 'sam@valuefabric.test', role: 'viewer', access: 'read_only' },
    ],
    comments: [
      { id: 'comment-001', author: 'Jordan Lee', text: 'The reconciliation signal confidence looks high — is this based on the April discovery call?', entity_type: 'signal', entity_id: 'sig-001', timestamp: '2026-05-01T09:00:00Z', resolved: false },
      { id: 'comment-002', author: 'Avery Stone', text: '@Jordan Lee Yes — confirmed with CFO in the April 28 session.', entity_type: 'signal', entity_id: 'sig-001', timestamp: '2026-05-01T09:30:00Z', resolved: true, parent_id: 'comment-001' },
      { id: 'comment-003', author: 'Jordan Lee', text: 'Benchmark data for cycle time (bench-002) is from 2024 — do we have a more recent source?', entity_type: 'evidence', entity_id: 'ev-002', timestamp: '2026-05-01T10:00:00Z', resolved: false },
    ],
    notifications: [
      { id: 'notif-001', type: 'ingestion_complete', message: 'Ingestion of meridian.example completed: 42 documents processed.', timestamp: '2026-05-01T10:05:00Z', read: false },
      { id: 'notif-002', type: 'review_request', message: 'Jordan Lee requested your review on Meridian Draft Business Case.', timestamp: '2026-05-01T11:00:00Z', read: false },
      { id: 'notif-003', type: 'approval', message: 'Value Engineering Lead approved the Meridian Business Case.', timestamp: '2026-04-29T15:30:00Z', read: true },
      { id: 'notif-004', type: 'stale_benchmark', message: 'Benchmark bench-002 (Cycle Time Reduction) was last verified over 12 months ago.', timestamp: '2026-05-01T08:00:00Z', read: false },
      { id: 'notif-005', type: 'failed_sync', message: 'Salesforce sync failed: Authentication token expired.', timestamp: '2026-05-01T07:00:00Z', read: false },
    ],
    tasks: [
      { id: 'task-001', title: 'Attach benchmark source for cycle time reduction claim', assignee: 'Avery Stone', account_id: DEEP_ACCOUNT_ID, status: 'open', due_date: '2026-05-05T00:00:00Z', stage: 'evidence' },
      { id: 'task-002', title: 'Get CFO sign-off on baseline hours assumption', assignee: 'Jordan Lee', account_id: DEEP_ACCOUNT_ID, status: 'in_progress', due_date: '2026-05-03T00:00:00Z', stage: 'assumptions' },
      { id: 'task-003', title: 'Submit business case for final review', assignee: 'Avery Stone', account_id: DEEP_ACCOUNT_ID, status: 'overdue', due_date: '2026-04-30T00:00:00Z', stage: 'approval' },
    ],
    share_link: { url: 'https://app.valuefabric.test/share/case/token-readonly-abc123', access: 'read_only', expires_at: '2026-06-01T00:00:00Z' },
  };
}

// ── Search Results Data ───────────────────────────────────────────────────────

export function createSearchResults(query = 'reconciliation') {
  return {
    query,
    total: 12,
    results: [
      { type: 'account', id: DEEP_ACCOUNT_ID, title: 'Meridian Health Group', snippet: 'Healthcare prospect — manual reconciliation automation opportunity', url: `/accounts/${DEEP_ACCOUNT_ID}`, tenant_id: DEEP_TENANT_ID },
      { type: 'document', id: 'doc-001', title: 'Q3 Earnings Call Transcript', snippet: '...the reconciliation burden remains our largest operational cost center...', url: `/context/ingestion/jobs/job-complete-001`, tenant_id: DEEP_TENANT_ID },
      { type: 'evidence', id: 'ev-001', title: 'Manual reconciliation baseline', snippet: 'Customer-confirmed: 120 hours/week at $85/hr fully loaded rate.', url: `/governance/evidence`, tenant_id: DEEP_TENANT_ID },
      { type: 'stakeholder', id: 'sh-001', title: 'Dr. Sarah Chen (CFO)', snippet: 'Economic buyer — owns the reconciliation pain and budget authority.', url: `/intelligence/${DEEP_ACCOUNT_ID}/stakeholders`, tenant_id: DEEP_TENANT_ID },
      { type: 'value_model', id: 'model-001', title: 'Meridian ROI Model v3', snippet: 'Expected ROI 2.87x, $700K annual savings, 9-month payback.', url: `/calculator/${DEEP_ACCOUNT_ID}/roi`, tenant_id: DEEP_TENANT_ID },
      { type: 'business_case', id: DEEP_CASE_APPROVED_ID, title: 'Meridian Automation Business Case', snippet: 'Approved case with verified evidence lineage and three-scenario ROI.', url: `/deliverables/cases/${DEEP_CASE_APPROVED_ID}`, tenant_id: DEEP_TENANT_ID },
    ],
    facets: {
      type: { account: 1, document: 3, evidence: 3, stakeholder: 1, value_model: 2, business_case: 2 },
      source_type: { customer_data: 5, benchmark: 3, earnings_call: 2, estimate: 2 },
    },
  };
}

// ── Admin Configuration Data ──────────────────────────────────────────────────

export function createAdminData() {
  return {
    users: [
      { id: 'user-001', name: 'Avery Stone', email: 'avery@valuefabric.test', role: 'admin', status: 'active', last_login: '2026-05-01T08:00:00Z' },
      { id: 'user-002', name: 'Jordan Lee', email: 'jordan@valuefabric.test', role: 'analyst', status: 'active', last_login: '2026-05-01T09:00:00Z' },
      { id: 'user-003', name: 'Sam Taylor', email: 'sam@valuefabric.test', role: 'read_only', status: 'active', last_login: '2026-04-30T10:00:00Z' },
    ],
    roles: [
      { id: 'role-admin', name: 'admin', description: 'Full platform access including governance and admin configuration.' },
      { id: 'role-analyst', name: 'analyst', description: 'Can create and edit value cases, evidence, and models.' },
      { id: 'role-read-only', name: 'read_only', description: 'Can view all content but cannot create or edit.' },
    ],
    tenant_settings: {
      name: 'Meridian Customer Success Org', slug: 'meridian-cs', plan: 'enterprise',
      default_value_pack: 'pack-healthcare-001',
      approval_required_before_export: true,
      evidence_threshold: 0.70,
      benchmark_policy: 'warn_if_stale',
      data_retention_days: 365,
      branding: { primary_color: '#1a6fbf', logo_url: 'https://cdn.example.com/logo.png' },
    },
    platform_health: {
      status: 'healthy',
      components: {
        l1_ingestion: { status: 'healthy', latency_p99_ms: 320 },
        l2_extraction: { status: 'healthy', latency_p99_ms: 1100 },
        l3_knowledge: { status: 'healthy', latency_p99_ms: 85 },
        l4_agents: { status: 'degraded', latency_p99_ms: 4200, note: 'Elevated latency due to model capacity.' },
        l5_ground_truth: { status: 'healthy', latency_p99_ms: 60 },
        l6_benchmarks: { status: 'healthy', latency_p99_ms: 45 },
      },
      failed_jobs: [
        { id: 'job-failed-001', type: 'ingestion', error: 'Duplicate source detected', timestamp: '2026-05-01T09:02:00Z' },
      ],
      security_events: [
        { id: 'sec-001', type: 'unauthorized_access', actor: 'unknown', resource: '/api/v1/agents/accounts', timestamp: '2026-05-01T07:30:00Z', resolved: true },
      ],
    },
  };
}

// ── Value Realization Data ────────────────────────────────────────────────────

export function createValueRealizationPlan() {
  return {
    id: 'real-001',
    account_id: DEEP_ACCOUNT_ID,
    pre_sale_case_id: DEEP_CASE_APPROVED_ID,
    status: 'active',
    target_outcomes: [
      { id: 'outcome-001', description: 'Reduce manual reconciliation hours by 65%', metric: 'hours_per_week', baseline: 120, target: 42, unit: 'hours/week', owner: 'Marcus Rivera' },
      { id: 'outcome-002', description: 'Achieve $700K annual operational savings', metric: 'annual_savings', baseline: 0, target: 700000, unit: 'USD', owner: 'Dr. Sarah Chen' },
    ],
    measurement_cadence: 'monthly',
    actual_results: [
      { period: '2026-06', metric: 'hours_per_week', actual: 98, target: 112, variance_pct: -12.5 },
      { period: '2026-07', metric: 'hours_per_week', actual: 74, target: 84, variance_pct: -11.9 },
    ],
    projected_value: 700000,
    realized_value: 640000,
    variance_pct: -8.6,
    risk_flags: ['Adoption slower than projected in regional billing centers.'],
    next_review_date: '2026-08-01T00:00:00Z',
  };
}

// ── Adversarial Test Data ─────────────────────────────────────────────────────

export function createAdversarialDocumentResult() {
  return {
    job_id: 'job-adversarial-001',
    status: 'completed',
    documents_processed: 3,
    warnings: [
      { type: 'prompt_injection_detected', document: 'analysis-report.pdf', message: 'Embedded system prompt instructions were detected and ignored. Document content was processed normally.' },
      { type: 'low_confidence_extraction', document: 'earnings-notes.txt', message: 'Contradictory signals detected: document contains conflicting revenue figures. All signals marked low-confidence.' },
      { type: 'pii_redacted', document: 'discovery-notes.docx', message: '3 PII items (names, emails) were detected and redacted before storage.' },
    ],
    signals_extracted: 4,
    signals_flagged_low_confidence: 3,
    injection_attempts_blocked: 1,
  };
}

export function createAdversarialAgentRefusal() {
  return {
    content: '**I cannot generate this claim.** The requested ROI projection of 500% is not supported by evidence in the current account context. The strongest evidence-backed projection is 4.2x ROI (optimistic scenario) with customer-validated inputs. Making unsupported claims would violate the platform\'s evidence grounding policy. Please provide additional validated data before claiming this figure.',
    metadata: {
      grounding: 'refusal',
      reason: 'unsupported_claim',
      policy_violated: 'evidence_grounding_policy',
      available_evidence: ['ev-001', 'ev-002', 'ev-003'],
      max_supported_roi: '4.2x',
      trace_id: 'trace-adversarial-001',
      audit_event_id: 'audit-adversarial-001',
    },
  };
}

// ── Mock Endpoint Builders ───────────────────────────────────────────────────

// ── Value Hypotheses ─────────────────────────────────────────────────────────

export function createHypothesisSet() {
  return [
    {
      id: 'hyp-001',
      account_id: DEEP_ACCOUNT_ID,
      product_id: 'prod-001',
      signal_id: 'sig-001',
      signal_name: 'Manual reconciliation burden',
      capability_id: 'cap-001',
      capability_name: 'Workflow Automation',
      hypothesis_text: 'Meridian Health Group can reduce manual reconciliation time by 65% using our workflow automation platform, saving approximately $273K annually.',
      value_path_category: 'cost_savings',
      confidence: 0.92,
      confidence_score: 0.92,
      estimated_impact_usd: 273000,
      status: 'draft',
      evidence_ids: ['ev-001', 'ev-002'],
      created_at: '2026-05-01T10:00:00Z',
      updated_at: '2026-05-01T12:00:00Z',
    },
    {
      id: 'hyp-002',
      account_id: DEEP_ACCOUNT_ID,
      product_id: 'prod-001',
      signal_id: 'sig-002',
      signal_name: 'Supply chain visibility gaps',
      capability_id: 'cap-002',
      capability_name: 'Analytics Dashboard',
      hypothesis_text: 'Improving supply chain visibility can reduce cycle time by 30%, generating $180K in annual value.',
      value_path_category: 'cost_savings',
      confidence: 0.87,
      confidence_score: 0.87,
      estimated_impact_usd: 180000,
      status: 'validated',
      evidence_ids: ['ev-002'],
      created_at: '2026-05-01T10:00:00Z',
      updated_at: '2026-05-01T12:00:00Z',
    },
    {
      id: 'hyp-003',
      account_id: DEEP_ACCOUNT_ID,
      product_id: 'prod-002',
      signal_id: 'sig-003',
      signal_name: 'Regulatory compliance overhead',
      capability_id: 'cap-003',
      capability_name: 'Compliance Module',
      hypothesis_text: 'Automating compliance reporting reduces audit overhead by 40%, saving $95K annually.',
      value_path_category: 'risk_reduction',
      confidence: 0.65,
      confidence_score: 0.65,
      estimated_impact_usd: 95000,
      status: 'draft',
      evidence_ids: ['ev-003'],
      created_at: '2026-05-01T10:00:00Z',
      updated_at: '2026-05-01T12:00:00Z',
    },
  ];
}

// ── ROI Calculation Result ────────────────────────────────────────────────────

export function createROICalculationResult() {
  return {
    id: 'calc-deep-001',
    npv: 1420000,
    irr: 0.42,
    payback_months: 9,
    total_roi_pct: 2.87,
    annual_projections: [
      { year: 1, cost: 180000, benefit: 700000, cumulative_net: 520000, discounted_benefit: 636363 },
      { year: 2, cost: 60000, benefit: 700000, cumulative_net: 1160000, discounted_benefit: 578512 },
      { year: 3, cost: 60000, benefit: 700000, cumulative_net: 1800000, discounted_benefit: 525920 },
    ],
    scenarios: {
      conservative: { npv: 820000, irr: 0.22, payback_months: 14, total_roi_pct: 1.8, multiplier: 0.63 },
      expected: { npv: 1420000, irr: 0.42, payback_months: 9, total_roi_pct: 2.87, multiplier: 1.0 },
      optimistic: { npv: 2340000, irr: 0.68, payback_months: 6, total_roi_pct: 4.2, multiplier: 1.46 },
    },
    created_at: '2026-05-01T12:00:00Z',
  };
}

// ── Industry Benchmarks ───────────────────────────────────────────────────────

export function createIndustryBenchmarks() {
  return {
    industry: 'Healthcare',
    has_benchmarks: true,
    message: 'Benchmarks available for Healthcare industry',
    defaults: {
      productivity_gain_pct: 0.18,
      error_reduction_pct: 0.25,
      time_savings_hours_per_week: 8,
      affected_employees_pct: 0.3,
    },
    avg_deal_size: 250000,
    avg_time_to_value_days: 90,
    avg_roi_pct: 287,
    avg_payback_months: 11,
    avg_npv: 1200000,
    case_count: 47,
    company_sizes: ['mid-market', 'enterprise'],
  };
}

// ── Value Case (Calculator) ───────────────────────────────────────────────────

export function createValueCaseMock() {
  const breakdown = [
    { area: 'Reconciliation Automation', value: 273000, percentage: 39 },
    { area: 'Cycle Time Reduction', value: 180000, percentage: 26 },
    { area: 'Compliance Reporting', value: 95000, percentage: 14 },
    { area: 'Other Efficiency Gains', value: 152000, percentage: 21 },
  ];
  return {
    case_id: 'vc-deep-001',
    account_id: DEEP_ACCOUNT_ID,
    name: 'Meridian Health Group Value Case',
    status: 'active',
    scenarios: [
      { name: 'Conservative', total_value: 1200000, roi_ratio: 1.8, payback_months: 14, annual_savings: 340000, currency: 'USD', breakdown: breakdown.map(b => ({ ...b, value: Math.round(b.value * 0.63) })) },
      { name: 'Expected', total_value: 2100000, roi_ratio: 2.87, payback_months: 9, annual_savings: 700000, currency: 'USD', breakdown },
      { name: 'Optimistic', total_value: 3400000, roi_ratio: 4.2, payback_months: 6, annual_savings: 1100000, currency: 'USD', breakdown: breakdown.map(b => ({ ...b, value: Math.round(b.value * 1.46) })) },
    ],
    levers: [
      { id: 'lever-001', name: 'Reconciliation Automation', base_value: 273000, min_value: 180000, max_value: 420000 },
      { id: 'lever-002', name: 'Cycle Time Reduction', base_value: 180000, min_value: 120000, max_value: 280000 },
    ],
    created_at: '2026-05-01T10:00:00Z',
    updated_at: '2026-05-01T12:00:00Z',
  };
}

// ── Value Case Artifact ───────────────────────────────────────────────────────

export function createValueCaseArtifact() {
  return {
    id: 'artifact-deep-001',
    account_id: DEEP_ACCOUNT_ID,
    version: 1,
    status: 'ready',
    title: 'Meridian Health Group — Value Case',
    executive_summary: 'Meridian Health Group can achieve $2.1M in total value over 3 years by automating manual reconciliation workflows, improving supply chain visibility, and streamlining compliance reporting.',
    lineage: {
      signal_ids: ['sig-001', 'sig-002', 'sig-003'],
      hypothesis_ids: ['hyp-001', 'hyp-002', 'hyp-003'],
      evidence_ids: ['ev-001', 'ev-002', 'ev-003'],
      calculation_id: 'calc-deep-001',
    },
    created_at: '2026-05-01T12:00:00Z',
    updated_at: '2026-05-01T12:00:00Z',
  };
}

// Canonical workspace case ID used by all workspace tab mocks
export const DEEP_WORKSPACE_CASE_ID = 'case-deep-workspace-001';

export function buildGoldenPathMocks(): MockEndpoint[] {
  const jobs = createIngestionJobs();
  const actionPlanContent = { recommendations: [
    { id: 'rec-001', title: 'Automate reconciliation workflow', priority: 'high', projectedValue: '$273K annually', confidence: 'high', horizon: 'Q2 2026', prospectPain: 'Manual reconciliation takes 120 hours/week', rootDriver: 'Operational Efficiency', ourCapability: 'Workflow automation platform', grounding_type: 'evidence_backed' },
    { id: 'rec-002', title: 'Deploy cycle time analytics', priority: 'medium', projectedValue: '$180K annually', confidence: 'medium', horizon: 'Q3 2026', prospectPain: 'Visibility into cycle times', rootDriver: 'Process Optimization', ourCapability: 'Analytics dashboard', grounding_type: 'assumption' },
    { id: 'rec-003', title: 'Integrate compliance reporting', priority: 'critical', projectedValue: '$95K annually', confidence: 'high', horizon: 'Q2 2026', prospectPain: 'Regulatory audit overhead', rootDriver: 'Risk Reduction', ourCapability: 'Compliance module', grounding_type: 'fact' },
  ] };

  return [
    // ── Accounts ──────────────────────────────────────────────────────────
    { pattern: /.*\/api\/v1\/agents\/accounts\?.*/, body: { items: [createFullAccountPayload()], total: 1, page: 1, page_size: 100, has_more: false } },
    { pattern: `**/api/v1/agents/accounts/${DEEP_ACCOUNT_ID}`, body: createFullAccountPayload() },
    { method: 'POST', pattern: /.*\/api\/v1\/agents\/accounts$/, status: 201, body: { account: createFullAccountPayload() } },

    // ── Case ID resolution — GET /cases?account_id=... ────────────────────
    // Must be registered before the generic /cases mock so it takes priority.
    {
      pattern: new RegExp(`.*\\/api\\/v1\\/agents\\/cases\\?account_id=${encodeURIComponent(DEEP_ACCOUNT_ID)}.*`),
      body: { items: [{ case_id: DEEP_WORKSPACE_CASE_ID, account_id: DEEP_ACCOUNT_ID, title: 'Meridian workspace', status: 'active' }], total: 1 },
    },
    // Fallback case lookup for any account
    { pattern: /.*\/api\/v1\/agents\/cases\?account_id=.*/, body: { items: [{ case_id: DEEP_WORKSPACE_CASE_ID, account_id: DEEP_ACCOUNT_ID, title: 'Meridian workspace', status: 'active' }], total: 1 } },
    // Case create
    { method: 'POST', pattern: /.*\/api\/v1\/agents\/cases$/, status: 201, body: { case_id: DEEP_WORKSPACE_CASE_ID, account_id: DEEP_ACCOUNT_ID, title: 'Meridian workspace', status: 'active' } },

    // ── Workspace tabs — wildcard caseId (survives localStorage caching) ──
    // The hook returns response.data directly, so body IS the TData the page reads.
    // More-specific patterns first so they win over the DEFAULT_MOCKS fallbacks.
    { pattern: /.*\/api\/v1\/agents\/cases\/[^/]+\/workspace\/signals$/, body: createSignalSet().content },
    { pattern: /.*\/api\/v1\/agents\/cases\/[^/]+\/workspace\/drivers$/, body: createValueDriverTree().content },
    { pattern: /.*\/api\/v1\/agents\/cases\/[^/]+\/workspace\/evidence$/, body: createEvidenceSet().content },
    { pattern: /.*\/api\/v1\/agents\/cases\/[^/]+\/workspace\/stakeholders$/, body: { stakeholders: [{ id: 'sh-001', name: 'CFO', influence: 'high' }] } },
    { pattern: /.*\/api\/v1\/agents\/cases\/[^/]+\/workspace\/value-model$/, body: { ...createROICalculatorMock(), latest_value_case_id: 'vc-deep-001', value_case: createValueCaseMock() } },
    { pattern: /.*\/api\/v1\/agents\/cases\/[^/]+\/workspace\/narrative$/, body: { narrative: 'Generated executive narrative for Meridian Health Group.' } },
    { pattern: /.*\/api\/v1\/agents\/cases\/[^/]+\/workspace\/action-plan$/, body: actionPlanContent },
    { pattern: /.*\/api\/v1\/agents\/cases\/[^/]+\/workspace\/evidence-links$/, body: { evidence_links: [] } },
    { method: 'POST', pattern: /.*\/api\/v1\/agents\/cases\/[^/]+\/workspace\/generate$/, body: { status: 'generating' } },
    { method: 'POST', pattern: /.*\/api\/v1\/agents\/cases\/[^/]+\/workspace\/signals\/[^/]+\/review$/, body: { status: 'ok' } },

    // ── Value Hypotheses (L4) — /api/v1/agents/hypotheses/... ────────────
    {
      pattern: /.*\/api\/v1\/agents\/hypotheses\/account\/.*/,
      body: { hypotheses: createHypothesisSet(), total: 3 },
    },
    { pattern: '**/api/v1/agents/hypotheses/summary/stats', body: { total: 3, by_status: { draft: 2, validated: 1 }, avg_confidence: 0.81, avg_estimated_impact: 182666, total_estimated_impact: 548000, unique_accounts: 1, unique_products: 2 } },
    { method: 'POST', pattern: '**/api/v1/agents/hypotheses/generate', body: { hypotheses: createHypothesisSet(), signals_analyzed: 4, products_matched: 2 } },
    { method: 'POST', pattern: /.*\/api\/v1\/agents\/hypotheses\/.*\/validate/, body: { hypothesis: { ...createHypothesisSet()[0], status: 'validated' }, promoted_artifacts: { drivers: [], levers: [], created: true }, status: 'ok' } },
    { method: 'POST', pattern: /.*\/api\/v1\/agents\/hypotheses\/.*\/convert/, body: { hypothesis_id: 'hyp-001', account_id: DEEP_ACCOUNT_ID, tenant_id: DEEP_TENANT_ID, evidence_ids: ['ev-001'], status: 'ok' } },
    { method: 'POST', pattern: '**/api/v1/agents/hypotheses/rank', body: createHypothesisSet() },
    { method: 'POST', pattern: '**/api/v1/agents/hypotheses/from-signal', body: { hypothesis: createHypothesisSet()[0] } },

    // ── ROI Calculator (L3) — /api/v1/graph/v1/roi/... ───────────────────
    // L3 layer prefix is /graph, so full path is /api/v1/graph/v1/roi/...
    { method: 'POST', pattern: /.*\/v1\/roi\/calculate/, body: createROICalculationResult() },
    { pattern: /.*\/v1\/roi\/benchmarks.*/, body: createIndustryBenchmarks() },
    { pattern: /.*\/v1\/roi\/templates.*/, body: { templates: [], total: 0, skip: 0, limit: 20 } },
    { pattern: /.*\/v1\/roi\/calculations.*/, body: { calculations: [createROICalculationResult()], total: 1, skip: 0, limit: 20 } },

    // ── Ingestion jobs — /api/v1/ingest/jobs ─────────────────────────────
    {
      pattern: /.*\/api\/v1\/ingest\/jobs(\?.*)?$/,
      body: { data: jobs, pagination: { page: 1, limit: 20, total: jobs.length, totalPages: 1 }, aggregation: { by_status: { completed: 1, failed: 1, running: 1 } } },
    },
    {
      pattern: /.*\/api\/v1\/ingest\/jobs\/[^/]+\/retry/,
      method: 'POST',
      status: 200,
      body: { status: 'retrying', job_id: 'job-failed-001' },
    },
    {
      pattern: /.*\/api\/v1\/ingest\/jobs\/[^/]+$/,
      body: { ...jobs[0], stages: [{ stage: 'Extract', status: 'COMPLETED' }, { stage: 'Transform', status: 'COMPLETED' }, { stage: 'Load', status: 'COMPLETED' }], progress: { percentComplete: 100, processedPages: 42, totalPages: 42 } },
    },

    // ── Agent stream ──────────────────────────────────────────────────────
    { method: 'POST', pattern: '**/agent-stream/chat', body: createGroundedAgentResponse() },

    // ── Account gates / reviews ───────────────────────────────────────────
    {
      pattern: /.*\/api\/v1\/agents\/accounts\/[^/]+\/gates$/,
      body: {
        all_passed: true,
        gates: [
          { type: 'evidence', status: 'closed', label: 'Evidence Gate' },
          { type: 'approval', status: 'closed', label: 'Approval Gate' },
          { type: 'export', status: 'closed', label: 'Export Gate' },
        ],
      },
    },
    { pattern: /.*\/api\/v1\/agents\/accounts\/[^/]+\/reviews$/, body: [] },

    // ── Business cases ────────────────────────────────────────────────────
    { pattern: `**/api/v1/agents/cases/${DEEP_CASE_APPROVED_ID}`, body: createApprovedBusinessCase() },
    { pattern: `**/api/v1/agents/cases/${DEEP_CASE_DRAFT_ID}`, body: createDraftBusinessCase() },
    { pattern: '**/api/v1/agents/cases', body: { items: [createApprovedBusinessCase(), createDraftBusinessCase()], total: 2 } },

    // ── Governance / approvals ────────────────────────────────────────────
    { pattern: '**/api/v1/governance/approvals**', body: [createApprovalWorkflow('approved')] },

    // ── Value cases (L3 /graph/v1/calculators/value-cases) ───────────────
    { pattern: /.*\/v1\/calculators\/value-cases\/vc-deep-001.*/, body: createValueCaseMock() },
    { pattern: /.*\/v1\/calculators\/value-cases.*/, body: { items: [createValueCaseMock()], total: 1 } },
    { method: 'POST', pattern: /.*\/v1\/calculators\/value-cases.*/, body: createValueCaseMock() },

    // ── Value levers (L3 /graph/v1/calculators/levers) ───────────────────
    {
      pattern: /.*\/v1\/calculators\/levers.*/,
      body: {
        levers: [
          { id: 'lever-001', name: 'Reconciliation Automation', category: 'cost_savings', base_value: 273000, min_value: 180000, max_value: 420000, annual_impact: 273000, confidence: 0.92, unit: 'USD' },
          { id: 'lever-002', name: 'Cycle Time Reduction', category: 'cost_savings', base_value: 180000, min_value: 120000, max_value: 280000, annual_impact: 180000, confidence: 0.87, unit: 'USD' },
        ],
        total: 2,
      },
    },

    // ── ROI scenario versions ─────────────────────────────────────────────
    { pattern: /.*\/api\/v1\/agents\/analysis\/cases\/[^/]+\/workspace\/value-model\/scenarios.*/, body: { items: [], total: 0 } },
    { method: 'POST', pattern: /.*\/api\/v1\/agents\/analysis\/cases\/[^/]+\/workspace\/value-model\/scenarios.*/, body: { versionId: 'ver-001', assumptions: {}, created_at: '2026-05-01T12:00:00Z' } },
    { method: 'PATCH', pattern: /.*\/api\/v1\/agents\/analysis\/cases\/[^/]+\/workspace\/value-model\/scenarios.*/, body: { versionId: 'ver-001', assumptions: {}, created_at: '2026-05-01T12:00:00Z' } },

    // ── Value trees (L3 /graph/value-trees) ──────────────────────────────
    { pattern: /.*\/value-trees\/.*\/paths.*/, body: { paths: [] } },
    { pattern: /.*\/value-trees\/.*/, body: { id: 'vt-001', entity_id: DEEP_ACCOUNT_ID, nodes: [], edges: [] } },

    // ── Integrations / benchmarks / ground truth ──────────────────────────
    { pattern: '**/api/v1/agents/integrations**', body: createCRMIntegration('idle') },
    { pattern: '**/api/v1/benchmarks/datasets**', body: createBenchmarkDatasets() },
    { pattern: '**/api/v1/agents/ground-truth/truths**', body: createGroundTruthSet() },
    { pattern: '**/api/v1/agents/recommendations**', body: [{ id: 'rec-001', status: 'pending_review', evidence_id: 'ev-001', text: 'Automate reconciliation workflow' }] },

    // ── Value case artifacts — /api/v1/agents/v1/value-case/artifacts ────
    { pattern: /.*\/v1\/value-case\/artifacts.*/, body: { versions: [createValueCaseArtifact()] } },
    { method: 'POST', pattern: /.*\/v1\/value-case\/artifacts.*/, body: createValueCaseArtifact() },
  ];
}
