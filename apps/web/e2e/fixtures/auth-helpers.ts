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
 * Stable identities reserved by scripts/db/seed-e2e-data.ts. Use these to
 * exercise role-authenticated and cross-tenant workflows without weakening
 * the backend minted-session path.
 *
 * - REVIEWER lives in the alpha (default) tenant and backs reviewer approval
 *   affordance assertions.
 * - TENANT_B_USER lives in the Beta tenant; cross-tenant reads from Beta are
 *   denied by seed verification (attemptCrossTenantVerification).
 */
export const E2E_REVIEWER_USER: TestUserInfo = {
  id: 'e2e-reviewer-user',
  email: 'reviewer@valuefabric.test',
  role: 'reviewer',
  tenantId: BACKEND_E2E_TENANT_ID,
  tenantSlug: 'e2e-test',
};

export const E2E_TENANT_BETA_ID =
  process.env.BACKEND_E2E_TENANT_BETA_ID || '00000000-0000-4000-e2e0-000000000002';

export const E2E_TENANT_B_USER: TestUserInfo = {
  id: 'e2e-reviewer-user',
  email: 'tenant-b@valuefabric.test',
  role: 'reviewer',
  tenantId: E2E_TENANT_BETA_ID,
  tenantSlug: 'tenant-e2e-beta',
};

/**
 * Determine the canonical backend role to send on a seed session request.
 *
 * The default admin test user must keep minting the super_admin session the
 * suite already relies on. Distinct requested roles (reviewer / sales /
 * read-only) are passed through so the minted session honors seed role
 * bindings for role-authenticated workflows instead of always escalating to
 * super_admin.
 */
export function canonicalSeedRole(role: string): string {
  if (role === 'admin' || role === 'super_admin') {
    return 'super_admin';
  }
  return role;
}

/**
 * Ensure the page is on a same-origin URL so localStorage is accessible.
 * If the page is on about:blank or a different origin, navigates to '/'.
 */
async function ensureSameOrigin(page: Page): Promise<void> {
  const url = page.url();
  if (url === 'about:blank' || url === '' || url === 'chrome://newtab/') {
    // Navigate to the app root rather than /login; /login may not exist in
    // legacy auth builds and would cause a 404 before localStorage seeding.
    await page.goto('/', { waitUntil: 'commit' });
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

  const backendUrl = process.env.PLAYWRIGHT_BACKEND_URL;
  const frontendOrigin = liveFrontendOrigin(page);
  // Use the backend directly when available to avoid Vite proxy timeouts/noise
  // during test fixture setup. The validation/session endpoint is still
  // requested service-to-service (X-Service-Auth), so the URL origin does not
  // affect authorization semantics.
  const sessionUrl = backendUrl
    ? `${backendUrl.replace(/\/$/, '')}/v1/validation/session`
    : `${frontendOrigin}/api/v1/agents/validation/session`;
  const requestUser = normalizeLiveUser(user);
  const response = await page.request.post(sessionUrl, {
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': requestUser.tenantId,
      'X-Service-Auth': serviceSecret,
      'X-Privileged-Reason': E2E_SEED_PRIVILEGED_REASON,
    },
    data: {
      user_id: requestUser.id,
      email: requestUser.email,
      role: canonicalSeedRole(requestUser.role),
      tenant_slug: requestUser.tenantSlug,
    },
  });

  if (!response.ok()) {
    throw new Error(`Backend-integrated validation session request failed: ${response.status()} ${await response.text()}`);
  }

  const payload = await response.json();

  // Persist the httpOnly vf_session cookie into the Playwright browser context
  // so that legacy mode API requests are authenticated. Playwright's
  // page.request does not automatically transfer Set-Cookie into the browser
  // context, and httpOnly cookies cannot be set from JavaScript.
  const setCookieHeader = response.headers()['set-cookie'];
  if (setCookieHeader) {
    // The browser sends API requests to the frontend origin (Vite proxies them
    // to the backend in legacy mode), so the cookie must be scoped to the
    // frontend hostname — not the backend host the session was minted from.
    const cookieDomain = new URL(frontendOrigin).hostname;
    const cookies = parseSetCookieHeader(setCookieHeader, cookieDomain);
    if (cookies.length > 0) {
      await page.context().addCookies(
        cookies.map((c) => ({
          name: c.name,
          value: c.value,
          domain: cookieDomain,
          path: c.path,
          httpOnly: c.httpOnly,
          secure: c.secure,
          sameSite: c.sameSite as 'Strict' | 'Lax' | 'None' | undefined,
          expires: c.expires,
        }))
      );
    }
  }

  return payload.user as TestUserInfo;
}

/**
 * Parse a raw Set-Cookie header value (possibly comma-joined) into cookie
 * objects suitable for Playwright's context.addCookies().
 */
function parseSetCookieHeader(
  header: string | string[],
  defaultDomain: string
): Array<{
  name: string;
  value: string;
  domain: string;
  path: string;
  httpOnly: boolean;
  secure: boolean;
  sameSite: 'Strict' | 'Lax' | 'None' | undefined;
  expires: number;
}> {
  const raw = Array.isArray(header) ? header.join(', ') : header;
  // Split on cookie-name boundaries; a new cookie starts with a name=value pair
  // followed by attributes. The two cookie names we issue are vf_session and
  // vf_csrf_token.
  const cookieTexts = raw
    .split(/,(?=[^\s=]+=)/)
    .map((s) => s.trim())
    .filter(Boolean);

  return cookieTexts
    .map((text) => {
      const parts = text.split(';').map((p) => p.trim());
      const [name, ...valueParts] = parts[0].split('=');
      if (!name) return null;
      const value = valueParts.join('=').trim();
      const attrs = new Map<string, string>();
      let httpOnly = false;
      let secure = false;
      let sameSite: 'Strict' | 'Lax' | 'None' | undefined = undefined;
      let path = '/';
      let maxAge: number | undefined;
      let expires: number | undefined;

      for (let i = 1; i < parts.length; i++) {
        const part = parts[i];
        const [attrName, ...attrValueParts] = part.split('=');
        const normalized = attrName.trim().toLowerCase();
        const attrValue = attrValueParts.join('=').trim();
        if (normalized === 'httponly') httpOnly = true;
        else if (normalized === 'secure') secure = true;
        else if (normalized === 'samesite') {
          const v = attrValue.toLowerCase();
          if (v === 'strict') sameSite = 'Strict';
          else if (v === 'lax') sameSite = 'Lax';
          else if (v === 'none') sameSite = 'None';
        } else if (normalized === 'path') path = attrValue || '/';
        else if (normalized === 'max-age') maxAge = parseInt(attrValue, 10);
        else if (normalized === 'expires') {
          const ts = Date.parse(attrValue);
          if (!Number.isNaN(ts)) expires = Math.round(ts / 1000);
        }
      }

      return {
        name: name.trim(),
        value,
        domain: defaultDomain,
        path,
        httpOnly,
        secure,
        sameSite,
        expires: expires ?? (maxAge ? Math.floor(Date.now() / 1000) + maxAge : Math.floor(Date.now() / 1000) + 3600),
      };
    })
    .filter((c): c is NonNullable<typeof c> => c !== null);
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

/**
 * Set an expired access token to simulate session expiry.
 * This is used to test token refresh and expiry handling.
 */
export async function setExpiredToken(page: Page, user: TestUserInfo = DEFAULT_TEST_USER): Promise<void> {
  await ensureSameOrigin(page);

  await page.evaluate((u) => {
    // Generate a token that is already expired
    const payload = {
      exp: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
      iat: Math.floor(Date.now() / 1000) - 7200,
      sub: u.id,
      tenant_id: u.tenantId,
    };
    const base64Payload = btoa(JSON.stringify(payload));
    const token = `header.${base64Payload}.signature`;

    localStorage.setItem('accessToken', token);
    localStorage.setItem('userInfo', JSON.stringify(u));
    localStorage.setItem('tenantId', u.tenantId);
    sessionStorage.setItem('vf.auth.session.meta', JSON.stringify({ user: u, tenantId: u.tenantId }));
  }, user);
}

/**
 * Set a token that will expire soon (within 30 seconds).
 * This is used to test proactive token refresh.
 */
export async function setExpiringToken(page: Page, user: TestUserInfo = DEFAULT_TEST_USER): Promise<void> {
  await ensureSameOrigin(page);

  await page.evaluate((u) => {
    // Generate a token that expires in 30 seconds
    const payload = {
      exp: Math.floor(Date.now() / 1000) + 30,
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
  }, user);
}

/**
 * Check if the current session is expired based on token payload.
 */
export async function isSessionExpired(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) return true;

    try {
      const parts = token.split('.');
      if (parts.length < 2) return true;

      const payload = JSON.parse(atob(parts[1]));
      const now = Math.floor(Date.now() / 1000);
      return payload.exp < now;
    } catch {
      return true;
    }
  });
}

/**
 * Simulate a multi-tab session by copying session state to another page.
 * This is used to test session synchronization across tabs.
 */
export async function syncSessionToPage(sourcePage: Page, targetPage: Page): Promise<void> {
  const sessionData = await sourcePage.evaluate(() => {
    return {
      accessToken: localStorage.getItem('accessToken'),
      userInfo: localStorage.getItem('userInfo'),
      tenantId: localStorage.getItem('tenantId'),
      sessionMeta: sessionStorage.getItem('vf.auth.session.meta'),
    };
  });

  await targetPage.evaluate((data) => {
    if (data.accessToken) localStorage.setItem('accessToken', data.accessToken);
    if (data.userInfo) localStorage.setItem('userInfo', data.userInfo);
    if (data.tenantId) localStorage.setItem('tenantId', data.tenantId);
    if (data.sessionMeta) sessionStorage.setItem('vf.auth.session.meta', data.sessionMeta);
  }, sessionData);
}
