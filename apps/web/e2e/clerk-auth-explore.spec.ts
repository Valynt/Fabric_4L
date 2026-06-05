import { test, expect } from '@playwright/test';

test.describe('Clerk Auth Exploration', () => {
  test('explore sign-in page', async ({ page }) => {
    const consoleErrors: string[] = [];
    const consoleWarnings: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
      if (msg.type() === 'warning') consoleWarnings.push(msg.text());
    });

    await page.goto('/sign-in', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    console.log('URL:', page.url());
    console.log('Console errors:', consoleErrors);
    console.log('Console warnings:', consoleWarnings);

    // Take screenshot
    await page.screenshot({ path: 'e2e-results/clerk-sign-in-explore.png', fullPage: true });

    // Check if Clerk component is present
    const clerkComponent = page.locator('[data-clerk-component]').first();
    console.log('Clerk component visible:', await clerkComponent.isVisible().catch(() => false));

    // Check for sign-in form elements
    const emailInput = page.locator('input[name="identifier"], input[type="email"]').first();
    console.log('Email input visible:', await emailInput.isVisible().catch(() => false));

    const passwordInput = page.locator('input[name="password"], input[type="password"]').first();
    console.log('Password input visible:', await passwordInput.isVisible().catch(() => false));

    // Check for social sign-in buttons
    const googleButton = page.locator('button, a').filter({ hasText: /google/i }).first();
    console.log('Google button visible:', await googleButton.isVisible().catch(() => false));
  });

  test('explore workspaces page', async ({ page }) => {
    await page.goto('/workspaces', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    console.log('URL:', page.url());
    await page.screenshot({ path: 'e2e-results/clerk-workspaces-explore.png', fullPage: true });

    const orgList = page.locator('[data-clerk-component="OrganizationList"]').first();
    console.log('OrgList visible:', await orgList.isVisible().catch(() => false));
  });

  test('explore home without auth', async ({ page }) => {
    await page.goto('/home', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    console.log('URL:', page.url());
    await page.screenshot({ path: 'e2e-results/clerk-home-noauth-explore.png', fullPage: true });
  });
});
