import { test, expect } from '@playwright/test';

test.describe('Debug Auth Behavior', () => {
  test('debug /workspaces redirect', async ({ page }) => {
    const logs: string[] = [];
    page.on('console', (msg) => logs.push(`[${msg.type()}] ${msg.text()}`));
    page.on('pageerror', (err) => logs.push(`[PAGE_ERROR] ${err.message}`));

    await page.goto('/workspaces', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);

    console.log('Final URL:', page.url());
    console.log('Logs:', logs.slice(0, 20));

    // Check if Clerk auth state is available
    const clerkState = await page.evaluate(() => {
      // @ts-expect-error
      const clerk = window.Clerk;
      return {
        hasClerk: !!clerk,
        user: clerk?.user ? { id: clerk.user.id } : null,
        session: clerk?.session ? { id: clerk.session.id } : null,
      };
    }).catch(() => ({ hasClerk: false, error: true }));

    console.log('Clerk state:', clerkState);
  });

  test('debug /signin route', async ({ page }) => {
    await page.goto('/signin', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    console.log('Final URL:', page.url());
    console.log('Title:', await page.title());
  });

  test('debug /home redirect', async ({ page }) => {
    await page.goto('/home', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);
    console.log('Final URL:', page.url());
  });
});
