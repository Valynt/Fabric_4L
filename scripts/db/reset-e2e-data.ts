#!/usr/bin/env npx tsx
/**
 * reset-e2e-data.ts — E2E Test Data Reset
 *
 * Cleans up all data scoped to the E2E tenant. Safe to run before or after
 * journey tests. Does NOT affect other tenants or production data.
 *
 * Usage:
 *   npx tsx scripts/reset-e2e-data.ts
 *   npx tsx scripts/reset-e2e-data.ts --base-url http://localhost:8004
 */

const BASE_URL =
  process.argv.find((a) => a.startsWith('--base-url='))?.split('=')[1] ??
  process.env.PLAYWRIGHT_BACKEND_URL ??
  'http://localhost:8004';

const E2E_TENANT_ID = process.env.BACKEND_E2E_TENANT_ID || '00000000-0000-4000-e2e0-000000000001';

const HEADERS: Record<string, string> = {
  'Content-Type': 'application/json',
  'X-Tenant-ID': E2E_TENANT_ID,
  'X-User-ID': 'e2e-admin-user',
  'X-User-Role': 'admin',
};

async function api(
  method: string,
  path: string,
  body?: unknown,
): Promise<{ status: number; data: unknown }> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    method,
    headers: HEADERS,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data: unknown;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  return { status: res.status, data };
}

async function main() {
  console.log('╔══════════════════════════════════════════════════════════╗');
  console.log('║  Fabric 4L — E2E Data Reset                            ║');
  console.log('╚══════════════════════════════════════════════════════════╝');
  console.log(`  Backend: ${BASE_URL}`);
  console.log(`  Tenant:  ${E2E_TENANT_ID}`);
  console.log('');

  // Health check
  console.log('[0/3] Health check...');
  const health = await api('GET', '/health');
  if (health.status !== 200) {
    console.error(`  ✗ Backend not healthy (status ${health.status})`);
    process.exit(1);
  }
  console.log('  ✓ Backend healthy');

  // Step 1: Clear workspace data for all known cases
  console.log('\n[1/3] Clearing workspace data...');
  const casesResult = await api('GET', '/v1/analysis/cases?account_id=acct-meridian-001');
  const items = Array.isArray((casesResult.data as any)?.items)
    ? (casesResult.data as any).items
    : [];

  for (const item of items) {
    const caseId = item.case_id || item.id;
    if (!caseId) continue;

    const tabs = ['signals', 'drivers', 'evidence', 'stakeholders', 'value-model', 'narrative', 'action-plan'];
    for (const tab of tabs) {
      await api('PUT', `/v1/analysis/cases/${caseId}/workspace/${tab}`, { [tab]: [] });
    }
    console.log(`  ✓ Cleared workspace for case ${caseId}`);
  }

  if (items.length === 0) {
    console.log('  ✓ No cases found — nothing to clear');
  }

  // Step 2: Clear localStorage-based case ID mappings
  // (This happens in the browser via Playwright — we just note it here)
  console.log('\n[2/3] Browser localStorage...');
  console.log('  ℹ localStorage is cleared per-test by Playwright context isolation');

  // Step 3: Reset platform settings to defaults
  console.log('\n[3/3] Resetting platform settings...');
  const resetSettings = await api('PATCH', '/v1/tenants/current/settings', {
    features: {},
    notifications: { email: false, slack: false },
    branding: {},
  });
  if (resetSettings.status >= 200 && resetSettings.status < 300) {
    console.log('  ✓ Platform settings reset');
  } else {
    console.log(`  ⚠ Settings reset returned ${resetSettings.status}`);
  }

  console.log('\n══════════════════════════════════════════════════════════');
  console.log('  E2E data reset complete');
  console.log('  Run `npx tsx scripts/seed-e2e-data.ts` to re-seed');
  console.log('══════════════════════════════════════════════════════════');
}

main().catch((err) => {
  console.error('Reset script failed:', err);
  process.exit(1);
});
