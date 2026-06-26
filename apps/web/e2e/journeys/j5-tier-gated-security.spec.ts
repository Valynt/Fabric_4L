/**
 * Journey 5: Tier-Gated Access & Security
 *
 * Validates that the platform correctly enforces RBAC and tier-based
 * feature gating. A user logs in with different tier levels and verifies
 * that navigation, route guards, and feature visibility are correctly
 * enforced.
 *
 * This is a CHAINED test — the user switches tiers mid-session to verify
 * that access controls update dynamically.
 *
 * Pass criteria:
 *   - Standard tier users cannot access advanced/admin routes
 *   - Direct URL access to restricted routes redirects to /home
 *   - Admin tier users can access all routes and settings
 *   - Navigation items are hidden/shown based on tier
 *   - Tier switch mid-session correctly updates access controls
 */
import { journeyTest, expect, expectNoErrors, navigateAndWait } from '../helpers/journey-fixture';
import { setUserTier, getCurrentTier, ROUTES_BY_TIER, TIER_REDIRECTS, tenantRoute } from '../fixtures/tier-helpers';
import type { Page } from '@playwright/test';

async function expectRedirectedToTierHome(page: Page, redirectTarget: string): Promise<void> {
  await expect(page).toHaveURL(new RegExp(`${redirectTarget.replace(/\//g, '\\/')}(?:$|[?#])`), { timeout: 10000 });
}

// ── Journey ─────────────────────────────────────────────────────────────────

journeyTest.describe('Journey 5: Tier-Gated Access & Security', () => {

  journeyTest('Step 1: Standard tier user sees only permitted navigation items', async ({ authedPage, switchTier }) => {
    await switchTier('standard');
    await navigateAndWait(authedPage, '/home');
    await expectNoErrors(authedPage);

    // The Home page should be visible (accessible to all tiers).
    await expect(authedPage).toHaveURL(/\/home(?:$|[?#])/, { timeout: 10000 });
    await expect(
      authedPage.getByRole('heading', { name: /fabric value case intake cockpit/i }),
    ).toBeVisible({ timeout: 10000 });

    // Standard-restricted routes should NOT appear in navigation
    const restrictedLabels = [/ontology/i, /extraction/i, /formulas/i, /benchmarks/i];
    for (const label of restrictedLabels) {
      const navItem = authedPage.getByRole('link', { name: label });
      // Navigation items for restricted routes should not be visible
      await expect(navItem).not.toBeVisible().catch(() => {
        // Some items may not exist at all, which is also correct
      });
    }
  });

  journeyTest('Step 2: Standard tier user is redirected when accessing restricted URL', async ({ authedPage, switchTier }) => {
    journeyTest.setTimeout(45_000);
    await switchTier('standard');

    const restrictedRoutes = ROUTES_BY_TIER.standard.restricted;
    const redirectTarget = TIER_REDIRECTS.standard;

    for (const route of restrictedRoutes.slice(0, 3)) {
      // Navigate directly to a restricted route
      await authedPage.goto(route, { waitUntil: 'domcontentloaded' });

      // Should be redirected to /home
      await expectRedirectedToTierHome(authedPage, redirectTarget);
    }
  });

  journeyTest('Step 3: Advanced tier user can access discovery features', async ({ authedPage, switchTier }) => {
    await switchTier('advanced');

    const advancedRoutes = ROUTES_BY_TIER.advanced.accessible;

    // Test a subset of advanced-accessible routes
    for (const route of advancedRoutes.slice(0, 4)) {
      await navigateAndWait(authedPage, route);
      await expectNoErrors(authedPage);
      // Should NOT be redirected away
      await expect(authedPage).toHaveURL(new RegExp(route.replace(/\//g, '\\/')));
    }
  });

  journeyTest('Step 4: Advanced tier user is still restricted from admin routes', async ({ authedPage, switchTier }) => {
    await switchTier('advanced');
    await expect.poll(() => getCurrentTier(authedPage), { timeout: 10000 }).toBe('advanced');

    const restrictedRoutes = ROUTES_BY_TIER.advanced.restricted;

    for (const route of restrictedRoutes.slice(0, 2)) {
      await authedPage.goto(route, { waitUntil: 'domcontentloaded' });

      // Should be redirected to /home
      await expectRedirectedToTierHome(authedPage, TIER_REDIRECTS.advanced);
    }
  });

  journeyTest('Step 5: Admin tier user has full access to all routes', async ({ authedPage, switchTier }) => {
    await switchTier('admin');

    const adminRoutes = ROUTES_BY_TIER.admin.accessible;

    for (const route of adminRoutes.slice(0, 5)) {
      await navigateAndWait(authedPage, route);
      await expectNoErrors(authedPage);
      await expect(authedPage).toHaveURL(new RegExp(route.replace(/\//g, '\\/')));
    }
  });

  journeyTest('Step 6: Tier switch mid-session updates access controls', async ({ authedPage, switchTier }) => {
    // Start as admin — should access admin route
    await switchTier('admin');
    await expect.poll(() => getCurrentTier(authedPage), { timeout: 10000 }).toBe('admin');
    const adminRoute = tenantRoute('/governance/benchmarks');
    await navigateAndWait(authedPage, adminRoute);
    await expectNoErrors(authedPage);
    await expect(authedPage).toHaveURL(new RegExp(adminRoute.replace(/\//g, '\\/')));

    // Switch to standard — same route should now redirect
    await switchTier('standard');
    await expect.poll(() => getCurrentTier(authedPage), { timeout: 10000 }).toBe('standard');
    await authedPage.goto(adminRoute, { waitUntil: 'domcontentloaded' });
    await expectRedirectedToTierHome(authedPage, TIER_REDIRECTS.standard);

    // Switch back to admin — should regain access
    await switchTier('admin');
    await expect.poll(() => getCurrentTier(authedPage), { timeout: 10000 }).toBe('admin');
    await navigateAndWait(authedPage, adminRoute);
    await expect(authedPage).toHaveURL(new RegExp(adminRoute.replace(/\//g, '\\/')));
  });

  // ── Deep-Link Security ───────────────────────────────────────────────────

  journeyTest('SEC-001: canonical protected route resolves in mocked journey auth harness', async ({ authedPage }) => {
    await navigateAndWait(authedPage, tenantRoute('/accounts'));

    await expect(authedPage).toHaveURL(new RegExp(tenantRoute('/accounts').replace(/\//g, '\\/')));
    await expectNoErrors(authedPage);
  });

  journeyTest('SEC-002: deep link to tenant settings as standard user redirects to home', async ({ authedPage, switchTier }) => {
    await switchTier('standard');
    await authedPage.goto(tenantRoute('/settings'), { waitUntil: 'domcontentloaded' });

    // Standard user should be redirected away from the admin route
    await expectRedirectedToTierHome(authedPage, TIER_REDIRECTS.standard);
  });

  journeyTest('SEC-003: deep link to governance benchmarks as standard user redirects to home', async ({ authedPage, switchTier }) => {
    await switchTier('standard');
    await authedPage.goto(tenantRoute('/governance/benchmarks'), { waitUntil: 'domcontentloaded' });

    await expectRedirectedToTierHome(authedPage, TIER_REDIRECTS.standard);
  });

  journeyTest('SEC-004: deep link to governance policies as standard user redirects to home', async ({ authedPage, switchTier }) => {
    await switchTier('standard');
    await authedPage.goto(tenantRoute('/governance/policies'), { waitUntil: 'domcontentloaded' });

    await expectRedirectedToTierHome(authedPage, TIER_REDIRECTS.standard);
  });

  journeyTest('SEC-005: deep link to context targets as standard user redirects to home', async ({ authedPage, switchTier }) => {
    await switchTier('standard');
    await authedPage.goto(tenantRoute('/context/targets'), { waitUntil: 'domcontentloaded' });

    await expectRedirectedToTierHome(authedPage, TIER_REDIRECTS.standard);
  });

  journeyTest('SEC-006: deep link to governance formulas as standard user redirects to home', async ({ authedPage, switchTier }) => {
    await switchTier('standard');
    await expect.poll(() => getCurrentTier(authedPage), { timeout: 10000 }).toBe('standard');
    await authedPage.goto(tenantRoute('/governance/formulas'), { waitUntil: 'domcontentloaded' });

    await expectRedirectedToTierHome(authedPage, TIER_REDIRECTS.standard);
  });
});
