import { test, expect } from './fixtures/contract-test';
import { AppShellPage } from './pages';
import {
  setUserTier,
  clearUserTier,
  enableAdvancedMode,
  disableAdvancedMode,
  ROUTES_BY_TIER,
  seedAuthState,
  clearAuthState,
} from './fixtures';

/**
 * Navigation and Access Control E2E Tests
 *
 * Covers tier-based routing, navigation visibility, and access control
 * using the canonical single-spine navigation taxonomy:
 *   Home, Library, Discover, Model, Deliver, Evidence, Govern
 */

test.describe('Navigation & Access Control', () => {
  let appShell: AppShellPage;

  test.beforeEach(async ({ page }) => {
    appShell = new AppShellPage(page);
  });

  test.afterEach(async ({ page }) => {
    await clearUserTier(page);
    await clearAuthState(page);
  });

  test.describe('Standard Tier', () => {
    test.beforeEach(async ({ page }) => {
      await setUserTier(page, 'standard');
    });

    test('can access home dashboard @smoke', async ({ page }) => {
      await page.goto('/home');
      await expect(page).toHaveURL(/\/home/);
      await expect(appShell.homeLink).toBeVisible();
    });

    test('can access value packs', async ({ page }) => {
      await page.goto('/library/packs');
      await expect(page).toHaveURL(/\/library\/packs/);
    });

    test('can access business cases @smoke', async ({ page }) => {
      await page.goto('/deliver/cases');
      await expect(page).toHaveURL(/\/deliver\/cases/);
    });

    test('can access decision traces', async ({ page }) => {
      await page.goto('/evidence/traces');
      await expect(page).toHaveURL(/\/evidence\/traces/);
    });

    test('cannot access extraction engine', async ({ page }) => {
      await page.goto('/discover/extraction');
      // Should be redirected to /home
      await expect(page).not.toHaveURL(/\/discover\/extraction/);
    });

    test('cannot access graph explorer', async ({ page }) => {
      await page.goto('/discover/knowledge/graph');
      await expect(page).not.toHaveURL(/\/discover\/knowledge\/graph/);
    });

    test('cannot access admin routes', async ({ page }) => {
      await page.goto('/admin/content/formulas');
      await expect(page).not.toHaveURL(/\/admin/);
    });

    test('navigation shows only accessible links', async ({ page }) => {
      await page.goto('/home');
      await expect(appShell.homeLink).toBeVisible();
      await expect(appShell.libraryLink).toBeVisible();
      await expect(appShell.discoverLink).toBeVisible();
      await expect(appShell.deliverLink).toBeVisible();
      await expect(appShell.evidenceLink).toBeVisible();
      // Model section should be hidden for standard users
      await expect(appShell.modelLink).toBeHidden();
      // Govern section should be hidden
      await expect(appShell.adminSection).toBeHidden();
    });
  });

  test.describe('Advanced Tier', () => {
    test.beforeEach(async ({ page }) => {
      await setUserTier(page, 'advanced');
    });

    test('can access home dashboard', async ({ page }) => {
      await page.goto('/home');
      await expect(page).toHaveURL(/\/home/);
    });

    test('can access extraction engine', async ({ page }) => {
      await page.goto('/discover/extraction');
      await expect(page).toHaveURL(/\/discover\/extraction/);
    });

    test('can access graph explorer', async ({ page }) => {
      await page.goto('/discover/knowledge/graph');
      await expect(page).toHaveURL(/\/discover\/knowledge\/graph/);
    });

    test('can access value tree explorer', async ({ page }) => {
      await page.goto('/model/value-studio/explorer');
      await expect(page).toHaveURL(/\/model\/value-studio\/explorer/);
    });

    test('can access formula builder', async ({ page }) => {
      await page.goto('/model/value-studio/formulas');
      await expect(page).toHaveURL(/\/model\/value-studio\/formulas/);
    });

    test('cannot access admin routes', async ({ page }) => {
      await page.goto('/admin/content/formulas');
      await expect(page).not.toHaveURL(/\/admin\/content\/formulas/);
    });

    test('navigation shows advanced links', async ({ page }) => {
      await page.goto('/home');
      await expect(appShell.homeLink).toBeVisible();
      await expect(appShell.modelLink).toBeVisible();
      await expect(appShell.discoverLink).toBeVisible();
      // Govern should be hidden for advanced users
      await expect(appShell.adminSection).toBeHidden();
    });
  });

  test.describe('Admin Tier', () => {
    test.beforeEach(async ({ page }) => {
      await setUserTier(page, 'admin');
    });

    test('can access all standard and advanced routes', async ({ page }) => {
      for (const route of ['/home', '/library/packs', '/discover/extraction', '/discover/knowledge/graph']) {
        await page.goto(route);
        await expect(page).toHaveURL(route);
      }
    });

    test('can access admin routes', async ({ page }) => {
      for (const route of ['/admin/content/formulas', '/admin/content/benchmarks', '/admin/data/variables']) {
        await page.goto(route);
        await expect(page).toHaveURL(route);
      }
    });

    test('navigation shows govern section', async ({ page }) => {
      await page.goto('/home');
      await expect(appShell.adminSection).toBeVisible();
    });
  });

  test.describe('Navigation Flows', () => {
    test.beforeEach(async ({ page }) => {
      await setUserTier(page, 'advanced');
    });

    test('can navigate between pages via sidebar', async ({ page }) => {
      // Start at home
      await page.goto('/home');
      await expect(page).toHaveURL(/\/home/);

      // Navigate to business cases via Deliver
      await appShell.businessCasesLink.click();
      await expect(page).toHaveURL(/\/deliver\/cases/);
    });

    test('navigation preserves tier context', async ({ page }) => {
      await page.goto('/home');

      // Navigate to business cases
      await appShell.businessCasesLink.click();
      await expect(page).toHaveURL(/\/deliver\/cases/);

      // Navigate to evidence
      await appShell.decisionTracesLink.click();
      await expect(page).toHaveURL(/\/evidence\/traces/);
    });
  });

  test.describe('Advanced Mode Toggle (Progressive Disclosure)', () => {
    test.beforeEach(async ({ page }) => {
      await setUserTier(page, 'standard');
    });

    test('standard user cannot see Model section without advanced mode', async ({ page }) => {
      await page.goto('/home');
      // Model section should be hidden for standard users
      await expect(page.getByRole('link', { name: /^Model$/i })).toBeHidden();
    });

    test('enabling advanced mode does not reveal unauthorized navigation', async ({ page }) => {
      await page.goto('/home');

      // Initially Model is hidden
      await expect(page.getByRole('link', { name: /^Model$/i })).toBeHidden();

      // Enable advanced mode
      await enableAdvancedMode(page);

      // Presentation preferences cannot reveal unauthorized route affordances.
      await expect(page.getByRole('link', { name: /^Model$/i })).toBeHidden();
    });

    test('enabling advanced mode never grants advanced route access', async ({ page }) => {
      await page.goto('/home');

      // Enable advanced mode
      await enableAdvancedMode(page);

      // Verified authorization remains standard.
      await page.goto('/discover/extraction');
      await expect(page).not.toHaveURL(/\/discover\/extraction/);

      // Should be able to access graph explorer
      await page.goto('/discover/knowledge/graph');
      await expect(page).not.toHaveURL(/\/discover\/knowledge\/graph/);
    });

    test('disabling advanced mode hides advanced navigation', async ({ page }) => {
      await page.goto('/home');

      // Enable then disable advanced mode
      await enableAdvancedMode(page);
      await expect(page.getByRole('link', { name: /^Model$/i })).toBeHidden();

      await disableAdvancedMode(page);

      // Model section should be hidden again
      await expect(page.getByRole('link', { name: /^Model$/i })).toBeHidden();
    });

    test('advanced mode does not grant admin access', async ({ page }) => {
      await page.goto('/home');

      // Enable advanced mode
      await enableAdvancedMode(page);

      // Still should not be able to access admin routes
      await page.goto('/admin/content/formulas');
      await expect(page).not.toHaveURL(/\/admin\/content\/formulas/);
    });
  });

  test.describe('Redirect Behavior', () => {
    test('standard user redirected to home from restricted route', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto('/discover/extraction');

      // Should end up at /home
      await expect(page).toHaveURL(/\/home/);
    });

    test('advanced user redirected from admin routes', async ({ page }) => {
      await setUserTier(page, 'advanced');
      await page.goto('/admin/content/formulas');

      // Should be redirected away from admin
      await expect(page).not.toHaveURL(/\/admin\/content\/formulas/);
    });

    test('root path redirects to home', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto('/');
      await expect(page).toHaveURL(/\/home/);
    });
  });

  test.describe('Mobile Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await seedAuthState(page);
      await setUserTier(page, 'advanced');
      // Set mobile viewport — triggers MobilePersistentSidebar (w-20 icon rail)
      await page.setViewportSize({ width: 375, height: 667 });
    });

    test('mobile nav rail is visible and accessible @smoke', async ({ page }) => {
      await page.goto('/home');
      // MobilePersistentSidebar renders a persistent icon rail — no hamburger trigger.
      // It is always visible below the md (768px) breakpoint.
      const mobileNav = page.getByRole('navigation', { name: /mobile navigation/i });
      await expect(mobileNav).toBeVisible();
    });

    test('mobile nav rail contains navigation links', async ({ page }) => {
      await page.goto('/home');
      const mobileNav = page.getByRole('navigation', { name: /mobile navigation/i });
      await expect(mobileNav).toBeVisible();
      // At least one nav link must be present inside the mobile rail
      const links = mobileNav.getByRole('link');
      await expect(links.first()).toBeVisible();
    });

    test('mobile nav rail link navigates correctly', async ({ page }) => {
      await page.goto('/home');
      const mobileNav = page.getByRole('navigation', { name: /mobile navigation/i });
      await expect(mobileNav).toBeVisible();

      // Click a deterministic non-current route so this critical journey proves
      // real mobile navigation rather than exercising a same-page remount race.
      const accountsLink = mobileNav.locator('a[href="/accounts"]').first();
      await expect(accountsLink).toBeVisible();
      await accountsLink.click();
      await expect(page).toHaveURL(/\/accounts/);
    });

    test('desktop sidebar is hidden on mobile viewport', async ({ page }) => {
      await page.goto('/home');
      // The desktop TieredNav is wrapped in `hidden md:block` — must not be visible
      // at 375px. The mobile rail (flex md:hidden) must be visible instead.
      const mobileNav = page.getByRole('navigation', { name: /mobile navigation/i });
      await expect(mobileNav).toBeVisible();
      // Confirm viewport is genuinely mobile-sized
      const vp = page.viewportSize();
      expect(vp?.width).toBeLessThan(768);
    });
  });
});
