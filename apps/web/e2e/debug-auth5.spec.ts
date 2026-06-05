import { test, expect } from '@playwright/test';

test('deep inspect /workspaces after full render', async ({ page }) => {
  await page.goto('/workspaces', { waitUntil: 'networkidle' });
  await page.waitForTimeout(8000);

  const html = await page.content();
  console.log('HTML length:', html.length);

  // Look for key elements
  const hasSpinner = html.includes('Verifying session');
  const hasChooseWorkspace = html.includes('Choose a workspace');
  const hasSignIn = html.includes('cl-signIn');
  const hasOrganizationList = html.includes('OrganizationList');

  console.log({
    url: page.url(),
    hasSpinner,
    hasChooseWorkspace,
    hasSignIn,
    hasOrganizationList,
  });

  // Check if the page is still loading Clerk
  const clerkState = await page.evaluate(() => {
    // @ts-expect-error
    return { loaded: window.Clerk?.loaded, session: !!window.Clerk?.session };
  });
  console.log('Clerk state:', clerkState);
});
