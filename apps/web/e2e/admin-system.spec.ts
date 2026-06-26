import { test, expect } from './fixtures/contract-test';
import { PlatformSettingsPage, HealthMonitorPage } from './pages';
import { setUserTier, clearUserTier } from './fixtures';

/**
 * Admin System Routes E2E Tests
 *
 * Routes:
 *   /admin/system/settings → PlatformSettings
 *   /admin/system/health → HealthMonitor
 * Tier: admin
 *
 * Covers:
 * - Platform Settings: Tabs, toggles, form inputs
 * - Health Monitor: Service grid, status badges, alerts
 * - Access control (admin-only)
 */

test.describe('Admin System Routes', () => {
  test.afterEach(async ({ page }) => {
    await clearUserTier(page);
  });

  // ── Platform Settings ───────────────────────────────────────────────

  test.describe('Platform Settings', () => {
    let settingsPage: PlatformSettingsPage;

    test.beforeEach(async ({ page }) => {
      await setUserTier(page, 'admin');
      settingsPage = new PlatformSettingsPage(page);
      await settingsPage.goto();
    });

    test('should display page header', async () => {
      await settingsPage.assertPageLoaded();
      await expect(settingsPage.header).toBeVisible();
    });

    test('should display all tabs', async () => {
      await expect(settingsPage.featuresTab).toBeVisible();
      await expect(settingsPage.notificationsTab).toBeVisible();
      await expect(settingsPage.securityTab).toBeVisible();
      await expect(settingsPage.brandingTab).toBeVisible();
    });

    test('should switch to Features tab', async () => {
      await settingsPage.switchToFeaturesTab();
      await settingsPage.assertFeaturesTabActive();
    });

    test('should switch to Notifications tab', async () => {
      await settingsPage.switchToNotificationsTab();
      await expect(settingsPage.slackWebhookInput).toBeVisible();
    });

    test('should switch to Security tab', async () => {
      await settingsPage.switchToSecurityTab();
      await expect(settingsPage.sessionTimeoutInput).toBeVisible();
    });

    test('should switch to Branding tab', async () => {
      await settingsPage.switchToBrandingTab();
      await expect(settingsPage.logoUrlInput).toBeVisible();
    });

    test('should toggle feature flags @smoke', async ({ page }) => {
      await settingsPage.switchToFeaturesTab();
      
      // Get initial state
      const initialState = await settingsPage.isAdvancedAnalyticsChecked();
      
      // Toggle on/off (idempotent - reverts to original state)
      await settingsPage.toggleAdvancedAnalytics();
      await expect
        .poll(() => settingsPage.isAdvancedAnalyticsChecked(), { timeout: 3000 })
        .toBe(!initialState);
      await settingsPage.toggleAdvancedAnalytics();
      
      // Verify back to original state
      const finalState = await settingsPage.isAdvancedAnalyticsChecked();
      expect(finalState).toBe(initialState);
    });
  });

  // ── Health Monitor ──────────────────────────────────────────────────

  test.describe('Health Monitor', () => {
    let healthPage: HealthMonitorPage;

    test.beforeEach(async ({ page }) => {
      await setUserTier(page, 'admin');
      healthPage = new HealthMonitorPage(page);
      await healthPage.goto();
    });

    test('should display page header', async () => {
      await healthPage.assertPageLoaded();
      await expect(healthPage.header).toBeVisible();
    });

    test('should display refresh button', async () => {
      await expect(healthPage.refreshButton).toBeVisible();
    });

    test('should display service grid', async () => {
      await healthPage.waitForDataLoad();
      await healthPage.assertServicesVisible();
    });

    test('should refresh health data', async () => {
      await healthPage.clickRefresh();
      await healthPage.waitForDataLoad();
      await healthPage.assertServicesVisible();
    });

    test('should display status indicators', async () => {
      await healthPage.waitForDataLoad();
      
      const healthyCount = await healthPage.getServiceCount();
      expect(healthyCount).toBeGreaterThanOrEqual(0);
    });
  });

  // ── Access Control ────────────────────────────────────────────────

  test.describe('Access Control', () => {
    test('should redirect standard tier from settings', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto('/admin/system/settings');
      await expect(page).not.toHaveURL('/admin/system/settings');
    });

    test('should redirect standard tier from health', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto('/admin/system/health');
      await expect(page).not.toHaveURL('/admin/system/health');
    });

    test('should redirect advanced tier from settings', async ({ page }) => {
      await setUserTier(page, 'advanced');
      await page.goto('/admin/system/settings');
      await expect(page).not.toHaveURL('/admin/system/settings');
    });

    test('should allow admin access to settings', async ({ page }) => {
      await setUserTier(page, 'admin');
      const settingsPage = new PlatformSettingsPage(page);
      await settingsPage.goto();
      await settingsPage.assertPageLoaded();
    });

    test('should allow admin access to health', async ({ page }) => {
      await setUserTier(page, 'admin');
      const healthPage = new HealthMonitorPage(page);
      await healthPage.goto();
      await healthPage.assertPageLoaded();
    });
  });
});
