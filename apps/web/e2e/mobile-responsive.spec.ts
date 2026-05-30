/**
 * P2-011: Mobile / Responsive E2E smoke test.
 *
 * Verifies core navigation and layout adapt to small viewports.
 * Runs in the contracts-mobile-chrome and contracts-mobile-safari projects.
 */
import { test, expect } from '@playwright/test';

test.describe('Mobile Responsive Smoke', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('login page renders without horizontal overflow on mobile', async ({ page }) => {
    await page.goto('/sign-in');
    await expect(page.locator('body')).toHaveCSS('overflow-x', /auto|hidden|clip/);
  });

  test('dashboard navigation is accessible on mobile viewport', async ({ page }) => {
    await page.goto('/');
    // Wait for any navigation element (hamburger, sidebar, or top nav)
    const nav = page.locator('nav, [role="navigation"]').first();
    await expect(nav).toBeVisible({ timeout: 5000 });
  });
});
