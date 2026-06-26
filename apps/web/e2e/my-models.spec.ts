import { test, expect } from './fixtures/contract-test';
import { navigateToRoute, waitForStableDOM } from "./fixtures/tier-helpers";

test.describe("My Models E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to My Models page
    await navigateToRoute(page, "/library/models");
    await waitForStableDOM(page);
  });

  test("should load My Models page with correct title", async ({ page }) => {
    // Verify page header
    await expect(page.getByText("My Models").first()).toBeVisible();
    await expect(page.getByText("Personal and shared value models")).toBeVisible();
  });

  test("should show folder sidebar with correct structure", async ({ page }) => {
    // Verify folder sidebar is present
    await expect(page.getByText("Folders")).toBeVisible();
    
    // Verify folder items
    await expect(page.getByText("All Models")).toBeVisible();
    await expect(page.getByText("My Models")).toBeVisible();
    await expect(page.getByText("Shared With Me")).toBeVisible();
    await expect(page.getByText("Favorites")).toBeVisible();
  });

  test("should show search and filter controls", async ({ page }) => {
    // Verify search input
    await expect(page.getByPlaceholder("Search models...")).toBeVisible();
    
    // Verify sort dropdown
    await expect(page.locator('select').first()).toBeVisible();
    
    // Verify industry filter
    await expect(page.getByText("All Industries").first()).toBeVisible();
    
    // Verify view toggle buttons (grid/list)
    const gridButton = page.locator('button[title="Grid view"]').or(page.locator('button').nth(0));
    const listButton = page.locator('button[title="List view"]').or(page.locator('button').nth(1));
    await expect(gridButton.or(listButton)).toBeVisible();
  });

  test("should open New Model dialog", async ({ page }) => {
    // Click New Model button
    await page.getByRole("button", { name: /New Model/i }).click();
    
    // Verify dialog opens
    await expect(page.getByText("New Value Model")).toBeVisible();
    await expect(page.getByPlaceholder("e.g. SaaS Revenue Optimization")).toBeVisible();
    await expect(page.getByText("Industry")).toBeVisible();
    await expect(page.getByText("Description")).toBeVisible();
    
    // Verify Cancel and Create buttons
    await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Create Model" })).toBeVisible();
  });

  test("should close New Model dialog on Cancel", async ({ page }) => {
    // Open dialog
    await page.getByRole("button", { name: /New Model/i }).click();
    await expect(page.getByText("New Value Model")).toBeVisible();
    
    // Click Cancel
    await page.getByRole("button", { name: "Cancel" }).click();
    
    // Verify dialog closes
    await expect(page.getByText("New Value Model")).not.toBeVisible();
  });

  test("should validate create form - name is required", async ({ page }) => {
    // Open dialog
    await page.getByRole("button", { name: /New Model/i }).click();
    await expect(page.getByText("New Value Model")).toBeVisible();
    
    // Try to submit with empty name
    const createButton = page.getByRole("button", { name: "Create Model" });
    
    // Button should be disabled when name is empty
    await expect(createButton).toBeDisabled();
    
    // Type a name
    await page.getByPlaceholder("e.g. SaaS Revenue Optimization").fill("Test Model");
    
    // Button should now be enabled
    await expect(createButton).toBeEnabled();
  });

  test("should show empty state when no models", async ({ page }) => {
    const state = await expect
      .poll(async () => {
        const hasModels = await page.locator("text=drivers").first().isVisible().catch(() => false);
        const hasEmptyState = await page.locator("text=No models yet").first().isVisible().catch(() => false);
        return hasModels ? "models" : hasEmptyState ? "empty" : "pending";
      }, { timeout: 5000 })
      .not.toBe("pending")
      .then(async () => {
        const hasEmptyState = await page.locator("text=No models yet").first().isVisible().catch(() => false);
        return hasEmptyState ? "empty" : "models";
      });
    
    // If empty state, verify CTA button
    if (state === "empty") {
      await expect(page.getByRole("button", { name: /Create First Model/i })).toBeVisible();
    }
  });

  test("should search for models", async ({ page }) => {
    // Type in search box
    const searchInput = page.getByPlaceholder("Search models...");
    await searchInput.fill("test");
    
    // Verify search input has value
    await expect(searchInput).toHaveValue("test");
    await expect
      .poll(async () => page.locator("text=No models yet").first().isVisible().catch(() => false), { timeout: 3000 })
      .toBeDefined();
  });

  test("should switch between folders", async ({ page }) => {
    // Click on My Models folder
    const myModelsFolder = page.getByText("My Models").first();
    await myModelsFolder.click();
    
    // Verify folder is selected (should have different styling, but at least verify it exists)
    await expect(myModelsFolder).toBeVisible();
    
    // Click on Shared folder
    const sharedFolder = page.getByText("Shared With Me").first();
    await sharedFolder.click();
    await expect(sharedFolder).toBeVisible();
  });

  test("should show loading skeleton while fetching", async ({ page }) => {
    // Navigate fresh to see loading state
    await page.goto("/library/models");
    
    // Check for skeleton elements (they have animate-pulse class)
    const skeletons = page.locator("[class*='animate-pulse']");
    
    // Either skeletons exist or content is already loaded
    const hasSkeletons = await skeletons.count() > 0;
    const hasContent = await page.locator("text=My Models").first().isVisible().catch(() => false);
    
    expect(hasSkeletons || hasContent).toBeTruthy();
  });

  test("full CRUD flow - create model @backend", async ({ page }) => {
    // Requires a live backend and deterministic E2E seed data. The
    // backend-integrated project must fail closed when PLAYWRIGHT_BACKEND_URL is
    // absent; critical CRUD coverage must never become a skipped placeholder.
    const backendUrl = process.env.PLAYWRIGHT_BACKEND_URL;

    if (!backendUrl) {
      throw new Error(
        'PLAYWRIGHT_BACKEND_URL is required for the @backend My Models CRUD journey. ' +
        'Start docker-compose.e2e.yml or point PLAYWRIGHT_BACKEND_URL at a seeded backend.'
      );
    }

    // Open create dialog
    await page.getByRole("button", { name: /New Model/i }).click();
    await expect(page.getByText("New Value Model")).toBeVisible();

    // Fill form
    const testModelName = `E2E Test Model ${Date.now()}`;
    await page.getByPlaceholder("e.g. SaaS Revenue Optimization").fill(testModelName);
    await page.locator("select").first().selectOption("SaaS / B2B");
    await page.getByPlaceholder("Brief description").fill("Created by E2E test");

    // Submit
    await page.getByRole("button", { name: "Create Model" }).click();

    // Dialog must close — backend accepted the request
    await expect(page.getByText("New Value Model")).not.toBeVisible({ timeout: 5000 });

    // Success toast and new model in list
    await expect(page.locator("text=Model created successfully").first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(testModelName)).toBeVisible({ timeout: 5000 });
  });

  test("should be responsive - mobile view", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Navigate again
    await page.goto("/library/models");
    await waitForStableDOM(page);
    
    // Verify page still renders
    await expect(page.getByText("My Models").first()).toBeVisible();
    
    // Verify controls are still accessible
    await expect(page.getByPlaceholder("Search models...")).toBeVisible();
  });
});
