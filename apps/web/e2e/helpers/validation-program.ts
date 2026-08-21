import type { Page, Route } from '@playwright/test';
import { expect } from '@playwright/test';
import { expectNoErrors, navigateAndWait } from './journey-fixture';
import { isLiveMode } from './api-harness';

export type ValidationTraceability = {
  id: string;
  suite: string;
  workflow: string;
  priority: 'P0 production gate' | 'P1 core workflow' | 'P2 important workflow';
};

// ── Deep-Test Utility Helpers ────────────────────────────────────────────────

export interface FormField {
  /** Locator strategy: 'label' | 'placeholder' | 'testid' | 'role' */
  by: 'label' | 'placeholder' | 'testid' | 'role';
  selector: string;
  value: string;
  /** For select/dropdown fields */
  type?: 'input' | 'select' | 'textarea';
}

/**
 * Fill a form and submit it, then assert a visible outcome.
 * Finds fields using accessible selectors and fills them.
 */
export async function expectFormSubmission(
  page: Page,
  fields: FormField[],
  submitButton: string | RegExp,
  expectedOutcome: string | RegExp,
  timeout = 10000,
): Promise<void> {
  for (const field of fields) {
    let locator;
    switch (field.by) {
      case 'label':
        locator = page.getByLabel(field.selector);
        break;
      case 'placeholder':
        locator = page.getByPlaceholder(field.selector);
        break;
      case 'testid':
        locator = page.getByTestId(field.selector);
        break;
      case 'role':
        locator = page.getByRole('textbox', { name: field.selector });
        break;
    }
    if (field.type === 'select') {
      await locator.selectOption(field.value);
    } else {
      await locator.fill(field.value);
    }
  }

  const btn = page.getByRole('button', { name: submitButton }).first();
  await expect(btn).toBeVisible({ timeout: 5000 });
  await btn.click();
  await expect(page.getByText(expectedOutcome).first()).toBeVisible({ timeout });
}

/**
 * Navigate to a path, perform a sequence of actions, and verify the outcome.
 */
export async function expectWorkflowStep(
  page: Page,
  path: string,
  actions: Array<{ click?: string | RegExp; fill?: { selector: string; value: string }; wait?: number }>,
  expectedOutcome: string | RegExp,
  timeout = 10000,
): Promise<void> {
  await navigateAndWait(page, path);
  await expectNoErrors(page);

  for (const action of actions) {
    if (action.wait) {
      await page.waitForLoadState('networkidle', { timeout: action.wait }).catch(async () => {
        await page.waitForLoadState('domcontentloaded', { timeout: action.wait });
      });
    }
    if (action.click) {
      const target = page.getByRole('button', { name: action.click })
        .or(page.getByRole('link', { name: action.click }))
        .or(page.getByRole('tab', { name: action.click }))
        .or(page.getByText(action.click))
        .first();
      await expect(target).toBeVisible({ timeout: 5000 });
      await target.click();
    }
    if (action.fill) {
      const input = page.getByPlaceholder(action.fill.selector)
        .or(page.getByLabel(action.fill.selector))
        .first();
      await input.fill(action.fill.value);
    }
  }

  await expect(page.getByText(expectedOutcome).first()).toBeVisible({ timeout });
}

/**
 * Assert that a named action button exists but is disabled.
 */
export async function expectDisabledAction(
  page: Page,
  actionName: string | RegExp,
  timeout = 5000,
): Promise<void> {
  const btn = page.getByRole('button', { name: actionName }).first();
  await expect(btn).toBeVisible({ timeout });
  await expect(btn).toBeDisabled();
}

/**
 * Assert that a named action button exists and is enabled.
 */
export async function expectEnabledAction(
  page: Page,
  actionName: string | RegExp,
  timeout = 5000,
): Promise<void> {
  const btn = page.getByRole('button', { name: actionName }).first();
  await expect(btn).toBeVisible({ timeout });
  await expect(btn).toBeEnabled();
}

/**
 * Intercept API calls matching a pattern and track whether they were made.
 * Returns a function that asserts the call was made.
 */
export async function expectApiCallMade(
  page: Page,
  pattern: string,
  method?: string,
): Promise<() => void> {
  let callMade = false;
  let requestUrl = '';

  await page.route(pattern, async (route: Route) => {
    if (!method || route.request().method() === method.toUpperCase()) {
      callMade = true;
      requestUrl = route.request().url();
    }
    await route.fallback();
  });

  return () => {
    expect(callMade, `Expected API call to ${pattern} (${method ?? 'any'}) but none was made. Last URL: ${requestUrl}`).toBe(true);
  };
}

/**
 * Assert that a visible audit event or status text appears after an action.
 */
export async function expectAuditEvent(
  page: Page,
  eventPattern: string | RegExp,
  timeout = 8000,
): Promise<void> {
  await expect(
    page.getByText(eventPattern).first(),
  ).toBeVisible({ timeout });
}

/**
 * Register sequential mock responses for the same endpoint pattern.
 * Each call returns the next response in the array.
 */
export async function mockSequentialResponses(
  page: Page,
  pattern: string,
  responses: Array<{ status?: number; body: unknown; delay?: number }>,
): Promise<void> {
  if (isLiveValidationMode()) {
    throw new Error(
      `mockSequentialResponses cannot be used during live validation for pattern ${pattern}. ` +
      'Live workflow validation must use real backend responses and route.fallback() only.',
    );
  }

  let callIndex = 0;
  await page.route(pattern, async (route: Route) => {
    const resp = responses[Math.min(callIndex, responses.length - 1)];
    callIndex++;
    if (resp.delay) {
      await new Promise((resolve) => setTimeout(resolve, resp.delay));
    }
    await route.fulfill({
      status: resp.status ?? 200,
      contentType: 'application/json',
      body: JSON.stringify(resp.body),
    });
  });
}

/**
 * Assert that specific text is NOT visible (negative assertion for security tests).
 */
export async function expectNotVisible(
  page: Page,
  text: string | RegExp,
  timeout = 3000,
): Promise<void> {
  await expect(page.getByText(text).first()).not.toBeVisible({ timeout });
}

/**
 * Switch user role mid-test and reload to take effect.
 * Stabilized with explicit navigation state checks to prevent timing race conditions.
 */
export async function switchToReadOnlyUser(page: Page): Promise<void> {
  await page.evaluate(() => {
    const storeKey = 'user-tier-storage';
    const storeState = {
      state: { currentTier: 'standard', isAdvancedModeEnabled: false, userRole: 'read_only' },
      version: 0,
    };
    localStorage.setItem(storeKey, JSON.stringify(storeState));
    const userInfoRaw = localStorage.getItem('userInfo');
    if (userInfoRaw) {
      try {
        const userInfo = JSON.parse(userInfoRaw);
        userInfo.role = 'read_only';
        localStorage.setItem('userInfo', JSON.stringify(userInfo));
      } catch { /* ignore */ }
    }
  });
  
  // Reload and wait for navigation to complete
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle');

  // Wait for URL to stabilize after reload (prevents timing race)
  const currentUrl = page.url();
  await page.waitForURL(currentUrl, { timeout: 5000 }).catch((err) => {
    // URL might change during reload, that's acceptable - log for debugging
    console.debug(`URL changed from ${currentUrl} to ${page.url()} during role switch: ${err.message}`);
  });

  await expect
    .poll(
      async () =>
        page.evaluate(() => {
          const userInfoRaw = localStorage.getItem('userInfo');
          if (!userInfoRaw) return null;
          try {
            return JSON.parse(userInfoRaw).role;
          } catch {
            return null;
          }
        }),
      { timeout: 5000 },
    )
    .toBe('read_only');
}

export async function expectAnyVisible(
  page: Page,
  candidates: Array<string | RegExp>,
  description: string,
  timeout = 3000,
): Promise<void> {
  const failures: string[] = [];

  for (const candidate of candidates) {
    const locator = page
      .getByRole('heading', { name: candidate })
      .or(page.getByRole('button', { name: candidate }))
      .or(page.getByRole('link', { name: candidate }))
      .or(page.getByPlaceholder(candidate))
      .or(page.getByText(candidate))
      .first();

    try {
      await expect(locator).toBeVisible({ timeout });
      // Verify the matched element has a non-zero bounding box. Zero-BB elements
      // (e.g. hidden nav icon labels) can satisfy toBeVisible() in some Playwright
      // versions while not being meaningfully rendered on screen.
      const bb = await locator.boundingBox().catch(() => null);
      if (bb && bb.width > 0 && bb.height > 0) return;
    } catch {
      // toBeVisible() failed — fall through to DOM scan below.
    }

    // Fallback: scan the DOM for any element whose rendered text matches the
    // candidate AND has a non-zero bounding box. This handles cases where
    // .first() resolved to a hidden element but the content IS on screen.
    const patSource = typeof candidate === 'string' ? candidate : candidate.source;
    const patFlags = typeof candidate === 'string' ? 'i' : candidate.flags;
    const domFound = await expect
      .poll(
        async () => page.evaluate(
        ([src, flags]) => {
          const re = new RegExp(src, flags);
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
          let node: Element | null;
          while ((node = walker.nextNode() as Element | null)) {
            const text = ('innerText' in node ? (node as HTMLElement).innerText : null) ?? node.textContent ?? '';
            if (!re.test(text)) continue;
            const bb = node.getBoundingClientRect();
            if (bb.width > 0 && bb.height > 0) return true;
          }
          return false;
        },
        [patSource, patFlags] as [string, string],
        ),
        { timeout, intervals: [100, 150, 250] },
      )
      .toBe(true)
      .then(() => true)
      .catch(() => false);
    if (domFound) return;

    failures.push(`${candidate}: no visible element with non-zero bounding box found within ${timeout}ms`);
  }

  throw new Error(`Expected visible UI evidence for ${description} at ${page.url()}. Tried: ${failures.join(' | ')}`);
}

export async function expectRouteSupportsWorkflow(
  page: Page,
  path: string,
  candidates: Array<string | RegExp>,
  description: string,
): Promise<void> {
  await navigateAndWait(page, path);
  await expectNoErrors(page);
  await expectAnyVisible(page, candidates, description);
}

export async function expectTenantContext(
  page: Page,
  expectedTenantId = 'tenant-e2e-001',
): Promise<void> {
  const tenantId = await page.evaluate(() => {
    const directTenant = localStorage.getItem('tenantId');
    if (directTenant) return directTenant;
    const userInfoRaw = localStorage.getItem('userInfo');
    if (userInfoRaw) {
      try {
        const parsed = JSON.parse(userInfoRaw);
        if (parsed.tenantId) return parsed.tenantId;
      } catch { /* ignore */ }
    }
    const sessionMetaRaw = sessionStorage.getItem('vf.auth.session.meta');
    if (sessionMetaRaw) {
      try {
        const parsed = JSON.parse(sessionMetaRaw);
        if (parsed.tenantId) return parsed.tenantId;
      } catch { /* ignore */ }
    }
    return null;
  });
  expect(tenantId).toBe(expectedTenantId);
}

export async function expectNoCrossTenantLeakage(page: Page): Promise<void> {
  // Check for foreign tenant signatures in both rendered text and DOM attributes
  const foreignPattern = /tenant-other|other tenant|globex confidential|cross-tenant|foreign-tenant|tenant-foreign|acct-other-tenant|acct-foreign-001/i;
  await expect(page.getByText(foreignPattern).first()).not.toBeVisible({ timeout: 3000 });
}

export async function expectSeededBusinessCaseWorkflowResults(
  page: Page,
  caseIds: string[],
): Promise<void> {
  if (!isLiveMode()) {
    // In contract mode, `page.request` bypasses page.route() mocks and there is no
    // seeded backend state. Journey-specific mocks are responsible for case data.
    return;
  }

  const missing: string[] = [];

  for (const caseId of caseIds) {
    const response = await page.request.get(`/api/v1/agents/cases/${encodeURIComponent(caseId)}`, {
      headers: {
        'X-Validation-Mode': 'backend-integrated',
      },
    });

    if (response.status() === 404) {
      missing.push(caseId);
      continue;
    }

    if (!response.ok()) {
      throw new Error(
        `Seeded business-case preflight failed for ${caseId}: ` +
        `GET /api/v1/agents/cases/${caseId} returned ${response.status()} ${await response.text()}`,
      );
    }
  }

  if (missing.length > 0) {
    throw new Error(
      `Seeded business-case workflow state missing for ${missing.join(', ')}; ` +
      'run scripts/db/seed-e2e-data.ts before seeded backend-integrated J1/J11 regressions.',
    );
  }
}

type IngestionReadinessOptions = {
  domain: string;
  description: string;
  jobId?: string;
  terminal?: boolean;
  timeoutMs?: number;
};

type ObservedIngestionJob = {
  id: string;
  domain: string;
  status: string;
  progress: number;
};

const TERMINAL_INGESTION_STATUSES = new Set(['COMPLETED', 'PARTIAL_SUCCESS', 'FAILED', 'CANCELLED']);
const FAILED_INGESTION_STATUSES = new Set(['FAILED', 'CANCELLED', 'ERROR', 'TIMEOUT']);

function normalizeDomain(value: string): string {
  return value
    .replace(/^https?:\/\//i, '')
    .replace(/\/$/, '')
    .toLowerCase();
}

function extractIngestionJobs(payload: unknown): ObservedIngestionJob[] {
  const envelope = payload && typeof payload === 'object' ? (payload as Record<string, unknown>) : {};
  // Support both the paginated envelope (`items`) and the legacy `data` array.
  const data = envelope.data ?? envelope.items;
  if (!Array.isArray(data)) return [];

  return data.map((item): ObservedIngestionJob => {
    const record = item && typeof item === 'object' ? item as Record<string, unknown> : {};
    const configuration = record.configuration && typeof record.configuration === 'object'
      ? record.configuration as Record<string, unknown>
      : {};
    const domain = String(configuration.url ?? configuration.domain ?? '');
    return {
      id: String(record.id ?? ''),
      domain,
      status: String(record.status ?? '').toUpperCase(),
      progress: Number(record.progress_percent_complete ?? record.progress ?? 0),
    };
  }).filter((job) => job.id);
}

export async function expectIngestionJobReady(
  page: Page,
  {
    domain,
    description,
    jobId,
    terminal = false,
  timeoutMs = 45000,
  }: IngestionReadinessOptions,
): Promise<ObservedIngestionJob> {
  const targetDomain = normalizeDomain(domain);
  let lastObserved = 'no jobs observed';
  let readyJob: ObservedIngestionJob | null = null;

  await expect.poll(async () => {
    const response = await page.request.get('/api/v1/ingest/jobs?limit=100&sort_by=created_at&sort_order=desc');
    if (!response.ok()) {
      lastObserved = `GET /api/v1/ingest/jobs returned ${response.status()} ${await response.text()}`;
      readyJob = null;
      return null;
    }

    const jobs = extractIngestionJobs(await response.json());
    const candidates = jobs.filter((job) => {
      const domainMatches = normalizeDomain(job.domain).includes(targetDomain);
      const idMatches = jobId ? job.id === jobId : true;
      return domainMatches && idMatches;
    });

    lastObserved = candidates.length > 0
      ? candidates.map((job) => `${job.id}:${job.status}:${job.progress}%:${job.domain}`).join(', ')
      : jobs.slice(0, 5).map((job) => `${job.id}:${job.status}:${job.progress}%:${job.domain}`).join(', ');

    const ready = candidates.find((job) => {
      if (FAILED_INGESTION_STATUSES.has(job.status)) {
        return false;
      }
      if (!terminal) {
        return job.status.length > 0;
      }
      return TERMINAL_INGESTION_STATUSES.has(job.status) && job.progress >= 100;
    });

    readyJob = ready ?? null;
    return readyJob;
  }, {
    message: `${description} did not become ready. Last observed: ${lastObserved}`,
    timeout: timeoutMs,
    intervals: [500, 1000, 2000, 5000],
  }).not.toBeNull();

  if (!readyJob) {
    throw new Error(`${description} readiness completed without an observed job. Last observed: ${lastObserved}`);
  }
  return readyJob;
}

export async function attemptOptionalAction(page: Page, actionName: RegExp): Promise<boolean> {
  const action = page.getByRole('button', { name: actionName }).or(page.getByRole('link', { name: actionName })).first();
  try {
    if (await action.isVisible({ timeout: 2000 })) {
      await action.click();
      return true;
    }
  } catch {
    return false;
  }
  return false;
}

export function requireBackendOrThrow(testName: string): void {
  const backendUrl = process.env.PLAYWRIGHT_BACKEND_URL;
  if (!backendUrl) {
    throw new Error(
      `PLAYWRIGHT_BACKEND_URL is required for ${testName}. ` +
      'Run this suite in the backend-integrated project against seeded validation data.',
    );
  }

  try {
    const parsed = new URL(backendUrl);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      throw new Error(`unsupported protocol ${parsed.protocol}`);
    }
  } catch (error) {
    throw new Error(
      `PLAYWRIGHT_BACKEND_URL must be a valid http(s) URL for ${testName}. ` +
      `Received: ${backendUrl}. ${error instanceof Error ? error.message : String(error)}`,
    );
  }

  if (isTruthyEnv('VITE_USE_MOCKS') || isTruthyEnv('VITE_ENABLE_MOCK_FALLBACK') || isTruthyEnv('MSW') || isTruthyEnv('MOCKS_ENABLED')) {
    throw new Error(
      `Mock environment flags are forbidden for backend-integrated live validation in ${testName}. ` +
      'Disable VITE_USE_MOCKS, VITE_ENABLE_MOCK_FALLBACK, MSW, and MOCKS_ENABLED.',
    );
  }
}

function isLiveValidationMode(): boolean {
  return process.env.PLAYWRIGHT_LIVE_MODE === 'true';
}

function isTruthyEnv(name: string): boolean {
  return /^(1|true|yes|on)$/i.test(process.env[name] ?? 'false');
}

export async function expectButtonStateIfVisible(
  page: Page,
  buttonName: RegExp,
  state: 'enabled' | 'disabled',
): Promise<void> {
  const button = page.getByRole('button', { name: buttonName }).first();
  if (await button.isVisible({ timeout: 3000 }).catch(() => false)) {
    if (state === 'enabled') {
      await expect(button).toBeEnabled();
    } else {
      await expect(button).toBeDisabled();
    }
  }
}

export async function expectFieldValueIfVisible(
  page: Page,
  labelOrPlaceholder: RegExp,
  expected: string,
): Promise<void> {
  const field = page
    .getByLabel(labelOrPlaceholder)
    .or(page.getByPlaceholder(labelOrPlaceholder))
    .first();

  if (await field.isVisible({ timeout: 3000 }).catch(() => false)) {
    await expect(field).toHaveValue(expected);
  }
}
