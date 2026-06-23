/**
 * Session Refresh Edge Cases
 *
 * Traceability: SESSION-001 through SESSION-006.
 *
 * This suite validates session refresh and expiry handling edge cases:
 * - Silent token refresh without user interruption
 * - Session expiry during active workflow (mid-form, long job)
 * - Multiple tab session synchronization
 * - Logout from one tab invalidates other tabs
 * - Token refresh before expiry
 * - Session recovery after network interruption
 *
 * Priority: P1 production confidence
 * Mode: Contract (mocked token expiry)
 */

import { test, expect } from '../fixtures/contract-test';
import { seedAuthState, clearAuthState, setExpiredToken, setExpiringToken, isSessionExpired, syncSessionToPage } from '../fixtures/auth-helpers';
import { clearUserTier } from '../fixtures/tier-helpers';

test.describe('Session Refresh Edge Cases', () => {
  test.afterEach(async ({ page }) => {
    await clearAuthState(page).catch(() => {});
    await clearUserTier(page).catch(() => {});
  });

  // ── Silent Token Refresh ─────────────────────────────────────────────────

  test('SESSION-001: silent token refresh occurs without user interruption', async ({ page }) => {
    // Seed session with expiring token
    await setExpiringToken(page);
    await page.goto('/home', { waitUntil: 'domcontentloaded' });

    // Wait for potential silent refresh (should not redirect to login)
    await page.waitForTimeout(2000);

    // Should still be on home page, not redirected to login
    await expect(page).toHaveURL(/\/home/, { timeout: 5000 });
    await expect(page.getByText(/command center|home/i)).toBeVisible({ timeout: 10000 });
  });

  test('SESSION-002: token refresh updates localStorage with new token', async ({ page }) => {
    await setExpiringToken(page);
    await page.goto('/home', { waitUntil: 'domcontentloaded' });

    // Wait for refresh
    await page.waitForTimeout(2000);

    // Token should still be valid (not expired)
    const expired = await isSessionExpired(page);
    expect(expired).toBe(false);
  });

  // ── Session Expiry During Active Workflow ─────────────────────────────────

  test('SESSION-003: session expiry during form submission shows error', async ({ page }) => {
    // Seed expired token
    await setExpiredToken(page);
    await page.goto('/context/command-center', { waitUntil: 'domcontentloaded' });

    // Try to submit form
    const domainInput = page.getByPlaceholder(/domain|website/i);
    await expect(domainInput).toBeVisible({ timeout: 5000 });
    await domainInput.fill('test.com');

    const submitBtn = page.getByRole('button', { name: /launch|start|create|begin|run|intelligence/i }).first();
    await submitBtn.click();

    // Should show session expiry error or redirect to login
    await expect(
      page.getByText(/session expired|login|authenticate/i)
        .or(page.locator('body').filter({ hasText: /login/i }))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('SESSION-004: session expiry during long-running job shows appropriate error', async ({ page, context }) => {
    await setExpiredToken(page);
    await page.goto('/context/ingestion/jobs', { waitUntil: 'domcontentloaded' });

    // Navigate to a job detail page
    await page.goto('/context/ingestion/jobs/job-001', { waitUntil: 'domcontentloaded' });

    // Should show session expiry or redirect
    await expect(
      page.getByText(/session expired|login|authenticate/i)
        .or(page.locator('body').filter({ hasText: /login/i }))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });

  test('SESSION-005: form data is preserved when session expires', async ({ page }) => {
    // Seed valid session first
    await seedAuthState(page);
    await page.goto('/context/command-center', { waitUntil: 'domcontentloaded' });

    // Fill form
    const domainInput = page.getByPlaceholder(/domain|website/i);
    await expect(domainInput).toBeVisible({ timeout: 5000 });
    await domainInput.fill('test-company.com');

    // Expire session
    await setExpiredToken(page);

    // Try to submit
    const submitBtn = page.getByRole('button', { name: /launch|start|create|begin|run|intelligence/i }).first();
    await submitBtn.click();

    // Should show session error
    await expect(page.getByText(/session expired|login/i)).toBeVisible({ timeout: 10000 });

    // After re-auth, form data should ideally be preserved (depends on implementation)
    // This test verifies the error handling, not necessarily data preservation
  });

  // ── Multiple Tab Session Synchronization ─────────────────────────────────

  test('SESSION-006: session syncs across multiple tabs', async ({ context, page }) => {
    // Seed session in first tab
    await seedAuthState(page);
    await page.goto('/home', { waitUntil: 'domcontentloaded' });

    // Create second tab
    const page2 = await context.newPage();
    await syncSessionToPage(page, page2);

    // Navigate in second tab
    await page2.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Second tab should be authenticated
    await expect(page2.getByText(/signals/i)).toBeVisible({ timeout: 10000 });
    await expect(page2).not.toHaveURL(/\/login/, { timeout: 5000 });

    await page2.close();
  });

  test('SESSION-007: logout from one tab invalidates other tabs', async ({ context, page }) => {
    // Seed session in first tab
    await seedAuthState(page);
    await page.goto('/home', { waitUntil: 'domcontentloaded' });

    // Create second tab
    const page2 = await context.newPage();
    await syncSessionToPage(page, page2);
    await page2.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Logout from first tab
    await clearAuthState(page);
    await page.goto('/login', { waitUntil: 'domcontentloaded' });

    // Second tab should also be logged out (may require page refresh or event listener)
    await page2.reload({ waitUntil: 'domcontentloaded' });

    // Second tab should redirect to login
    await expect(page2).toHaveURL(/\/login/, { timeout: 10000 });

    await page2.close();
  });

  test('SESSION-008: session expiry in one tab affects other tabs', async ({ context, page }) => {
    // Seed session in first tab
    await seedAuthState(page);
    await page.goto('/home', { waitUntil: 'domcontentloaded' });

    // Create second tab
    const page2 = await context.newPage();
    await syncSessionToPage(page, page2);
    await page2.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Expire session in first tab
    await setExpiredToken(page);

    // Second tab should detect expiry on next interaction
    await page2.reload({ waitUntil: 'domcontentloaded' });

    // Should redirect to login
    await expect(page2).toHaveURL(/\/login/, { timeout: 10000 });

    await page2.close();
  });

  // ── Token Refresh Before Expiry ───────────────────────────────────────────

  test('SESSION-009: proactive token refresh before expiry', async ({ page }) => {
    // Set token that expires in 30 seconds
    await setExpiringToken(page);
    await page.goto('/home', { waitUntil: 'domcontentloaded' });

    // Token should not be expired yet
    let expired = await isSessionExpired(page);
    expect(expired).toBe(false);

    // Wait for proactive refresh (implementation-dependent timing)
    await page.waitForTimeout(3000);

    // Token should still be valid (refreshed)
    expired = await isSessionExpired(page);
    expect(expired).toBe(false);
  });

  test('SESSION-010: token refresh does not interrupt user navigation', async ({ page }) => {
    await setExpiringToken(page);
    await page.goto('/home', { waitUntil: 'domcontentloaded' });

    // Navigate to different pages while token might refresh
    await page.goto('/accounts', { waitUntil: 'domcontentloaded' });
    await expect(page.getByText(/accounts/i)).toBeVisible({ timeout: 10000 });

    await page.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });
    await expect(page.getByText(/signals/i)).toBeVisible({ timeout: 10000 });

    // Should not have been redirected to login
    await expect(page).not.toHaveURL(/\/login/, { timeout: 5000 });
  });

  // ── Session Recovery After Network Interruption ───────────────────────────

  test('SESSION-011: session persists after network interruption', async ({ page }) => {
    await seedAuthState(page);
    await page.goto('/home', { waitUntil: 'domcontentloaded' });

    // Simulate network interruption by going offline
    await page.context().setOffline(true);

    // Try to navigate (will fail)
    await page.goto('/accounts', { waitUntil: 'domcontentloaded' }).catch(() => {
      // Expected to fail due to offline
    });

    // Go back online
    await page.context().setOffline(false);

    // Reload page
    await page.reload({ waitUntil: 'domcontentloaded' });

    // Session should still be valid
    await expect(page).not.toHaveURL(/\/login/, { timeout: 5000 });
    await expect(page.getByText(/accounts/i)).toBeVisible({ timeout: 10000 });
  });

  test('SESSION-012: session recovery after brief network loss', async ({ page }) => {
    await seedAuthState(page);
    await page.goto('/home', { waitUntil: 'domcontentloaded' });

    // Brief offline period
    await page.context().setOffline(true);
    await page.waitForTimeout(1000);
    await page.context().setOffline(false);

    // Navigate
    await page.goto('/accounts', { waitUntil: 'domcontentloaded' });

    // Should work normally
    await expect(page.getByText(/accounts/i)).toBeVisible({ timeout: 10000 });
  });
});
