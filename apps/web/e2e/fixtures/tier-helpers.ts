/**
 * Tier/permission helpers for access control testing
 *
 * Provides utilities to set user tier and verify route access
 * in a way that respects the application's actual access control logic.
 *
 * IMPORTANT: All localStorage operations require the page to be on a
 * same-origin URL first. These helpers ensure that by navigating to
 * the app if the page is still on about:blank.
 */

import { Page } from '@playwright/test';

export type UserTier = 'standard' | 'advanced' | 'admin';

/**
 * Backend-canonical roles from identity provider
 */
export type BackendRole =
  | 'super_admin'
  | 'tenant_admin'
  | 'content_admin'
  | 'analyst'
  | 'read_only'
  | 'system'
  | 'admin'
  | 'advanced'
  | 'standard';

/**
 * Ensure the page is on a same-origin URL so localStorage is accessible.
 */
async function ensureSameOrigin(page: Page): Promise<void> {
  const url = page.url();
  if (url === 'about:blank' || url === '' || url === 'chrome://newtab/') {
    await page.goto('/sign-in', { waitUntil: 'domcontentloaded' });
  }
  await page.waitForLoadState('domcontentloaded').catch(() => {
    // The caller only needs a stable same-origin execution context.
  });
}

/**
 * Set the user tier in localStorage (simulating login/role assignment)
 *
 * This works because the app uses Zustand with persist middleware
 * to store tier state in localStorage under the key 'user-tier-storage'.
 *
 * @param page - Playwright page object
 * @param tier - Frontend presentation tier
 * @param backendRole - Optional backend-canonical role (defaults to tier value)
 */
export async function setUserTier(
  page: Page,
  tier: UserTier,
  backendRole?: BackendRole
): Promise<void> {
  await ensureSameOrigin(page);
  const role = backendRole || tier;
  const seededTierState = {
    state: {
      currentTier: tier,
      isAdvancedModeEnabled: tier !== 'standard',
      userRole: role,
    },
    version: 0,
  };

  await page.evaluate((params: { userTier: UserTier; role: string; storeState: typeof seededTierState }) => {
    // 1. Set the zustand tier store
    const storeKey = 'user-tier-storage';
    const storeState = params.storeState;
    localStorage.setItem(storeKey, JSON.stringify(storeState));

    // 2. Also sync the auth user's role in userInfo so that
    //    AuthContext.initAuth() → setUserRole() doesn't overwrite the tier.
    //    This is critical: the app reads userInfo.role on boot and calls
    //    setUserRole(role) which normalizes to a tier and overwrites the store.
    const userInfoRaw = localStorage.getItem('userInfo');
    let updatedUserInfo: Record<string, unknown> | null = null;
    if (userInfoRaw) {
      try {
        const userInfo = JSON.parse(userInfoRaw) as Record<string, unknown>;
        userInfo.role = params.role;
        updatedUserInfo = userInfo;
        localStorage.setItem('userInfo', JSON.stringify(userInfo));
      } catch {
        // ignore parse errors
      }
    }

    const sessionMetaRaw = sessionStorage.getItem('vf.auth.session.meta');
    if (sessionMetaRaw) {
      try {
        const sessionMeta = JSON.parse(sessionMetaRaw) as Record<string, unknown>;
        const sessionUser = (
          typeof sessionMeta.user === 'object' && sessionMeta.user !== null
            ? { ...(sessionMeta.user as Record<string, unknown>) }
            : updatedUserInfo
        );
        if (sessionUser) {
          sessionUser.role = params.role;
          sessionMeta.user = sessionUser;
          sessionStorage.setItem('vf.auth.session.meta', JSON.stringify(sessionMeta));
        }
      } catch {
        // ignore parse errors
      }
    }

    // Also set a flag for tests to detect
    localStorage.setItem('test-user-tier', params.userTier);
  }, { userTier: tier, role, storeState: seededTierState });

  // The app may already have initialized the persisted Zustand store on the
  // bootstrap page. Reload so route guards hydrate the seeded tier before the
  // next navigation evaluates access.
  await page.reload({ waitUntil: 'domcontentloaded' });
}

/**
 * Enable advanced mode for a standard user (progressive disclosure toggle)
 */
export async function enableAdvancedMode(page: Page): Promise<void> {
  await ensureSameOrigin(page);

  await page.evaluate(() => {
    const storeKey = 'user-tier-storage';
    const existing = localStorage.getItem(storeKey);
    const storeState = existing
      ? JSON.parse(existing)
      : { state: { currentTier: 'standard', isAdvancedModeEnabled: false, userRole: null }, version: 0 };

    storeState.state.isAdvancedModeEnabled = true;
    localStorage.setItem(storeKey, JSON.stringify(storeState));
  });

  await page.reload();
}

/**
 * Disable advanced mode
 */
export async function disableAdvancedMode(page: Page): Promise<void> {
  await ensureSameOrigin(page);

  await page.evaluate(() => {
    const storeKey = 'user-tier-storage';
    const existing = localStorage.getItem(storeKey);
    if (!existing) return;

    const storeState = JSON.parse(existing);
    storeState.state.isAdvancedModeEnabled = false;
    localStorage.setItem(storeKey, JSON.stringify(storeState));
  });

  await page.reload();
}

/**
 * Clear user tier (logout/reset)
 */
export async function clearUserTier(page: Page): Promise<void> {
  try {
    await page.evaluate(() => {
      localStorage.removeItem('user-tier-storage');
      localStorage.removeItem('test-user-tier');
    });
  } catch {
    // Page may already be closed — safe to ignore
  }
}

/**
 * Get current tier from page
 */
export async function getCurrentTier(page: Page): Promise<UserTier | null> {
  return page.evaluate(() => {
    const stored = localStorage.getItem('user-tier-storage');
    if (!stored) return null;
    try {
      const parsed = JSON.parse(stored);
      return parsed.state?.currentTier || null;
    } catch {
      return null;
    }
  });
}

/**
 * Routes accessible by tier — uses CANONICAL URLs (not redirect aliases).
 *
 * IMPORTANT: The app defines many legacy alias routes (e.g., /library/packs,
 * /discover/accounts) that immediately redirect via <Navigate>. Tests must
 * use the canonical destination URLs so assertions match the final URL after
 * redirect.
 *
 * Mapping of aliases → canonical:
 *   /library/packs          → /context/packs
 *   /discover/accounts      → /accounts
 *   /discover/jobs          → /context/ingestion/jobs
 *   /discover/extraction    → /context/extraction
 *   /discover/knowledge/graph    → /context/ontology/graph
 *   /discover/knowledge/ontology → /context/ontology
 *   /model/value-studio/explorer → /context/value-trees/explorer
 *   /model/value-studio/formulas → /context/formulas
 *   /deliver/cases          → /deliverables/cases
 *   /deliver/agents         → /context/agents
 *   /evidence/traces        → /governance/traces
 *   /admin/content/benchmarks → /t/{tenant}/governance/benchmarks
 *   /admin/data/integrations  → /t/{tenant}/context/integrations
 */
/**
 * Tenant slug used for tier-gated route tests. Keep this in sync with the
 * tenant seeded by the test harness (auth-helpers / global setup).
 */
export const TEST_TENANT_SLUG = 'demo';

/**
 * Build a tenant-scoped route under the canonical test tenant.
 */
export function tenantRoute(path: string): string {
  return `/t/${TEST_TENANT_SLUG}${path}`;
}

export const ROUTES_BY_TIER: Record<UserTier, { accessible: string[]; restricted: string[] }> = {
  standard: {
    accessible: [
      '/home',
      '/context/packs',
      '/accounts',
      '/context/ingestion/jobs',
      '/deliverables/cases',
      '/governance/traces',
    ],
    restricted: [
      '/context/extraction',
      '/context/ontology/graph',
      '/context/ontology',
      '/context/value-trees/explorer',
      '/context/formulas',
      tenantRoute('/governance/benchmarks'),
    ],
  },
  advanced: {
    accessible: [
      '/home',
      '/context/packs',
      '/accounts',
      '/context/ingestion/jobs',
      '/context/extraction',
      '/context/ontology/graph',
      '/context/ontology',
      '/context/value-trees/explorer',
      '/context/formulas',
      '/deliverables/cases',
      '/context/agents',
      '/governance/traces',
    ],
    restricted: [
      tenantRoute('/governance/benchmarks'),
      tenantRoute('/settings'),
      tenantRoute('/context/integrations'),
    ],
  },
  admin: {
    accessible: [
      '/home',
      '/context/packs',
      '/accounts',
      '/context/extraction',
      '/context/ontology/graph',
      '/context/value-trees/explorer',
      '/context/formulas',
      '/deliverables/cases',
      '/context/agents',
      '/governance/traces',
      tenantRoute('/governance/benchmarks'),
      tenantRoute('/settings'),
      tenantRoute('/context/integrations'),
    ],
    restricted: [],
  },
};

/**
 * Expected redirect destination when accessing restricted routes.
 * The RouteGuard in App.tsx redirects all restricted access to /home.
 */
export const TIER_REDIRECTS: Record<UserTier, string> = {
  standard: '/home',
  advanced: '/home',
  admin: '/home',
};

/**
 * Navigate to a route, ensuring the page is on a same-origin URL first.
 */
export async function navigateToRoute(page: Page, route: string): Promise<void> {
  await page.goto(route, { waitUntil: 'domcontentloaded' });
}

/**
 * Wait for the DOM to stabilise (no pending network activity).
 * Falls back gracefully if networkidle times out (e.g. long-polling pages).
 */
export async function waitForStableDOM(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {
    // networkidle can be unreliable on pages with persistent connections;
    // domcontentloaded is already satisfied at this point.
  });
}
