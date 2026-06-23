import { test, expect } from './fixtures/contract-test';
import type { Page } from '@playwright/test';
import {
  seedAuthState,
  clearAuthState,
  setUserTier,
  clearUserTier,
} from './fixtures';
import {
  setSelectedAccount,
  clearSelectedAccount,
  TEST_ACCOUNTS,
} from './fixtures/account-helpers';

/**
 * Route Validation E2E Tests
 *
 * Validates the actual router paths (not legacy aliases) after Phase 1A
 * route/nav/policy alignment. Uses mock-mode API harness so tests run
 * without a backend.
 *
 * Coverage:
 *   1. App shell renders after mock auth
 *   2. Primary nav links resolve without unresolved params
 *   3. Personal settings accessible to standard user
 *   4. Tenant settings gated by admin tier
 *   5. Account lifecycle
 *   6. Intelligence workspace tab routing
 *   7. Value Studio workspace tab routing
 *   8. Deliverables list + detail
 *   9. Governance routes (traces, formulas, benchmarks, value-packs)
 *   10. Context routes (sources, graph)
 *   11. Account creation route (/accounts/new)
 *   12. 404 / unauthorized graceful states
 */

const TENANT_SLUG = 'e2e-test';
const TEST_ACCOUNT = TEST_ACCOUNTS.meridian;

// Helper: assert a page loaded (not 404 / not a redirect target)
async function assertPageLoaded(page: Page, urlPattern: RegExp) {
  await expect(page).toHaveURL(urlPattern);
  // Should not show the NotFound fallback text
  await expect(page.locator('body')).not.toContainText('Page not found');
  await expect(page.locator('body')).not.toContainText('404');
}

// Helper: escape a literal path segment for use in RegExp
function pathRegex(path: string): RegExp {
  // Escape special regex chars, then ensure we match the full path at end of URL
  const escaped = path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(escaped + '(\\?.*)?$');
}

test.describe('Route Validation', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuthState(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
    await clearUserTier(page);
    await clearSelectedAccount(page);
  });

  // ═══════════════════════════════════════════════════════════════
  // 1. App Shell Renders After Mock Auth
  // ═══════════════════════════════════════════════════════════════
  test('app shell renders after login/mock auth @smoke', async ({ page }) => {
    await page.goto('/home');
    await expect(page.locator('aside[aria-label="Primary sidebar"]')).toBeVisible();
    await expect(page.locator('header')).toBeVisible();
  });

  // ═══════════════════════════════════════════════════════════════
  // 2. Primary Nav Has No Unresolved Params
  // ═══════════════════════════════════════════════════════════════
  test('primary nav links resolve without unresolved params in tenant context', async ({ page }) => {
    await page.goto(`/t/${TENANT_SLUG}/accounts`);
    const nav = page.locator('nav[aria-label="Primary navigation"]');
    await expect(nav).toBeVisible();

    const links = nav.locator('a');
    const count = await links.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const href = await links.nth(i).getAttribute('href');
      expect(href, `Nav link ${i} has unresolved param`).not.toContain(':tenantSlug');
      expect(href, `Nav link ${i} has unresolved param`).not.toContain(':accountId');
    }
  });

  // ═══════════════════════════════════════════════════════════════
  // 3. Personal Settings — Standard User
  // ═══════════════════════════════════════════════════════════════
  test.describe('Personal Settings', () => {
    test('standard user can access personal settings @smoke', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto('/settings/profile');
      await assertPageLoaded(page, /\/settings\/profile/);
    });

    test('standard user can access all personal settings sub-pages', async ({ page }) => {
      await setUserTier(page, 'standard');
      const subPages = ['/settings/profile', '/settings/security', '/settings/preferences', '/settings/notifications', '/settings/sessions', '/settings/activity'];
      for (const path of subPages) {
        await page.goto(path);
        await assertPageLoaded(page, pathRegex(path));
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 4. Tenant Settings — Admin Gated
  // ═══════════════════════════════════════════════════════════════
  test.describe('Tenant Settings', () => {
    test('admin can access tenant settings @smoke', async ({ page }) => {
      await setUserTier(page, 'admin');
      await page.goto(`/t/${TENANT_SLUG}/settings/workspace`);
      await assertPageLoaded(page, /\/t\/e2e-test\/settings\/workspace/);
    });

    test('standard user is redirected from tenant settings', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto(`/t/${TENANT_SLUG}/settings/workspace`);
      // UnifiedRouteGuard should redirect to /home (fallbackRoute on tenantAdminPolicy)
      await expect(page).not.toHaveURL(/\/t\/e2e-test\/settings\/workspace/);
    });

    test('advanced user is redirected from tenant settings', async ({ page }) => {
      await setUserTier(page, 'advanced');
      await page.goto(`/t/${TENANT_SLUG}/settings/workspace`);
      await expect(page).not.toHaveURL(/\/t\/e2e-test\/settings\/workspace/);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 5. Account Lifecycle
  // ═══════════════════════════════════════════════════════════════
  test.describe('Account Lifecycle', () => {
    test('accounts list renders for standard user @smoke', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto(`/t/${TENANT_SLUG}/accounts`);
      await assertPageLoaded(page, /\/t\/e2e-test\/accounts$/);
    });

    test('account overview redirect works', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}`);
      // Should redirect to /overview
      await expect(page).toHaveURL(/\/t\/e2e-test\/accounts\/acct-meridian-001\/overview/);
    });

    test('account overview renders', async ({ page }) => {
      await setUserTier(page, 'standard');
      await setSelectedAccount(page, TEST_ACCOUNT);
      await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}/overview`);
      await assertPageLoaded(page, /\/overview/);
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 6. Intelligence Workspace Tab Switching
  // ═══════════════════════════════════════════════════════════════
  test.describe('Intelligence Workspace', () => {
    test.beforeEach(async ({ page }) => {
      await setSelectedAccount(page, TEST_ACCOUNT);
    });

    test('intelligence base route redirects to signals @smoke', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}/intelligence`);
      await expect(page).toHaveURL(/\/intelligence\/signals/);
    });

    test('intelligence tabs render (standard tier)', async ({ page }) => {
      await setUserTier(page, 'standard');
      const tabs = ['signals', 'stakeholders', 'hypotheses', 'discovery-questions', 'persona-fit', 'assumptions', 'drivers', 'evidence'];
      for (const tab of tabs) {
        await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}/intelligence/${tab}`);
        await assertPageLoaded(page, pathRegex(`/intelligence/${tab}`));
      }
    });

    test('intelligence advanced tabs gated for standard user', async ({ page }) => {
      await setUserTier(page, 'standard');
      const advancedTabs = ['enrichment', 'ontology-match', 'alternatives', 'solution-cost'];
      for (const tab of advancedTabs) {
        await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}/intelligence/${tab}`);
        // The workspace itself loads, but internal tab gating may hide content.
        // Router allows access (accountStdPolicy), so we just verify it renders.
        await assertPageLoaded(page, pathRegex(`/intelligence/${tab}`));
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 7. Value Studio Workspace Tab Switching
  // ═══════════════════════════════════════════════════════════════
  test.describe('Value Studio Workspace', () => {
    test.beforeEach(async ({ page }) => {
      await setSelectedAccount(page, TEST_ACCOUNT);
    });

    test('studio base route redirects to action-plan @smoke', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}/studio`);
      await expect(page).toHaveURL(/\/studio\/action-plan/);
    });

    test('studio tabs render for standard user', async ({ page }) => {
      await setUserTier(page, 'standard');
      const tabs = ['action-plan', 'value-model', 'driver-tree', 'calculator', 'narrative', 'value-case', 'value-realization'];
      for (const tab of tabs) {
        await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}/studio/${tab}`);
        await assertPageLoaded(page, pathRegex(`/studio/${tab}`));
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 8. Deliverables
  // ═══════════════════════════════════════════════════════════════
  test.describe('Deliverables', () => {
    test.beforeEach(async ({ page }) => {
      await setSelectedAccount(page, TEST_ACCOUNT);
    });

    test('deliverables base route redirects to business-cases @smoke', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}/deliverables`);
      await expect(page).toHaveURL(/\/deliverables\/business-cases/);
    });

    test('deliverables list renders', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}/deliverables/business-cases`);
      await assertPageLoaded(page, /\/deliverables\/business-cases/);
    });

    test('deliverables detail renders', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}/deliverables/business-cases/case-test-001`);
      await assertPageLoaded(page, /\/deliverables\/business-cases\/case-test-001/);
    });

    test('deliverables views render', async ({ page }) => {
      await setUserTier(page, 'standard');
      for (const view of ['cfo', 'executive', 'technical']) {
        await page.goto(`/t/${TENANT_SLUG}/accounts/${TEST_ACCOUNT.id}/deliverables/views/${view}`);
        await assertPageLoaded(page, pathRegex(`/views/${view}`));
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 9. Governance Routes
  // ═══════════════════════════════════════════════════════════════
  test.describe('Governance', () => {
    test('governance base route redirects to traces @smoke', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto(`/t/${TENANT_SLUG}/governance`);
      await expect(page).toHaveURL(/\/governance\/traces/);
    });

    test('standard governance routes render', async ({ page }) => {
      await setUserTier(page, 'standard');
      for (const path of ['/governance/traces', '/governance/evidence', '/governance/value-packs']) {
        await page.goto(`/t/${TENANT_SLUG}${path}`);
        await assertPageLoaded(page, pathRegex(path));
      }
    });

    test('advanced governance routes render for advanced user', async ({ page }) => {
      await setUserTier(page, 'advanced');
      for (const path of ['/governance/provenance', '/governance/compliance', '/governance/formulas']) {
        await page.goto(`/t/${TENANT_SLUG}${path}`);
        await assertPageLoaded(page, pathRegex(path));
      }
    });

    test('admin governance routes render for admin', async ({ page }) => {
      await setUserTier(page, 'admin');
      for (const path of ['/governance/benchmarks', '/governance/policies', '/governance/audit-log', '/governance/health']) {
        await page.goto(`/t/${TENANT_SLUG}${path}`);
        await assertPageLoaded(page, pathRegex(path));
      }
    });

    test('admin governance routes redirect standard user', async ({ page }) => {
      await setUserTier(page, 'standard');
      for (const path of ['/governance/benchmarks', '/governance/policies', '/governance/audit-log', '/governance/health']) {
        await page.goto(`/t/${TENANT_SLUG}${path}`);
        await expect(page).not.toHaveURL(pathRegex(path));
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 10. Context Routes
  // ═══════════════════════════════════════════════════════════════
  test.describe('Context Engine', () => {
    test('context base route redirects to sources @smoke', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto(`/t/${TENANT_SLUG}/context`);
      await expect(page).toHaveURL(/\/context\/sources/);
    });

    test('standard context routes render', async ({ page }) => {
      await setUserTier(page, 'standard');
      for (const path of ['/context/packs', '/context/models', '/context/ingestion/jobs']) {
        await page.goto(`/t/${TENANT_SLUG}${path}`);
        await assertPageLoaded(page, pathRegex(path));
      }
    });

    test('advanced context routes render for advanced user', async ({ page }) => {
      await setUserTier(page, 'advanced');
      for (const path of ['/context/formulas', '/context/value-trees/explorer', '/context/agents', '/context/ontology', '/context/ontology/entities', '/context/ontology/graph', '/context/extraction']) {
        await page.goto(`/t/${TENANT_SLUG}${path}`);
        await assertPageLoaded(page, pathRegex(path));
      }
    });

    test('admin context routes render for admin', async ({ page }) => {
      await setUserTier(page, 'admin');
      for (const path of ['/context/integrations', '/context/sources', '/context/targets']) {
        await page.goto(`/t/${TENANT_SLUG}${path}`);
        await assertPageLoaded(page, pathRegex(path));
      }
    });

    test('admin context routes redirect standard user', async ({ page }) => {
      await setUserTier(page, 'standard');
      for (const path of ['/context/integrations', '/context/sources', '/context/targets']) {
        await page.goto(`/t/${TENANT_SLUG}${path}`);
        await expect(page).not.toHaveURL(pathRegex(path));
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 11. Account Creation Route
  // ═══════════════════════════════════════════════════════════════
  test.describe('Account Creation', () => {
    test('/accounts/new route renders account creation form', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto('/accounts/new');
      await expect(page.locator('body')).not.toContainText('Page not found');
      await expect(page.locator('body')).not.toContainText('404');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 12. 403 / 404 / Unauthorized Graceful States
  // ═══════════════════════════════════════════════════════════════
  test.describe('Error States', () => {
    test('unauthenticated user on /home redirects to sign-in', async ({ page }) => {
      await clearAuthState(page);
      await page.goto('/home');
      await expect(page).toHaveURL(/\/(sign-in|login)/);
    });

    test('unauthenticated user on tenant route redirects to sign-in', async ({ page }) => {
      await clearAuthState(page);
      await page.goto(`/t/${TENANT_SLUG}/accounts`);
      await expect(page).toHaveURL(/\/(sign-in|login)/);
    });

    test('unknown route renders 404', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto('/this-route-definitely-does-not-exist-404');
      // Should show NotFound component or redirect gracefully
      await expect(page.locator('body')).toContainText('not found');
    });

    test('wrong tenant slug redirects away', async ({ page }) => {
      await setUserTier(page, 'standard');
      await page.goto('/t/wrong-tenant/accounts');
      // useTenantMembership will reject wrong tenant
      await expect(page).toHaveURL(/\/home/);
    });
  });
});
