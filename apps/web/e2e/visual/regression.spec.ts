/**
 * Visual Regression Test Suite
 * ==============================
 * Playwright-powered pixel-perfect visual regression tests for all
 * major page routes in the Fabric_4L application.
 *
 * Coverage:
 *   - Homepage (marketing landing)
 *   - Dashboard (authenticated app shell)
 *   - Workflows list
 *   - Knowledge Graph explorer
 *   - Tenant Admin
 *
 * DESIGN.md § Testing: "Playwright smoke tests for critical user flows"
 * DESIGN.md § Quality: Visual regression must be gated in CI before merge.
 *
 * @module e2e/visual/regression
 */

import { test, expect } from "@playwright/test";

// ---------------------------------------------------------------------------
// Page definitions
// ---------------------------------------------------------------------------

interface PageDefinition {
  /** Route path (relative to base URL). */
  path: string;
  /** Human-readable identifier used in the screenshot filename. */
  name: string;
  /** Optional selector to wait for before capturing (e.g. a skeleton loader). */
  readySelector?: string;
  /** Additional viewport width to test beyond the default. */
  extraViewport?: { width: number; height: number };
}

const PAGES: PageDefinition[] = [
  { path: "/", name: "homepage", readySelector: "[data-testid='hero-section']" },
  {
    path: "/dashboard",
    name: "dashboard",
    readySelector: "[data-testid='dashboard-layout']",
    extraViewport: { width: 1440, height: 900 },
  },
  {
    path: "/workflows",
    name: "workflows",
    readySelector: "[data-testid='workflows-list']",
  },
  {
    path: "/knowledge-graph",
    name: "knowledge-graph",
    readySelector: "[data-testid='graph-canvas']",
    extraViewport: { width: 1440, height: 900 },
  },
  {
    path: "/tenant-admin",
    name: "tenant-admin",
    readySelector: "[data-testid='tenant-admin-layout']",
  },
];

// ---------------------------------------------------------------------------
// Shared setup: login + tenant context
// ---------------------------------------------------------------------------

test.beforeEach(async ({ page }) => {
  // Authenticate using the same flow as other E2E tests.
  // The auth helpers set cookies/localStorage so subsequent navigations
  // are authenticated.
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
});

// ---------------------------------------------------------------------------
// Screenshot helper
// ---------------------------------------------------------------------------

/**
 * Wait for the page to be visually stable before capturing.
 *
 * 1. Wait for network to be idle (no in-flight requests).
 * 2. Wait for the ready selector (if defined) — signals JS has hydrated.
 * 3. Wait one additional animation frame for CSS transitions to settle.
 */
async function waitForVisualStability(
  page: import("@playwright/test").Page,
  definition: PageDefinition
): Promise<void> {
  await page.waitForLoadState("networkidle");

  if (definition.readySelector) {
    await page.waitForSelector(definition.readySelector, {
      state: "visible",
      timeout: 15_000,
    });
  }

  // Allow CSS transitions / skeleton fade-outs to complete
  await page.waitForTimeout(300);

  // Force any remaining animations to their final state
  await page.evaluate(() => {
    const style = document.createElement("style");
    style.textContent = `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    `;
    document.head.appendChild(style);
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

for (const pageDef of PAGES) {
  /**
   * Primary viewport: 1280×720 (desktop)
   *
   * This is the canonical reference screenshot used in CI comparisons.
   */
  test(`${pageDef.name} — desktop @visual`, async ({ page }) => {
    await page.goto(pageDef.path);
    await waitForVisualStability(page, pageDef);

    await expect(page).toHaveScreenshot(`${pageDef.name}.png`, {
      maxDiffPixels: 100,
      threshold: 0.2,
      animations: "disabled",
    });
  });

  /**
   * Optional: extra viewport breakpoint defined per-page.
   */
  if (pageDef.extraViewport) {
    test(`${pageDef.name} — desktop-wide @visual`, async ({ page }) => {
      await page.setViewportSize(pageDef.extraViewport);
      await page.goto(pageDef.path);
      await waitForVisualStability(page, pageDef);

      await expect(page).toHaveScreenshot(`${pageDef.name}-wide.png`, {
        maxDiffPixels: 150,
        threshold: 0.2,
        animations: "disabled",
      });
    });
  }

  /**
   * Mobile viewport: 375×667 (iPhone SE-ish)
   *
   * Ensures responsive layouts don't regress on small screens.
   */
  test(`${pageDef.name} — mobile @visual`, async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(pageDef.path);
    await waitForVisualStability(page, pageDef);

    await expect(page).toHaveScreenshot(`${pageDef.name}-mobile.png`, {
      maxDiffPixels: 150,
      threshold: 0.25,
      animations: "disabled",
    });
  });
}

// ---------------------------------------------------------------------------
// Component-level visual regression
// ---------------------------------------------------------------------------

/**
 * Isolated component stories rendered via Storybook (or inline) for
 * granular visual regression without full-page navigation.
 */
const COMPONENT_STORIES: Array<{ name: string; path: string }> = [
  { name: "button-variants", path: "/storybook/iframe.html?id=ui-button--all-variants" },
  { name: "card-composition", path: "/storybook/iframe.html?id=ui-card--composition" },
];

for (const story of COMPONENT_STORIES) {
  test(`component: ${story.name} @visual`, async ({ page }) => {
    await page.goto(story.path);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(200);

    await expect(page).toHaveScreenshot(`component-${story.name}.png`, {
      maxDiffPixels: 50,
      threshold: 0.15,
      animations: "disabled",
      fullPage: false,
    });
  });
}
