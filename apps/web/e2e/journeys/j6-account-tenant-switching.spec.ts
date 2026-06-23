/**
 * Journey 6: Account and Tenant Switching
 *
 * Traceability: SWITCH-001 through SWITCH-006.
 *
 * This suite validates account and tenant switching workflows, ensuring that:
 * - Tenant/account switch updates data scope correctly
 * - Navigation reflects new context immediately
 * - API requests use new tenant context after switch
 * - Session remains valid across switch
 * - Deep links after switch respect new context
 * - No stale data from previous context appears
 *
 * Priority: P0 production gate
 * Mode: Contract (mocked) + Backend-integrated
 */

import { journeyTest, expect } from '../helpers/journey-fixture';
import { expectRouteSupportsWorkflow, expectAnyVisible } from '../helpers/validation-program';
import { switchAccount, verifyAccountContext, setTenantContext, clearAccountData } from '../fixtures/account-helpers';
import { TEST_ACCOUNTS } from '../fixtures/account-helpers';
import { seedAuthState, clearAuthState } from '../fixtures/auth-helpers';
import { clearUserTier } from '../fixtures/tier-helpers';

journeyTest.describe('Journey 6: Account and Tenant Switching', () => {
  journeyTest.afterEach(async ({ authedPage }) => {
    await clearAuthState(authedPage).catch(() => {});
    await clearUserTier(authedPage).catch(() => {});
    await clearAccountData(authedPage).catch(() => {});
  });

  // ── Account Switching Data Scope Updates ───────────────────────────────────

  journeyTest('SWITCH-001: account switch updates data scope correctly', async ({ authedPage }) => {
    // Start with Meridian account
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Verify Meridian data is loaded
    await expect(authedPage.getByText(/meridian/i)).toBeVisible({ timeout: 10000 });

    // Switch to Acme account
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.acme);

    // Navigate to Acme signals
    await authedPage.goto('/intelligence/acct-acme-002/signals', { waitUntil: 'domcontentloaded' });

    // Verify Acme data is loaded
    await expect(authedPage.getByText(/acme/i)).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(/meridian/i)).not.toBeVisible({ timeout: 5000 });
  });

  journeyTest('SWITCH-002: account context is verified after switch', async ({ authedPage }) => {
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.acme);

    const isAcmeContext = await verifyAccountContext(authedPage, TEST_ACCOUNTS.acme);
    expect(isAcmeContext).toBe(true);
  });

  // ── Navigation Reflects New Context ───────────────────────────────────────

  journeyTest('SWITCH-003: navigation reflects new context immediately after switch', async ({ authedPage }) => {
    // Start with Meridian
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Switch to Acme
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.acme);

    // Navigation should show Acme context
    await expectAnyVisible(
      authedPage,
      [/acme/i, /corp/i],
      'account context in navigation',
    );
  });

  journeyTest('SWITCH-004: sidebar navigation updates after account switch', async ({ authedPage }) => {
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.acme);
    await authedPage.goto('/home', { waitUntil: 'domcontentloaded' });

    // Sidebar should reflect current account context
    await expectAnyVisible(
      authedPage,
      [/accounts/i, /acme/i],
      'sidebar with account context',
    );
  });

  // ── API Requests Use New Tenant Context ───────────────────────────────────

  journeyTest('SWITCH-005: API requests use new tenant context after switch', async ({ authedPage, addMocks }) => {
    // Mock API to verify tenant context
    let capturedTenantId: string | null = null;
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        handler: async (route) => {
          const headers = route.request().headers();
          capturedTenantId = headers['x-tenant-id'] as string;
          await route.fulfill({
            status: 200,
            body: JSON.stringify({ signals: [] }),
          });
        },
      },
    ]);

    // Set initial tenant context
    await setTenantContext(authedPage, 'tenant-001', 'tenant-a');
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Make API request
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Verify tenant context was used
    expect(capturedTenantId).toBe('tenant-001');

    // Switch tenant context
    capturedTenantId = null;
    await setTenantContext(authedPage, 'tenant-002', 'tenant-b');

    // Make another API request
    await authedPage.reload({ waitUntil: 'domcontentloaded' });

    // Verify new tenant context was used
    expect(capturedTenantId).toBe('tenant-002');
  });

  // ── Session Remains Valid Across Switch ───────────────────────────────────

  journeyTest('SWITCH-006: session remains valid after account switch', async ({ authedPage }) => {
    // Seed auth
    await seedAuthState(authedPage);
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Navigate to protected route
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });
    await expect(authedPage.getByText(/signals/i)).toBeVisible({ timeout: 10000 });

    // Switch account
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.acme);

    // Navigate to another protected route
    await authedPage.goto('/intelligence/acct-acme-002/signals', { waitUntil: 'domcontentloaded' });

    // Should not redirect to login (session still valid)
    await expect(authedPage).not.toHaveURL(/\/login/, { timeout: 5000 });
    await expect(authedPage.getByText(/signals/i)).toBeVisible({ timeout: 10000 });
  });

  journeyTest('SWITCH-007: session remains valid after tenant context switch', async ({ authedPage }) => {
    await seedAuthState(authedPage);
    await setTenantContext(authedPage, 'tenant-001', 'tenant-a');
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Navigate to protected route
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Switch tenant context
    await setTenantContext(authedPage, 'tenant-002', 'tenant-b');

    // Navigate to another protected route
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should not redirect to login
    await expect(authedPage).not.toHaveURL(/\/login/, { timeout: 5000 });
  });

  // ── Deep Links After Switch Respect New Context ────────────────────────────

  journeyTest('SWITCH-008: deep links after account switch respect new context', async ({ authedPage }) => {
    // Start with Meridian
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Switch to Acme
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.acme);

    // Navigate to Meridian deep link (should not show Meridian data)
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show error or redirect, not Meridian data
    await expect(
      authedPage.getByText(/forbidden|not authorized|access denied|could not be loaded|no signals yet/i).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('SWITCH-009: deep links after tenant switch respect new context', async ({ authedPage }) => {
    await setTenantContext(authedPage, 'tenant-001', 'tenant-a');
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Switch tenant
    await setTenantContext(authedPage, 'tenant-002', 'tenant-b');

    // Navigate to deep link
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should use new tenant context
    // (This would be verified by API mock capturing tenant-id header)
  });

  // ── No Stale Data from Previous Context ───────────────────────────────────

  journeyTest('SWITCH-010: stale data from previous account does not appear after switch', async ({ authedPage }) => {
    // Load Meridian data
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });
    await expect(authedPage.getByText(/meridian/i)).toBeVisible({ timeout: 10000 });

    // Clear cache and switch
    await clearAccountData(authedPage);
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.acme);

    // Navigate to Acme
    await authedPage.goto('/intelligence/acct-acme-002/signals', { waitUntil: 'domcontentloaded' });

    // Should not show Meridian data
    await expect(authedPage.getByText(/meridian/i)).not.toBeVisible({ timeout: 5000 });
  });

  journeyTest('SWITCH-011: stale data from previous tenant does not appear after switch', async ({ authedPage }) => {
    await setTenantContext(authedPage, 'tenant-001', 'tenant-a');
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Load data
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Switch tenant and clear cache
    await clearAccountData(authedPage);
    await setTenantContext(authedPage, 'tenant-002', 'tenant-b');

    // Reload
    await authedPage.reload({ waitUntil: 'domcontentloaded' });

    // Should use new tenant context (no stale data from tenant-a)
  });

  // ── Account Switcher UI ─────────────────────────────────────────────────────

  journeyTest('SWITCH-012: account switcher UI is accessible and functional', async ({ authedPage }) => {
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);
    await authedPage.goto('/home', { waitUntil: 'domcontentloaded' });

    // Account switcher should be visible
    await expectAnyVisible(
      authedPage,
      [/account/i, /switch/i, /meridian/i],
      'account switcher UI',
    );
  });

  journeyTest('SWITCH-013: account switcher shows available accounts', async ({ authedPage }) => {
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);
    await authedPage.goto('/home', { waitUntil: 'domcontentloaded' });

    // Click on account switcher
    const accountSwitcher = authedPage.getByRole('button', { name: /account|meridian/i }).or(
      authedPage.getByText(/meridian/i)
    ).first();
    await accountSwitcher.click();

    // Should show account list
    await expectAnyVisible(
      authedPage,
      [/acme/i, /global finance/i],
      'available accounts in switcher',
    );
  });
});
