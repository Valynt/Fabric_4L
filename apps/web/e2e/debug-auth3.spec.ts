import { test, expect } from '@playwright/test';

test('inspect /workspaces DOM', async ({ page }) => {
  await page.goto('/workspaces', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  // Get the full text content
  const text = await page.locator('body').textContent();
  console.log('Body text:', text?.substring(0, 500));

  // Check for specific elements
  const html = await page.locator('body').innerHTML();
  console.log('Has spinner:', html.includes('Verifying session'));
  console.log('Has Navigate:', html.includes('Navigate')); // Navigate doesn't render DOM

  // Look for Clerk components
  const clerkElements = await page.locator('[class*="cl-"]').count();
  console.log('Clerk element count:', clerkElements);

  // Check for any anchor with /sign-in
  const signInLinks = await page.locator('a[href*="sign-in"]').count();
  console.log('Sign-in links:', signInLinks);
});

test('inspect /home DOM', async ({ page }) => {
  await page.goto('/home', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  const text = await page.locator('body').textContent();
  console.log('Body text:', text?.substring(0, 500));
  console.log('URL:', page.url());
});
