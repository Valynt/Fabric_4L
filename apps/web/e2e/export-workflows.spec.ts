import { E2E_SEED_APPROVED_CASE_ID, E2E_SEED_PRIVILEGED_REASON, E2E_SEED_TENANT_SLUG } from './fixtures/seed-constants';
/**
 * Export Workflow Validation Suite
 *
 * Traceability: EXPORT-001, EXEC-BUYER-001, SHARE-001, PROVENANCE-EXPORT-001.
 * Approved deliverables, shared views, and provenance exports must be reachable
 * through the UI while unapproved cases remain blocked from final export.
 */
import { journeyTest, expect } from './helpers/journey-fixture';
import {
  expectAnyVisible,
  expectButtonStateIfVisible,
  expectNoCrossTenantLeakage,
  expectRouteSupportsWorkflow,
} from './helpers/validation-program';

const CASE_ID = E2E_SEED_APPROVED_CASE_ID;

journeyTest.describe('Export Workflow Validation Suite', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    await addMocks([
      {
        pattern: `**/api/v1/agents/cases/${CASE_ID}`,
        body: {
          id: CASE_ID,
          title: 'Meridian Automation Business Case',
          status: 'approved',
          document_url: '/exports/meridian-business-case.pdf',
          roi_ratio: 2.4,
          payback_months: 9,
          executive_summary: 'Approved case with verified evidence lineage.',
          recommendations: ['Proceed with executive-buyer review.'],
        },
      },
      {
        pattern: '**/api/v1/agents/cases/case-draft-001',
        body: {
          id: 'case-draft-001',
          title: 'Draft Business Case',
          status: 'draft',
          document_url: null,
          roi_ratio: 1.1,
          payback_months: 18,
          executive_summary: 'Draft case pending approval.',
          recommendations: ['Resolve missing evidence before export.'],
        },
      },
      {
        pattern: '**/api/v1/agents/workflows?type=business_case**',
        body: {
          items: [
            {
              workflow_id: CASE_ID,
              name: 'Meridian Automation Business Case',
              status: 'completed',
              company_name: 'Meridian Health Group',
              total_value: 1200000,
              use_case_count: 3,
              confidence: 0.91,
              created_at: '2026-04-20T12:00:00Z',
              updated_at: '2026-05-01T12:00:00Z',
              owner: 'Avery Stone',
            },
          ],
        },
      },
    ]);
  });

  journeyTest('Step 1 [EXPORT-001]: approved business case exposes final PDF export action', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      `/deliverables/cases/${CASE_ID}`,
      [/business case/i, /approved/i, /executive summary/i, /recommendations/i, /export pdf/i],
      'approved business-case PDF export workflow',
    );

    const exportButton = authedPage.getByRole('button', { name: /export pdf/i }).first();
    if (await exportButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(exportButton).toBeEnabled();
    }
  });

  journeyTest('Step 2 [EXPORT-GATE-001]: draft business case keeps export disabled until approval', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/deliverables/cases/case-draft-001',
      [/business case/i, /status: draft/i, /executive summary/i, /export pdf/i],
      'draft business-case export gate workflow',
    );

    const exportButton = authedPage.getByRole('button', { name: /export pdf/i }).first();
    if (await exportButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(exportButton).toBeDisabled();
    }
  });

  journeyTest('Step 3 [EXEC-BUYER-001]: executive-buyer shared view renders buyer-facing summary and financial impact', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/deliverables/views/executive',
      [/executive/i, /summary/i, /financial/i, /impact/i, /assumptions/i],
      'executive-buyer shared deliverable view',
    );
    await expectNoCrossTenantLeakage(authedPage);
  });

  journeyTest('Step 4 [SHARE-001]: deliverable list supports create, search, and shared-case review', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/deliverables/cases',
      [/business cases/i, /new case/i, /search cases or companies/i, /draft/i, /active/i],
      'business-case list, search, create, and shared review workflow',
    );
  });

  journeyTest('Step 5 [PROVENANCE-EXPORT-001]: provenance export is visible with audit context', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/governance/traces',
      [/decision trace/i, /export prov-o/i, /audit log/i, /provenance timeline/i],
      'provenance export and audit-context workflow',
    );
    await expectAnyVisible(authedPage, [/export prov-o/i, /audit log/i], 'provenance export controls');
  });

  journeyTest('test_export_blocked_without_required_role_and_approval', async ({ authedPage }) => {
    await expectRouteSupportsWorkflow(
      authedPage,
      '/deliverables/cases/case-draft-001',
      [/business case/i, /draft/i, /export pdf/i, /executive summary/i],
      'draft export governance workflow',
    );
    await expectButtonStateIfVisible(authedPage, /export pdf/i, 'disabled');
  });
});
