import { test, expect } from '@playwright/test';

test('check auth mode in browser', async ({ page }) => {
  await page.goto('/workspaces', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);

  const authMode = await page.evaluate(() => {
    // Read Vite env var directly
    // @ts-expect-error
    const provider = import.meta.env.VITE_AUTH_PROVIDER;
    // @ts-expect-error
    const mockAuth = import.meta.env.VITE_ENABLE_MOCK_AUTH;
    return { provider, mockAuth };
  });

  console.log('Auth mode:', authMode);

  // Check if Clerk JS is loaded
  const clerkState = await page.evaluate(() => {
    // @ts-expect-error
    const c = window.Clerk;
    return {
      loaded: c?.loaded,
      sessionExists: !!c?.session,
      userExists: !!c?.user,
    };
  });

  console.log('Clerk state:', clerkState);

  // Check the page title and URL
  console.log('URL:', page.url());
  console.log('Title:', await page.title());
});
