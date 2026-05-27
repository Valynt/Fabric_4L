/**
 * Mock Authentication Constants
 *
 * Exported for use in Playwright tests and development tools.
 * These values match the mock identity defined in AuthContext.tsx.
 *
 * Usage in Playwright:
 *   import { MOCK_TENANT_SLUG, MOCK_ACCOUNT_ID } from '@/test/mockAuth';
 *   await page.goto(`/t/${MOCK_TENANT_SLUG}/accounts/${MOCK_ACCOUNT_ID}/intelligence/signals`);
 */

export const MOCK_USER_ID = 'user_demo';
export const MOCK_TENANT_ID = 'ten_demo';
export const MOCK_TENANT_SLUG = 'demo';
export const MOCK_ACCOUNT_ID = 'acc_demo';
export const MOCK_USER_EMAIL = 'demo@valuepact.ai';
export const MOCK_USER_ROLE = 'admin';

/**
 * Helper to generate mock-auth URLs for testing
 */
export function getMockAuthUrl(path: string): string {
  return `/t/${MOCK_TENANT_SLUG}${path}`;
}

/**
 * Helper to generate account-scoped URLs for testing
 */
export function getMockAccountUrl(path: string): string {
  return `/t/${MOCK_TENANT_SLUG}/accounts/${MOCK_ACCOUNT_ID}${path}`;
}

/**
 * Common mock-auth URLs for testing
 */
export const MOCK_URLS = {
  home: '/home',
  accounts: getMockAuthUrl('/accounts'),
  accountDetail: getMockAccountUrl(''),
  intelligenceSignals: getMockAccountUrl('/intelligence/signals'),
  intelligenceEvidence: getMockAccountUrl('/intelligence/evidence'),
  studioValueModel: getMockAccountUrl('/studio/value-model'),
  studioDriverTree: getMockAccountUrl('/studio/driver-tree'),
  studioCalculator: getMockAccountUrl('/studio/calculator'),
  studioValueCase: getMockAccountUrl('/studio/value-case'),
  deliverables: getMockAuthUrl('/deliverables'),
  governanceFormulas: getMockAuthUrl('/governance/formulas'),
  governanceBenchmarks: getMockAuthUrl('/governance/benchmarks'),
  governanceValuePacks: getMockAuthUrl('/governance/value-packs'),
  contextSources: getMockAuthUrl('/context/sources'),
  contextGraph: getMockAuthUrl('/context/graph'),
  settings: getMockAuthUrl('/settings'),
} as const;
