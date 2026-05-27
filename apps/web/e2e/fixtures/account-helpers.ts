/**
 * Account Context Helpers for Playwright Contract Tests
 *
 * Provides utilities to set/clear the selected account context
 * in the browser. Account-scoped routes (intelligence/:accountId,
 * studio/:accountId) require an account to be selected before
 * the workspace tabs become accessible.
 *
 * Contract: The accountContextStore is a zustand store persisted
 *           to localStorage under the key 'fabric-account-context'.
 *
 * IMPORTANT: All localStorage operations require the page to be on a
 * same-origin URL first. These helpers ensure that.
 */
import { Page } from '@playwright/test';

export interface TestAccount {
  id: string;
  name: string;
  industry?: string;
  tier?: string;
}

/**
 * Canonical test accounts for deterministic testing.
 */
export const TEST_ACCOUNTS = {
  meridian: {
    id: 'acct-meridian-001',
    name: 'Meridian Automotive',
    industry: 'Manufacturing',
    tier: 'enterprise',
  } satisfies TestAccount,

  acme: {
    id: 'acct-acme-002',
    name: 'Acme Corp',
    industry: 'Technology',
    tier: 'mid-market',
  } satisfies TestAccount,

  globalFinance: {
    id: 'acct-gf-003',
    name: 'Global Finance Inc',
    industry: 'Financial Services',
    tier: 'enterprise',
  } satisfies TestAccount,
};

/**
 * Ensure the page is on a same-origin URL so localStorage is accessible.
 */
async function ensureSameOrigin(page: Page): Promise<void> {
  const url = page.url();
  if (url === 'about:blank' || url === '' || url === 'chrome://newtab/') {
    await page.goto('/login', { waitUntil: 'commit' });
  }
}

/**
 * Set the selected account in the zustand store via localStorage.
 * Must be called before navigating to account-scoped routes.
 */
export async function setSelectedAccount(page: Page, account: TestAccount): Promise<void> {
  await ensureSameOrigin(page);

  await page.evaluate((acct: TestAccount) => {
    // Must match zustand persist shape: only selectedAccountId is partialised
    const storeState = {
      state: {
        selectedAccountId: acct.id,
      },
      version: 0,
    };
    localStorage.setItem('fabric-account-context', JSON.stringify(storeState));
  }, account);
}

/**
 * Clear the selected account from the zustand store.
 */
export async function clearSelectedAccount(page: Page): Promise<void> {
  try {
    await page.evaluate(() => {
      localStorage.removeItem('fabric-account-context');
    });
  } catch {
    // Page may already be closed — safe to ignore
  }
}

/**
 * Get the currently selected account ID from the store.
 */
export async function getSelectedAccountId(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    const raw = localStorage.getItem('fabric-account-context');
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      return parsed?.state?.selectedAccountId ?? null;
    } catch {
      return null;
    }
  });
}

/**
 * Switch from one account to another.
 * This simulates the user clicking on a different account in the account switcher.
 */
export async function switchAccount(page: Page, fromAccount: TestAccount, toAccount: TestAccount): Promise<void> {
  await ensureSameOrigin(page);

  await page.evaluate((acct: TestAccount) => {
    const storeState = {
      state: {
        selectedAccountId: acct.id,
      },
      version: 0,
    };
    localStorage.setItem('fabric-account-context', JSON.stringify(storeState));
  }, toAccount);

  // Trigger a page reload to simulate the context switch
  await page.reload({ waitUntil: 'domcontentloaded' });
}

/**
 * Verify that the account context has been updated.
 * Returns true if the current selected account matches the expected account.
 */
export async function verifyAccountContext(page: Page, expectedAccount: TestAccount): Promise<boolean> {
  const currentAccountId = await getSelectedAccountId(page);
  return currentAccountId === expectedAccount.id;
}

/**
 * Clear all account-related data from localStorage to simulate a fresh context.
 * Useful for testing cross-account data isolation.
 */
export async function clearAccountData(page: Page): Promise<void> {
  try {
    await page.evaluate(() => {
      localStorage.removeItem('fabric-account-context');
      // Clear any cached account-specific data
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith('account-') || key.startsWith('acct-')) {
          localStorage.removeItem(key);
        }
      });
    });
  } catch {
    // Page may already be closed — safe to ignore
  }
}

/**
 * Simulate a multi-tenant scenario by setting tenant context.
 * This is used in conjunction with account switching for cross-tenant isolation tests.
 */
export async function setTenantContext(page: Page, tenantId: string, tenantSlug: string): Promise<void> {
  await ensureSameOrigin(page);

  await page.evaluate((ctx: { tenantId: string; tenantSlug: string }) => {
    localStorage.setItem('tenantId', ctx.tenantId);
    localStorage.setItem('tenantSlug', ctx.tenantSlug);
    sessionStorage.setItem('vf.auth.session.meta', JSON.stringify({
      tenantId: ctx.tenantId,
      tenantSlug: ctx.tenantSlug,
    }));
  }, { tenantId, tenantSlug });
}
