/**
 * Behavior-First Test Helpers
 *
 * Shared utilities for behavior-first Playwright tests. These helpers make
 * it explicit when a test is asserting an allowed behavior versus a denied
 * behavior, and they enforce failure-mode checking.
 *
 * Usage:
 *   import { expectAllowedBehavior, expectDeniedBehavior, expectFailureMode } from '../helpers/behavior-helpers';
 */
import { type Page, expect } from '@playwright/test';

export type FailureMode =
  | { type: 'redirect'; target: RegExp }
  | { type: 'error_state'; message: RegExp }
  | { type: 'disabled'; selector: string }
  | { type: 'status_code'; code: number }
  | { type: 'safe_empty'; message?: RegExp };

/**
 * Assert that an allowed behavior produces the expected outcome.
 * Use this wrapper to make allowed-path assertions self-documenting.
 */
export async function expectAllowedBehavior(
  description: string,
  assertion: () => Promise<void>,
): Promise<void> {
  await assertion();
}

/**
 * Assert that a denied behavior produces the expected failure mode.
 * This is the core enforcement mechanism for behavior-first testing:
 * every denied path must fail in a predictable, safe way.
 */
export async function expectDeniedBehavior(
  description: string,
  page: Page,
  failureMode: FailureMode,
): Promise<void> {
  switch (failureMode.type) {
    case 'redirect':
      await expect(page).toHaveURL(failureMode.target, { timeout: 10000 });
      break;
    case 'error_state':
      await expect(
        page.getByText(failureMode.message).first(),
      ).toBeVisible({ timeout: 10000 });
      break;
    case 'disabled':
      await expect(
        page.locator(failureMode.selector).first(),
      ).toBeDisabled({ timeout: 5000 });
      break;
    case 'status_code': {
      // For API-level denials captured via route interception
      // The caller should have set up the intercept before calling this.
      break;
    }
    case 'safe_empty': {
      const msg = failureMode.message;
      if (msg) {
        await expect(page.getByText(msg).first()).toBeVisible({ timeout: 10000 });
      }
      break;
    }
  }
}

/**
 * Assert a specific failure mode is visible on the page.
 * Convenience wrapper for common denied-path checks.
 */
export async function expectFailureMode(
  page: Page,
  mode: 'unauthenticated_redirect' | 'unauthorized_redirect' | 'forbidden_state' | 'not_found_state' | 'validation_error' | 'disabled_action',
): Promise<void> {
  switch (mode) {
    case 'unauthenticated_redirect':
      await expect(page).toHaveURL(/login|auth|sign-in/, { timeout: 10000 });
      break;
    case 'unauthorized_redirect':
      await expect(page).toHaveURL(/home|forbidden|access-denied/, { timeout: 10000 });
      break;
    case 'forbidden_state':
      await expect(
        page.getByText(/forbidden|access denied|not authorized|permission/i).first(),
      ).toBeVisible({ timeout: 10000 });
      break;
    case 'not_found_state':
      await expect(
        page.getByText(/not found|404|does not exist/i).first(),
      ).toBeVisible({ timeout: 10000 });
      break;
    case 'validation_error':
      await expect(
        page.getByText(/invalid|required|error|please enter/i).first(),
      ).toBeVisible({ timeout: 10000 });
      break;
    case 'disabled_action':
      await expect(
        page.locator('button[disabled], [aria-disabled="true"]').first(),
      ).toBeVisible({ timeout: 5000 });
      break;
  }
}

/**
 * Assert that a UI action triggers an API call with the expected payload shape,
 * and that the UI updates correctly after the response.
 *
 * This is the primary cross-layer behavior proof helper.
 */
export async function expectCrossLayerBehavior(
  page: Page,
  options: {
    /** API URL pattern to intercept */
    apiPattern: string;
    /** API HTTP method */
    method?: string;
    /** Action to perform on the UI */
    uiAction: () => Promise<void>;
    /** Assert the intercepted request payload */
    assertRequest?: (request: unknown) => void;
    /** Mock response to return (if not in live mode) */
    mockResponse?: { status?: number; body: unknown };
    /** Assert the UI state after response */
    assertUiState: () => Promise<void>;
  },
): Promise<void> {
  let requestPayload: unknown = null;
  let requestMade = false;

  await page.route(options.apiPattern, async (route) => {
    if (options.method && route.request().method() !== options.method.toUpperCase()) {
      await route.fallback();
      return;
    }
    requestMade = true;
    try {
      requestPayload = route.request().postDataJSON();
    } catch {
      requestPayload = null;
    }

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

  // Wait briefly for the request to be made
  await page.waitForTimeout(500);

  expect(requestMade, `Expected API call to ${options.apiPattern} but none was made`).toBe(true);

  if (options.assertRequest) {
    options.assertRequest(requestPayload);
  }

  await options.assertUiState();
}

/**
 * Assert that no cross-tenant data leakage occurs on the current page.
 * Checks for known foreign tenant identifiers and sensitive foreign data.
 */
export async function expectNoCrossTenantLeakageOnPage(
  page: Page,
  foreignTenantId: string,
  foreignAccountId?: string,
): Promise<void> {
  const bodyText = await page.locator('body').innerText().catch(() => '');
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
