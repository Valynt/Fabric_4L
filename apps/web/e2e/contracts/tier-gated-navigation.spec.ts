/**
 * CONTRACT TEST: Tier-Gated Navigation
 *
 * These tests define the behavioral contract for the tiered progressive
 * disclosure system. The sidebar navigation uses a 7-domain left rail:
 *
 *   1. Accounts      — Entry point for prospect accounts
 *   2. Intelligence  — Discovery workspace (signals, drivers, evidence, stakeholders)
 *   3. Value Studio  — Synthesis workspace (action plan, value model, narrative)
 *   4. Context Engine — Vendor knowledge base
 *   5. Deliverables  — Packaged outputs
 *   6. Governance    — Audit, provenance, compliance
 *   7. Settings      — Tenant configuration (admin only)
 *
 * All top-level workflow domains are visible to standard tier and above.
 * Admin-only sections (Settings) are hidden from non-admin users.
 *
 * References:
 *   - TieredNav.tsx NAV_SPINE
 *   - CONTRACT.md §2.6 UI State Machine
 */
import { test, expect } from '../fixtures/contract-test';
import { setUserTier, clearUserTier, seedAuthState, clearAuthState } from '../fixtures';

test.describe('Contract: Tier-Gated Navigation', () => {
  test.afterEach(async ({ page }) => {
    await clearUserTier(page);
    await clearAuthState(page);
  });

  // ── Standard Tier (Tier 1) ────────────────────────────────────────────
  test.describe('Standard Tier', () => {
    test.beforeEach(async ({ page }) => {
      await seedAuthState(page, {
        id: 'test-user-e2e',
        email: 'e2e@valuefabric.test',
        role: 'standard',
        tenantId: 'tenant-e2e-001',
        tenantSlug: 'e2e-test',
      });
      await setUserTier(page, 'standard');
      await page.goto('/home');
      await page.waitForLoadState('networkidle');
    });

    test('should show Accounts in sidebar', async ({ page }) => {
      await expect(page.getByRole('link', { name: /^Accounts$/i })).toBeVisible();
    });

    test('should show Intelligence in sidebar', async ({ page }) => {
      await expect(page.getByRole('link', { name: /^Intelligence$/i })).toBeVisible();
    });

    test('should show Value Studio in sidebar', async ({ page }) => {
      await expect(page.getByRole('link', { name: /^Value Studio$/i })).toBeVisible();
    });

    test('should show Context Engine in sidebar', async ({ page }) => {
      await expect(page.getByRole('link', { name: /^Context Engine$/i })).toBeVisible();
    });

    test('should show Deliverables in sidebar', async ({ page }) => {
      await expect(page.getByRole('link', { name: /^Deliverables$/i })).toBeVisible();
    });

    test('should show Governance in sidebar', async ({ page }) => {
      await expect(page.getByRole('link', { name: /^Governance$/i })).toBeVisible();
    });

    test('should not show Settings in sidebar', async ({ page }) => {
      await expect(page.getByRole('link', { name: /^Settings$/i })).not.toBeVisible();
    });

    test('should redirect to /home when navigating to admin route', async ({ page }) => {
      await page.goto('/t/e2e-test/settings/users');
      await expect(page).toHaveURL(/\/home/);
    });
  });

  // ── Advanced Tier (Tier 2) ────────────────────────────────────────────
  test.describe('Advanced Tier', () => {
    test.beforeEach(async ({ page }) => {
      await seedAuthState(page, {
        id: 'test-user-e2e',
        email: 'e2e@valuefabric.test',
        role: 'advanced',
        tenantId: 'tenant-e2e-001',
        tenantSlug: 'e2e-test',
      });
      await setUserTier(page, 'advanced');
      await page.goto('/home');
      await page.waitForLoadState('networkidle');
    });

    test('should show all workflow domains', async ({ page }) => {
      await expect(page.getByRole('link', { name: /^Accounts$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Intelligence$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Value Studio$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Context Engine$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Deliverables$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Governance$/i })).toBeVisible();
    });

    test('should not show Settings in sidebar', async ({ page }) => {
      await expect(page.getByRole('link', { name: /^Settings$/i })).not.toBeVisible();
    });

    test('should allow navigation to Context Engine routes', async ({ page }) => {
      await page.goto('/t/e2e-test/context/ontology/graph');
      await expect(page).not.toHaveURL(/\/home/);
    });
  });

  // ── Admin Tier (Tier 3) ───────────────────────────────────────────────
  test.describe('Admin Tier', () => {
    test.beforeEach(async ({ page }) => {
      await seedAuthState(page, {
        id: 'test-admin-e2e',
        email: 'admin@valuefabric.test',
        role: 'admin',
        tenantId: 'tenant-e2e-001',
        tenantSlug: 'e2e-test',
      });
      await setUserTier(page, 'admin');
      await page.goto('/home');
      await page.waitForLoadState('networkidle');
    });

    test('should show all workflow domains plus Settings', async ({ page }) => {
      await expect(page.getByRole('link', { name: /^Accounts$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Intelligence$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Value Studio$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Context Engine$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Deliverables$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Governance$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Settings$/i })).toBeVisible();
    });

    test('should allow navigation to Settings routes', async ({ page }) => {
      await page.goto('/t/e2e-test/settings/workspace');
      await expect(page).not.toHaveURL(/\/home/);
    });
  });

  // ── Tier Switching ────────────────────────────────────────────────────
  test.describe('Tier Switching', () => {
    test('should maintain workflow visibility across tier changes', async ({ page }) => {
      await seedAuthState(page);
      await setUserTier(page, 'standard');
      await page.goto('/home');
      await page.waitForLoadState('networkidle');

      // All workflow domains visible at standard
      await expect(page.getByRole('link', { name: /^Intelligence$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Value Studio$/i })).toBeVisible();

      // Switch to advanced — still visible
      await setUserTier(page, 'advanced');
      await page.reload();
      await page.waitForLoadState('networkidle');
      await expect(page.getByRole('link', { name: /^Intelligence$/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /^Value Studio$/i })).toBeVisible();
    });
  });
});
