#!/usr/bin/env node

import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { execSync } from 'node:child_process';
import path from 'node:path';

const LOCKFILE_PATTERN = /(\/(?:package-lock\.json|yarn\.lock)$|^(?:package-lock\.json|yarn\.lock)$|\/(?:pnpm-lock\.yaml|uv\.lock)$|^(?:pnpm-lock\.yaml|uv\.lock)$)/;
const ALLOWED_LOCKFILE_PATHS = new Set([
  'pnpm-lock.yaml',
  'apps/web/pnpm-lock.yaml',
  'services/api/uv.lock',
  'services/billing/uv.lock',
  'services/layer1-ingestion/uv.lock',
  'services/layer2-extraction/uv.lock',
  'services/layer2-5-signal-refinery/uv.lock',
  'services/layer3-knowledge/uv.lock',
  'services/layer4-agents/uv.lock',
  'services/layer5-ground-truth/uv.lock',
  'services/layer6-benchmarks/uv.lock',
]);
const ALLOWED_NPM_YARN_LOCKFILE_PATHS = new Set([
  'prototypes/ui-pruit.
  
  Alertmanager Config Validation	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528166	
  Analyze (actions)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605310/job/89088527459	
  Analyze (javascript-typescript)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605310/job/89088527518	
  Analyze (python)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605310/job/89088527466	
  Analyze Bundle	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605338/job/89088527770	
  Billing/Entitlements Regression + Evidence	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528098	
  Build App	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605279/job/89088527463	
  Build images & security scan (layer1-ingestion)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605295/job/89088527634	
  Build images & security scan (layer2-extraction)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605295/job/89088527648	
  Build images & security scan (layer3-knowledge)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605295/job/89088527683	
  Build images & security scan (layer4-agents)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605295/job/89088527651	
  Build images & security scan (layer5-ground-truth)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605295/job/89088527641	
  Build images & security scan (layer6-benchmarks)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605295/job/89088527652	
  Canonical Layout & Legacy Path Check	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605291/job/89088527629	
  Collect Test Results	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605277/job/89088527555	
  Container Scan (Trivy) (layer1-ingestion)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528717	
  Container Scan (Trivy) (layer2-extraction)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528722	
  Container Scan (Trivy) (layer3-knowledge)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528697	
  Container Scan (Trivy) (layer4-agents)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528709	
  Container Scan (Trivy) (layer5-ground-truth)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528724	
  Container Scan (Trivy) (layer6-benchmarks)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528746	
  Critical Behaviors Gate	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528111	
  Critical Gate: adr027-deprecated-namespaces	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527778	
  Critical Gate: adr027-duplicate-source-trees	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527753	
  Critical Gate: adr027-import-hygiene	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527730	
  Critical Gate: adr027-layer3-imports	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527758	
  Critical Gate: adr027-layer4-imports	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527797	
  Critical Gate: adr027-layer5-shim	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527819	
  Critical Gate: adr027-layer6-imports	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527769	
  Critical Gate: alembic-head-consistency	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527830	
  Critical Gate: auth-coverage	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527786	
  Critical Gate: behavior-contract	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527748	
  Critical Gate: compatibility-shims-unified	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527759	
  Critical Gate: correlation-log-contract	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527738	
  Critical Gate: env-contract-structure	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527804	
  Critical Gate: generated-client-reproducibility	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527815	
  Critical Gate: hermetic-build-inputs	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527814	
  Critical Gate: l1-target-schema	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527809	
  Critical Gate: l4-generated-jsonvalue	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527808	
  Critical Gate: layer1-api-main-shim-drift	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527824	
  Critical Gate: layer3-tenant-dependency-imports	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527741	
  Critical Gate: openapi-drift	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527799	
  Critical Gate: p0-auth-boundaries	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527806	
  Critical Gate: p0-auth-source	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527787	
  Critical Gate: p0-cross-tenant-write	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527803	
  Critical Gate: p0-jwt-config	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527794	
  Critical Gate: p0-rate-limit-safety	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527812	
  Critical Gate: production-config-policy	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527767	
  Critical Gate: production-config-policy-layer6	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527760	
  Critical Gate: shared-identity-canonical-imports	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527776	
  Critical Gate: stale-namespace-dirs	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527805	
  Critical Gate: targets-stats-named-schema	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527820	
  Critical Gate: tenant-isolation-hostile	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605312/job/89088527781	
  Cross-Layer Contract Tests	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528285	
  Cypher Dynamic Construction Guard (SEC-L3-CYPHER-003)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528729	
  DAST (OWASP ZAP baseline)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528820	
  Dependency Review	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528795	
  Determine CI Profile	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605303/job/89088527468	
  Dev Auth Bypass Guard	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528676	
  Docker Compose Config Contract	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528070	
  Docker Image Build Verification (frontend)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528238	
  Docker Image Build Verification (layer1-ingestion)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528228	
  Docker Image Build Verification (layer2-extraction)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528225	
  Docker Image Build Verification (layer3-knowledge)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528230	
  Docker Image Build Verification (layer4-agents)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528239	
  Docker Image Build Verification (layer5-ground-truth)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528219	
  Docker Image Build Verification (layer6-benchmarks)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528226	
  Dockerfile Non-Root User Check	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528807	
  ESLint Plugin Tests	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605304/job/89088527711	
  Frontend	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528186	
  Frontend Security Audit (pnpm)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605540/job/89088528804	
  Generate OpenAPI from Code (layer3-knowledge)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605304/job/89088527712	
  Generate OpenAPI from Code (layer5-ground-truth)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605304/job/89088527739	
  Governance Docs Guard	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528059	
  Integration Tests (Docker)	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528112	
  Kubernetes Dry-Run Validation	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528118	
  Layer 1 - Ingestion	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528023	
  Layer 2 - Extraction	pending	0	https://github.com/bmsull560/Fabric_4L/actions/runs/29969605298/job/89088528018	
  
  Waiting up tototype/app/package-lock.json',
]);
const WORKFLOW_FORBIDDEN_PM_PATTERN = /(^|[^a-z])(?:npm|yarn)(?:\s|$)/i;
const UNSUPPORTED_PNPM_ACTION_PATTERN = /pnpm\/action-setup@v2(?:\.\d+)?\b/;
const COREPACK_PNPM_PATTERN = /\bcorepack\s+pnpm\b/;

function fail(message) {
  console.error(`❌ ${message}`);
  process.exit(1);
}

function loadJson(filePath) {
  return JSON.parse(readFileSync(filePath, 'utf8'));
}

function gitOutput(args) {
  return execSync(`git ${args}`, { encoding: 'utf8' }).trim();
}

function resolveDiffRange() {
  if (process.argv.includes('--staged')) return 'diff --cached --name-only';
  const baseSha = process.env.GITHUB_BASE_SHA;
  const headSha = process.env.GITHUB_SHA;
  if (baseSha && headSha) return `diff --name-only ${baseSha}...${headSha}`;
  const baseRef = process.env.GITHUB_BASE_REF;
  if (baseRef) return `diff --name-only origin/${baseRef}...HEAD`;
  return 'diff --name-only';
}

function getChangedFiles() {
  const output = gitOutput(resolveDiffRange());
  return output ? output.split('\n').map((line) => line.trim()).filter(Boolean) : [];
}

function* walkFiles(dir) {
  if (!existsSync(dir)) return;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* walkFiles(fullPath);
    else if (entry.isFile()) yield fullPath;
  }
}

function checkWorkflowPackageManagerPolicy() {
  const violations = [];
  for (const file of walkFiles('.github/workflows')) {
    if (!file.endsWith('.yml') && !file.endsWith('.yaml')) continue;
    const text = readFileSync(file, 'utf8');
    for (const [idx, line] of text.split(/\r?\n/).entries()) {
      const trimmed = line.trim();
      if (trimmed.startsWith('#')) continue;
      if (WORKFLOW_FORBIDDEN_PM_PATTERN.test(trimmed)) {
        violations.push(`${file}:${idx + 1}: ${trimmed}`);
      }
    }
  }
  if (violations.length > 0) {
    fail(`Forbidden package-manager usage found in workflow YAML: ${violations.join(' | ')}`);
  }
}

function checkPnpmActionSetupVersions() {
  const violations = [];
  for (const file of walkFiles('.github/workflows')) {
    if (!file.endsWith('.yml') && !file.endsWith('.yaml')) continue;
    const text = readFileSync(file, 'utf8');
    for (const [idx, line] of text.split(/\r?\n/).entries()) {
      if (UNSUPPORTED_PNPM_ACTION_PATTERN.test(line)) {
        violations.push(`${file}:${idx + 1}: ${line.trim()}`);
      }
    }
  }
  if (violations.length > 0) {
    fail(`Unsupported pnpm/action-setup version found in workflow YAML (use v3+ or the setup-pnpm composite): ${violations.join(' | ')}`);
  }
}

function checkCorepackPnpmInScripts() {
  const violations = [];
  const packageJsonFiles = gitOutput('ls-files')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((file) => file.endsWith('package.json'));

  for (const file of packageJsonFiles) {
    const pkg = loadJson(file);
    if (!pkg.scripts) continue;
    for (const [name, script] of Object.entries(pkg.scripts)) {
      if (typeof script === 'string' && COREPACK_PNPM_PATTERN.test(script)) {
        violations.push(`${file} script "${name}": ${script}`);
      }
    }
  }

  if (violations.length > 0) {
    fail(
      `Use plain pnpm in package.json scripts; do not invoke pnpm through corepack: ${violations.join(' | ')}`,
    );
  }
}

if (existsSync('package-lock.json')) {
  fail('Root package-lock.json is not allowed. Use pnpm-lock.yaml as the canonical lockfile.');
}

const rootPkg = loadJson('package.json');
if (!rootPkg.packageManager || !String(rootPkg.packageManager).startsWith('pnpm@')) {
  fail('Root package.json must pin pnpm via the packageManager field.');
}
if (rootPkg.scripts?.preinstall !== 'node scripts/enforce-package-manager.cjs') {
  fail('Root package.json must enforce pnpm via scripts.preinstall.');
}

const webPkg = loadJson('apps/web/package.json');
if (!webPkg.packageManager || !String(webPkg.packageManager).startsWith('pnpm@')) {
  fail('apps/web/package.json must pin pnpm via the packageManager field.');
}
if (webPkg.scripts?.preinstall !== 'node ./scripts/enforce-package-manager.cjs') {
  fail('apps/web/package.json must enforce pnpm via scripts.preinstall.');
}

const changedLockfiles = getChangedFiles().filter((filePath) => LOCKFILE_PATTERN.test(filePath));
const blockedNpmOrYarn = changedLockfiles.filter(
  (filePath) => (filePath.endsWith('package-lock.json') || filePath.endsWith('yarn.lock')) && !ALLOWED_NPM_YARN_LOCKFILE_PATHS.has(filePath),
);
if (blockedNpmOrYarn.length > 0) {
  fail(`npm/yarn lockfiles are not allowed in changesets: ${blockedNpmOrYarn.join(', ')}`);
}

const unauthorizedLockfiles = changedLockfiles.filter(
  (filePath) => (filePath.endsWith('pnpm-lock.yaml') || filePath.endsWith('uv.lock')) && !ALLOWED_LOCKFILE_PATHS.has(filePath),
);
if (unauthorizedLockfiles.length > 0) {
  fail(`Lockfile churn is only allowed in approved paths. Unauthorized: ${unauthorizedLockfiles.join(', ')}`);
}

checkWorkflowPackageManagerPolicy();
checkPnpmActionSetupVersions();
checkCorepackPnpmInScripts();

console.log('✅ Package manager policy checks passed (pnpm policy + lockfile path guard + workflow YAML enforcement + pnpm setup patterns).');
