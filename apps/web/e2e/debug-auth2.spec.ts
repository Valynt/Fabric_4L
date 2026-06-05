import { test, expect } from '@playwright/test';

test('debug RequireClerkAuth state on /workspaces', async ({ page }) => {
  await page.goto('/workspaces', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);

  // Inject a script to read React internals
  const reactState = await page.evaluate(() => {
    // @ts-expect-error
    const clerk = window.Clerk;
    return {
      url: window.location.href,
      hasClerk: !!clerk,
      clerkLoaded: clerk?.loaded,
      clerkSession: clerk?.session ? { id: clerk.session.id } : null,
      clerkUser: clerk?.user ? { id: clerk.user.id } : null,
    };
  });

  console.log('React/Clerk state:', reactState);

  // Also try to find the Clerk auth hook state by looking for data attributes
  const bodyHTML = await page.locator('body').innerHTML();
  console.log('Body contains "Verifying session":', bodyHTML.includes('Verifying session'));
  console.log('Body contains "Choose a workspace":', bodyHTML.includes('Choose a workspace'));
  console.log('Body contains "cl-signIn":', bodyHTML.includes('cl-signIn'));
  console.log('Body contains "OrganizationList":', bodyHTML.includes('OrganizationList'));
});

test('debug what happens with useAuth on sign-in page', async ({ page }) => {
  await page.goto('/sign-in', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  const state = await page.evaluate(() => {
    // @ts-expect-error
    const clerk = window.Clerk;
    return {
      url: window.location.href,
      hasClerk: !!clerk,
      clerkLoaded: clerk?.loaded,
      session: clerk?.session ? 'has session' : 'no session',
    };
  });

  console.log('Sign-in page state:', state);
});
