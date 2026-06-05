/**
 * Journey 0: Authentication & Session Lifecycle — Clerk Mode
 *
 * Behavior-First Test Contract
 *
 * This file is the executable definition of how Clerk authentication MUST behave
 * in this repository. Every test encodes either:
 *   1. An intended allowed behavior (positive), or
 *   2. An intended denied behavior (negative)
 *
 * Operating Principle: No critical auth behavior exists unless it is tested.
 *
 * Auth Mode:
 *   - The app runs in Clerk mode when VITE_AUTH_PROVIDER=clerk.
 *   - In this mode, legacy localStorage-based auth is NOT authoritative.
 *   - Clerk's useAuth()/useOrganization() hooks govern all route guards.
 *
 * Intended Behavior (Allowed):
 *   - Unauthenticated users hitting any protected route are redirected to /sign-in.
 *   - The /sign-in route renders Clerk's SignIn component with identifier + password fields.
 *   - Clerk JavaScript loads without CSP or network errors.
 *   - The legacy /login route does not render a functional legacy auth form.
 *   - The /signin shorthand redirects to /sign-in.
 *
 * Intended Behavior (Denied):
 *   - Legacy localStorage tokens (accessToken, userInfo) do NOT bypass Clerk auth.
 *   - The legacy dev-bypass button is NOT available on the Clerk sign-in page.
 *   - Unauthenticated direct navigation to /home, /workspaces, /onboarding is blocked.
 *
 * Test Categories:
 *   - Route Guard Contract: Redirect behavior for unauthenticated users.
 *   - Sign-In Page Contract: Clerk UI structure and error-free loading.
 *   - Legacy Auth Denial: Legacy auth mechanisms are inaccessible or ineffective.
 *   - CSP & Security Contract: Clerk domains are permitted; no unsafe fallbacks.
 *
 * Environment:
 *   - Contract mode (no backend required).
 *   - Requires VITE_AUTH_PROVIDER=clerk and a valid Clerk publishable key.
 *   - Tests that require a real Clerk session are skipped when credentials are absent
 *     (see: testAuthenticatedShell).
 */

import { test, expect, type Page } from '@playwright/test';

// ── Helpers ──────────────────────────────────────────────────────────────────

async function go(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle').catch(() => {
    // networkidle can be flaky with Clerk's async bootstrap; domcontentloaded is sufficient
  });
}

/**
 * Collect console errors and warnings during a test flow.
 * Returns a function that asserts no critical errors occurred.
 */
function captureConsole(page: Page) {
  const errors: string[] = [];
  const warnings: string[] = [];

  const onConsole = (msg: { type(): string; text(): string }) => {
    const text = msg.text();
    if (msg.type() === 'error') errors.push(text);
    if (msg.type() === 'warning') warnings.push(text);
  };

  page.on('console', onConsole);

  return {
    assertNoCriticalErrors: (allowList: string[] = []) => {
      page.off('console', onConsole);
      const critical = errors.filter(
        (e) =>
          !e.includes('favicon') &&
          !e.includes('ResizeObserver') &&
          !allowList.some((allowed) => e.includes(allowed)),
      );
      expect(
        critical,
        `Unexpected console errors: ${critical.join('; ')}`,
      ).toHaveLength(0);
    },
    get errors() {
      return [...errors];
    },
    get warnings() {
      return [...warnings];
    },
  };
}

// ── Route Guard Contract ─────────────────────────────────────────────────────

test.describe('Route Guard Contract', () => {
  test.afterEach(async ({ page }) => {
    // Clean Clerk session state between tests
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    }).catch(() => {});
  });

  test('unauthenticated / redirects to /sign-in', async ({ page }) => {
    await go(page, '/');
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  test('unauthenticated /home redirects to /sign-in', async ({ page }) => {
    await go(page, '/home');
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  test('unauthenticated /workspaces redirects to /sign-in', async ({ page }) => {
    await go(page, '/workspaces');
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  test('unauthenticated /onboarding redirects to /sign-in', async ({ page }) => {
    await go(page, '/onboarding');
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  test('unauthenticated /accounts/new redirects to /sign-in', async ({ page }) => {
    await go(page, '/accounts/new');
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  test('unauthenticated /personal/profile redirects to /sign-in', async ({ page }) => {
    await go(page, '/personal/profile');
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });

  test('/signin shorthand redirects to /sign-in', async ({ page }) => {
    await go(page, '/signin');
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });
});

// ── Sign-In Page Contract ────────────────────────────────────────────────────

test.describe('Sign-In Page Contract', () => {
  test('Clerk SignIn component renders without console errors', async ({ page }) => {
    const consoleCapture = captureConsole(page);

    await go(page, '/sign-in');

    // Wait for Clerk to bootstrap its UI
    await page.waitForSelector('input[name="identifier"], input[type="email"]', {
      timeout: 15000,
      state: 'visible',
    });

    // The Clerk component should be in the DOM
    const clerkRoot = page.locator('.cl-rootBox, [data-clerk-component], .cl-signIn-root').first();
    await expect(clerkRoot).toBeVisible();

    // Allow the expected Clerk dev-key warning
    consoleCapture.assertNoCriticalErrors([
      'Clerk: Clerk has been loaded with development keys',
      'Clerk: "useOrganization" requires',
    ]);
  });

  test('sign-in page has identifier input', async ({ page }) => {
    await go(page, '/sign-in');
    const identifierInput = page.locator('input[name="identifier"], input[type="email"]').first();
    await expect(identifierInput).toBeVisible({ timeout: 15000 });
  });

  test('sign-in page has password input', async ({ page }) => {
    await go(page, '/sign-in');
    // Clerk may show password field immediately or after identifier entry.
    // Wait for the form to settle, then check for password presence.
    await page.waitForTimeout(1000);
    const passwordInput = page.locator('input[name="password"], input[type="password"]').first();
    await expect(passwordInput).toBeVisible({ timeout: 15000 });
  });

  test('sign-in page has a submit button', async ({ page }) => {
    await go(page, '/sign-in');
    await page.waitForSelector('input[name="identifier"], input[type="email"]', {
      timeout: 15000,
      state: 'visible',
    });
    const submitButton = page.locator('button[type="submit"], button.cl-formButtonPrimary').first();
    await expect(submitButton).toBeVisible();
  });

  test('sign-in page has a link to sign-up', async ({ page }) => {
    await go(page, '/sign-in');
    await page.waitForSelector('input[name="identifier"], input[type="email"]', {
      timeout: 15000,
      state: 'visible',
    });
    const signUpLink = page.locator('a[href*="sign-up"], a[href*="signup"]').first();
    await expect(signUpLink).toBeVisible();
  });

  test('sign-in page title contains "Sign in"', async ({ page }) => {
    await go(page, '/sign-in');
    await expect(page).toHaveTitle(/sign in/i);
  });

  test('no CSP errors when loading Clerk scripts', async ({ page }) => {
    const cspErrors: string[] = [];
    page.on('console', (msg) => {
      const text = msg.text();
      if (
        msg.type() === 'error' &&
        (text.includes('Content-Security-Policy') || text.includes('csp'))
      ) {
        cspErrors.push(text);
      }
    });

    page.on('pageerror', (err) => {
      const text = err.message;
      if (text.includes('Content-Security-Policy') || text.includes('csp')) {
        cspErrors.push(text);
      }
    });

    await go(page, '/sign-in');
    await page.waitForTimeout(2000);

    expect(
      cspErrors,
      `CSP errors detected while loading Clerk: ${cspErrors.join('; ')}`,
    ).toHaveLength(0);
  });
});

// ── Legacy Auth Denial Contract ──────────────────────────────────────────────

test.describe('Legacy Auth Denial Contract', () => {
  test('legacy /login route does not render legacy auth form', async ({ page }) => {
    await go(page, '/login');

    // In Clerk mode, /login should either redirect away or not show the legacy form.
    // We assert that the legacy form elements are NOT present.
    const legacyEmail = page.locator('[data-testid="login-email"]');
    const legacyPassword = page.locator('[data-testid="login-password"]');
    const legacySubmit = page.locator('[data-testid="login-submit"]');

    await expect(legacyEmail).toHaveCount(0);
    await expect(legacyPassword).toHaveCount(0);
    await expect(legacySubmit).toHaveCount(0);
  });

  test('dev bypass button is NOT present on Clerk sign-in page', async ({ page }) => {
    await go(page, '/sign-in');
    await page.waitForSelector('input[name="identifier"], input[type="email"]', {
      timeout: 15000,
      state: 'visible',
    });

    const bypassButton = page.getByRole('button', { name: /development bypass/i });
    await expect(bypassButton).toHaveCount(0);
  });

  test('legacy localStorage tokens do NOT bypass Clerk route guards', async ({ page }) => {
    // Seed legacy auth state (the old localStorage-based auth)
    await go(page, '/');
    await page.evaluate(() => {
      const payload = {
        exp: Math.floor(Date.now() / 1000) + 86400,
        iat: Math.floor(Date.now() / 1000),
        sub: 'user-e2e-legacy',
        tenant_id: 'tenant-e2e-001',
      };
      const token = `header.${btoa(JSON.stringify(payload))}.signature`;
      localStorage.setItem('accessToken', token);
      localStorage.setItem(
        'userInfo',
        JSON.stringify({
          id: 'user-e2e-legacy',
          email: 'legacy@valuefabric.test',
          role: 'admin',
          tenantId: 'tenant-e2e-001',
          tenantSlug: 'e2e-test',
        }),
      );
      localStorage.setItem('tenantId', 'tenant-e2e-001');
      sessionStorage.setItem(
        'vf.auth.session.meta',
        JSON.stringify({
          user: {
            id: 'user-e2e-legacy',
            email: 'legacy@valuefabric.test',
            role: 'admin',
            tenantId: 'tenant-e2e-001',
            tenantSlug: 'e2e-test',
          },
          tenantId: 'tenant-e2e-001',
        }),
      );
    });

    // Attempt to access a protected route
    await go(page, '/home');

    // Clerk route guards MUST ignore legacy tokens and redirect to /sign-in
    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });
});

// ── Clerk Bootstrap Contract ─────────────────────────────────────────────────

test.describe('Clerk Bootstrap Contract', () => {
  test('Clerk JavaScript loads and initializes without fatal errors', async ({ page }) => {
    const fatalErrors: string[] = [];
    page.on('pageerror', (err) => {
      fatalErrors.push(err.message);
    });

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        fatalErrors.push(msg.text());
      }
    });

    await go(page, '/sign-in');

    // Wait for Clerk to be available on window
    const clerkLoaded = await page.waitForFunction(
      () => {
        // @ts-expect-error Clerk may attach to window
        return typeof window.Clerk !== 'undefined';
      },
      { timeout: 15000 },
    );

    expect(clerkLoaded).toBeTruthy();

    // No fatal errors during Clerk bootstrap
    const nonFatal = fatalErrors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('ResizeObserver') &&
        !e.includes('Clerk has been loaded with development keys') &&
        !e.includes('useOrganization') &&
        !e.includes('clerk-telemetry'),
    );
    expect(
      nonFatal,
      `Fatal errors during Clerk bootstrap: ${nonFatal.join('; ')}`,
    ).toHaveLength(0);
  });

  test('Clerk publishable key is present and well-formed', async ({ page }) => {
    await go(page, '/sign-in');

    const publishableKey = await page.evaluate(() => {
      // @ts-expect-error Accessing Vite env at runtime
      return import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
    });

    // The key must be present and match pk_test_* or pk_live_* pattern.
    // An empty key means Clerk components may render in a degraded state.
    expect(
      publishableKey,
      'VITE_CLERK_PUBLISHABLE_KEY must be set when VITE_AUTH_PROVIDER=clerk',
    ).toBeTruthy();
    expect(publishableKey).toMatch(/^pk_(test|live)_[A-Za-z0-9]+$/);
  });
});

// ── Cross-Origin & Security Contract ─────────────────────────────────────────

test.describe('Security Contract', () => {
  test('no unexpected third-party script errors on auth pages', async ({ page }) => {
    const thirdPartyErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Flag errors from unknown domains
        if (
          text.includes('clerk') &&
          !text.includes('accounts.dev') &&
          !text.includes('clerk-telemetry')
        ) {
          thirdPartyErrors.push(text);
        }
      }
    });

    await go(page, '/sign-in');
    await page.waitForTimeout(2000);

    expect(thirdPartyErrors).toHaveLength(0);
  });
});

// ── Session State Contract (requires Clerk credentials) ──────────────────────

test.describe('Authenticated Session Contract', () => {
  test.skip(
    true,
    'Authenticated session tests require a Clerk testing token. ' +
      'Enable by setting CLERK_TESTING_TOKEN and removing this skip. ' +
      'See: https://clerk.com/docs/testing/playwright',
  );

  test('authenticated user navigates to /home without redirect', async ({ page }) => {
    // Placeholder for when Clerk testing token is available.
    // This test should use setupClerkTestingToken() from @clerk/testing
    // and perform a real sign-in flow or session injection.
    await go(page, '/home');
    await expect(page).toHaveURL(/\/home/, { timeout: 10000 });
  });

  test('authenticated shell renders sidebar and navigation', async ({ page }) => {
    await go(page, '/home');
    const sidebar = page.locator('aside, nav[aria-label], [data-testid="sidebar"]').first();
    await expect(sidebar).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('link', { name: /^Home$/i })).toBeVisible();
  });

  test('sign-out clears session and redirects to /sign-in', async ({ page }) => {
    // This test requires an authenticated session.
    // After signing out, protected routes must redirect to /sign-in.
    await go(page, '/home');
    await expect(page).toHaveURL(/\/home/, { timeout: 10000 });

    // Trigger sign-out via UserButton or equivalent
    const userButton = page.locator('.cl-userButtonTrigger').first();
    await userButton.click();
    const signOutItem = page.getByRole('menuitem', { name: /sign out/i });
    await signOutItem.click();

    await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
  });
});
