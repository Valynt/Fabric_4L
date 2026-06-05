#!/usr/bin/env node
/**
 * Fails when critical E2E journeys are weakened with test.skip/test.fixme or
 * a backend skip valve. H-06 requires mobile navigation and backend CRUD
 * journeys to fail closed rather than disappearing from CI coverage.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, relative } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, '..', '..');

const criticalFiles = [
  'e2e/navigation.spec.ts',
  'e2e/my-models.spec.ts',
  'playwright.config.ts',
  'e2e/global-setup.ts',
  'package.json',
  'e2e/helpers/validation-program.ts',
  'e2e/journeys/j1-ingestion-to-value-tree.spec.ts',
  'e2e/journeys/j2-intelligence-workspace.spec.ts',
  'e2e/journeys/j3-value-studio-deliverable.spec.ts',
  'e2e/journeys/j6-account-prospect-lifecycle.spec.ts',
  'e2e/journeys/j6-account-tenant-switching.spec.ts',
  'e2e/journeys/j7-value-realization-and-calculation.spec.ts',
  'e2e/journeys/j8-approval-review-gates.spec.ts',
  'e2e/journeys/j9-agent-grounding-governance.spec.ts',
  'e2e/journeys/j10-layer-ui-validation.spec.ts',
  'e2e/journeys/j12-resilience-error-recovery.spec.ts',
  'e2e/journeys/j13-stakeholder-mapping.spec.ts',
  'e2e/journeys/j14-value-pack-governance.spec.ts',
  'e2e/journeys/j15-narrative-proposal.spec.ts',
  'e2e/journeys/j16-collaboration.spec.ts',
  'e2e/journeys/j17-crm-integration.spec.ts',
  'e2e/journeys/j18-search-retrieval.spec.ts',
  'e2e/journeys/j19-notifications-tasks.spec.ts',
  'e2e/journeys/j20-admin-configuration.spec.ts',
  'e2e/journeys/j20-billing-entitlement-gates.spec.ts',
  'e2e/journeys/j21-persona-journeys.spec.ts',
  'e2e/journeys/j22-adversarial-e2e.spec.ts',
  'e2e/journeys/j23-personal-settings.spec.ts',
  'e2e/security/tenant-isolation-validation.spec.ts',
  'e2e/security/deep-link-tenant-isolation-deep.spec.ts',
  'e2e/resilience/operational-resilience.spec.ts',
  'e2e/collaboration/collaboration-notifications-tasks.spec.ts',
  'e2e/export-workflows.spec.ts',
  'e2e/personas/persona-journeys.spec.ts',
  'e2e/journeys/j11-golden-path-business-lifecycle.spec.ts',
  'e2e/integrations/crm-external-integrations.spec.ts',
  'e2e/journeys/j1-golden-path-deep.spec.ts',
  'e2e/journeys/j1-golden-path-backend-integrated.spec.ts',
  'e2e/journeys/j7-calculation-evidence-deep.spec.ts',
  'e2e/journeys/j8-approval-review-deep.spec.ts',
  'e2e/journeys/j9-agent-grounding-deep.spec.ts',
  'e2e/journeys/j10-layer-ui-validation-deep.spec.ts',
  'e2e/security/tenant-isolation-deep.spec.ts',
  'e2e/export/export-workflows-deep.spec.ts',
  'e2e/admin.spec.ts',
  'e2e/admin-system.spec.ts',
  'e2e/contracts/account-scoped-workspaces.spec.ts',
  'e2e/contracts/settings-governance.spec.ts',
  'e2e/value-tree-explorer.spec.ts',
  'e2e/business-case.spec.ts',
  'e2e/business-case-list.spec.ts',
  'docs/frontend-workflow-coverage-matrix.md',
  'scripts/quality/assert-frontend-workflow-matrix.mjs',
  'scripts/quality/verify-frontend.mjs',
];

const forbidden = [
  { pattern: /test\.(skip|fixme)\s*\(/, label: 'test.skip/test.fixme' },
  { pattern: /\btest\.skip\s*\(/, label: 'test.skip' },
  { pattern: /\btest\.fixme\s*\(/, label: 'test.fixme' },
  { pattern: /\bjourneyTest\.skip\s*\(/, label: 'journeyTest.skip' },
  { pattern: /\bSKIP_BACKEND_TESTS\b/, label: 'SKIP_BACKEND_TESTS backend skip valve' },
  { pattern: /Mobile navigation.*skipped|not yet implemented in AppShell/i, label: 'stale mobile-navigation skipped claim' },
];

const requiredEvidence = [
  {
    file: 'playwright.config.ts',
    pattern: /name:\s*['"]backend-integrated['"]/,
    label: 'backend-integrated Playwright project',
  },
  {
    file: 'playwright.config.ts',
    pattern: /grep:\s*\/@backend\//,
    label: '@backend-only backend-integrated project filter',
  },
  {
    file: 'playwright.config.ts',
    pattern: /globalSetup:\s*['"]\.\/e2e\/global-setup\.ts['"]/,
    label: 'backend deterministic global setup wiring',
  },
  {
    file: 'e2e/my-models.spec.ts',
    pattern: /PLAYWRIGHT_BACKEND_URL is required for the @backend My Models CRUD journey/,
    label: 'fail-closed backend URL requirement in My Models CRUD journey',
  },
  {
    file: 'e2e/global-setup.ts',
    pattern: /seed-e2e-data/,
    label: 'deterministic backend seed execution',
  },
  {
    file: 'package.json',
    pattern: /test:e2e:validation/,
    label: 'dedicated validation-program E2E command',
  },
  {
    file: 'package.json',
    pattern: /test:e2e:validation:p0(?=[\s\S]*j6-account-prospect-lifecycle\.spec\.ts)(?=[\s\S]*j1-golden-path-backend-integrated\.spec\.ts)(?=[\s\S]*j20-billing-entitlement-gates\.spec\.ts)/,
    label: 'P0 validation command with account lifecycle, backend golden path, and billing gate coverage',
  },
  {
    file: 'package.json',
    pattern: /test:e2e:validation:p1[\s\S]*j2-intelligence-workspace\.spec\.ts[\s\S]*j23-personal-settings\.spec\.ts[\s\S]*crm-external-integrations\.spec\.ts/,
    label: 'P1 validation command with intelligence, personal, and integration coverage',
  },
  {
    file: 'package.json',
    pattern: /j11-golden-path-business-lifecycle\.spec\.ts/,
    label: 'golden-path validation suite wiring',
  },
  {
    file: 'package.json',
    pattern: /crm-external-integrations\.spec\.ts/,
    label: 'CRM validation suite wiring',
  },
  {
    file: 'e2e/journeys/j9-agent-grounding-governance.spec.ts',
    pattern: /SECURITY-PROMPT-INJECTION-001/,
    label: 'agent prompt-injection validation coverage',
  },
  {
    file: 'e2e/security/tenant-isolation-validation.spec.ts',
    pattern: /SEC-TENANT-001/,
    label: 'tenant isolation validation coverage',
  },
  {
    file: 'e2e/export-workflows.spec.ts',
    pattern: /EXPORT-GATE-001/,
    label: 'approval-gated export validation coverage',
  },
  {
    file: 'e2e/journeys/j11-golden-path-business-lifecycle.spec.ts',
    pattern: /test_golden_path_account_to_approved_business_case @backend/,
    label: 'backend-integrated golden path validation coverage',
  },
  {
    file: 'package.json',
    pattern: /test:e2e:validation:deep/,
    label: 'dedicated deep validation-program E2E command',
  },
  {
    file: 'e2e/journeys/j1-golden-path-deep.spec.ts',
    pattern: /GP-DEEP-001/,
    label: 'deep golden path validation coverage',
  },
  {
    file: 'e2e/security/tenant-isolation-deep.spec.ts',
    pattern: /SEC-DEEP-001/,
    label: 'deep tenant isolation validation coverage',
  },
  {
    file: 'e2e/journeys/j9-agent-grounding-deep.spec.ts',
    pattern: /AG-DEEP-001/,
    label: 'deep agent grounding validation coverage',
  },
  {
    file: 'docs/frontend-workflow-coverage-matrix.md',
    pattern: /P0-ACCOUNT-LIFECYCLE[\s\S]*P0-CALC-EVIDENCE[\s\S]*P0-APPROVAL-EXPORT[\s\S]*P0-AGENT-GOVERNANCE[\s\S]*P0-LAYER-VALIDATION/,
    label: 'P0 workflow coverage matrix rows',
  },
  {
    file: 'docs/frontend-workflow-coverage-matrix.md',
    pattern: /P1-INTELLIGENCE[\s\S]*P1-STUDIO[\s\S]*P1-CONTEXT[\s\S]*P1-STAKEHOLDERS[\s\S]*P1-NARRATIVE-PROPOSAL[\s\S]*P1-COLLABORATION[\s\S]*P1-SEARCH-SECURITY[\s\S]*P1-NOTIFICATIONS-TASKS[\s\S]*P1-ADMIN-CONFIG[\s\S]*P1-RESILIENCE[\s\S]*P1-ADVERSARIAL[\s\S]*P1-PERSONAS[\s\S]*P1-SETTINGS[\s\S]*P1-PERSONAL[\s\S]*P1-INTEGRATIONS/,
    label: 'P1 workflow coverage matrix rows',
  },
  {
    file: 'e2e/journeys/j23-personal-settings.spec.ts',
    pattern: /PERSONAL-001[\s\S]*PERSONAL-006/,
    label: 'direct personal settings journey coverage',
  },
  {
    file: 'package.json',
    pattern: /verify:frontend/,
    label: 'single frontend verification command',
  },
  {
    file: 'package.json',
    pattern: /test:workflow-matrix/,
    label: 'workflow matrix validation command',
  },
  {
    file: 'package.json',
    pattern: /test:bundle-budget/,
    label: 'frontend bundle-budget command',
  },
  {
    file: 'e2e/export/export-workflows-deep.spec.ts',
    pattern: /EXPORT-DEEP-001/,
    label: 'deep export gate validation coverage',
  },
];

const failures = [];
for (const file of criticalFiles) {
  const path = resolve(webRoot, file);
  const text = readFileSync(path, 'utf8');
  for (const { pattern, label } of forbidden) {
    if (pattern.test(text)) {
      failures.push(`${relative(webRoot, path)} contains forbidden ${label}`);
    }
  }
}

for (const { file, pattern, label } of requiredEvidence) {
  const path = resolve(webRoot, file);
  const text = readFileSync(path, 'utf8');
  if (!pattern.test(text)) {
    failures.push(`${relative(webRoot, path)} is missing required ${label}`);
  }
}

if (failures.length > 0) {
  console.error('Critical E2E journey coverage must fail closed.');
  for (const failure of failures) {
    console.error(` - ${failure}`);
  }
  process.exit(1);
}

console.log('Critical E2E journey guard passed: no skipped mobile, backend CRUD, P0, or P1 validation journeys, and product-confidence wiring is present.');
