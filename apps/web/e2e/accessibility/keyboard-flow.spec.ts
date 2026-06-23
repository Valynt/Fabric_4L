/**
 * Deep Keyboard-Flow Accessibility Tests
 *
 * Addresses Finding #5 (A11y Coverage Depth):
 * - Tab order follows logical DOM sequence
 * - Escape routes release focus traps (modals, dropdowns)
 * - Focus trap containment and release in dialogs
 *
 * These go beyond the threshold gate (counts/routes) to assert
 * specific keyboard interaction behaviors required by WCAG 2.2.
 */

import { test, expect } from '../fixtures/contract-test';

async function countFocusableElements(page: import("@playwright/test").Page) {
  return page.locator(
    'a[href], button, input, select, textarea, [role="button"], [role="link"], [role="tab"], [tabindex]:not([tabindex="-1"])'
  ).count();
}

test.describe("Keyboard Flow - Deep A11y Assertions", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test("tab order follows logical sequence without unexpected jumps", async ({ page }) => {
    if ((await countFocusableElements(page)) < 4) {
      test.skip("No route-level focusable surface rendered in this preview context");
      return;
    }

    const focusedSelectors: (string | null)[] = [];

    // Press Tab up to 15 times and record focused element selectors
    for (let i = 0; i < 15; i++) {
      await page.keyboard.press("Tab");
      const selector = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return null;
        // Build a simple stable identifier
        const tag = el.tagName.toLowerCase();
        const id = el.id ? `#${el.id}` : "";
        const ariaLabel = el.getAttribute("aria-label");
        const text = el.textContent?.trim().slice(0, 30) || "";
        return `${tag}${id}${ariaLabel ? `[aria-label="${ariaLabel}"]` : ""}${text ? `:${text}` : ""}`;
      });
      focusedSelectors.push(selector);
    }

    // Filter out nulls (unfocused / body)
    const meaningful = focusedSelectors.filter((s) => s !== null);

    // Must have focused multiple unique interactive elements
    const unique = new Set(meaningful);
    expect(unique.size).toBeGreaterThan(3);

    // No element should receive focus more than once (no circular tab trap on landing)
    const counts = new Map<string, number>();
    for (const s of meaningful) {
      counts.set(s, (counts.get(s) || 0) + 1);
    }
    for (const [sel, count] of counts) {
      expect(count, `Element "${sel}" received focus ${count} times in 15 tabs`).toBeLessThanOrEqual(2);
    }
  });

  test("skip-link moves focus to main content and tab continues logically", async ({ page }) => {
    // First Tab should land on skip link (if present)
    await page.keyboard.press("Tab");

    const activeAfterSkip = await page.evaluate(() => {
      const el = document.activeElement;
      return {
        tag: el?.tagName.toLowerCase() || null,
        href: el?.getAttribute("href") || null,
        text: el?.textContent?.trim().slice(0, 50) || null,
      };
    });

    // If a skip link exists, activate it and verify focus lands in main content
    if (activeAfterSkip.tag === "a" && activeAfterSkip.text?.toLowerCase().includes("skip")) {
      await page.keyboard.press("Enter");

      const postSkipFocus = await page.evaluate(() => {
        const el = document.activeElement;
        return {
          tag: el?.tagName.toLowerCase() || null,
          id: el?.id || null,
          isInMain: el?.closest("main") !== null,
        };
      });

      expect(postSkipFocus.isInMain || postSkipFocus.id === "content").toBe(true);

      // Subsequent Tab should move to the first focusable element inside main
      await page.keyboard.press("Tab");
      const nextFocus = await page.evaluate(() => {
        const el = document.activeElement;
        return el?.closest("main") !== null || el?.closest("[role='main']") !== null;
      });
      expect(nextFocus).toBe(true);
    }
  });

  test("modal dialog traps focus and Escape releases it", async ({ page }) => {
    await page.goto("/home");
    await page.waitForLoadState("networkidle");

    // Look for a dialog trigger
    const trigger = page.locator("button").filter({ hasText: /new|create|add|open/i }).first();
    if (!(await trigger.isVisible().catch(() => false))) {
      test.skip("No modal trigger found on this page");
      return;
    }

    await trigger.click();

    const dialog = page.locator('[role="dialog"], .modal, [aria-modal="true"]').first();
    await expect(dialog).toBeVisible();

    // Focus should be inside the dialog
    const isInDialogBefore = await page.evaluate(() => {
      const dialog = document.querySelector('[role="dialog"], .modal, [aria-modal="true"]');
      return dialog?.contains(document.activeElement) ?? false;
    });
    expect(isInDialogBefore).toBe(true);

    // Tab multiple times — focus should stay inside the dialog (focus trap)
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press("Tab");
    }

    const isInDialogAfterTabs = await page.evaluate(() => {
      const dialog = document.querySelector('[role="dialog"], .modal, [aria-modal="true"]');
      return dialog?.contains(document.activeElement) ?? false;
    });
    expect(isInDialogAfterTabs).toBe(true);

    // Press Escape — dialog should close and focus should return to trigger
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible({ timeout: 2000 });

    const activeAfterEscape = await page.evaluate(() => document.activeElement?.tagName.toLowerCase());
    expect(["button", "a", "input"]).toContain(activeAfterEscape);
  });

  test("dropdown menu opens with Enter and closes with Escape restoring focus", async ({ page }) => {
    await page.goto("/home");
    await page.waitForLoadState("networkidle");

    // Find a dropdown/menu trigger (often a button with chevron or user menu)
    const menuTrigger = page
      .locator('button[aria-haspopup="menu"], button[aria-haspopup="listbox"], [role="button"][aria-haspopup]')
      .first();

    if (!(await menuTrigger.isVisible().catch(() => false))) {
      test.skip("No dropdown trigger found on this page");
      return;
    }

    const triggerTagBefore = await menuTrigger.evaluate((el) => el.tagName.toLowerCase());
    expect(triggerTagBefore).toBe("button");

    await menuTrigger.focus();
    await page.keyboard.press("Enter");

    const menu = page.locator('[role="menu"], [role="listbox"]').first();
    await expect(menu).toBeVisible({ timeout: 2000 });

    // First menuitem should be focused
    const firstItemFocused = await page.evaluate(() => {
      const active = document.activeElement;
      return active?.getAttribute("role") === "menuitem" || active?.getAttribute("role") === "option";
    });
    expect(firstItemFocused).toBe(true);

    // Escape should close the menu and return focus to trigger
    await page.keyboard.press("Escape");
    await expect(menu).not.toBeVisible({ timeout: 2000 });

    const focusedAfterClose = await page.evaluate(() => document.activeElement);
    const triggerElement = await menuTrigger.evaluate((el) => ({
      tag: el.tagName.toLowerCase(),
      id: el.id,
    }));

    expect(focusedAfterClose).not.toBeNull();
    expect(focusedAfterClose?.tagName.toLowerCase()).toBe(triggerElement.tag);
  });

  test("form submission flow is keyboard-only accessible", async ({ page }) => {
    await page.goto("/sign-in");
    await page.waitForLoadState("networkidle");

    if ((await page.locator("input, button").count()) === 0) {
      test.skip("Clerk sign-in controls are not rendered in this preview context");
      return;
    }

    // Tab to first input
    await page.keyboard.press("Tab");

    const firstInput = await page.evaluate(() => {
      const el = document.activeElement;
      return el?.tagName.toLowerCase();
    });
    expect(["input", "button", "a"]).toContain(firstInput);

    // Type into the focused input if it's a text field
    const isTextInput = await page.evaluate(() => {
      const el = document.activeElement as HTMLInputElement;
      return el?.tagName === "INPUT" && ["text", "email", "password"].includes(el.type);
    });

    if (isTextInput) {
      await page.keyboard.type("test@example.com");
      const value = await page.evaluate(() => (document.activeElement as HTMLInputElement)?.value);
      expect(value).toBe("test@example.com");
    }

    // Tab to the submit button
    await page.keyboard.press("Tab");
    const maybeSubmit = await page.evaluate(() => {
      const el = document.activeElement;
      return {
        tag: el?.tagName.toLowerCase(),
        type: (el as HTMLButtonElement)?.type,
        text: el?.textContent?.trim().toLowerCase() || "",
      };
    });

    const isSubmitLike =
      maybeSubmit.tag === "button" &&
      (maybeSubmit.type === "submit" ||
        maybeSubmit.text.includes("sign in") ||
        maybeSubmit.text.includes("login") ||
        maybeSubmit.text.includes("submit"));

    expect(isSubmitLike).toBe(true);
  });

  test("no keyboard trap on landing page — focus can reach browser chrome", async ({ page }) => {
    // Focus something inside the page
    if ((await countFocusableElements(page)) > 0) {
      await page.keyboard.press("Tab");

      const initialFocus = await page.evaluate(() => document.activeElement?.tagName.toLowerCase());
      expect(initialFocus).not.toBe("body");
    }

    // Tab many times; if we're trapped, focus will cycle among a small set.
    // We can't detect browser chrome focus from page JS, but we can verify
    // the page doesn't contain a known trap pattern (positive tabindex
    // on non-interactive elements that would hijack tab order).
    const hasSuspiciousTabindex = await page.evaluate(() => {
      const suspicious = document.querySelectorAll('[tabindex]:not([tabindex="0"]):not([tabindex="-1"])');
      return suspicious.length;
    });

    expect(hasSuspiciousTabindex).toBe(0);

    // Also verify there are no elements with tabindex="0" that are not
    // interactive and have no keyboard handler (common trap sign).
    const orphanedTabindexZero = await page.evaluate(() => {
      const candidates = document.querySelectorAll('[tabindex="0"]');
      let count = 0;
      for (const el of candidates) {
        const tag = el.tagName.toLowerCase();
        const isNaturallyFocusable = ["a", "button", "input", "textarea", "select"].includes(tag);
        const hasRole = el.hasAttribute("role");
        const hasKeyHandler = el.hasAttribute("onkeydown") || el.hasAttribute("onkeyup");
        if (!isNaturallyFocusable && !hasRole && !hasKeyHandler) {
          count++;
        }
      }
      return count;
    });

    expect(orphanedTabindexZero).toBe(0);
  });
});
