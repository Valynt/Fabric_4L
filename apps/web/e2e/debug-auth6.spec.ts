import { test, expect } from '@playwright/test';

test('check isClerkAuthEnabled in browser', async ({ page }) => {
  await page.goto('/workspaces', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);

  const state = await page.evaluate(() => {
    // @ts-expect-error
    const clerk = window.Clerk;
    return {
      hasClerk: !!clerk,
      clerkLoaded: clerk?.loaded,
      hasSession: !!clerk?.session,
    };
  });

  console.log('Clerk state:', state);

  // Check if the app thinks Clerk is enabled by looking at the DOM
  const html = await page.content();
  const isClerkMode = html.includes('cl-'); // Clerk components use cl- prefix
  console.log('Has Clerk elements:', isClerkMode);
});
