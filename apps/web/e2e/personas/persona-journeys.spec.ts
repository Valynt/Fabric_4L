/**
 * Persona Journey Validation Suite
 *
 * Traceability: PERSONA-SALES-001, PERSONA-VE-001, PERSONA-LEADER-001,
 * PERSONA-CSM-001, PERSONA-ADMIN-001, PERSONA-BUYER-001. Persona tests
 * validate that the same critical workflows are reachable from the role-shaped
 * surfaces real users depend on.
 */
import { journeyTest } from '../helpers/journey-fixture';
import { expectRouteSupportsWorkflow } from '../helpers/validation-program';

const ACCOUNT_ID = 'acct-meridian';

journeyTest.describe('Persona Journey Validation Suite', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/accounts',
        body: [{ id: ACCOUNT_ID, name: 'Meridian Health Group', owner: 'Avery Stone', stage: 'prospect' }],
      },
    ]);
  });

  journeyTest('Step 1 [PERSONA-SALES-001]: sales rep can start account setup and push toward CRM context', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/workflow',
      [/start a new value case/i, /search company/i, /attach source material/i, /run account enrichment/i],
      'sales rep account setup, discovery notes, enrichment, and handoff workflow',
    );
  });

  journeyTest('Step 2 [PERSONA-VE-001]: value engineer can review evidence and build scenario model', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/calculator/${ACCOUNT_ID}/roi`,
      [/roi calculator/i, /scenario-based roi/i, /payback/i, /risk-adjusted/i],
      'value engineer evidence, formula, and scenario-model workflow',
    );
  });

  journeyTest('Step 3 [PERSONA-LEADER-001]: sales leader can inspect value-case and decision trace quality', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/value-case/${ACCOUNT_ID}`,
      [/value case/i, /roi/i, /evidence/i, /recommendations/i, /executive summary/i],
      'sales leader strategic review, weak-evidence, and high-value approval workflow',
    );
  });

  journeyTest('Step 4 [PERSONA-CSM-001]: customer success manager can track realized value for renewal narrative', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/realization/${ACCOUNT_ID}`,
      [/value realization/i, /action plan/i, /outcomes/i, /renewal/i, /expansion/i],
      'customer success realized-value, renewal, and expansion workflow',
    );
  });

  journeyTest('Step 5 [PERSONA-ADMIN-001]: admin can configure team, integrations, and governance controls', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/settings/team',
      [/team members/i, /invite user/i, /manage/i, /review active members/i],
      'admin team, integration, governance, and access-control workflow',
    );
  });

  journeyTest('Step 6 [PERSONA-BUYER-001]: executive buyer can view approved case summary and assumptions', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/deliverables/views/executive',
      [/executive/i, /summary/i, /financial/i, /impact/i, /assumptions/i],
      'executive buyer shared business-case workflow',
    );
  });

  journeyTest('test_sales_rep_to_crm_push_persona_journey', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/workflow',
      [/start a new value case/i, /launch intelligence/i, /attach source material/i],
      'sales rep account creation and discovery workflow',
    );

    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/integrations',
      [/crm/i, /salesforce/i, /push/i, /sync/i],
      'sales rep CRM handoff workflow',
    );
  });
});
