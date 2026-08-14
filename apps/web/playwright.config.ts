import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * Playwright configuration for Value Fabric frontend E2E tests
 *
 * Test layers:
 *   1. contracts/  — Isolated page-level contract tests (fast, mocked)
 *   2. journeys/   — Chained user journey tests (live or contract mode)
 *   3. behaviors/  — Behavior-first allowed/denied path tests (mocked, cross-layer)
 *   4. accessibility/ — Accessibility audits
 *
 * Standards:
 * - Journey tests run against real backend when PLAYWRIGHT_BACKEND_URL is set
 * - Contract tests always use mocks (no backend required)
 * - Tests tagged @backend only run in the `backend-integrated` project
 * - Parallel execution where safe
 * - Trace/screenshot on failure for debugging
 * - Accessibility-conscious selectors preferred
 *
 * Environment variables:
 *   PLAYWRIGHT_BASE_URL      — Frontend dev server URL (default: http://localhost:3001)
 *   PLAYWRIGHT_BACKEND_URL   — Backend API base URL; required for @backend tests
 *   E2E_SEED_DATA            — Set to 'false' only when an external backend is already seeded
 */

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3001';
const BASE_PORT = new URL(BASE_URL).port || '3001';
const BACKEND_URL = process.env.PLAYWRIGHT_BACKEND_URL || '';
const CI = process.env.CI === 'true';
const LIVE_MODE = process.env.PLAYWRIGHT_LIVE_MODE === 'true';
const HTML_REPORT_DIR = process.env.PLAYWRIGHT_HTML_REPORT || 'playwright-report';
const JUNIT_OUTPUT_FILE = process.env.PLAYWRIGHT_JUNIT_FILE || 'e2e-results/junit.xml';
const TEST_OUTPUT_DIR = process.env.PLAYWRIGHT_OUTPUT_DIR || 'e2e-results/';
const WEBSERVER_COMMAND =
  process.env.PLAYWRIGHT_WEBSERVER_COMMAND ||
  `corepack pnpm --dir apps/web exec vite --host 127.0.0.1 --port ${BASE_PORT}`;
const SKIP_WEBSERVER = process.env.PLAYWRIGHT_SKIP_WEBSERVER === 'true';
const WEB_ROOT = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(WEB_ROOT, '../..');

export default defineConfig({
  testDir: "./e2e",
  testIgnore: [
    '**/debug-*',
    '**/*.debug.*',
  ],

  /* Run tests in files in parallel where safe */
  fullyParallel: !CI,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: CI,

  /* Retry on CI only - helps with flaky environments */
  retries: CI ? 2 : 1,

  /* Limit workers to prevent resource contention, but allow parallelism */
  workers: CI ? 2 : undefined,

  /* Reporter configuration */
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: HTML_REPORT_DIR }],
    ['junit', { outputFile: JUNIT_OUTPUT_FILE }],
  ],

  /* Shared settings for all projects */
  use: {
    /* Base URL for all tests */
    baseURL: BASE_URL,

    /* Retain failure artifacts for workflow release evidence. */
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    /* Action timeout - generous for slower operations */
    actionTimeout: 15000,

    /* Navigation timeout */
    navigationTimeout: 30000,

    /* Viewport - desktop default */
    viewport: { width: 1280, height: 720 },

    /* Ignore HTTPS errors in local dev */
    ignoreHTTPSErrors: true,
  },

  /* Configure projects for different test layers and browsers */
  projects: [
    // ── Layer 1: Contract Tests (fast, mocked, chromium-only in dev) ──────
    {
      name: 'contracts',
      testDir: "./e2e",
      // Exclude @backend tests — they require a live API and run separately
      grep: /^(?!.*@backend)/,
      use: { ...devices['Desktop Chrome'] },
    },
    // ── Layer 2: Behavior Tests (strict allowed/denied path contracts) ─────
    {
      name: 'behaviors',
      testDir: "./e2e/behaviors",
      // Behavior tests are mocked by default; @backend variants run in backend-integrated
      grep: /^(?!.*@backend)/,
      // Strict behavior flows chain several navigations and explicit polling
      // assertions; 30 s is not enough headroom on a dev-server stack.
      timeout: 90_000,
      use: { ...devices['Desktop Chrome'] },
    },
    // ── Layer 3: Journey Tests (chained workflows, chromium-only in dev) ──
    {
      name: 'journeys',
      testDir: "./e2e",
      grep: /^(?!.*@backend)/,
      use: { ...devices['Desktop Chrome'] },
    },
    // ── Layer 4: Backend-integrated Tests (require PLAYWRIGHT_BACKEND_URL) ─
    // Only runs tests tagged @backend. Critical backend journeys fail closed
    // when PLAYWRIGHT_BACKEND_URL is absent; they are never silently skipped.
    {
      name: 'backend-integrated',
      testDir: "./e2e",
      grep: /@backend/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: BASE_URL,
        extraHTTPHeaders: BACKEND_URL ? { 'X-Backend-URL': BACKEND_URL } : {},
      },
    },
    // ── Cross-browser: Contracts on Firefox ──────────────────────────────
    {
      name: 'contracts-firefox',
      testDir: "./e2e",
      grep: /^(?!.*@backend)/,
      use: { ...devices['Desktop Firefox'] },
    },
    // ── Cross-browser: Contracts on WebKit ───────────────────────────────
    {
      name: 'contracts-webkit',
      testDir: "./e2e",
      grep: /^(?!.*@backend)/,
      use: { ...devices['Desktop Safari'] },
    },
    // ── Mobile: Contracts on Mobile Chrome ───────────────────────────────
    {
      name: 'contracts-mobile-chrome',
      testDir: "./e2e",
      grep: /^(?!.*@backend)/,
      use: { ...devices['Pixel 5'] },
    },
    // ── Mobile: Contracts on Mobile Safari ───────────────────────────────
    {
      name: 'contracts-mobile-safari',
      testDir: "./e2e",
      grep: /^(?!.*@backend)/,
      use: { ...devices['iPhone 12'] },
    },
  ],

  /* Seed deterministic backend data before backend-integrated tests when configured */
  globalSetup: './e2e/global-setup.ts',

  /* Run local dev server before starting tests */
  webServer: SKIP_WEBSERVER ? undefined : {
    command: WEBSERVER_COMMAND,
    cwd: REPO_ROOT,
    url: BASE_URL,
    env: {
      ...process.env,
      ...(LIVE_MODE ? {} : { VITE_AUTH_PROVIDER: 'legacy', VITE_ENABLE_MOCK_AUTH: 'true' }),
    },
    reuseExistingServer: LIVE_MODE || !CI,
    timeout: 120000,
  },

  /* Output directories */
  outputDir: TEST_OUTPUT_DIR,

  /* Global setup/teardown if needed */
  // globalSetup: require.resolve('./e2e/global-setup'),
  // globalTeardown: require.resolve('./e2e/global-teardown'),
});
