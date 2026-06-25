#!/usr/bin/env node
/**
 * Validates the frontend workflow coverage matrix.
 *
 * The matrix is intentionally checked as release evidence, not as prose only.
 * If a critical workflow, route, test file, resilience expectation, or
 * accessibility expectation is removed, this script fails the frontend gate.
 */
import { readFileSync } from 'node:fs';
import { dirname, resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, '..', '..');
const matrixPath = resolve(webRoot, 'docs', 'frontend-workflow-coverage-matrix.md');
const matrix = readFileSync(matrixPath, 'utf8');

const requiredEvidence = [
  ['P0-ACCOUNT-LIFECYCLE', /P0-ACCOUNT-LIFECYCLE/, 'account lifecycle workflow row'],
  ['P0-CALC-EVIDENCE', /P0-CALC-EVIDENCE/, 'calculation and evidence workflow row'],
  ['P0-APPROVAL-EXPORT', /P0-APPROVAL-EXPORT/, 'approval and export workflow row'],
  ['P0-AGENT-GOVERNANCE', /P0-AGENT-GOVERNANCE/, 'agent governance workflow row'],
  ['P0-LAYER-VALIDATION', /P0-LAYER-VALIDATION/, 'layer validation workflow row'],
  ['P1-INTELLIGENCE', /P1-INTELLIGENCE/, 'intelligence workspace workflow row'],
  ['P1-STUDIO', /P1-STUDIO/, 'studio workflow row'],
  ['P1-CONTEXT', /P1-CONTEXT/, 'context workflow row'],
  ['P1-SETTINGS', /P1-SETTINGS/, 'settings workflow row'],
  ['P1-PERSONAL', /P1-PERSONAL/, 'personal workflow row'],
  ['P1-INTEGRATIONS', /P1-INTEGRATIONS/, 'integration workflow row'],
  ['P1-STAKEHOLDERS', /P1-STAKEHOLDERS/, 'stakeholder mapping workflow row'],
  ['P1-NARRATIVE-PROPOSAL', /P1-NARRATIVE-PROPOSAL/, 'narrative and proposal workflow row'],
  ['P1-COLLABORATION', /P1-COLLABORATION/, 'collaboration workflow row'],
  ['P1-SEARCH-SECURITY', /P1-SEARCH-SECURITY/, 'search and tenant-safe retrieval workflow row'],
  ['P1-NOTIFICATIONS-TASKS', /P1-NOTIFICATIONS-TASKS/, 'notifications and tasks workflow row'],
  ['P1-ADMIN-CONFIG', /P1-ADMIN-CONFIG/, 'admin configuration workflow row'],
  ['P1-RESILIENCE', /P1-RESILIENCE/, 'resilience workflow row'],
  ['P1-ADVERSARIAL', /P1-ADVERSARIAL/, 'adversarial workflow row'],
  ['P1-PERSONAS', /P1-PERSONAS/, 'persona workflow row'],
  ['master inventory', /docs\/validation\/product_workflow_validation_inventory\.md/, 'master workflow inventory reference'],
  ['workflow contracts', /docs\/frontend-workflow-contracts\.json/, 'executable workflow contracts reference'],
  ['workflow contracts command', /test:workflow-contracts/, 'workflow contracts validation command reference'],
  ['route inventory command', /test:route-inventory/, 'route inventory validation command reference'],
  ['release evidence template', /docs\/frontend-release-evidence\.template\.json/, 'frontend release evidence template reference'],
  ['release evidence command', /test:frontend-release-evidence/, 'frontend release evidence validation command reference'],
  ['release evidence live P0', /live P0 browser journeys against real internal infra/, 'live P0 release evidence requirement'],
  ['release evidence image digest', /image digest/, 'release image digest requirement'],
  ['release evidence provider smoke', /live-provider smoke/, 'live-provider smoke requirement'],
  ['release evidence synthetics', /post-deploy synthetics/, 'post-deploy synthetics requirement'],
  ['j6', /e2e\/journeys\/j6-account-prospect-lifecycle\.spec\.ts/, 'account/prospect lifecycle journey evidence'],
  ['j7', /e2e\/journeys\/j7-value-realization-and-calculation\.spec\.ts/, 'value realization journey evidence'],
  ['j8', /e2e\/journeys\/j8-approval-review-gates\.spec\.ts/, 'approval/review journey evidence'],
  ['j9', /e2e\/journeys\/j9-agent-grounding-governance\.spec\.ts/, 'agent grounding journey evidence'],
  ['j10', /e2e\/journeys\/j10-layer-ui-validation\.spec\.ts/, 'layer UI validation evidence'],
  ['j11', /e2e\/journeys\/j11-golden-path-business-lifecycle\.spec\.ts/, 'golden path lifecycle evidence'],
  ['j12', /e2e\/journeys\/j12-resilience-error-recovery\.spec\.ts/, 'resilience journey evidence'],
  ['j13', /e2e\/journeys\/j13-stakeholder-mapping\.spec\.ts/, 'stakeholder mapping journey evidence'],
  ['j14', /e2e\/journeys\/j14-value-pack-governance\.spec\.ts/, 'value pack governance journey evidence'],
  ['j15', /e2e\/journeys\/j15-narrative-proposal\.spec\.ts/, 'narrative proposal journey evidence'],
  ['j16', /e2e\/journeys\/j16-collaboration\.spec\.ts/, 'collaboration journey evidence'],
  ['j17', /e2e\/journeys\/j17-crm-integration\.spec\.ts/, 'CRM integration journey evidence'],
  ['j18', /e2e\/journeys\/j18-search-retrieval\.spec\.ts/, 'search retrieval journey evidence'],
  ['j19', /e2e\/journeys\/j19-notifications-tasks\.spec\.ts/, 'notifications tasks journey evidence'],
  ['j20', /e2e\/journeys\/j20-admin-configuration\.spec\.ts/, 'admin configuration journey evidence'],
  ['j21', /e2e\/journeys\/j21-persona-journeys\.spec\.ts/, 'persona journey evidence'],
  ['j22', /e2e\/journeys\/j22-adversarial-e2e\.spec\.ts/, 'adversarial journey evidence'],
  ['j23 personal', /e2e\/journeys\/j23-personal-settings\.spec\.ts/, 'direct personal settings journey evidence'],
  ['tenant', /e2e\/security\/tenant-isolation-validation\.spec\.ts/, 'tenant isolation evidence'],
  ['export', /e2e\/export-workflows\.spec\.ts/, 'export workflow evidence'],
  ['P1 validation command', /test:e2e:validation:p1/, 'P1 workflow validation command reference'],
  ['persona coverage', /Persona coverage/, 'persona coverage column'],
  ['resilience proof', /Resilience proof/, 'resilience proof column'],
  ['accessibility proof', /Accessibility proof/, 'accessibility proof column'],
  ['watchlist formula', /\/formula-builder/, 'formula builder watchlist'],
  ['watchlist graph', /\/graph-explorer/, 'graph explorer watchlist'],
  ['verify frontend', /verify:frontend/, 'frontend verification gate reference'],
  ['bundle budget', /test:bundle-budget/, 'bundle-budget gate reference'],
];

const failures = requiredEvidence
  .filter(([, pattern]) => !pattern.test(matrix))
  .map(([, , label]) => `Missing ${label}`);

if (failures.length > 0) {
  console.error(`Frontend workflow matrix is incomplete: ${relative(webRoot, matrixPath)}`);
  for (const failure of failures) {
    console.error(` - ${failure}`);
  }
  process.exit(1);
}

console.log(`Frontend workflow matrix passed: ${requiredEvidence.length} release-confidence markers present.`);
