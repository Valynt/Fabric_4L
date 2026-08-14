/**
 * FULL UI DEBUG SUITE
 * Diagnoses routing, navigation, layout, and console errors across the entire SPA.
 *
 * Run: cd frontend && pnpm exec playwright test e2e/journeys/full-ui-debug.spec.ts --project=journeys --reporter=list
 */
import { test, expect, type ConsoleMessage, type Page } from '../fixtures/contract-test';
import { setUserTier, seedAuthState, clearUserTier, clearAuthState } from '../fixtures';
import { ACCOUNT_CONTEXT_STORAGE_KEY, ACCOUNT_CONTEXT_STORAGE_VERSION } from '@fabric/platform-contract/stores';

type RouteStatus = 'ok' | '404' | 'error' | 'redirect' | 'timeout' | 'crash';

interface RouteResult {
  path: string;
  status: RouteStatus;
  finalUrl: string;
  consoleErrors: string[];
  pageErrors: string[];
  hasSidebar: boolean;
  hasHeader: boolean;
}

const ALL_ROUTES = [
  { path: '/login', auth: false },
  { path: '/home', tier: 'standard' as const },
  { path: '/accounts', tier: 'standard' as const },
  { path: '/intelligence', tier: 'standard' as const, scoped: true },
  { path: '/hypothesis', tier: 'standard' as const, scoped: true },
  { path: '/drivers', tier: 'standard' as const, scoped: true },
  { path: '/calculator', tier: 'standard' as const, scoped: true },
  { path: '/value-case', tier: 'standard' as const, scoped: true },
  { path: '/realization', tier: 'standard' as const, scoped: true },
  { path: '/accounts/new', tier: 'standard' as const },
  { path: '/context/packs', tier: 'advanced' as const },
  { path: '/context/ontology/graph', tier: 'advanced' as const },
  { path: '/graph-explorer', tier: 'advanced' as const },
  { path: '/formula-builder', tier: 'advanced' as const },
  { path: '/settings', tier: 'admin' as const },
  { path: '/settings/content/formulas', tier: 'admin' as const },
  { path: '/governance', tier: 'standard' as const },
  { path: '/trust', tier: 'standard' as const, alias: true },
  { path: '/deliverables/cases', tier: 'standard' as const },
  { path: '/studio', tier: 'standard' as const, scoped: true },
];

type ConsoleErrorHandler = (message: ConsoleMessage) => void;

function isErrorWithName(value: unknown): value is { name: string } {
  return typeof value === 'object' && value !== null && 'name' in value && typeof (value as { name: unknown }).name === 'string';
}

async function diagnoseRoute(page: Page, route: typeof ALL_ROUTES[number]): Promise<RouteResult> {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const onConsole: ConsoleErrorHandler = (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); };
  const onPageError = (err: Error) => pageErrors.push(err.message);
  page.on('console', onConsole);
  page.on('pageerror', onPageError);

  if (route.tier) {
    await seedAuthState(page, {
      id: 'debug-user', email: 'debug@valuefabric.test', role: route.tier,
      tenantId: 'tenant-debug', tenantSlug: 'debug',
    });
    await setUserTier(page, route.tier);
  }

  if (route.scoped) {
    await page.evaluate(({ storageKey, storageVersion }) => {
      try {
        sessionStorage.setItem(storageKey, JSON.stringify({ state: { fabricTenantId: 'tenant-debug', selectedAccountId: 'acc-debug-001' }, version: storageVersion }));
      } catch {}
    }, { storageKey: ACCOUNT_CONTEXT_STORAGE_KEY, storageVersion: ACCOUNT_CONTEXT_STORAGE_VERSION });
  }

  let status: RouteResult['status'] = 'ok';
  let finalUrl = '';
  let hasSidebar = false;
  let hasHeader = false;

  try {
    await page.goto(route.path, { waitUntil: 'domcontentloaded', timeout: 10000 });
    // Give React time to hydrate
    await page.waitForTimeout(800);
    finalUrl = page.url();

    // Check for 404 indicators (strict: actual 404 page, not API error messages)
    const has404Heading = await page.locator('h1:has-text("404"), h2:has-text("404"), [data-testid="not-found"]').count() > 0;
    const has404PageText = await page.locator('text=Page Not Found').count() > 0;
    if (finalUrl.includes('/not-found') || finalUrl.includes('/404') || has404Heading || has404PageText) {
      status = '404';
    } else if (finalUrl !== route.path && !route.scoped && !route.alias) {
      status = 'redirect';
    }

    // Layout checks: look for header and at least one sidebar (desktop or mobile)
    hasHeader = await page.locator('header').isVisible().catch(() => false);
    hasSidebar = await page.locator('aside:visible, nav:visible').count().then(c => c > 0).catch(() => false);

    // Screenshot
    const safe = route.path.replace(/[^a-z0-9]/gi, '_');
    await page.screenshot({ path: `e2e-results/debug-${safe}-${status}.png`, fullPage: false });
  } catch (e: unknown) {
    status = isErrorWithName(e) && e.name.includes('Timeout') ? 'timeout' : 'error';
    finalUrl = page.url();
  }

  page.off('console', onConsole);
  page.off('pageerror', onPageError);

  return { path: route.path, status, finalUrl, consoleErrors: consoleErrors.slice(0, 5), pageErrors: pageErrors.slice(0, 5), hasSidebar, hasHeader };
}

test.describe('Full UI Debug @debug', () => {
  test.setTimeout(120000);

  test('diagnose all routes and print report', async ({ page }) => {
    const results: RouteResult[] = [];
    for (const route of ALL_ROUTES) {
      await clearAuthState(page); await clearUserTier(page);
      results.push(await diagnoseRoute(page, route));
    }

    const summary = {
      timestamp: new Date().toISOString(),
      total: results.length,
      ok: results.filter(r => r.status === 'ok').length,
      redirect: results.filter(r => r.status === 'redirect').length,
      error: results.filter(r => r.status === 'error').length,
      notFound: results.filter(r => r.status === '404').length,
      timeout: results.filter(r => r.status === 'timeout').length,
      missingSidebar: results.filter(r => r.status === 'ok' && !r.hasSidebar).map(r => r.path),
      missingHeader: results.filter(r => r.status === 'ok' && !r.hasHeader).map(r => r.path),
      failures: results.filter(r => r.status !== 'ok' && r.status !== 'redirect'),
      allResults: results,
    };

    console.log('\n========== DEBUG REPORT ==========\n' + JSON.stringify(summary, null, 2));

    for (const c of ['/home', '/accounts', '/login', '/accounts/new']) {
      const r = results.find(x => x.path === c);
      expect(r?.status, `Critical route ${c} failed with status ${r?.status}`).toMatch(/ok|redirect/);
    }
  });
});
