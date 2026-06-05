import { test, expect } from '@playwright/test';

test('debug /workspaces all console', async ({ page }) => {
  const logs: string[] = [];
  page.on('console', (msg) => logs.push(`[${msg.type()}] ${msg.text()}`));

  await page.goto('/workspaces', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(8000);

  console.log('Final URL:', page.url());
  console.log('All logs:');
  logs.forEach(l => console.log(l));
});
