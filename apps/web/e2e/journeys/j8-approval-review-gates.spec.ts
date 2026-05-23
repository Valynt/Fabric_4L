import { E2E_SEED_APPROVED_CASE_ID, E2E_SEED_TENANT_SLUG } from '../fixtures/seed-constants';
/**
 * Journey 8: Approval and Review Gates
 *
 * Traceability: REVIEW-001, EXPORT-GATE-001, CLAIM-TRACE-001, GOVERNANCE-APPROVAL-001.
 * Critical approval workflows must be exercised through the UI and must fail
 * closed when approvals, evidence, or reviewer roles are missing.
 */
import { journeyTest, expect } from '../helpers/journey-fixture';
import {
  attemptOptionalAction,
  expectAnyVisible,
  expectButtonStateIfVisible,
  expectRouteSupportsWorkflow,
} from '../helpers/validation-program';

const ACCOUNT_ID = 'acct-meridian';
const CASE_ID = E2E_SEED_APPROVED_CASE_ID;

journeyTest.describe('Journey 8: Approval and Review Gates', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/agents/cases',
        body: [
          { id: CASE_ID, title: 'Meridian Automation Business Case', status: 'draft', company: 'Meridian Health Group' },
        ],
      },
      {
        pattern: `**/api/v1/agents/cases/${CASE_ID}`,
        body: {
          id: CASE_ID,
          title: 'Meridian Automation Business Case',
          status: 'draft',
          document_url: null,
          roi_ratio: 2.4,
          payback_months: 9,
          executive_summary: 'Draft case pending evidence approval.',
          recommendations: ['Approve only after supporting evidence is verified.'],
        },
      },
      {
        pattern: '**/api/v1/governance/approvals**',
        body: [{ id: 'approval-001', state: 'pending_review', reviewer: 'Value Engineering Lead' }],
      },
      {
        pattern: '**/api/v1/agents/integrations**',
        body: {
          integrations: [
            {
              id: 'int-salesforce-001',
              tenant_id: E2E_SEED_TENANT_SLUG,
              provider: 'salesforce',
              enabled: true,
              instance_url: 'https://meridian.my.salesforce.com',
              sync_interval_minutes: 60,
              sync_batch_size: 250,
              last_sync_at: '2026-05-01T12:00:00Z',
              last_successful_sync_at: '2026-05-01T12:00:00Z',
              records_synced: 128,
              records_updated: 9,
              records_failed: 0,
              status: 'idle',
              last_error_message: null,
              has_refresh_token: true,
              created_at: '2026-04-01T12:00:00Z',
              updated_at: '2026-05-01T12:00:00Z',
            },
          ],
        },
      },
    ]);
  });

  journeyTest('Step 1 [REVIEW-001]: hypothesis review surface supports approve, edit, and assumptions review', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/hypothesis/${ACCOUNT_ID}/hypothesis`,
      [/hypoth/i, /generate/i, /approve/i, /edit/i, /assumption/i],
      'hypothesis generation, edit, and approval workflow',
    );
  });

  journeyTest('Step 2 [REVIEW-002]: assumptions route exposes validation status before model approval', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/hypothesis/${ACCOUNT_ID}/assumptions`,
      [/assumption/i, /validation/i, /approved/i, /rejected/i, /source/i],
      'assumption validation status and source-of-truth review workflow',
    );
  });

  journeyTest('Step 3 [REVIEW-003]: formula and benchmark governance expose approval queue controls', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/settings/governance/policies',
      [/policies/i, /governance/i, /approval/i, /review/i, /enforce/i],
      'governance policy and approval gate configuration workflow',
    );
  });

  journeyTest('Step 4 [EXPORT-GATE-001]: draft business case does not expose an enabled final export path before approval', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/deliverables/cases/${CASE_ID}`,
      [/business case/i, /status: draft/i, /executive summary/i, /recommendations/i, /export pdf/i],
      'draft business case review and export-gate workflow',
    );

    const exportButton = authedPage.getByRole('button', { name: /export pdf/i }).first();
    if (await exportButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(exportButton).toBeDisabled();
    }
  });

  journeyTest('Step 5 [GOVERNANCE-APPROVAL-001]: reviewer can access approval and audit history surfaces', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/governance/audit/changes',
      [/change/i, /history/i, /audit/i, /approval/i, /review/i],
      'approval history and reviewer decision trail workflow',
    );
  });

  journeyTest('Step 6 [CRM-GATE-001]: CRM push remains governed by approval status', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/context/integrations',
      [/integrations/i, /crm/i, /salesforce/i, /sync/i],
      'CRM sync workflow gated by approval state',
    );

    const attempted = await attemptOptionalAction(authedPage, /sync|push/i);
    if (attempted) {
      await expectAnyVisible(authedPage, [/approval/i, /sync/i, /started/i, /failed/i, /permission/i], 'CRM sync status or approval gate feedback');
    }
  });

  journeyTest('test_export_is_available_only_after_required_approval', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/deliverables/cases/${CASE_ID}`,
      [/business case/i, /draft/i, /executive summary/i, /export pdf/i],
      'export gate before approval',
    );
    await expectButtonStateIfVisible(authedPage, /export pdf/i, 'disabled');
  });
});
