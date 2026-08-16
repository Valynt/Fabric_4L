/**
 * Journey Test Fixture
 *
 * Extends the base Playwright test with a pre-configured environment
 * for chained user journey tests. Each journey test gets:
 *
 * - An authenticated session (admin by default, overridable)
 * - A selected account context
 * - The API harness installed (live or contract mode)
 * - Page objects for common pages
 *
 * Usage:
 *   import { journeyTest } from '../helpers/journey-fixture';
 *
 *   journeyTest('ingestion to value tree', async ({ authedPage, apiHarness }) => {
 *     // authedPage is already authenticated and has API harness installed
 *     await authedPage.goto('/home');
 *     // ...
 *   });
 *
 * IMPORTANT: The `addMocks` fixture depends on `authedPage` to guarantee that
 * `installApiHarness` (which registers DEFAULT_MOCKS) runs BEFORE any journey-
 * specific mocks are registered. Playwright routes use last-registered-first
 * priority, so journey mocks registered via `addMocks` will correctly override
 * the DEFAULT_MOCKS from the harness.
 */
import { test as base, Page, expect } from '@playwright/test';
import { seedAuthState, DEFAULT_TEST_USER, type TestUserInfo } from '../fixtures/auth-helpers';
import { setSelectedAccount, TEST_ACCOUNTS, type TestAccount } from '../fixtures/account-helpers';
import { setUserTier, type UserTier } from '../fixtures/tier-helpers';
import { addHarnessMocks, installApiHarness, isLiveMode, type MockEndpoint } from './api-harness';
import { attachUnexpectedErrorAudit } from '../support/unexpected-errors';

// Re-export for convenience
export { expect } from '@playwright/test';
export { isLiveMode } from './api-harness';

// ── Fixture Types ───────────────────────────────────────────────────────────

interface JourneyFixtures {
  /** A page that is already authenticated with the API harness installed */
  authedPage: Page;
  /** The test account that is pre-selected */
  testAccount: TestAccount;
  /** Function to change the user tier mid-test */
  switchTier: (tier: UserTier) => Promise<void>;
  /** Function to add additional API mocks mid-test */
  addMocks: (mocks: MockEndpoint[]) => Promise<void>;
  /** Whether the test is running against a live backend */
  isLive: boolean;
}

const unexpectedErrorAudits = new WeakMap<Page, ReturnType<typeof attachUnexpectedErrorAudit>>();

// ── Journey Test Definition ─────────────────────────────────────────────────

export const journeyTest = base.extend<JourneyFixtures>({
  testAccount: [TEST_ACCOUNTS.meridian, { option: true }],

  authedPage: async ({ page, testAccount }, use) => {
    // 1. Attach fail-closed browser/network error audit before any navigation.
    const audit = attachUnexpectedErrorAudit(page);
    unexpectedErrorAudits.set(page, audit);

    // 2. Install API harness before auth/tier/account helpers boot the app.
    await installApiHarness(page, {
      onUnhandledRequest: audit.recordUnhandledApiRequest,
    });

    let testError: unknown;
    try {
      // 3. Seed auth state
      await seedAuthState(page, DEFAULT_TEST_USER);

      // 4. Set admin tier (journey tests need full access by default)
      await setUserTier(page, 'admin', 'admin');

      // 5. Set account context
      await setSelectedAccount(page, testAccount);

      // 6. Provide the page to the test
      await use(page);
    } catch (e) {
      testError = e;
    }

    // 7. Fail closed on unexpected browser/network/test-environment errors.
    // Run the audit even when the test body failed so we don't swallow
    // console/HTTP errors that may explain the failure, but preserve the
    // original test error if an audit assertion would otherwise hide it.
    try {
      await audit.assertClean();
    } catch (auditError) {
      if (testError) {
        console.error('[journey-fixture] Unexpected errors observed during failing test:', auditError);
      } else {
        throw auditError;
      }
    } finally {
      unexpectedErrorAudits.delete(page);
      audit.teardown();
      // Keep API routes installed until Playwright disposes the page. Removing
      // them here lets late React Query retries escape to Vite's backend proxy.
    }

    if (testError) {
      throw testError;
    }
  },

  switchTier: async ({ page }, use) => {
    const fn = async (tier: UserTier) => {
      await setUserTier(page, tier, tier);
      await page.reload();
    };
    await use(fn);
  },

  // CRITICAL: `addMocks` depends on `authedPage` (not just `page`) to ensure
  // that installApiHarness has already run and registered DEFAULT_MOCKS before
  // any journey-specific mocks are added. This guarantees that journey mocks
  // are registered LAST and therefore take priority (Playwright last-registered-first).
  addMocks: async ({ authedPage }, use) => {
    const fn = async (mocks: MockEndpoint[]) => {
      const audit = unexpectedErrorAudits.get(authedPage);
      // Register on the harness catch-all first so /v1/ overrides cannot lose
      // to DEFAULT_MOCKS when Playwright route order is not last-wins.
      addHarnessMocks(authedPage, mocks);
      for (const mock of mocks) {
        const status = mock.status ?? 200;
        if (status >= 500) {
          audit?.recordExpectedHttp5xxPattern(mock.pattern);
        }
        if (status >= 400) {
          // Deliberate error responses produce two kinds of expected console
          // noise that must not trip the fail-closed audit:
          //   1. Chromium's "Failed to load resource: ... status of NNN" network log.
          //   2. The app's dev-mode telemetry logger ("[Fabric]" prefix), which
          //      records handled API failures on the error path under test.
          // Everything else (page errors, other console errors, unhandled
          // requests, unregistered 5xx) still fails the test.
          audit?.recordExpectedConsoleErrorPattern(
            new RegExp(`Failed to load resource: the server responded with a status of ${status}`),
          );
          audit?.recordExpectedConsoleErrorPattern(/^\[Fabric\]/);
        }
        await authedPage.route(mock.pattern, async (route) => {
          if (mock.delay) {
            await new Promise((resolve) => setTimeout(resolve, mock.delay));
          }
          await route.fulfill({
            status: mock.status ?? 200,
            contentType: 'application/json',
            body: JSON.stringify(mock.body),
          });
        });
      }
    };
    await use(fn);
  },

  isLive: async ({}, use) => {
    await use(isLiveMode());
  },
});

// ── Assertion Helpers ───────────────────────────────────────────────────────

/**
 * Build a canonical tenant-scoped path for the current auth environment.
 *
 * Mock-auth contract mode (VITE_ENABLE_MOCK_AUTH=true) authenticates every
 * user as the built-in demo tenant (slug "demo" — see MOCK_TENANT_SLUG in
 * src/contexts/AuthContextCompat.ts). Live backend mode seeds the e2e tenant
 * (slug "e2e-test" — see normalizeLiveUser in e2e/fixtures/auth-helpers.ts).
 *
 * Prefer legacy redirect routes (e.g. /intelligence/:accountId/:tabId,
 * /governance/*) when they exist; use this for routes that only exist in
 * canonical /t/:tenantSlug/... form or when you need query params, which the
 * legacy redirect does not preserve.
 */
export function tenantScopedPath(path: string): string {
  const slug = isLiveMode() ? 'e2e-test' : 'demo';
  return `/t/${slug}${path}`;
}

/**
 * Assert that the page navigated to the expected URL pattern.
 * Waits for navigation to complete before checking.
 */
export async function expectUrl(page: Page, pattern: string | RegExp): Promise<void> {
  if (typeof pattern === 'string') {
    await expect(page).toHaveURL(pattern);
  } else {
    await expect(page).toHaveURL(pattern);
  }
}

/**
 * Assert that a specific element is visible on the page.
 * Uses getByRole or getByText for accessibility-conscious selectors.
 */
export async function expectVisible(page: Page, text: string | RegExp): Promise<void> {
  await expect(page.getByText(text).first()).toBeVisible({ timeout: 10000 });
}

/**
 * Assert that the page does NOT contain a specific error message.
 * Useful for verifying that a page loaded successfully.
 */
export async function expectNoErrors(page: Page): Promise<void> {
  const errorPatterns = [
    /failed to load/i,
    /something went wrong/i,
    /error loading/i,
    /cannot read properties/i,
    /unexpected token/i,
  ];

  for (const pattern of errorPatterns) {
    const errorElement = page.getByText(pattern).first();
    await expect(errorElement).not.toBeVisible({ timeout: 3000 }).catch(() => {
      // If the element is visible, the test should fail with a clear message
      throw new Error(`Page contains error text matching: ${pattern}`);
    });
  }
}

/**
 * Wait for the page to finish loading.
 *
 * NOTE: `networkidle` is deliberately NOT used here. The Vite dev server
 * keeps a permanent HMR websocket open and several screens poll on
 * 2–5 s intervals, so `networkidle` never settles and always burns the
 * full timeout (15 s per navigation), pushing strict behavior tests past
 * the project timeout. Load-state + the explicit, polling `expect`
 * assertions in the tests provide the real readiness signal.
 */
export async function waitForPageReady(page: Page): Promise<void> {
  await page.waitForLoadState('load', { timeout: 15000 }).catch(() => {
    // 'load' can be slow on first Vite transform; the test's own assertions
    // poll for the actual content they need.
  });
}

/**
 * Navigate to a route and wait for it to be ready.
 */
export async function navigateAndWait(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  await waitForPageReady(page);
}
