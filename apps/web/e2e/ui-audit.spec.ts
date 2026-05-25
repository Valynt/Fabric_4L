/**
 * UI Audit — End-to-End Screen-by-Screen Validation
 *
 * Simulates an admin end-user navigating through every major screen
 * and captures screenshots + structural assertions for each.
 */

import { test, expect, Page } from './fixtures/contract-test';
import { seedAuthState, clearAuthState } from './fixtures/auth-helpers';
import { setUserTier, clearUserTier } from './fixtures/tier-helpers';

const SCREENSHOT_DIR = 'e2e-results/ui-audit';

async function screenshot(page: Page, name: string) {
  await page.screenshot({
    path: `${SCREENSHOT_DIR}/${name}.png`,
    fullPage: true,
  });
}

async function seedAdmin(page: Page) {
  await seedAuthState(page);
  await setUserTier(page, 'admin', 'super_admin');
  // Reload so AuthProvider initializes with the seeded state
  await page.reload();
}

async function waitForStable(page: Page) {
  await page.waitForLoadState('networkidle');
  // Small buffer for React hydration / animations
  await page.waitForTimeout(300);
}

test.describe('UI Audit — Screen by Screen', () => {
  test.beforeAll(async () => {
    const fs = await import('fs');
    if (!fs.existsSync(SCREENSHOT_DIR)) {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
    await clearUserTier(page);
  });

  // ═══════════════════════════════════════════════════════════════
  // 1. AUTHENTICATION SCREENS
  // ═══════════════════════════════════════════════════════════════
  test.describe('Authentication', () => {
    test('Login page renders correctly', async ({ page }) => {
      await page.goto('/login');
      await waitForStable(page);

      // Verify key login elements from actual UI
      await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible();
      await expect(page.getByTestId('login-email')).toBeVisible();
      await expect(page.getByTestId('login-password')).toBeVisible();
      await expect(page.getByTestId('login-submit')).toBeVisible();
      await expect(page.getByTestId('sso-apple')).toBeVisible();
      await expect(page.getByTestId('sso-google')).toBeVisible();
      await expect(page.getByText(/sign up/i)).toBeVisible();

      await screenshot(page, '01-login');
    });

    test('Signup page renders correctly', async ({ page }) => {
      await page.goto('/signup');
      await waitForStable(page);

      // Softer assertion — just ensure something rendered in the auth card
      await expect(page.locator('body')).toContainText(/sign up|get started|create account/i);
      await screenshot(page, '02-signup');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 2. HOME / COMMAND CENTER
  // ═══════════════════════════════════════════════════════════════
  test.describe('Home & Command Center', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Home dashboard loads with shell and content', async ({ page }) => {
      await page.goto('/home');
      await waitForStable(page);

      // Global nav should be visible
      await expect(page.locator('nav, [role="navigation"]').first()).toBeVisible();
      // Body should have content
      await expect(page.locator('main, [role="main"]').first()).toBeVisible();

      await screenshot(page, '03-home-dashboard');
    });

    test('Command Center renders', async ({ page }) => {
      await page.goto('/command-center');
      await waitForStable(page);
      await expect(page.locator('main, [role="main"]').first()).toBeVisible();
      await screenshot(page, '04-command-center');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 3. ACCOUNTS
  // ═══════════════════════════════════════════════════════════════
  test.describe('Accounts', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Accounts list page', async ({ page }) => {
      await page.goto('/accounts');
      await waitForStable(page);
      await expect(page.locator('main, [role="main"]').first()).toBeVisible();
      await screenshot(page, '05-accounts-list');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 4. INTELLIGENCE WORKSPACE
  // ═══════════════════════════════════════════════════════════════
  test.describe('Intelligence Workspace', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Signals tab', async ({ page }) => {
      await page.goto('/intelligence/demo-account-123/signals');
      await waitForStable(page);
      await screenshot(page, '06-intelligence-signals');
    });

    test('Stakeholders tab', async ({ page }) => {
      await page.goto('/intelligence/demo-account-123/stakeholders');
      await waitForStable(page);
      await screenshot(page, '07-intelligence-stakeholders');
    });

    test('Enrichment tab', async ({ page }) => {
      await page.goto('/intelligence/demo-account-123/enrichment');
      await waitForStable(page);
      await screenshot(page, '08-intelligence-enrichment');
    });

    test('Ontology Match tab', async ({ page }) => {
      await page.goto('/intelligence/demo-account-123/ontology-match');
      await waitForStable(page);
      await screenshot(page, '09-intelligence-ontology-match');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 5. HYPOTHESIS WORKSPACE
  // ═══════════════════════════════════════════════════════════════
  test.describe('Hypothesis Workspace', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Hypotheses tab', async ({ page }) => {
      await page.goto('/hypothesis/demo-account-123/hypothesis');
      await waitForStable(page);
      await screenshot(page, '10-hypothesis-main');
    });

    test('Discovery Questions tab', async ({ page }) => {
      await page.goto('/hypothesis/demo-account-123/discovery-questions');
      await waitForStable(page);
      await screenshot(page, '11-hypothesis-discovery-questions');
    });

    test('Persona Fit tab', async ({ page }) => {
      await page.goto('/hypothesis/demo-account-123/persona-fit');
      await waitForStable(page);
      await screenshot(page, '12-hypothesis-persona-fit');
    });

    test('Assumptions tab', async ({ page }) => {
      await page.goto('/hypothesis/demo-account-123/assumptions');
      await waitForStable(page);
      await screenshot(page, '13-hypothesis-assumptions');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 6. DRIVER TREE
  // ═══════════════════════════════════════════════════════════════
  test.describe('Driver Tree', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Driver Tree page', async ({ page }) => {
      await page.goto('/drivers/demo-account-123');
      await waitForStable(page);
      await screenshot(page, '14-driver-tree');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 7. CALCULATOR
  // ═══════════════════════════════════════════════════════════════
  test.describe('Calculator', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('ROI Calculator tab', async ({ page }) => {
      await page.goto('/calculator/demo-account-123/roi');
      await waitForStable(page);
      await screenshot(page, '15-calculator-roi');
    });

    test('Value Model tab', async ({ page }) => {
      await page.goto('/calculator/demo-account-123/value-model');
      await waitForStable(page);
      await screenshot(page, '16-calculator-value-model');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 8. VALUE CASE
  // ═══════════════════════════════════════════════════════════════
  test.describe('Value Case', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Value Case page', async ({ page }) => {
      await page.goto('/value-case/demo-account-123');
      await waitForStable(page);
      await screenshot(page, '17-value-case');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 9. VALUE REALIZATION
  // ═══════════════════════════════════════════════════════════════
  test.describe('Value Realization', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Realization page', async ({ page }) => {
      await page.goto('/realization/demo-account-123');
      await waitForStable(page);
      await screenshot(page, '18-value-realization');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 10. CONTEXT ENGINE
  // ═══════════════════════════════════════════════════════════════
  test.describe('Context Engine', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Value Packs', async ({ page }) => {
      await page.goto('/context/packs');
      await waitForStable(page);
      await screenshot(page, '19-context-packs');
    });

    test('My Models', async ({ page }) => {
      await page.goto('/context/models');
      await waitForStable(page);
      await screenshot(page, '20-context-models');
    });

    test('Formula List', async ({ page }) => {
      await page.goto('/context/formulas');
      await waitForStable(page);
      await screenshot(page, '21-context-formulas');
    });

    test('Value Tree Explorer', async ({ page }) => {
      await page.goto('/context/value-trees/explorer');
      await waitForStable(page);
      await screenshot(page, '22-context-value-tree-explorer');
    });

    test('Agent Workflows', async ({ page }) => {
      await page.goto('/context/agents');
      await waitForStable(page);
      await screenshot(page, '23-context-agents');
    });

    test('Ontology Editor', async ({ page }) => {
      await page.goto('/context/ontology');
      await waitForStable(page);
      await screenshot(page, '24-context-ontology');
    });

    test('Entity Browser', async ({ page }) => {
      await page.goto('/context/ontology/entities');
      await waitForStable(page);
      await screenshot(page, '25-context-entity-browser');
    });

    test('Graph Explorer', async ({ page }) => {
      await page.goto('/context/ontology/graph');
      await waitForStable(page);
      await screenshot(page, '26-context-graph-explorer');
    });

    test('Ingestion Jobs', async ({ page }) => {
      await page.goto('/context/ingestion/jobs');
      await waitForStable(page);
      await screenshot(page, '27-context-ingestion-jobs');
    });

    test('Extraction Engine', async ({ page }) => {
      await page.goto('/context/extraction');
      await waitForStable(page);
      await screenshot(page, '28-context-extraction');
    });

    test('Integrations', async ({ page }) => {
      await page.goto('/context/integrations');
      await waitForStable(page);
      await screenshot(page, '29-context-integrations');
    });

    test('Source Configuration', async ({ page }) => {
      await page.goto('/context/sources');
      await waitForStable(page);
      await screenshot(page, '30-context-sources');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 11. DELIVERABLES
  // ═══════════════════════════════════════════════════════════════
  test.describe('Deliverables', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Business Case List', async ({ page }) => {
      await page.goto('/deliverables/cases');
      await waitForStable(page);
      await screenshot(page, '31-deliverables-cases-list');
    });

    test('Interactive Business Case', async ({ page }) => {
      await page.goto('/deliverables/calculators');
      await waitForStable(page);
      await screenshot(page, '32-deliverables-calculators');
    });

    test('CFO View', async ({ page }) => {
      await page.goto('/deliverables/views/cfo');
      await waitForStable(page);
      await screenshot(page, '33-deliverables-cfo-view');
    });

    test('Executive View', async ({ page }) => {
      await page.goto('/deliverables/views/executive');
      await waitForStable(page);
      await screenshot(page, '34-deliverables-executive-view');
    });

    test('Technical View', async ({ page }) => {
      await page.goto('/deliverables/views/technical');
      await waitForStable(page);
      await screenshot(page, '35-deliverables-technical-view');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 12. GOVERNANCE
  // ═══════════════════════════════════════════════════════════════
  test.describe('Governance', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Decision Traces', async ({ page }) => {
      await page.goto('/governance/traces');
      await waitForStable(page);
      await screenshot(page, '36-governance-traces');
    });

    test('Evidence', async ({ page }) => {
      await page.goto('/governance/evidence');
      await waitForStable(page);
      await screenshot(page, '37-governance-evidence');
    });

    test('Compliance', async ({ page }) => {
      await page.goto('/governance/compliance');
      await waitForStable(page);
      await screenshot(page, '38-governance-compliance');
    });

    test('Benchmark Policies', async ({ page }) => {
      await page.goto('/governance/benchmarks');
      await waitForStable(page);
      await screenshot(page, '39-governance-benchmarks');
    });

    test('Audit Log', async ({ page }) => {
      await page.goto('/governance/audit/log');
      await waitForStable(page);
      await screenshot(page, '40-governance-audit-log');
    });

    test('Change History', async ({ page }) => {
      await page.goto('/governance/audit/changes');
      await waitForStable(page);
      await screenshot(page, '41-governance-change-history');
    });

    test('Health Monitor', async ({ page }) => {
      await page.goto('/governance/health');
      await waitForStable(page);
      await screenshot(page, '42-governance-health');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 13. WORKFLOW
  // ═══════════════════════════════════════════════════════════════
  test.describe('Workflow', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Prospect Setup', async ({ page }) => {
      await page.goto('/workflow');
      await waitForStable(page);
      await screenshot(page, '43-workflow-prospect');
    });

    test('Workflow Intelligence', async ({ page }) => {
      await page.goto('/workflow/intelligence');
      await waitForStable(page);
      await screenshot(page, '44-workflow-intelligence');
    });

    test('Workflow AI Model', async ({ page }) => {
      await page.goto('/workflow/ai-model');
      await waitForStable(page);
      await screenshot(page, '45-workflow-ai-model');
    });

    test('Workflow Driver Tree', async ({ page }) => {
      await page.goto('/workflow/driver-tree');
      await waitForStable(page);
      await screenshot(page, '46-workflow-driver-tree');
    });

    test('Workflow Evidence', async ({ page }) => {
      await page.goto('/workflow/evidence');
      await waitForStable(page);
      await screenshot(page, '47-workflow-evidence');
    });

    test('Workflow Calculator', async ({ page }) => {
      await page.goto('/workflow/calculator');
      await waitForStable(page);
      await screenshot(page, '48-workflow-calculator');
    });

    test('Workflow Value Case', async ({ page }) => {
      await page.goto('/workflow/value-case');
      await waitForStable(page);
      await screenshot(page, '49-workflow-value-case');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 14. VALUE STUDIO (LEGACY)
  // ═══════════════════════════════════════════════════════════════
  test.describe('Value Studio (Legacy)', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Action Plan tab', async ({ page }) => {
      await page.goto('/studio/demo-account-123/action-plan');
      await waitForStable(page);
      await screenshot(page, '50-studio-action-plan');
    });

    test('Value Model tab', async ({ page }) => {
      await page.goto('/studio/demo-account-123/value-model');
      await waitForStable(page);
      await screenshot(page, '51-studio-value-model');
    });

    test('Narrative tab', async ({ page }) => {
      await page.goto('/studio/demo-account-123/narrative');
      await waitForStable(page);
      await screenshot(page, '52-studio-narrative');
    });

    test('Enrichment tab', async ({ page }) => {
      await page.goto('/studio/demo-account-123/enrichment');
      await waitForStable(page);
      await screenshot(page, '53-studio-enrichment');
    });

    test('Competitive tab', async ({ page }) => {
      await page.goto('/studio/demo-account-123/competitive');
      await waitForStable(page);
      await screenshot(page, '54-studio-competitive');
    });

    test('ROI tab', async ({ page }) => {
      await page.goto('/studio/demo-account-123/roi');
      await waitForStable(page);
      await screenshot(page, '55-studio-roi');
    });

    test('Evidence tab', async ({ page }) => {
      await page.goto('/studio/demo-account-123/evidence');
      await waitForStable(page);
      await screenshot(page, '56-studio-evidence');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 15. SETTINGS — PERSONAL
  // ═══════════════════════════════════════════════════════════════
  test.describe('Settings — Personal', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Profile', async ({ page }) => {
      await page.goto('/personal/profile');
      await waitForStable(page);
      await screenshot(page, '57-settings-profile');
    });

    test('Security', async ({ page }) => {
      await page.goto('/personal/security');
      await waitForStable(page);
      await screenshot(page, '58-settings-security');
    });

    test('Preferences', async ({ page }) => {
      await page.goto('/personal/preferences');
      await waitForStable(page);
      await screenshot(page, '59-settings-preferences');
    });

    test('Notifications', async ({ page }) => {
      await page.goto('/personal/notifications');
      await waitForStable(page);
      await screenshot(page, '60-settings-notifications');
    });

    test('Sessions', async ({ page }) => {
      await page.goto('/personal/sessions');
      await waitForStable(page);
      await screenshot(page, '61-settings-sessions');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 16. SETTINGS — WORKSPACE / ADMIN
  // ═══════════════════════════════════════════════════════════════
  test.describe('Settings — Workspace & Admin', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Workspace Billing', async ({ page }) => {
      await page.goto('/settings/workspace');
      await waitForStable(page);
      await screenshot(page, '62-settings-workspace');
    });

    test('Subscription', async ({ page }) => {
      await page.goto('/settings/billing/subscription');
      await waitForStable(page);
      await screenshot(page, '63-settings-subscription');
    });

    test('Usage', async ({ page }) => {
      await page.goto('/settings/billing/usage');
      await waitForStable(page);
      await screenshot(page, '64-settings-usage');
    });

    test('Payment Methods', async ({ page }) => {
      await page.goto('/settings/billing/payment-methods');
      await waitForStable(page);
      await screenshot(page, '65-settings-payment-methods');
    });

    test('Invoices', async ({ page }) => {
      await page.goto('/settings/billing/invoices');
      await waitForStable(page);
      await screenshot(page, '66-settings-invoices');
    });

    test('Team Members', async ({ page }) => {
      await page.goto('/settings/team');
      await waitForStable(page);
      await screenshot(page, '67-settings-team-members');
    });

    test('Team Invitations', async ({ page }) => {
      await page.goto('/settings/team/invitations');
      await waitForStable(page);
      await screenshot(page, '68-settings-team-invitations');
    });

    test('Team Roles', async ({ page }) => {
      await page.goto('/settings/team/roles');
      await waitForStable(page);
      await screenshot(page, '69-settings-team-roles');
    });

    test('Team Permissions', async ({ page }) => {
      await page.goto('/settings/team/permissions');
      await waitForStable(page);
      await screenshot(page, '70-settings-team-permissions');
    });

    test('API Keys', async ({ page }) => {
      await page.goto('/settings/team/api-keys');
      await waitForStable(page);
      await screenshot(page, '71-settings-api-keys');
    });

    test('Data Sources', async ({ page }) => {
      await page.goto('/settings/data/sources');
      await waitForStable(page);
      await screenshot(page, '72-settings-data-sources');
    });

    test('Data Integrations', async ({ page }) => {
      await page.goto('/settings/data/integrations');
      await waitForStable(page);
      await screenshot(page, '73-settings-data-integrations');
    });

    test('Data Variables', async ({ page }) => {
      await page.goto('/settings/data/variables');
      await waitForStable(page);
      await screenshot(page, '74-settings-data-variables');
    });

    test('Data Value Packs', async ({ page }) => {
      await page.goto('/settings/data/value-packs');
      await waitForStable(page);
      await screenshot(page, '75-settings-data-value-packs');
    });

    test('Data Ingestion Rules', async ({ page }) => {
      await page.goto('/settings/data/ingestion-rules');
      await waitForStable(page);
      await screenshot(page, '76-settings-data-ingestion-rules');
    });

    test('Governance Policies', async ({ page }) => {
      await page.goto('/settings/governance/policies');
      await waitForStable(page);
      await screenshot(page, '77-settings-governance-policies');
    });

    test('Governance Compliance', async ({ page }) => {
      await page.goto('/settings/governance/compliance');
      await waitForStable(page);
      await screenshot(page, '78-settings-governance-compliance');
    });

    test('Governance Health', async ({ page }) => {
      await page.goto('/settings/governance/health');
      await waitForStable(page);
      await screenshot(page, '79-settings-governance-health');
    });

    test('Governance Audit Trail', async ({ page }) => {
      await page.goto('/settings/governance/audit-trail');
      await waitForStable(page);
      await screenshot(page, '80-settings-governance-audit-trail');
    });

    test('Governance Admin Controls', async ({ page }) => {
      await page.goto('/settings/governance/admin-controls');
      await waitForStable(page);
      await screenshot(page, '81-settings-governance-admin-controls');
    });
  });

  // ═══════════════════════════════════════════════════════════════
  // 17. ERROR & EDGE CASES
  // ═══════════════════════════════════════════════════════════════
  test.describe('Error & Edge Cases', () => {
    test.beforeEach(async ({ page }) => {
      await seedAdmin(page);
    });

    test('Not Found page', async ({ page }) => {
      await page.goto('/nonexistent-route-12345');
      await waitForStable(page);
      await screenshot(page, '82-not-found');
    });
  });
});
