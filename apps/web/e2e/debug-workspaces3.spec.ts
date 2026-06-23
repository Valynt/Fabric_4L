import { test, expect } from '@playwright/test';

test('fetch RequireClerkAuth module from Vite', async ({ page }) => {
  // Vite serves source files at /@fs/ paths or via the module graph
  const response = await page.request.get('http://localhost:3001/src/components/routing/RequireClerkAuth.tsx');
  const body = await response.text();
  console.log('Has console.log:', body.includes('console.log'));
  console.log('Has RequireClerkAuth render:', body.includes('RequireClerkAuth render'));
});
