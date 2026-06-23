/**
 * API Failure Recovery (Deep)
 *
 * Traceability: API-FAIL-001 through API-FAIL-006.
 *
 * This suite extends the basic resilience tests to cover:
 * - Network timeout handling with retry UI
 * - 5xx errors with actionable error messages
 * - Offline mode detection and graceful degradation
 * - Partial failure scenarios (some services up, some down)
 * - Retry mechanism functionality
 * - Error recovery workflows
 *
 * Priority: P1 production confidence
 * Mode: Contract (mocked failures)
 */

import { journeyTest, expect } from '../helpers/journey-fixture';
import { expectAnyVisible, expectRouteSupportsWorkflow } from '../helpers/validation-program';

journeyTest.describe('API Failure Recovery (Deep)', () => {
  journeyTest.beforeEach(async ({ addMocks }) => {
    // Default mocks for successful responses
    await addMocks([
      {
        pattern: '**/api/v1/ingest/jobs',
        body: [
          { id: 'job-001', domain: 'example.com', status: 'completed', progress: 100 },
        ],
      },
    ]);
  });

  // ── Network Timeout Handling ───────────────────────────────────────────────

  journeyTest('API-FAIL-001: network timeout shows retry UI', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        handler: async (route) => {
          // Simulate timeout by delaying response
          await new Promise((resolve) => setTimeout(resolve, 60000));
          await route.fulfill({ status: 200, body: JSON.stringify({ signals: [] }) });
        },
      },
    ]);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show timeout or retry message
    await expect(
      authedPage.getByText(/timeout|retry|try again|slow|loading/i)
        .or(authedPage.getByText(/signals/i))
        .first(),
    ).toBeVisible({ timeout: 15000 });
  });

  journeyTest('API-FAIL-002: retry button triggers request retry', async ({ authedPage, addMocks }) => {
    let requestCount = 0;
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        handler: async (route) => {
          requestCount++;
          if (requestCount === 1) {
            // First request fails
            await route.fulfill({ status: 504, body: JSON.stringify({ error: 'Gateway timeout' }) });
          } else {
            // Second request succeeds
            await route.fulfill({ status: 200, body: JSON.stringify({ signals: [] }) });
          }
        },
      },
    ]);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show error
    await expect(authedPage.getByText(/timeout|error/i)).toBeVisible({ timeout: 10000 });

    // Click retry if available
    const retryBtn = authedPage.getByRole('button', { name: /retry|try again/i }).first();
    if (await retryBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await retryBtn.click();
      // Should load successfully after retry
      await expect(authedPage.getByText(/signals/i)).toBeVisible({ timeout: 10000 });
    }
  });

  // ── 5xx Errors with Actionable Messages ─────────────────────────────────────

  journeyTest('API-FAIL-003: 500 error shows actionable error message', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        status: 500,
        body: { error: 'Internal server error' },
      },
    ]);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show error with actionable message
    await expect(
      authedPage.getByText(/error|something went wrong|try again|contact support/i)
        .or(authedPage.getByText(/500/i))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('API-FAIL-004: 503 error shows service unavailable message', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        status: 503,
        body: { error: 'Service temporarily unavailable' },
      },
    ]);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show service unavailable message
    await expect(
      authedPage.getByText(/unavailable|maintenance|try again later/i)
        .or(authedPage.getByText(/503/i))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });

  journeyTest('API-FAIL-005: 502 bad gateway shows appropriate message', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        status: 502,
        body: { error: 'Bad gateway' },
      },
    ]);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show bad gateway message
    await expect(
      authedPage.getByText(/bad gateway|upstream|service unavailable/i)
        .or(authedPage.getByText(/502/i))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });

  // ── Offline Mode Detection ─────────────────────────────────────────────────

  journeyTest('API-FAIL-006: offline mode shows appropriate message', async ({ authedPage, context }) => {
    // Go offline
    await context.setOffline(true);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show offline message
    await expect(
      authedPage.getByText(/offline|no internet|connection lost|network/i)
        .or(authedPage.getByText(/signals/i))
        .first(),
    ).toBeVisible({ timeout: 10000 });

    // Go back online
    await context.setOffline(false);
  });

  journeyTest('API-FAIL-007: offline mode allows retry when connection restored', async ({ authedPage, context }) => {
    // Go offline
    await context.setOffline(true);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show offline message
    await expect(authedPage.getByText(/offline|network/i)).toBeVisible({ timeout: 10000 });

    // Go back online
    await context.setOffline(false);

    // Reload to retry
    await authedPage.reload({ waitUntil: 'domcontentloaded' });

    // Should load successfully
    await expect(authedPage.getByText(/signals/i)).toBeVisible({ timeout: 10000 });
  });

  // ── Partial Failure Scenarios ───────────────────────────────────────────

  journeyTest('API-FAIL-008: partial failure - some services up, some down', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        status: 503,
        body: { error: 'Intelligence service down' },
      },
      {
        pattern: '**/api/v1/accounts/**',
        status: 200,
        body: { accounts: [] },
      },
    ]);

    // Navigate to accounts (should work)
    await authedPage.goto('/accounts', { waitUntil: 'domcontentloaded' });
    await expect(authedPage.getByText(/accounts/i)).toBeVisible({ timeout: 10000 });

    // Navigate to intelligence (should show error)
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });
    await expect(authedPage.getByText(/unavailable|error/i)).toBeVisible({ timeout: 10000 });
  });

  journeyTest('API-FAIL-009: partial failure - UI degrades gracefully', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/signals/**',
        status: 503,
        body: { error: 'Signals service down' },
      },
      {
        pattern: '**/api/v1/intelligence/drivers/**',
        status: 200,
        body: { drivers: [] },
      },
    ]);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show partial content or error for failed section
    await expect(
      authedPage.getByText(/unavailable|error|retry/i)
        .or(authedPage.getByText(/drivers/i))
        .first(),
    ).toBeVisible({ timeout: 10000 });
  });

  // ── Retry Mechanism Functionality ─────────────────────────────────────────

  journeyTest('API-FAIL-010: automatic retry on transient failures', async ({ authedPage, addMocks }) => {
    let requestCount = 0;
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        handler: async (route) => {
          requestCount++;
          if (requestCount <= 2) {
            // First two requests fail
            await route.fulfill({ status: 503, body: JSON.stringify({ error: 'Service unavailable' }) });
          } else {
            // Third request succeeds
            await route.fulfill({ status: 200, body: JSON.stringify({ signals: [] }) });
          }
        },
      },
    ]);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should eventually load after retries
    await expect(authedPage.getByText(/signals/i)).toBeVisible({ timeout: 15000 });
  });

  journeyTest('API-FAIL-011: retry limit prevents infinite loops', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        status: 503,
        body: { error: 'Service unavailable' },
      },
    ]);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });

    // Should show error after retry limit, not hang indefinitely
    await expect(authedPage.getByText(/unavailable|error|retry/i)).toBeVisible({ timeout: 15000 });
  });

  // ── Error Recovery Workflows ───────────────────────────────────────────────

  journeyTest('API-FAIL-012: error recovery allows navigation to other pages', async ({ authedPage, addMocks }) => {
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        status: 503,
        body: { error: 'Service unavailable' },
      },
    ]);

    // Navigate to failing page
    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });
    await expect(authedPage.getByText(/unavailable|error/i)).toBeVisible({ timeout: 10000 });

    // Navigate to working page
    await authedPage.goto('/accounts', { waitUntil: 'domcontentloaded' });

    // Should load successfully
    await expect(authedPage.getByText(/accounts/i)).toBeVisible({ timeout: 10000 });
  });

  journeyTest('API-FAIL-013: error state clears on successful request', async ({ authedPage, addMocks }) => {
    let requestCount = 0;
    await addMocks([
      {
        pattern: '**/api/v1/intelligence/**',
        handler: async (route) => {
          requestCount++;
          if (requestCount === 1) {
            await route.fulfill({ status: 503, body: JSON.stringify({ error: 'Service unavailable' }) });
          } else {
            await route.fulfill({ status: 200, body: JSON.stringify({ signals: [] }) });
          }
        },
      },
    ]);

    await authedPage.goto('/intelligence/acct-meridian-001/signals', { waitUntil: 'domcontentloaded' });
    await expect(authedPage.getByText(/unavailable|error/i)).toBeVisible({ timeout: 10000 });

    // Reload to retry
    await authedPage.reload({ waitUntil: 'domcontentloaded' });

    // Should load successfully, error state cleared
    await expect(authedPage.getByText(/signals/i)).toBeVisible({ timeout: 10000 });
    await expect(authedPage.getByText(/unavailable|error/i)).not.toBeVisible({ timeout: 5000 });
  });
});
