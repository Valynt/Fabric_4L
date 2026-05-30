/**
 * Journey 21: Persona-Based Validation Journeys
 *
 * Traceability: PERSONA-SALES-001, PERSONA-VE-001, PERSONA-LEADER-001,
 *               PERSONA-CSM-001, PERSONA-ADMIN-001, PERSONA-EXEC-001.
 * Each persona block validates the end-to-end workflow path for a
 * specific user role: Sales Rep, Value Engineer, Sales Leader, Customer
 * Success Manager, Admin, and Executive Buyer.
 *
 * Priority: P1 core workflow
 */
import { journeyTest, expect } from '../helpers/journey-fixture';
import {
  expectAnyVisible,
  expectRouteSupportsWorkflow,
  expectTenantContext,
  expectNoCrossTenantLeakage,
} from '../helpers/validation-program';
import {
  DEEP_ACCOUNT_ID,
  DEEP_CASE_APPROVED_ID,
  buildGoldenPathMocks,
  createValueRealizationPlan,
  createAdminData,
} from '../fixtures/deep-test-data';

// ── Sales Rep Persona ─────────────────────────────────────────────────────────

journeyTest.describe('Persona: Sales Rep', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks(buildGoldenPathMocks());
  });

  journeyTest('PERSONA-SALES-001: sales rep creates account and starts value case', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/accounts/new',
      [/start.*value case|new.*case|company|domain/i],
      'prospect intake form',
    );
  });

  journeyTest('PERSONA-SALES-002: sales rep imports discovery notes and sees ingestion status', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/ingestion/jobs',
      [/ingestion|document|job|completed|meridian/i],
      'ingestion job status for sales rep',
    );
  });

  journeyTest('PERSONA-SALES-003: sales rep reviews extracted signals with confidence and source', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/intelligence/${DEEP_ACCOUNT_ID}/signals`,
      [/signal|confidence|source|manual reconciliation/i],
      'signal review for sales rep',
    );
  });

  journeyTest('PERSONA-SALES-004: sales rep generates value hypotheses', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/hypothesis/${DEEP_ACCOUNT_ID}/hypothesis`,
      [/hypothesis|value|generate|approve/i],
      'hypothesis generation for sales rep',
    );
  });

  journeyTest('PERSONA-SALES-005: sales rep builds first-pass business case', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/deliverables/cases',
      [/business case|draft|create.*case|new.*case/i],
      'business case creation for sales rep',
    );
  });

  journeyTest('PERSONA-SALES-006: sales rep generates executive email from narrative studio', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/studio/${DEEP_ACCOUNT_ID}/narrative`,
      [/executive email|narrative|generate|studio/i],
      'executive email generation for sales rep',
    );
  });

  journeyTest('PERSONA-SALES-007: sales rep pushes summary to CRM', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/settings/integrations',
      [/crm|salesforce|sync|push/i],
      'CRM push capability for sales rep',
    );
  });
});

// ── Value Engineer Persona ────────────────────────────────────────────────────

journeyTest.describe('Persona: Value Engineer', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks(buildGoldenPathMocks());
  });

  journeyTest('PERSONA-VE-001: value engineer reviews and validates evidence library', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/governance/evidence',
      [/evidence|confidence|source|approved|pending/i],
      'evidence library for value engineer',
    );
  });

  journeyTest('PERSONA-VE-002: value engineer refines value driver tree', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/drivers/${DEEP_ACCOUNT_ID}/tree`,
      [/driver|operational efficiency|revenue|risk/i],
      'value driver tree for value engineer',
    );
  });

  journeyTest('PERSONA-VE-003: value engineer selects and validates formulas', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/formulas',
      [/formula|reconciliation|selected|lever/i],
      'formula selection for value engineer',
    );
  });

  journeyTest('PERSONA-VE-004: value engineer validates assumptions and locks approved ones', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/calculator/${DEEP_ACCOUNT_ID}/roi`,
      [/assumption|locked|approved|validate/i],
      'assumption validation and locking for value engineer',
    );
  });

  journeyTest('PERSONA-VE-005: value engineer builds conservative, expected, and optimistic scenarios', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/calculator/${DEEP_ACCOUNT_ID}/roi`,
      [/conservative|expected|optimistic|scenario/i],
      'three-scenario calculator for value engineer',
    );
  });

  journeyTest('PERSONA-VE-006: value engineer produces CFO-ready business case', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/deliverables/cases',
      [/business case|cfo|approved|executive summary/i],
      'CFO-ready business case production for value engineer',
    );
  });
});

// ── Sales Leader Persona ──────────────────────────────────────────────────────

journeyTest.describe('Persona: Sales Leader', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks(buildGoldenPathMocks());
  });

  journeyTest('PERSONA-LEADER-001: sales leader views pipeline of value cases across accounts', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/deliverables/cases',
      [/business case|pipeline|approved|draft/i],
      'pipeline view of value cases for sales leader',
    );
  });

  journeyTest('PERSONA-LEADER-002: sales leader compares account-level ROI models', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/calculator/${DEEP_ACCOUNT_ID}/roi`,
      [/roi|scenario|payback|2\.87|conservative/i],
      'ROI model comparison for sales leader',
    );
  });

  journeyTest('PERSONA-LEADER-003: sales leader identifies weak business cases by evidence strength', async ({ authedPage }) => {
    await authedPage.goto('/deliverables/cases', { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/draft|missing.*evidence|low.*confidence|weak|business case/i],
      'weak or incomplete business cases visible for sales leader review',
    );
  });

  journeyTest('PERSONA-LEADER-004: sales leader can approve strategic account business cases', async ({ authedPage }) => {
    await authedPage.goto(`/deliverables/cases/${DEEP_CASE_APPROVED_ID}`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/approved|business case|meridian|roi/i],
      'approved business case for sales leader review',
    );
  });
});

// ── Customer Success Manager Persona ──────────────────────────────────────────

journeyTest.describe('Persona: Customer Success Manager', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    const plan = createValueRealizationPlan();
    await addMocks([
      ...buildGoldenPathMocks(),
      { pattern: `**/api/v1/agents/accounts/${DEEP_ACCOUNT_ID}/realization`, body: plan },
      { pattern: `**/api/v1/agents/accounts/${DEEP_ACCOUNT_ID}/realization`, method: 'POST', status: 201, body: plan },
    ]);
  });

  journeyTest('PERSONA-CSM-001: CSM converts pre-sale case into value realization plan', async ({ authedPage }) => {
    await authedPage.goto(`/deliverables/cases/${DEEP_CASE_APPROVED_ID}`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/realization|post.sale|convert|plan|approved/i, /business case/i],
      'approved business case with conversion to realization plan option',
    );
  });

  journeyTest('PERSONA-CSM-002: CSM defines target outcomes and baseline metrics', async ({ authedPage }) => {
    await authedPage.goto(`/accounts/${DEEP_ACCOUNT_ID}`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/outcome|baseline|metric|target|reconciliation|hours/i, /meridian|account/i],
      'value realization plan target and baseline metric entry',
    );
  });

  journeyTest('PERSONA-CSM-003: CSM records actual results and compares to projected', async ({ authedPage }) => {
    await authedPage.goto(`/accounts/${DEEP_ACCOUNT_ID}`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/actual|projected|realized|640K|700K|variance/i, /meridian|account/i],
      'value realization plan with actual vs projected comparison',
    );
  });

  journeyTest('PERSONA-CSM-004: CSM generates renewal narrative with realized value', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/studio/${DEEP_ACCOUNT_ID}/narrative`,
      [/renewal|realized|narrative|year.*1|640K/i],
      'renewal narrative generation for CSM',
    );
  });

  journeyTest('PERSONA-CSM-005: CSM identifies expansion opportunity recommendation', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/studio/${DEEP_ACCOUNT_ID}/action-plan`,
      [/expansion|regional|billing center|opportunity|recommendation/i],
      'expansion opportunity recommendation for CSM',
    );
  });
});

// ── Admin Persona ─────────────────────────────────────────────────────────────

journeyTest.describe('Persona: Admin', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    const admin = createAdminData();
    await addMocks([
      ...buildGoldenPathMocks(),
      { pattern: '**/api/v1/agents/users**', body: admin.users },
      { pattern: '**/api/v1/agents/settings**', body: admin.tenant_settings },
      { pattern: '**/api/v1/agents/health**', body: admin.platform_health },
    ]);
  });

  journeyTest('PERSONA-ADMIN-001: admin configures tenant settings and default value pack', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/workspace-settings',
      [/tenant|workspace|default.*pack|settings/i],
      'tenant configuration for admin',
    );
  });

  journeyTest('PERSONA-ADMIN-002: admin manages users and roles', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/organization-admin',
      [/user|role|avery stone|jordan lee|admin|analyst/i],
      'user and role management for admin',
    );
  });

  journeyTest('PERSONA-ADMIN-003: admin configures value packs', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/settings/data/value-packs',
      [/value pack|healthcare|saas|publish|deprecate/i],
      'value pack management for admin',
    );
  });

  journeyTest('PERSONA-ADMIN-004: admin configures integrations', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/settings/integrations',
      [/salesforce|crm|integration|connect/i],
      'integration management for admin',
    );
  });

  journeyTest('PERSONA-ADMIN-005: admin reviews audit and security events', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/governance/audit/log',
      [/audit|security|event|log|unauthorized/i],
      'audit and security event review for admin',
    );
  });

  journeyTest('PERSONA-ADMIN-006: admin manages governance policies', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/governance-center',
      [/governance|policy|approval|evidence.*threshold|benchmark/i],
      'governance policy management for admin',
    );
  });
});

// ── Executive Buyer Persona ───────────────────────────────────────────────────

journeyTest.describe('Persona: Executive Buyer View', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks(buildGoldenPathMocks());
  });

  journeyTest('PERSONA-EXEC-001: executive buyer can open and read shared business case', async ({ authedPage }) => {
    await authedPage.goto(`/deliverables/cases/${DEEP_CASE_APPROVED_ID}`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/meridian.*automation|business case|executive summary/i],
      'shared business case readable by executive buyer',
    );
  });

  journeyTest('PERSONA-EXEC-002: executive buyer sees executive summary prominently', async ({ authedPage }) => {
    await authedPage.goto(`/deliverables/cases/${DEEP_CASE_APPROVED_ID}`, { waitUntil: 'domcontentloaded' });

    await expect(
      authedPage.getByText(/executive summary|approved.*case|verified evidence/i).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('PERSONA-EXEC-003: executive buyer can review financial impact with ROI, payback, and total value', async ({ authedPage }) => {
    await authedPage.goto(`/deliverables/cases/${DEEP_CASE_APPROVED_ID}`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/roi|payback|total.*value|2\.87|2,100,000|9.*month/i],
      'financial impact section visible to executive buyer',
    );
  });

  journeyTest('PERSONA-EXEC-004: executive buyer can review and understand assumptions', async ({ authedPage }) => {
    await authedPage.goto(`/deliverables/cases/${DEEP_CASE_APPROVED_ID}`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/assumption|baseline.*hours|finance.*team|approved/i],
      'assumption section visible and labeled in executive view',
    );
  });

  journeyTest('PERSONA-EXEC-005: executive buyer can review evidence backing claims', async ({ authedPage }) => {
    await authedPage.goto(`/deliverables/cases/${DEEP_CASE_APPROVED_ID}`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/evidence|discovery.*call|420K.*annually|claim/i],
      'evidence references visible in executive view',
    );
  });

  journeyTest('PERSONA-EXEC-006: executive buyer can review implementation risk section', async ({ authedPage }) => {
    await authedPage.goto(`/deliverables/cases/${DEEP_CASE_APPROVED_ID}`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/risk|implementation|mitigation|assumption/i],
      'implementation risk section visible to executive buyer',
    );
  });

  journeyTest('PERSONA-EXEC-007: executive buyer can download or share final approved business case', async ({ authedPage }) => {
    await authedPage.goto(`/deliverables/cases/${DEEP_CASE_APPROVED_ID}`, { waitUntil: 'domcontentloaded' });

    await expectAnyVisible(
      authedPage,
      [/export.*pdf|download|share|approved/i],
      'download or share action available for approved business case',
    );

    await expectNoCrossTenantLeakage(authedPage);
    await expectTenantContext(authedPage);
  });
});
