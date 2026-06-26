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
  'e2e/helpers/journey-fixture.ts',
  'e2e/helpers/api-harness.ts',
  'e2e/support/unexpected-errors.ts',
  'e2e/journeys/j1-ingestion-to-value-tree.spec.ts',
  'e2e/journeys/j2-intelligence-workspace.spec.ts',
  'e2e/journeys/j3-value-studio-deliverable.spec.ts',
  'e2e/journeys/j5-tier-gated-security.spec.ts',
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
  'e2e/security/hostile-tenant-journey.spec.ts',
  'e2e/security/hostile-tenant-enforcement-matrix.spec.ts',
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
  'docs/frontend-user-workflows.md',
  'docs/frontend-workflow-contracts.json',
  'docs/frontend-release-evidence.template.json',
  'src/test/oracles/valueCalculationOracle.test.ts',
  '../../tests/security/test_hostile_tenant_e2e_matrix.py',
  '../../services/layer4-agents/tests/test_analysis_routes.py',
  '../../services/layer4-agents/tests/test_agent_grounding_and_refusal.py',
  'scripts/quality/assert-frontend-workflow-matrix.mjs',
  'scripts/quality/assert-frontend-workflow-contracts.mjs',
  'scripts/quality/assert-route-inventory.mjs',
  'scripts/quality/assert-frontend-release-evidence.mjs',
  'scripts/quality/test-frontend-release-evidence-validator.mjs',
  'scripts/quality/verify-frontend.mjs',
];

const forbidden = [
  { pattern: /test\.(skip|fixme)\s*\(/, label: 'test.skip/test.fixme' },
  { pattern: /\btest\.skip\s*\(/, label: 'test.skip' },
  { pattern: /\btest\.fixme\s*\(/, label: 'test.fixme' },
  { pattern: /\bjourneyTest\.skip\s*\(/, label: 'journeyTest.skip' },
  { pattern: /\bpytest\.mark\.skip\b/, label: 'pytest.mark.skip backend skip' },
  { pattern: /\bSKIP_BACKEND_TESTS\b/, label: 'SKIP_BACKEND_TESTS backend skip valve' },
  { pattern: /\bwaitForTimeout\s*\(/, label: 'arbitrary Playwright timeout' },
  { pattern: /\[401,\s*403,\s*404\]/, label: 'loose security status bucket' },
  { pattern: /403\s+or\s+404|401\s+or\s+403\s+or\s+404/i, label: 'loose security status wording' },
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
    file: 'e2e/helpers/journey-fixture.ts',
    pattern: /attachUnexpectedErrorAudit[\s\S]*onUnhandledRequest[\s\S]*audit\.assertClean/,
    label: 'journey fixture unexpected browser and network error audit',
  },
  {
    file: 'e2e/support/unexpected-errors.ts',
    pattern: /pageErrors[\s\S]*consoleErrors[\s\S]*http5xx[\s\S]*failedJobs[\s\S]*unhandledApiRequests[\s\S]*page\.on\('pageerror'[\s\S]*page\.on\('console'[\s\S]*page\.on\('response'/,
    label: 'unexpected page, console, HTTP 5xx, failed-job, and unhandled-mock detection',
  },
  {
    file: 'e2e/helpers/api-harness.ts',
    pattern: /onUnhandledRequest[\s\S]*Unmatched request aborted[\s\S]*onUnhandledRequest\?\./,
    label: 'API harness unhandled request reporting',
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
    file: 'e2e/security/hostile-tenant-enforcement-matrix.spec.ts',
    pattern: /status === vector\.status && denied\.code === vector\.errorCode[\s\S]*expected exact denial/,
    label: 'exact hostile-tenant status and error-code assertions',
  },
  {
    file: 'e2e/security/hostile-tenant-enforcement-matrix.spec.ts',
    pattern: /(?=[\s\S]*operation:\s*'list')(?=[\s\S]*operation:\s*'read')(?=[\s\S]*operation:\s*'create')(?=[\s\S]*operation:\s*'update')(?=[\s\S]*operation:\s*'delete')(?=[\s\S]*operation:\s*'search')(?=[\s\S]*operation:\s*'export')(?=[\s\S]*operation:\s*'background-job lookup')(?=[\s\S]*operation:\s*'file download')(?=[\s\S]*operation:\s*'agent retrieval')(?=[\s\S]*deniedActionsObserved)/,
    label: 'hostile-tenant tenant-owned operation family matrix',
  },
  {
    file: '../../tests/security/test_hostile_tenant_e2e_matrix.py',
    pattern: /REQUIRED_OPERATIONS[\s\S]*operation: 'list'[\s\S]*operation: 'read'[\s\S]*operation: 'create'[\s\S]*operation: 'update'[\s\S]*operation: 'delete'[\s\S]*operation: 'search'[\s\S]*operation: 'export'[\s\S]*operation: 'background-job lookup'[\s\S]*operation: 'file download'[\s\S]*operation: 'agent retrieval'/,
    label: 'root hostile-tenant operation family static guard',
  },
  {
    file: 'e2e/export-workflows.spec.ts',
    pattern: /EXPORT-GATE-001/,
    label: 'approval-gated export validation coverage',
  },
  {
    file: '../../services/layer4-agents/tests/test_analysis_routes.py',
    pattern: /test_export_route_rejects_draft_case_before_document_generation(?=[\s\S]*status_code == 409)(?=[\s\S]*fake_executor\.get_result_calls == \[\])(?=[\s\S]*denied_reason": "approval_required")/,
    label: 'endpoint-level draft export denial before document generation',
  },
  {
    file: '../../services/layer4-agents/tests/test_analysis_routes.py',
    pattern: /test_export_route_approved_case_uploads_tenant_scoped_artifacts_and_audits[\s\S]*download_ready[\s\S]*tenant_id[\s\S]*EXPORT_PACKAGE_GENERATED[\s\S]*EXPORT_DOWNLOAD_ACCESSED/,
    label: 'endpoint-level approved export, tenant-scoped artifact, and audit proof',
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
    file: '../../services/layer4-agents/tests/test_agent_grounding_and_refusal.py',
    pattern: /AgentGovernanceCorpusCase[\s\S]*valid grounded question[\s\S]*question without supporting evidence[\s\S]*cross-tenant document reference[\s\S]*indirect prompt injection in ingested document[\s\S]*system prompt or credential exposure[\s\S]*unauthorized tool invocation[\s\S]*malformed citation[\s\S]*provider timeout fallback/,
    label: 'deterministic agent governance adversarial corpus',
  },
  {
    file: '../../services/layer4-agents/tests/test_agent_grounding_and_refusal.py',
    pattern: /(?=[\s\S]*expected_refusal_reason)(?=[\s\S]*POLICY_DECISION)(?=[\s\S]*AGENT_EXECUTION)(?=[\s\S]*forbidden_content)(?=[\s\S]*stack trace)(?=[\s\S]*traceback)/,
    label: 'agent governance audit and safe-error assertions',
  },
  {
    file: 'package.json',
    pattern: /test:calculation-oracle/,
    label: 'calculation oracle validation command',
  },
  {
    file: 'src/test/oracles/valueCalculationOracle.test.ts',
    pattern: /canonical one-year ROI case[\s\S]*grossValue:\s*400_000[\s\S]*realizedValue:\s*300_000[\s\S]*netValue:\s*150_000[\s\S]*roiPercent:\s*100/,
    label: 'independently reviewed canonical calculation oracle case',
  },
  {
    file: 'src/test/oracles/valueCalculationOracle.test.ts',
    pattern: /zero total cost[\s\S]*roiPercent:\s*null[\s\S]*negative values[\s\S]*periodYears must be > 0[\s\S]*higher implementation cost cannot increase ROI/,
    label: 'calculation oracle boundary and invariant coverage',
  },
  {
    file: 'docs/frontend-workflow-coverage-matrix.md',
    pattern: /P0-ACCOUNT-LIFECYCLE[\s\S]*P0-CALC-EVIDENCE[\s\S]*valueCalculationOracle\.test\.ts[\s\S]*P0-APPROVAL-EXPORT[\s\S]*P0-AGENT-GOVERNANCE[\s\S]*P0-LAYER-VALIDATION/,
    label: 'P0 workflow coverage matrix rows',
  },
  {
    file: 'docs/frontend-user-workflows.md',
    pattern: /J0 \/ Auth Session[\s\S]*J1 \/ Domain Ingestion To Value Tree[\s\S]*P0 \/ Approval-Gated Export[\s\S]*P1 \/ Integrations/,
    label: 'step-by-step frontend workflow inventory',
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
    pattern: /test:workflow-contracts/,
    label: 'workflow business-contract validation command',
  },
  {
    file: 'docs/frontend-workflow-coverage-matrix.md',
    pattern: /docs\/frontend-workflow-contracts\.json[\s\S]*test:workflow-contracts/,
    label: 'workflow matrix executable-contract reference',
  },
  {
    file: 'docs/frontend-workflow-contracts.json',
    pattern: /P0-ACCOUNT-LIFECYCLE[\s\S]*expectedBackend[\s\S]*securityInvariants[\s\S]*auditInvariants/,
    label: 'P0 business contract planes',
  },
  {
    file: 'docs/frontend-workflow-contracts.json',
    pattern: /evidenceByPlane[\s\S]*"ui"[\s\S]*"backend"[\s\S]*"security"[\s\S]*"audit"/,
    label: 'per-plane workflow evidence ownership',
  },
  {
    file: 'package.json',
    pattern: /test:route-inventory/,
    label: 'route inventory validation command',
  },
  {
    file: 'package.json',
    pattern: /test:frontend-release-evidence/,
    label: 'frontend release evidence validation command',
  },
  {
    file: 'package.json',
    pattern: /test:frontend-release-evidence:validator/,
    label: 'frontend release evidence validator self-test command',
  },
  {
    file: 'package.json',
    pattern: /verify:frontend:release/,
    label: 'frontend release verification command',
  },
  {
    file: 'docs/frontend-workflow-coverage-matrix.md',
    pattern: /docs\/frontend-release-evidence\.template\.json[\s\S]*test:frontend-release-evidence[\s\S]*exact commit SHA[\s\S]*image digest[\s\S]*live P0 browser journeys/,
    label: 'release evidence supplement policy',
  },
  {
    file: 'scripts/quality/assert-frontend-release-evidence.mjs',
    pattern: /requiredP0Journeys[\s\S]*requireInfrastructure[\s\S]*requiredAuthorizationActors[\s\S]*requiredLiveProviders[\s\S]*requiredSyntheticChecks/,
    label: 'frontend release evidence validator coverage',
  },
  {
    file: 'scripts/quality/test-frontend-release-evidence-validator.mjs',
    pattern: /buildEvidence[\s\S]*runValidator[\s\S]*missingProvider[\s\S]*liveProviderSmoke\.providers must include crm/,
    label: 'frontend release evidence validator positive and negative self-test',
  },
  {
    file: 'docs/frontend-release-evidence.template.json',
    pattern: /"infrastructure"[\s\S]*"P0-ACCOUNT-LIFECYCLE"[\s\S]*"P0-CALC-EVIDENCE"[\s\S]*"P0-APPROVAL-EXPORT"[\s\S]*"P0-AGENT-GOVERNANCE"[\s\S]*"P0-LAYER-VALIDATION"[\s\S]*"llm"[\s\S]*"crm"[\s\S]*"email"[\s\S]*"clerk"[\s\S]*"pdf-processing"[\s\S]*"export-rendering"[\s\S]*"sign-in"[\s\S]*"trace-and-audit"/,
    label: 'frontend release evidence template named live proof fields',
  },
  {
    file: 'docs/frontend-workflow-coverage-matrix.md',
    pattern: /test:route-inventory[\s\S]*TieredNav[\s\S]*legacy redirects/,
    label: 'route inventory safety gate reference',
  },
  {
    file: 'scripts/quality/assert-route-inventory.mjs',
    pattern: /validateTieredNavDestinations[\s\S]*validateRouteAccessPolicyMetadata[\s\S]*validateAdminRoutePolicyMetadata[\s\S]*validateLegacyRedirectTargets/,
    label: 'route inventory static drift checks',
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
