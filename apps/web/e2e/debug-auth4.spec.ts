import { test, expect } from '@playwright/test';

test('check isClerkAuthEnabled and useAuth on /workspaces', async ({ page }) => {
  await page.goto('/workspaces', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);

  // Inject a script to access the app's internal state
  const state = await page.evaluate(() => {
    // Try to find React fiber root
    const rootEl = document.getElementById('root');
    // @ts-expect-error React internal
    const fiber = rootEl?._reactRootContainer?._internalRoot?.current;

    return {
      url: window.location.href,
      hasRootEl: !!rootEl,
      hasFiber: !!fiber,
    };
  });

  console.log('State:', state);

  // Wait for any navigation
  await page.waitForTimeout(5000);
  console.log('URL after 10s total:', page.url());

  // Take screenshot
  const buffer = await page.screenshot();
  console.log('Screenshot size:', buffer.length);
});
