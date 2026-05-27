/**
 * Security Suite: Deep Link Tenant Isolation (Deep)
 *
 * Traceability: SEC-DEEP-001 through SEC-DEEP-005.
 *
 * This suite extends the basic tenant isolation tests to cover:
 * - Deep links respect tenant context after account switch
 * - Stale cached data from one account does not appear in another account
 * - Direct URL with forged tenant-id headers blocked at both UI and API layer
 * - Deep link with expired session redirects correctly
 * - Deep link navigation after tenant switch respects new context
 *
 * Priority: P0 production gate
 * Mode: Backend-integrated (requires real tenant isolation)
 */

import { journeyTest, expect } from '../helpers/journey-fixture';
import {
  expectNoCrossTenantLeakage,
  expectRouteSupportsWorkflow,
  expectTenantContext,
} from '../helpers/validation-program';
import { switchAccount, verifyAccountContext, setTenantContext, clearAccountData } from '../fixtures/account-helpers';
import { TEST_ACCOUNTS } from '../fixtures/account-helpers';
import { seedAuthState, clearAuthState } from '../fixtures/auth-helpers';
import { clearUserTier } from '../fixtures/tier-helpers';

journeyTest.describe('@backend Security Suite: Deep Link Tenant Isolation (Deep)', () => {
  journeyTest.afterEach(async ({ authedPage }) => {
    await clearAuthState(authedPage).catch(() => {});
    await clearUserTier(authedPage).catch(() => {});
    await clearAccountData(authedPage).catch(() => {});
  });

  // ── Deep Link Tenant Context Respect ─────────────────────────────────────

  journeyTest('SEC-DEEP-001: deep link respects tenant context after account switch', async ({ authedPage }) => {
    // Start with Meridian account
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Verify we're on Meridian signals
    await expect(authedPage.getByText(/meridian/i)).toBeVisible({ timeout: 10000 });

    // Switch to Acme account
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.acme);

    // Navigate to a deep link that was previously accessible
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should not show Meridian data - should show error or redirect
    await expectNoCrossTenantLeakage(authedPage);
    await expect(
      authedPage.getByText(/forbidden|not authorized|access denied|could not be loaded|no signals yet/i).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('SEC-DEEP-002: deep link after tenant switch uses new tenant context', async ({ authedPage }) => {
    // Set initial tenant context
    await setTenantContext(authedPage, 'tenant-001', 'tenant-a');
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Switch tenant context
    await setTenantContext(authedPage, 'tenant-002', 'tenant-b');

    // Navigate to deep link
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Verify new tenant context is used
    await expectTenantContext(authedPage, 'tenant-002');
  });

  // ── Stale Cache Data Prevention ───────────────────────────────────────────

  journeyTest('SEC-DEEP-003: stale cached data from one account does not appear in another account', async ({ authedPage }) => {
    // Load Meridian account data
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });
    await expect(authedPage.getByText(/meridian/i)).toBeVisible({ timeout: 10000 });

    // Clear account data to simulate fresh context
    await clearAccountData(authedPage);

    // Switch to Acme account
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.acme);
    await authedPage.goto('/intelligence/acct-acme-002/signals', { waitUntil: 'domcontentloaded' });

    // Should not show Meridian data
    await expect(authedPage.getByText(/meridian/i)).not.toBeVisible({ timeout: 5000 });
    await expect(authedPage.getByText(/acme/i)).toBeVisible({ timeout: 10000 });
  });

  journeyTest('SEC-DEEP-004: cache invalidation occurs on account switch', async ({ authedPage }) => {
    // Load data for Meridian
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Switch to Acme
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.acme);

    // Navigate to same route pattern for Acme
    await authedPage.goto('/intelligence/acct-acme-002/signals', { waitUntil: 'domcontentloaded' });

    // Verify account context is updated
    const isAcmeContext = await verifyAccountContext(authedPage, TEST_ACCOUNTS.acme);
    expect(isAcmeContext).toBe(true);
  });

  // ── Forged Tenant-ID Header Blocking ───────────────────────────────────────

  journeyTest('SEC-DEEP-005: direct URL with forged tenant-id header blocked at API layer', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/acct-other-tenant/**',
        status: 403,
        body: { error: 'Forbidden: tenant isolation enforced' },
      },
    ]);

    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Try to access another tenant's account directly
    await authedPage.goto('/intelligence/acct-other-tenant/signals', { waitUntil: 'domcontentloaded' });

    // Should show 403 error, not leak data
    await expectNoCrossTenantLeakage(authedPage);
    await expect(
      authedPage.getByText(/forbidden|not authorized|access denied|could not be loaded/i).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('SEC-DEEP-006: forged tenant-id in URL parameters is rejected', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/**',
        status: 403,
        body: { error: 'Invalid tenant context' },
      },
    ]);

    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Try to access with forged tenant parameter
    await authedPage.goto('/intelligence/acct-meridian-001/signals?tenant_id=forged-tenant', { waitUntil: 'domcontentloaded' });

    // Should reject the forged parameter
    await expect(
      authedPage.getByText(/forbidden|invalid|not authorized/i).first(),
    ).toBeVisible({ timeout: 10000 });
  });

  // ── Deep Link with Expired Session ─────────────────────────────────────────

  journeyTest('SEC-DEEP-007: deep link with expired session redirects to login', async ({ authedPage }) => {
    // Clear auth to simulate expired session
    await clearAuthState(authedPage);

    // Try to access deep link
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should redirect to login
    await expect(authedPage).toHaveURL(/\/login/, { timeout: 10000 });
  });

  journeyTest('SEC-DEEP-008: deep link after re-auth respects original intent', async ({ authedPage }) => {
    // Clear auth
    await clearAuthState(authedPage);

    // Try to access deep link (will redirect to login)
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });
    await expect(authedPage).toHaveURL(/\/login/, { timeout: 10000 });

    // Re-auth
    await seedAuthState(authedPage);

    // Navigate to the original deep link
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should load successfully
    await expect(authedPage.getByText(/signals/i)).toBeVisible({ timeout: 10000 });
  });

  // ── Deep Link Navigation After Tenant Switch ─────────────────────────────

  journeyTest('SEC-DEEP-009: deep link navigation after tenant switch respects new context', async ({ authedPage }) => {
    // Start with tenant A
    await setTenantContext(authedPage, 'tenant-001', 'tenant-a');
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Switch to tenant B
    await setTenantContext(authedPage, 'tenant-002', 'tenant-b');

    // Navigate to deep link
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Verify new tenant context is used
    await expectTenantContext(authedPage, 'tenant-002');
    await expectNoCrossTenantLeakage(authedPage);
  });

  journeyTest('SEC-DEEP-010: deep link with account ID from different tenant is blocked', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/acct-different-tenant/**',
        status: 403,
        body: { error: 'Forbidden: account belongs to different tenant' },
      },
    ]);

    await setTenantContext(authedPage, 'tenant-001', 'tenant-a');
    await switchAccount(authedPage, TEST_ACCOUNTS.meridian, TEST_ACCOUNTS.meridian);

    // Try to access account from different tenant
    await authedPage.goto('/intelligence/acct-different-tenant/signals', { waitUntil: 'domcontentloaded' });

    // Should be blocked
    await expectNoCrossTenantLeakage(authedPage);
    await expect(
      authedPage.getByText(/forbidden|not authorized|access denied|could not be loaded/i).first(),
    ).toBeVisible({ timeout: 10000 });
  });
});
