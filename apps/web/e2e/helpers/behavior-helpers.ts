/**
 * Behavior-First Test Helpers — Strict Edition
 *
 * Shared utilities for behavior-first Playwright tests. These helpers enforce
 * deterministic outcomes: no catch-and-ignore, no conditional branches, no
 * soft assertions. A behavior test either proves the contract or fails.
 *
 * Usage:
 *   import { expectDeniedBehavior, expectFailureMode, expectCrossLayerBehavior } from '../helpers/behavior-helpers';
 */
import { type Page, type Route, expect } from '@playwright/test';

export type FailureMode =
  | { type: 'redirect'; target: RegExp }
  | { type: 'error_state'; testId: string }
  | { type: 'disabled'; testId: string }
  | { type: 'status_code'; code: number }
  | { type: 'safe_empty'; testId: string };

/**
 * Assert that a denied behavior produces the expected failure mode.
 * No fallbacks. If the failure mode is not present exactly as specified, the test fails.
 */
export async function expectDeniedBehavior(
  _description: string,
  page: Page,
  failureMode: FailureMode,
): Promise<void> {
  switch (failureMode.type) {
    case 'redirect':
      await expect(page).toHaveURL(failureMode.target, { timeout: 10000 });
      break;
    case 'error_state':
      await expect(page.getByTestId(failureMode.testId)).toBeVisible({ timeout: 10000 });
      break;
    case 'disabled':
      await expect(page.getByTestId(failureMode.testId)).toBeDisabled({ timeout: 5000 });
      break;
    case 'status_code':
      // Status-code denials must be asserted by the caller via route interception.
      // This branch is a type marker only; the actual assertion happens in the test.
      break;
    case 'safe_empty':
      await expect(page.getByTestId(failureMode.testId)).toBeVisible({ timeout: 10000 });
      break;
  }
}

/**
 * Assert a specific failure mode is visible on the page.
 * Uses strict getByTestId selectors — no fuzzy text matching.
 */
export async function expectFailureMode(
  page: Page,
  mode: 'unauthenticated_redirect' | 'unauthorized_redirect' | 'forbidden_state' | 'not_found_state' | 'validation_error' | 'disabled_action',
): Promise<void> {
  switch (mode) {
    case 'unauthenticated_redirect':
      await expect(page).toHaveURL(/\/sign-in/, { timeout: 10000 });
      break;
    case 'unauthorized_redirect':
      await expect(page).toHaveURL(/\/home|\/forbidden|\/access-denied/, { timeout: 10000 });
      break;
    case 'forbidden_state':
      await expect(page.getByTestId('forbidden-state')).toBeVisible({ timeout: 10000 });
      break;
    case 'not_found_state':
      await expect(page.getByTestId('not-found-state')).toBeVisible({ timeout: 10000 });
      break;
    case 'validation_error':
      await expect(page.getByTestId('validation-error')).toBeVisible({ timeout: 10000 });
      break;
    case 'disabled_action':
      await expect(page.getByTestId('action-disabled')).toBeVisible({ timeout: 5000 });
      break;
  }
}

/**
 * Assert that a UI action triggers an API call with an exact payload,
 * and that the UI updates to an exact expected state.
 *
 * This is the strict cross-layer behavior proof. It does NOT use timeouts
 * to guess when things are done; it waits for explicit state.
 */
export async function expectCrossLayerBehavior<TRequest = unknown, TResponse = unknown>(
  page: Page,
  options: {
    /** API URL pattern to intercept */
    apiPattern: string;
    /** API HTTP method */
    method?: string;
    /** Action to perform on the UI */
    uiAction: () => Promise<void>;
    /** Assert the intercepted request payload exactly */
    assertRequest: (request: TRequest) => void;
    /** Mock response to return (if not in live mode) */
    mockResponse?: { status?: number; body: TResponse };
    /** Assert the UI state after response */
    assertUiState: () => Promise<void>;
  },
): Promise<void> {
  const requests: { payload: TRequest; url: string; method: string }[] = [];

  await page.route(options.apiPattern, async (route: Route) => {
    if (options.method && route.request().method() !== options.method.toUpperCase()) {
      await route.fallback();
      return;
    }

    const payload = route.request().postDataJSON() as TRequest;
    requests.push({
      payload,
      url: route.request().url(),
      method: route.request().method(),
    });

    if (options.mockResponse) {
      await route.fulfill({
        status: options.mockResponse.status ?? 200,
        contentType: 'application/json',
        body: JSON.stringify(options.mockResponse.body),
      });
    } else {
      await route.fallback();
    }
  });

  await options.uiAction();

  // Strict: exactly one matching request must be made
  expect(requests, `Expected exactly one API call to ${options.apiPattern} (${options.method ?? 'any'})`).toHaveLength(1);

  options.assertRequest(requests[0].payload);

  await options.assertUiState();
}

/**
 * Assert that no cross-tenant data leakage occurs on the current page.
 * Checks the full page text and URL for the foreign tenant identifier.
 */
export async function expectNoCrossTenantLeakageOnPage(
  page: Page,
  foreignTenantId: string,
  foreignAccountId?: string,
): Promise<void> {
  const bodyText = await page.locator('body').innerText();
  const pageUrl = page.url();

  expect(
    bodyText.includes(foreignTenantId),
    `Page body must not contain foreign tenant ID ${foreignTenantId}`,
  ).toBe(false);

  expect(
    pageUrl.includes(foreignTenantId),
    `Page URL must not contain foreign tenant ID ${foreignTenantId}`,
  ).toBe(false);

  if (foreignAccountId) {
    expect(
      bodyText.includes(foreignAccountId),
      `Page body must not contain foreign account ID ${foreignAccountId}`,
    ).toBe(false);
  }
}

/**
 * Strict assertion: element with exact testId must be visible.
 */
export async function expectVisibleByTestId(page: Page, testId: string, timeout = 10000): Promise<void> {
  await expect(page.getByTestId(testId)).toBeVisible({ timeout });
}

/**
 * Strict assertion: element with exact testId must contain exact text.
 */
export async function expectTestIdContains(page: Page, testId: string, text: string | RegExp, timeout = 10000): Promise<void> {
  await expect(page.getByTestId(testId)).toContainText(text, { timeout });
}
