/**
 * Account Context Helpers for Playwright Contract Tests
 *
 * Provides utilities to set/clear the selected account context
 * in the browser. Account-scoped routes (intelligence/:accountId,
 * studio/:accountId) require an account to be selected before
 * the workspace tabs become accessible.
 *
 * Contract: The accountContextStore is a zustand store persisted
 *           to the canonical versioned sessionStorage key.
 *
 * IMPORTANT: All storage operations require the page to be on a
 * same-origin URL first. These helpers ensure that.
 */
import { Page } from '@playwright/test';
import { ACCOUNT_CONTEXT_STORAGE_KEY, ACCOUNT_CONTEXT_STORAGE_VERSION } from '@fabric/platform-contract/stores';

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
    await page.goto('/sign-in', { waitUntil: 'commit' });
  }
}

/**
 * Set the selected account in the zustand store via sessionStorage.
 * Must be called before navigating to account-scoped routes.
 */
export async function setSelectedAccount(page: Page, account: TestAccount): Promise<void> {
  await ensureSameOrigin(page);

  await page.evaluate(({ acct, storageKey, storageVersion }) => {
    const authMeta = JSON.parse(sessionStorage.getItem('vf.auth.session.meta') ?? '{}');
    const fabricTenantId = authMeta.tenantId;
    if (typeof fabricTenantId !== 'string' || !fabricTenantId) throw new Error('verified Fabric tenant fixture required');
    // Must match zustand persist shape: only selectedAccountId is partialised
    const storeState = {
      state: {
        fabricTenantId, selectedAccountId: acct.id,
      },
      version: storageVersion,
    };
    sessionStorage.setItem(storageKey, JSON.stringify(storeState));
  }, { acct: account, storageKey: ACCOUNT_CONTEXT_STORAGE_KEY, storageVersion: ACCOUNT_CONTEXT_STORAGE_VERSION });
}

/**
 * Clear the selected account from the zustand store.
 */
export async function clearSelectedAccount(page: Page): Promise<void> {
  try {
    await page.evaluate(storageKey => sessionStorage.removeItem(storageKey), ACCOUNT_CONTEXT_STORAGE_KEY);
  } catch {
    // Page may already be closed — safe to ignore
  }
}

/**
 * Get the currently selected account ID from the store.
 */
export async function getSelectedAccountId(page: Page): Promise<string | null> {
  return page.evaluate(storageKey => {
    const raw = sessionStorage.getItem(storageKey);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      return parsed?.state?.selectedAccountId ?? null;
    } catch {
      return null;
    }
  }, ACCOUNT_CONTEXT_STORAGE_KEY);
}

/**
 * Switch from one account to another.
 * This simulates the user clicking on a different account in the account switcher.
 */
export async function switchAccount(page: Page, fromAccount: TestAccount, toAccount: TestAccount): Promise<void> {
  await ensureSameOrigin(page);

  const currentUrl = page.url();
  const nextUrl = currentUrl.includes(encodeURIComponent(fromAccount.id)) || currentUrl.includes(fromAccount.id)
    ? currentUrl.replaceAll(encodeURIComponent(fromAccount.id), encodeURIComponent(toAccount.id)).replaceAll(fromAccount.id, toAccount.id)
    : null;

  await page.evaluate(({ acct, storageKey, storageVersion }) => {
    const authMeta = JSON.parse(sessionStorage.getItem('vf.auth.session.meta') ?? '{}');
    const fabricTenantId = authMeta.tenantId;
    if (typeof fabricTenantId !== 'string' || !fabricTenantId) throw new Error('verified Fabric tenant fixture required');
    const storeState = {
      state: {
        fabricTenantId, selectedAccountId: acct.id,
      },
      version: storageVersion,
    };
    sessionStorage.setItem(storageKey, JSON.stringify(storeState));
  }, { acct: toAccount, storageKey: ACCOUNT_CONTEXT_STORAGE_KEY, storageVersion: ACCOUNT_CONTEXT_STORAGE_VERSION });

  // Trigger navigation/reload to simulate the context switch. When already on
  // an account-scoped route, keep the same workspace tab but replace the
  // account id so the route, guard query, and selected context move together.
  if (nextUrl) {
    await page.goto(nextUrl, { waitUntil: 'domcontentloaded' });
  } else {
    await page.reload({ waitUntil: 'domcontentloaded' });
  }
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
    await page.evaluate(storageKey => {
      sessionStorage.removeItem(storageKey);
      // Clear any cached account-specific data
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith('account-') || key.startsWith('acct-')) {
          localStorage.removeItem(key);
        }
      });
    }, ACCOUNT_CONTEXT_STORAGE_KEY);
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

    const userInfoRaw = localStorage.getItem('userInfo');
    let userInfo: Record<string, unknown> | null = null;
    if (userInfoRaw) {
      try {
        userInfo = JSON.parse(userInfoRaw) as Record<string, unknown>;
        userInfo.tenantId = ctx.tenantId;
        userInfo.tenantSlug = ctx.tenantSlug;
        localStorage.setItem('userInfo', JSON.stringify(userInfo));
      } catch {
        userInfo = null;
      }
    }

    sessionStorage.setItem('vf.auth.session.meta', JSON.stringify({
      tenantId: ctx.tenantId,
      tenantSlug: ctx.tenantSlug,
      ...(userInfo ? { user: userInfo } : {}),
    }));
  }, { tenantId, tenantSlug });
}
