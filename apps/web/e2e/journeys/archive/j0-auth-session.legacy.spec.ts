/**
 * Journey 0: Authentication & Session Lifecycle
 *
 * The entry-point journey. Validates the full auth lifecycle that every
 * other journey depends on:
 *
 *   1. Unauthenticated access is redirected to /login
 *   2. Login page renders with correct form elements
 *   3. Dev-bypass produces an authenticated session and lands on /home
 *   4. Authenticated shell renders (sidebar, navigation)
 *   5. Session persists across a full page reload
 *   6. Logout clears the session and redirects to /login
 *   7. Post-logout, protected routes redirect back to /login
 *
 * This journey uses the raw Playwright `test` (not `journeyTest`) because
 * it explicitly tests the unauthenticated and logout states — the
 * `journeyTest` fixture pre-seeds auth, which would defeat the purpose.
 *
 * Environment:
 *   - Contract mode only (no backend required — auth is localStorage-based)
 *   - Dev bypass button is only rendered when import.meta.env.DEV is true,
 *     which is always the case when running against the Vite dev server.
 *
 * Pass criteria:
 *   - All steps complete without console errors
 *   - Session tokens are correctly written and cleared from localStorage
 *   - Route guards enforce authentication on every protected route
 */

import { test, expect, type Page } from '../fixtures/contract-test';
import { seedAuthState, clearAuthState } from '../fixtures/auth-helpers';
import { clearUserTier } from '../fixtures/tier-helpers';

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Navigate to a route and wait for the DOM to settle. */
async function go(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle').catch(() => {
    // networkidle can be flaky on first load; domcontentloaded is sufficient
  });
}

/** Assert localStorage key is present and truthy. */
async function expectStorageKey(page: Page, key: string): Promise<void> {
  const value = await page.evaluate((k) => localStorage.getItem(k), key);
  expect(value, `Expected localStorage["${key}"] to be set`).toBeTruthy();
}

/** Assert localStorage key is absent or null. */
async function expectStorageKeyAbsent(page: Page, key: string): Promise<void> {
  const value = await page.evaluate((k) => localStorage.getItem(k), key);
  expect(value, `Expected localStorage["${key}"] to be cleared`).toBeNull();
}

// ── Test Suite ────────────────────────────────────────────────────────────────

test.describe('Journey 0: Authentication & Session Lifecycle', () => {
  test.afterEach(async ({ page }) => {
    // Clean up auth state so tests don't bleed into each other
    await clearAuthState(page).catch(() => {});
    await clearUserTier(page).catch(() => {});
  });

  // ── Step 1: Unauthenticated redirect ───────────────────────────────────────

  test('Step 1: Unauthenticated access to protected route redirects to /login', async ({ page }) => {
    // Ensure no session exists
    await go(page, '/');
    await page.evaluate(() => {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('userInfo');
    });

    // Attempt to access a protected route
    await go(page, '/home');

    // RouteGuard should redirect to /login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  // ── Step 2: Login page renders correctly ──────────────────────────────────

  test('Step 2: Login page renders all required form elements', async ({ page }) => {
    await go(page, '/login');

    // Heading
    await expect(page.getByTestId('login-heading')).toBeVisible();

    // SSO buttons (Apple and Google — no Microsoft)
    await expect(page.getByTestId('sso-apple')).toBeVisible();
    await expect(page.getByTestId('sso-google')).toBeVisible();

    // Email/password fields
    await expect(page.getByTestId('login-email')).toBeVisible();
    await expect(page.getByTestId('login-password')).toBeVisible();

    // Submit button
    await expect(page.getByTestId('login-submit')).toBeVisible();

    // Password visibility toggle
    await expect(page.getByTestId('password-toggle')).toBeVisible();

    // Sign-up link
    await expect(page.getByTestId('link-to-signup')).toHaveAttribute('href', '/signup');
  });

  // ── Step 3: Dev-bypass login ───────────────────────────────────────────────

  test('Step 3: Dev-bypass button creates session and navigates to /home', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });

    await go(page, '/login');

    // Dev bypass button is only rendered in DEV mode (Vite dev server)
    const bypassButton = page.getByRole('button', { name: /development bypass/i });
    await expect(bypassButton).toBeVisible({ timeout: 5000 });
    await bypassButton.click();

    // Should land on /home
    await expect(page).toHaveURL(/\/home/, { timeout: 10000 });

    // Session tokens must be written to localStorage
    await expectStorageKey(page, 'accessToken');
    await expectStorageKey(page, 'userInfo');

    // No console errors during login flow
    const criticalErrors = consoleErrors.filter(
      (e) => !e.includes('favicon') && !e.includes('ResizeObserver'),
    );
    expect(criticalErrors, `Unexpected console errors: ${criticalErrors.join(', ')}`).toHaveLength(0);
  });

  // ── Step 4: Authenticated shell renders ───────────────────────────────────

  test('Step 4: Authenticated shell renders sidebar and core navigation', async ({ page }) => {
    await go(page, '/login');
    await page.getByRole('button', { name: /development bypass/i }).click();
    await expect(page).toHaveURL(/\/home/, { timeout: 10000 });

    // The app shell should render a sidebar/nav with core workflow items
    const sidebar = page.locator('aside, nav[aria-label], [data-testid="sidebar"]').first();
    await expect(sidebar).toBeVisible({ timeout: 10000 });

    // Core navigation items visible to all tiers
    await expect(page.getByRole('link', { name: /^Home$/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /^Accounts$/i })).toBeVisible();

    // Home page content
    await expect(
      page.getByRole('heading', { name: /create a value case/i })
        .or(page.getByText(/value fabric/i).first()),
    ).toBeVisible({ timeout: 10000 });
  });

  // ── Step 5: Session persists across reload ────────────────────────────────

  test('Step 5: Session persists across a full page reload', async ({ page }) => {
    // Seed auth state directly (faster than going through the login UI)
    await go(page, '/login');
    await seedAuthState(page);

    // Navigate to a protected route
    await go(page, '/home');
    await expect(page).toHaveURL(/\/home/, { timeout: 10000 });

    // Reload the page
    await page.reload({ waitUntil: 'domcontentloaded' });

    // Should remain on /home — not redirected to /login
    await expect(page).toHaveURL(/\/home/, { timeout: 10000 });
    await expect(page).not.toHaveURL(/\/login/);

    // Session tokens should still be present
    await expectStorageKey(page, 'accessToken');
    await expectStorageKey(page, 'userInfo');
  });

  // ── Step 6: Logout clears session ─────────────────────────────────────────

  test('Step 6: Logout clears session and redirects to /login', async ({ page }) => {
    // Start authenticated
    await go(page, '/login');
    await page.getByRole('button', { name: /development bypass/i }).click();
    await expect(page).toHaveURL(/\/home/, { timeout: 10000 });

    // Trigger logout — try AppHeader dropdown first, fall back to sidebar.
    // The header trigger uses only stable selectors: accessible name or
    // data-testid. The sidebar "Sign Out" button is the reliable fallback.
    const logoutViaHeader = async () => {
      const userMenuTrigger = page
        .getByRole('button', { name: /account|profile|user menu/i })
        .or(page.locator('[data-testid="user-menu-trigger"]'));
      await userMenuTrigger.first().click({ timeout: 5000 });

      const logoutItem = page.getByRole('menuitem', { name: /log out/i });
      await expect(logoutItem).toBeVisible({ timeout: 3000 });
      await logoutItem.click();
    };

    const logoutViaSidebar = async () => {
      const signOutButton = page.getByRole('button', { name: /sign out/i });
      await expect(signOutButton).toBeVisible({ timeout: 5000 });
      await signOutButton.click();
    };

    // Try header dropdown first; fall back to sidebar button
    await logoutViaHeader().catch(() => logoutViaSidebar());

    // Should redirect to /login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    // Session must be cleared
    await expectStorageKeyAbsent(page, 'accessToken');
    await expectStorageKeyAbsent(page, 'userInfo');
  });

  // ── Step 7: Post-logout route guard ───────────────────────────────────────

  test('Step 7: After logout, protected routes redirect to /login', async ({ page }) => {
    // Seed then explicitly clear auth (simulates post-logout state)
    await go(page, '/login');
    await seedAuthState(page);
    await go(page, '/home');
    await expect(page).toHaveURL(/\/home/, { timeout: 10000 });

    // Clear session (simulate logout without UI)
    await page.evaluate(() => {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('userInfo');
      localStorage.removeItem('tenantId');
    });

    // Attempt to navigate to a protected route
    await go(page, '/accounts');

    // RouteGuard should redirect to /login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  // ── Step 8: Expired token is rejected ─────────────────────────────────────

  test('Step 8: Expired access token is cleared and session redirects to /login', async ({ page }) => {
    await go(page, '/');

    // Seed an expired JWT (exp in the past)
    await page.evaluate(() => {
      const expiredPayload = {
        exp: Math.floor(Date.now() / 1000) - 3600, // 1 hour ago
        iat: Math.floor(Date.now() / 1000) - 7200,
        sub: 'user-e2e-expired',
        tenant_id: 'tenant-e2e-001',
      };
      const token = `header.${btoa(JSON.stringify(expiredPayload))}.signature`;
      localStorage.setItem('accessToken', token);
      localStorage.setItem(
        'userInfo',
        JSON.stringify({
          id: 'user-e2e-expired',
          email: 'expired@valuefabric.test',
          role: 'analyst',
          tenantId: 'tenant-e2e-001',
          tenantSlug: 'e2e-test',
        }),
      );
    });

    // Reload to trigger AuthContext.initAuth() expiry check
    await page.reload({ waitUntil: 'domcontentloaded' });

    // Should redirect to /login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    // Expired token must be cleared
    await expectStorageKeyAbsent(page, 'accessToken');
  });
});
