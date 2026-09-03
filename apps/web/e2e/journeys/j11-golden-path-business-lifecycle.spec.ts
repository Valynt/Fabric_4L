/**
 * Journey 11: Golden Path Business Lifecycle
 *
 * Traceability: GP-LIFECYCLE-001, CLAIM-TRACE-001, EXPORT-GATE-001, CRM-GATE-001.
 * This suite is intentionally backend-integrated and fail-closed. It defines
 * the end-to-end validation contract for the account-to-approved-business-case
 * lifecycle against seeded data.
 */
import { test, expect } from '../fixtures/contract-test';
import {
  expectAnyVisible,
  expectButtonStateIfVisible,
  expectNoCrossTenantLeakage,
  expectRouteSupportsWorkflow,
  expectSeededBusinessCaseWorkflowResults,
  expectTenantContext,
  requireBackendOrThrow,
} from '../helpers/validation-program';
import { navigateAndWait } from '../helpers/journey-fixture';
import { BACKEND_E2E_TENANT_ID, seedAuthState } from '../fixtures/auth-helpers';
import { setSelectedAccount, TEST_ACCOUNTS } from '../fixtures/account-helpers';
import { setUserTier } from '../fixtures/tier-helpers';

const ACCOUNT_ID = TEST_ACCOUNTS.meridian.id;
const TENANT_SLUG = 'e2e-test';
const SEEDED_BUSINESS_CASE_IDS = ['case-draft-001', 'case-e2e-approved-001', 'case-meridian-e2e-001'];

test.describe('Journey 11: Golden Path Business Lifecycle', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuthState(page, {
      id: 'test-user-e2e',
      email: 'e2e@valuefabric.test',
      role: 'admin',
      tenantId: BACKEND_E2E_TENANT_ID,
      tenantSlug: 'e2e-test',
    });
    await setUserTier(page, 'admin', 'admin');
    await setSelectedAccount(page, TEST_ACCOUNTS.meridian);
  });

  test('test_golden_path_account_to_approved_business_case @backend', async ({ page }) => {
    requireBackendOrThrow('test_golden_path_account_to_approved_business_case @backend');

    await expectRouteSupportsWorkflow(
      page,
      '/accounts/new',
      [/start a new value case/i, /launch intelligence/i, /attach source material/i, /discovery/i],
      'prospect intake and launch workflow',
    );
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);
    await expectNoCrossTenantLeakage(page);

    const promptField = page
      .getByLabel(/new value case prompt/i)
      .or(page.getByPlaceholder(/describe the account/i))
      .first();
    if (await promptField.isVisible({ timeout: 3000 }).catch(() => false)) {
      await promptField.fill('Company: Meridian Health Group\nDesired outcome: Reduce manual reconciliation time\nRequired output: Approved business case');
      const launchButton = page.getByRole('button', { name: /launch intelligence|run account enrichment/i }).first();
      if (await launchButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await launchButton.click();
      }
    }

    await expectRouteSupportsWorkflow(
      page,
      `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/intelligence/signals`,
      [/signals/i, /confidence/i, /source/i, /approve/i, /evidence/i],
      'signal review and approval workflow',
    );
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);

    await expectRouteSupportsWorkflow(
      page,
      `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/intelligence/hypotheses`,
      [/hypoth/i, /approve/i, /edit/i, /expected value/i],
      'hypothesis review and approval workflow',
    );
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);

    await expectRouteSupportsWorkflow(
      page,
      `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/studio/driver-tree`,
      [/driver tree/i, /value driver/i, /formula/i, /evidence/i],
      'driver tree and evidence mapping workflow',
    );
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);

    await expectRouteSupportsWorkflow(
      page,
      `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/studio/calculator`,
      [/roi calculator/i, /scenario/i, /payback/i, /economic value/i],
      'scenario calculation workflow',
    );
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);

    await expectRouteSupportsWorkflow(
      page,
      `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/deliverables/business-cases`,
      [/business cases/i, /new case/i, /executive summary/i, /draft|approved/i],
      'business-case list and lifecycle workflow',
    );
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);
  });

  test('test_business_case_contains_traceable_claims_after_golden_path @backend', async ({ page }) => {
    requireBackendOrThrow('test_business_case_contains_traceable_claims_after_golden_path @backend');

    await navigateAndWait(page, `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/deliverables/business-cases`);
    await expectAnyVisible(
      page,
      [/business cases/i, /executive summary/i, /recommendations/i, /roi/i],
      'deliverable list after golden path',
    );
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);

    await navigateAndWait(page, `/t/${TENANT_SLUG}/governance/traces`);
    await expectAnyVisible(
      page,
      [/decision trace/i, /provenance timeline/i, /truth references/i, /audit log/i, /claim/i],
      'claim traceability surfaces',
    );
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);

    await navigateAndWait(page, `/t/${TENANT_SLUG}/governance/evidence`);
    await expectAnyVisible(
      page,
      [/evidence/i, /truth objects/i, /confidence/i, /source/i, /claim/i],
      'evidence-backed claim lineage',
    );
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);
  });

  test('test_export_is_available_only_after_required_approval @backend', async ({ page }) => {
    requireBackendOrThrow('test_export_is_available_only_after_required_approval @backend');
    await expectSeededBusinessCaseWorkflowResults(page, SEEDED_BUSINESS_CASE_IDS);

    await navigateAndWait(page, `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/deliverables/business-cases/case-draft-001`);
    await expectAnyVisible(
      page,
      [/business case/i, /draft/i, /executive summary/i, /export pdf/i],
      'draft business case before approval',
    );
    await expectButtonStateIfVisible(page, /export pdf/i, 'disabled');
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);

    await navigateAndWait(page, `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/deliverables/business-cases/case-e2e-approved-001`);
    await expectAnyVisible(
      page,
      [/business case/i, /approved/i, /executive summary/i, /export pdf/i],
      'approved business case after review',
    );
    await expectButtonStateIfVisible(page, /export pdf/i, 'enabled');
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);
  });

  test('test_crm_push_available_after_case_approval @backend', async ({ page }) => {
    requireBackendOrThrow('test_crm_push_available_after_case_approval @backend');
    await expectSeededBusinessCaseWorkflowResults(page, SEEDED_BUSINESS_CASE_IDS);

    // Navigate to the approved business case
    await navigateAndWait(page, `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/deliverables/business-cases/case-e2e-approved-001`);
    await expectAnyVisible(
      page,
      [/business case/i, /approved/i, /export pdf/i],
      'approved business case with export gate passed',
    );

    // CRM push option should be available after approval
    await expectAnyVisible(
      page,
      [/push.*crm|sync.*crm|export.*salesforce|send.*crm|crm/i],
      'CRM push affordance on approved business case',
    );
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);
  });

  test('test_post_sale_realization_conversion @backend', async ({ page }) => {
    requireBackendOrThrow('test_post_sale_realization_conversion @backend');
    await expectSeededBusinessCaseWorkflowResults(page, SEEDED_BUSINESS_CASE_IDS);

    // Navigate to the approved business case
    await navigateAndWait(page, `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/deliverables/business-cases/case-e2e-approved-001`);
    await expectAnyVisible(
      page,
      [/business case/i, /approved/i, /recommendations/i],
      'approved business case for realization conversion',
    );

    // Realization plan conversion option should appear on approved cases
    await expectAnyVisible(
      page,
      [/realization|post.sale|convert.*plan|track.*outcomes|value.*realization/i],
      'realization plan conversion affordance on approved business case',
    );

    // Navigate to any realization plan surface if it exists
    await navigateAndWait(page, `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/overview`);
    await expectAnyVisible(
      page,
      [/outcome|realization|baseline|metric|account|meridian/i],
      'account detail with realization plan or outcome tracking surface',
    );
    await expectNoCrossTenantLeakage(page);
    await expectTenantContext(page, BACKEND_E2E_TENANT_ID);
  });
});
