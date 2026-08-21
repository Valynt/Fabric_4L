/**
 * Journey 1 Created Account Backend-Integrated: Golden Path Handoff
 *
 * This test proves a newly created account, not the seeded Meridian account,
 * anchors account-scoped workspace routing after prospect setup.
 *
 * Tag: @backend
 */
import type { Page } from '@playwright/test';
import { journeyTest, expect, expectNoErrors } from '../helpers/journey-fixture';
import {
  expectAnyVisible,
  expectNoCrossTenantLeakage,
  expectTenantContext,
  requireBackendOrThrow,
} from '../helpers/validation-program';
import { BACKEND_E2E_TENANT_ID } from '../fixtures/auth-helpers';

const SEED_ACCOUNT_ID = 'acct-meridian-001';
const SEED_TENANT_ID = BACKEND_E2E_TENANT_ID;

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function extractAccountIdFromSignalsUrl(page: Page): string {
  const match = new URL(page.url()).pathname.match(/^\/intelligence\/([^/]+)\/signals$/);
  if (!match?.[1]) {
    throw new Error(`Expected created-account signals URL, received ${page.url()}`);
  }
  return decodeURIComponent(match[1]);
}

async function expectNoAccountScopeFailure(page: Page): Promise<void> {
  await expectNoErrors(page);
  await expect(page.getByText(/account not found/i).first()).not.toBeVisible({ timeout: 3000 });
  await expect(page.getByText(/select a valid account/i).first()).not.toBeVisible({ timeout: 3000 });
}

async function expectAccountScopedRoute(
  page: Page,
  path: string,
  accountId: string,
  evidencePatterns: Array<string | RegExp>,
  description: string,
): Promise<void> {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  await expect(page).toHaveURL(new RegExp(`/${escapeRegex(accountId)}(?:/|$|[?#])`));
  await expectNoAccountScopeFailure(page);
  await expectAnyVisible(page, evidencePatterns, description, 10000);
  await expectNoCrossTenantLeakage(page);
}

journeyTest.describe('@backend Created Account Golden Path Backend-Integrated', () => {
  journeyTest.setTimeout(120000);

  journeyTest.beforeEach(async () => {
    requireBackendOrThrow('created-account golden path');
  });

  journeyTest('GP-BI-CREATED-ACCOUNT: created account anchors downstream workflow routes', async ({ authedPage }) => {
    const suffix = Date.now();
    const accountName = `Created Account Golden Path ${suffix}`;
    const accountDomain = `created-account-golden-path-${suffix}.example`;

    await authedPage.goto('/accounts/new', { waitUntil: 'domcontentloaded' });
    await expect(authedPage).toHaveURL(/\/accounts\/new(?:[?#].*)?$/););

    const companyInput = authedPage.getByLabel(/company name/i).or(authedPage.getByPlaceholder(/company name/i)).first();
    const domainInput = authedPage.getByLabel(/website/i).or(authedPage.getByPlaceholder(/website/i)).first();
    const promptInput = authedPage.getByRole('textbox', { name: /new value case prompt/i }).first();

    await expect(companyInput).toBeVisible({ timeout: 10000 });
    await companyInput.fill(accountName);
    await companyInput.blur();

    await expect(domainInput).toBeVisible({ timeout: 10000 });
    await domainInput.fill(accountDomain);
    await domainInput.blur();

    if (await promptInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await promptInput.fill(
        [
          `Company: ${accountName}`,
          `Website: ${accountDomain}`,
          'Industry: Manufacturing',
          'Desired output:',
          '- Account brief',
          '- Value hypotheses',
          '- Executive summary',
        ].join('\n'),
      );
    }

    const submitBtn = authedPage.getByRole('button', { name: /launch intelligence/i }).first();
    await expect(submitBtn).toBeVisible({ timeout: 5000 });
    await submitBtn.click();

    await authedPage.waitForURL(/\/intelligence\/[^/]+\/signals(?:[?#].*)?$/, { timeout: 20000 });
    const createdAccountId = extractAccountIdFromSignalsUrl(authedPage);
    expect(createdAccountId).toBeTruthy();
    expect(createdAccountId).not.toBe(SEED_ACCOUNT_ID);
    expect(createdAccountId.startsWith('temp_')).toBe(false);
    await expectTenantContext(authedPage, SEED_TENANT_ID);

    await expectNoAccountScopeFailure(authedPage);
    await expectAnyVisible(
      authedPage,
      [new RegExp(escapeRegex(accountName), 'i'), /signals/i, /confidence/i, /source/i, /generating|loading/i],
      'created-account signals workspace',
      10000,
    );

    await authedPage.reload({ waitUntil: 'domcontentloaded' });
    await expect(authedPage).toHaveURL(new RegExp(`/intelligence/${escapeRegex(createdAccountId)}/signals`));
    await expectNoAccountScopeFailure(authedPage);
    await expectAnyVisible(
      authedPage,
      [new RegExp(escapeRegex(accountName), 'i'), /signals/i, /confidence/i, /source/i, /no signals/i],
      'created-account signals workspace after reload',
      10000,
    );

    await authedPage.goto(`/accounts/${createdAccountId}`, { waitUntil: 'domcontentloaded' });
    await expect(authedPage).toHaveURL(new RegExp(`/${escapeRegex(createdAccountId)}(?:/|$|[?#])`));
    await expectNoAccountScopeFailure(authedPage);
    await expect(
      authedPage
        .getByRole('row', { name: new RegExp(escapeRegex(accountName), 'i') })
        .or(authedPage.getByRole('heading', { name: new RegExp(escapeRegex(accountName), 'i') }))
        .first(),
    ).toBeVisible({ timeout: 30000 });
    await expectNoCrossTenantLeakage(authedPage);

    await expectAccountScopedRoute(
      authedPage,
      `/hypothesis/${createdAccountId}/hypothesis`,
      createdAccountId,
      [new RegExp(escapeRegex(accountName), 'i'), /hypoth/i, /value/i, /generate/i],
      'created-account hypothesis workspace',
    );

    await expectAccountScopedRoute(
      authedPage,
      `/drivers/${createdAccountId}/tree`,
      createdAccountId,
      [new RegExp(escapeRegex(accountName), 'i'), /driver/i, /value/i, /evidence/i],
      'created-account driver tree workspace',
    );

    await expectAccountScopedRoute(
      authedPage,
      `/calculator/${createdAccountId}/roi`,
      createdAccountId,
      [new RegExp(escapeRegex(accountName), 'i'), /roi calculator/i, /scenario/i, /payback/i],
      'created-account calculator workspace',
    );

    await expectAccountScopedRoute(
      authedPage,
      `/value-case/${createdAccountId}`,
      createdAccountId,
      [new RegExp(escapeRegex(accountName), 'i'), /value case/i, /business case/i, /generate/i],
      'created-account value case workspace',
    );

    await expectAccountScopedRoute(
      authedPage,
      `/realization/${createdAccountId}`,
      createdAccountId,
      [new RegExp(escapeRegex(accountName), 'i'), /realization/i, /outcome/i, /initiative/i, /baseline/i],
      'created-account realization workspace',
    );
  });
});
