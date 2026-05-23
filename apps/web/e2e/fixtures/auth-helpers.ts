import { E2E_SEED_PRIVILEGED_REASON, E2E_SEED_TENANT_SLUG } from './seed-constants';
/**
 * Auth Helpers for Playwright Contract Tests
 *
 * Seeds the browser's localStorage with a valid authenticated session
 * so that RouteGuard (AuthContext) considers the user logged in.
 *
 * Contract: AuthContext.initAuth() checks:
 *   1. localStorage.getItem('accessToken') — must be truthy
 *   2. authClient.getCurrentSession() — reads 'userInfo' from localStorage
 *      and validates against UserInfoSchema (id, email, role, tenantId, tenantSlug)
 *
 * IMPORTANT: page.evaluate() can only access localStorage when the page
 * is on a same-origin URL (not about:blank). All helpers navigate first
 * if the page hasn't been loaded yet.
 */
import { Page } from '@playwright/test';

export interface TestUserInfo {
  id: string;
  email: string;
  role: string;
  tenantId: string;
  tenantSlug: string;
}

export const BACKEND_E2E_TENANT_ID =
  process.env.BACKEND_E2E_TENANT_ID || '00000000-0000-4000-e2e0-000000000001';
const BACKEND_E2E_USER_ID =
  process.env.BACKEND_E2E_USER_ID || '00000000-0000-4000-e2e0-0000000000a1';

/**
 * Default test user — admin role for maximum access in contract tests.
 * Individual tests override tier via setUserTier() after this.
 */
export const DEFAULT_TEST_USER: TestUserInfo = {
  id: 'test-user-e2e',
  email: 'e2e@valuefabric.test',
  role: 'admin',
  tenantId: E2E_SEED_TENANT_SLUG,
  tenantSlug: 'e2e-test',
};

/**
 * Ensure the page is on a same-origin URL so localStorage is accessible.
 * If the page is on about:blank or a different origin, navigates to '/'.
 */
async function ensureSameOrigin(page: Page): Promise<void> {
  const url = page.url();
  if (url === 'about:blank' || url === '' || url === 'chrome://newtab/') {
    await page.goto('/login', { waitUntil: 'commit' });
  }
}

/**
 * Generate a valid JWT-format token for E2E tests.
 * refreshToken() validates JWT structure (header.payload.signature)
 * and checks expiry, so test tokens must conform.
 */
function generateTestToken(userId: string, tenantId: string): string {
  const payload = {
    exp: Math.floor(Date.now() / 1000) + 86400, // 24 hours from now
    iat: Math.floor(Date.now() / 1000),
    sub: userId,
    tenant_id: tenantId,
  };
  const base64Payload = btoa(JSON.stringify(payload));
  return `header.${base64Payload}.signature`;
}

function isBackendIntegratedLiveMode(): boolean {
  return process.env.PLAYWRIGHT_LIVE_MODE === 'true' && Boolean(process.env.PLAYWRIGHT_BACKEND_URL);
}

function liveFrontendOrigin(page: Page): string {
  const configured = process.env.PLAYWRIGHT_LIVE_FRONTEND_URL || process.env.PLAYWRIGHT_BASE_URL;
  if (configured) {
    return new URL(configured).origin;
  }
  return new URL(page.url()).origin;
}

function normalizeLiveUser(user: TestUserInfo): TestUserInfo {
  if (user.tenantId !== DEFAULT_TEST_USER.tenantId) {
    return user;
  }
  return {
    ...user,
    id: BACKEND_E2E_USER_ID,
    tenantId: BACKEND_E2E_TENANT_ID,
    tenantSlug: 'e2e-test',
  };
}

function seedBrowserSessionScript(u: TestUserInfo) {
  const payload = {
    exp: Math.floor(Date.now() / 1000) + 86400,
    iat: Math.floor(Date.now() / 1000),
    sub: u.id,
    tenant_id: u.tenantId,
  };
  const base64Payload = btoa(JSON.stringify(payload));
  const token = `header.${base64Payload}.signature`;

  localStorage.setItem('accessToken', token);
  localStorage.setItem('userInfo', JSON.stringify(u));
  localStorage.setItem('tenantId', u.tenantId);
  sessionStorage.setItem('vf.auth.session.meta', JSON.stringify({ user: u, tenantId: u.tenantId }));
}

async function waitForSeededBrowserSession(page: Page, user: TestUserInfo): Promise<void> {
  await page.waitForFunction(
    (expected) => {
      const sessionRaw = sessionStorage.getItem('vf.auth.session.meta');
      const accessToken = localStorage.getItem('accessToken');
      const tenantId = localStorage.getItem('tenantId');
      const userInfoRaw = localStorage.getItem('userInfo');

      if (!sessionRaw || !accessToken || tenantId !== expected.tenantId || !userInfoRaw) {
        return false;
      }

      try {
        const session = JSON.parse(sessionRaw);
        const userInfo = JSON.parse(userInfoRaw);
        return (
          session?.tenantId === expected.tenantId &&
          session?.user?.id === expected.id &&
          userInfo?.id === expected.id &&
          userInfo?.tenantId === expected.tenantId
        );
      } catch {
        return false;
      }
    },
    user,
    { timeout: 10000 },
  ).catch((error) => {
    throw new Error(
      `Backend-integrated auth session was not ready after validation session seed for user ${user.id}. ` +
      `${error instanceof Error ? error.message : String(error)}`,
    );
  });
}

async function seedBackendIntegratedSession(page: Page, user: TestUserInfo): Promise<TestUserInfo> {
  const serviceSecret = process.env.SERVICE_AUTH_SECRET;
  if (!serviceSecret) {
    throw new Error('SERVICE_AUTH_SECRET is required for backend-integrated Playwright auth seeding.');
  }

  const frontendOrigin = liveFrontendOrigin(page);
  const requestUser = normalizeLiveUser(user);
  const response = await page.request.post(`${frontendOrigin}/api/v1/agents/validation/session`, {
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': requestUser.tenantId,
      'X-Service-Auth': serviceSecret,
      'X-Privileged-Reason': E2E_SEED_PRIVILEGED_REASON,
    },
    data: {
      user_id: requestUser.id,
      email: requestUser.email,
      role: 'super_admin',
      tenant_slug: requestUser.tenantSlug,
    },
  });

  if (!response.ok()) {
    throw new Error(`Backend-integrated validation session request failed: ${response.status()} ${await response.text()}`);
  }

  const payload = await response.json();
  return payload.user as TestUserInfo;
}

/**
 * Seed authenticated session in localStorage.
 * Must be called before any route navigation that requires auth.
 *
 * @param page - Playwright page object
 * @param user - Optional user info override (defaults to admin test user)
 */
export async function seedAuthState(
  page: Page,
  user: TestUserInfo = DEFAULT_TEST_USER
): Promise<void> {
  const liveMode = isBackendIntegratedLiveMode();
  const seededUser = liveMode ? await seedBackendIntegratedSession(page, user) : user;

  if (liveMode) {
    await page.addInitScript(seedBrowserSessionScript, seededUser);
    await ensureSameOrigin(page);
    await page.evaluate(seedBrowserSessionScript, seededUser);
    await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => undefined);
    await waitForSeededBrowserSession(page, seededUser);
    return;
  }

  await ensureSameOrigin(page);

  await page.evaluate((u) => {
    // Generate a valid JWT-format token so refreshToken() doesn't clear it
    const payload = {
      exp: Math.floor(Date.now() / 1000) + 86400, // 24 hours from now
      iat: Math.floor(Date.now() / 1000),
      sub: u.id,
      tenant_id: u.tenantId,
    };
    const base64Payload = btoa(JSON.stringify(payload));
    const token = `header.${base64Payload}.signature`;

    localStorage.setItem('accessToken', token);
    localStorage.setItem('userInfo', JSON.stringify(u));
    localStorage.setItem('tenantId', u.tenantId);

    // Current auth uses cookie-backed sessions with non-secret metadata in
    // sessionStorage. Keep the legacy localStorage keys above for older E2E
    // helpers, but seed the canonical session metadata key so AuthProvider and
    // ProtectedRoute treat the journey page as authenticated.
    sessionStorage.setItem('vf.auth.session.meta', JSON.stringify({ user: u, tenantId: u.tenantId }));
  }, seededUser);

  // AuthProvider reads sessionStorage on mount. If ensureSameOrigin loaded the
  // app at /login before storage was seeded, reload once so the provider observes
  // the seeded session instead of retaining the unauthenticated initial state.
  await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => undefined);
  await waitForSeededBrowserSession(page, seededUser);
}

/**
 * Clear authenticated session from localStorage.
 */
export async function clearAuthState(page: Page): Promise<void> {
  try {
    await page.evaluate(() => {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('userInfo');
      localStorage.removeItem('tenantId');
      sessionStorage.removeItem('vf.auth.session.meta');
    });
  } catch {
    // Page may already be closed or on about:blank — safe to ignore
  }
}
