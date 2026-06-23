import { test, expect } from '@playwright/test';

test('debug /workspaces auth state', async ({ page }) => {
  const logs: string[] = [];
  page.on('console', (msg) => {
    const text = msg.text();
    if (text.includes('[RequireClerkAuth]')) logs.push(text);
  });

  await page.goto('/workspaces', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(8000);

  console.log('Final URL:', page.url());
  console.log('Auth logs:', logs);
});
