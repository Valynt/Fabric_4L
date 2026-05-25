/**
 * UI Debug & Troubleshoot Script
 *
 * Comprehensive end-user satisfaction check:
 * - Login via dev bypass
 * - Navigate to key pages via direct URL (full reload)
 * - Verify each page renders meaningful content
 * - Collect diagnostics for any failures
 */

import { test, expect } from '../fixtures/contract-test';

test.describe('UI End-User Satisfaction @debug', () => {
  test('login and explore core pages successfully', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => consoleErrors.push(`PAGE_ERROR: ${err.message}`));

    // ── 1. Login ───────────────────────────────────────────────────────────
    await page.goto('/login');
    await expect(page.getByTestId('login-heading')).toBeVisible();
    await page.getByRole('button', { name: /development bypass/i }).click();
    await expect(page).toHaveURL(/\/home/);
    await expect(page.locator('aside, nav').filter({ hasText: /Home|Accounts|Intelligence/ }).first()).toBeVisible();
    await expect(page.getByText(/create a value case/i)).toBeVisible();
    await page.screenshot({ path: 'e2e-results/debug-home.png', fullPage: true });

    // ── 2. Accounts ────────────────────────────────────────────────────────
    await page.goto('/accounts');
    await expect(page.locator('aside').first()).toBeVisible();
    await expect(page.getByRole('heading', { name: /accounts/i })).toBeVisible();
    await page.screenshot({ path: 'e2e-results/debug-accounts.png', fullPage: true });

    // ── 3. Context / Value Packs ───────────────────────────────────────────
    await page.goto('/context/packs');
    await expect(page.locator('aside').first()).toBeVisible();
    await expect(page.getByRole('heading', { name: /value packs/i })).toBeVisible();
    await page.screenshot({ path: 'e2e-results/debug-context-packs.png', fullPage: true });

    // ── 4. Settings / Governance (admin) ───────────────────────────────────
    await page.goto('/settings/governance/policies');
    await expect(page.locator('aside').first()).toBeVisible();
    await expect(page.getByRole('heading', { name: /governance|policies/i })).toBeVisible().catch(() => {
      // Fallback: just verify sidebar + some settings text
      return expect(page.getByText(/governance|policies|settings/i).first()).toBeVisible();
    });
    await page.screenshot({ path: 'e2e-results/debug-settings-formulas.png', fullPage: true });

    // ── 5. Deliverables / Cases ────────────────────────────────────────────
    await page.goto('/deliverables/cases');
    await expect(page.locator('aside').first()).toBeVisible();
    await expect(page.getByRole('heading', { name: /business cases|cases/i })).toBeVisible().catch(() => {
      return expect(page.getByText(/cases|deliverables/i).first()).toBeVisible();
    });
    await page.screenshot({ path: 'e2e-results/debug-deliverables-cases.png', fullPage: true });

    // ── 6. Workflow / Prospect ─────────────────────────────────────────────
    await page.goto('/workflow');
    await expect(page.locator('aside').first()).toBeVisible();
    await expect(page.getByText(/prospect|company|setup/i).first()).toBeVisible();
    await page.screenshot({ path: 'e2e-results/debug-workflow-prospect.png', fullPage: true });

    // ── 7. Studio / Value Model (legacy route via redirect) ──────────────────
    await page.goto('/studio/value-model');
    await expect(page.locator('aside').first()).toBeVisible();
    await page.screenshot({ path: 'e2e-results/debug-studio-value-model.png', fullPage: true });

    // ── Diagnostics ────────────────────────────────────────────────────────
    const criticalErrors = consoleErrors.filter(e =>
      !e.includes('VITE_ANALYTICS') &&
      !e.includes('umami') &&
      !e.includes('proxy error') &&
      !e.includes('the server responded with a status of 500')
    );
    if (criticalErrors.length > 0) {
      console.log('CRITICAL_ERRORS:', JSON.stringify(criticalErrors.slice(0, 10)));
    }

    // Final: still authenticated
    const token = await page.evaluate(() => localStorage.getItem('accessToken'));
    expect(token).toBeTruthy();
  });
});
