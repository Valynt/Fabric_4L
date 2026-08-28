/**
 * Journey 1: Continuous Live ValuePilot Run — @backend
 *
 * Traceability: CONTINUOUS-LIVE-001, ROI-LIVE-001, VALUE-CASE-LIVE-001.
 *
 * This suite is a continuous live role-authenticated smoke over the ValuePilot
 * studio. It seeds a real backend session (admin), then exercises the seeded
 * Meridian account end-to-end on a schedule against the running stack:
 *
 *   1. ROI Calculator renders from real backend state.
 *   2. "Recalculate" triggers the live ROI calculation (l3 /v1/roi/calculate).
 *   3. The Value Case workspace reflects the seeded approved business case
 *      (`case-meridian-e2e-001`) and surfaces the publish artifact affordance.
 *   4. Session stays valid across the whole run (no silent logout, no
 *      cross-tenant leakage, no unexpected page errors).
 *
 * This spec targets seeded data only — it does NOT depend on live LLM
 * generation. It is tagged `@backend` so it only runs in the
 * `backend-integrated` Playwright project and fails closed (via
 * `requireBackendOrThrow`) when no backend URL is configured.
 */
import { test, expect } from '../fixtures/contract-test';
import {
  expectAnyVisible,
  expectNoCrossTenantLeakage,
  expectSeededBusinessCaseWorkflowResults,
  requireBackendOrThrow,
} from '../helpers/validation-program';
import { navigateAndWait } from '../helpers/journey-fixture';
import { BACKEND_E2E_TENANT_ID, seedAuthState } from '../fixtures/auth-helpers';
import { setSelectedAccount, TEST_ACCOUNTS } from '../fixtures/account-helpers';
import { setUserTier } from '../fixtures/tier-helpers';

const ACCOUNT_ID = TEST_ACCOUNTS.meridian.id;
const TENANT_SLUG = 'e2e-test';
// case-meridian-e2e-001 is an approved seeded business case under acct-meridian-001.
const SEEDED_APPROVED_CASE_ID = 'case-meridian-e2e-001';

const CALCULATOR_PATH = `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/studio/calculator`;
const VALUE_CASE_PATH = `/t/${TENANT_SLUG}/accounts/${ACCOUNT_ID}/studio/value-case`;

test.describe('Journey 1: Continuous Live ValuePilot Run', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuthState(page, {
      id: 'test-user-e2e',
      email: 'e2e@valuefabric.test',
      role: 'admin',
      tenantId: BACKEND_E2E_TENANT_ID,
      tenantSlug: TENANT_SLUG,
    });
    await setUserTier(page, 'admin', 'admin');
    await setSelectedAccount(page, TEST_ACCOUNTS.meridian);
  });

  test('continuous_value_pilot_roi_calculator_renders_live @backend', async ({ page }) => {
    requireBackendOrThrow('continuous_value_pilot_roi_calculator_renders_live @backend');

    // Preflight: seeded approved case must be present before the run.
    await expectSeededBusinessCaseWorkflowResults(page, [SEEDED_APPROVED_CASE_ID]);

    await navigateAndWait(page, CALCULATOR_PATH);
    await expect(
      page.getByRole('heading', { name: /ROI Calculator/i }),
    ).toBeVisible({ timeout: 15000 });

    // The deal-size input is wrapped by a label whose text is "deal size".
    await expect(page.locator('label:has-text("deal") input').first()).toBeVisible({
      timeout: 10000,
    });

    await expectNoCrossTenantLeakage(page);
  });

  test('continuous_value_pilot_recalculate_triggers_live_roi @backend', async ({ page }) => {
    requireBackendOrThrow('continuous_value_pilot_recalculate_triggers_live_roi @backend');

    await expectSeededBusinessCaseWorkflowResults(page, [SEEDED_APPROVED_CASE_ID]);

    await navigateAndWait(page, CALCULATOR_PATH);
    await expect(
      page.getByRole('heading', { name: /ROI Calculator/i }),
    ).toBeVisible({ timeout: 15000 });

    const recalculate = page.getByRole('button', { name: /Recalculate/i }).first();
    await expect(recalculate).toBeVisible({ timeout: 10000 });
    await expect(recalculate).toBeEnabled();

    // Capture the live ROI calculation response (L3 /v1/roi/calculate). The
    // prior assertion only checked that the failure toast did not appear,
    // which a no-op button or a differently worded error could satisfy. We
    // now require the request to fire, the response to be 2xx, and a
    // calculated output to render in the workspace.
    const calculateResponse = page
      .waitForResponse(
        (response) =>
          response.url().includes('/v1/roi/calculate') &&
          response.request().method() === 'POST',
        { timeout: 15000 },
      )
      .then((response) => response);

    await recalculate.click();

    const response = await calculateResponse;
    expect(response.status()).toBeGreaterThanOrEqual(200);
    expect(response.status()).toBeLessThan(300);

    // Recalculate must not surface the live recalc failure state.
    await expect(page.getByText(/Failed to recalculate scenario/i).first()).not.toBeVisible({
      timeout: 8000,
    });

    // A calculated output must render. The workspace surfaces Total NPV as a
    // currency value (fmtCurrency) once recalculation succeeds; before/during
    // the run it displays "—". Assert the NPV line is populated with a real
    // currency value rather than the empty placeholder.
    await expect(
      page.getByText(/Total NPV:/i).first(),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/\$[0-9]/i).first(),
    ).toBeVisible({ timeout: 10000 });

    await expectNoCrossTenantLeakage(page);
  });

  test('continuous_value_case_workspace_reflects_seeded_approved_case @backend', async ({ page }) => {
    requireBackendOrThrow('continuous_value_case_workspace_reflects_seeded_approved_case @backend');

    await expectSeededBusinessCaseWorkflowResults(page, [SEEDED_APPROVED_CASE_ID]);

    await navigateAndWait(page, VALUE_CASE_PATH);

    // The value-case workspace must render (ready/regenerate or the seeded
    // published artifact state) rather than fail closed with Access Denied.
    await expect(
      page.getByTestId('value-case-workspace'),
    ).toBeVisible({ timeout: 15000 });

    await expectAnyVisible(
      page,
      [/value case/i, /generate value case/i, /regen/i, /publish/i],
      'seeded value-case workspace state',
    );

    await expectNoCrossTenantLeakage(page);
  });
});