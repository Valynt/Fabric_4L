#!/usr/bin/env node

import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { execSync } from 'node:child_process';
import path from 'node:path';

const LOCKFILE_PATTERN = /(\/(?:package-lock\.json|yarn\.lock)$|^(?:package-lock\.json|yarn\.lock)$|\/(?:pnpm-lock\.yaml|uv\.lock|requirements-test\.lock)$|^(?:pnpm-lock\.yaml|uv\.lock|requirements-test\.lock)$)/;
const ALLOWED_LOCKFILE_PATHS = new Set([
  'pnpm-lock.yaml',
  'apps/web/pnpm-lock.yaml',
  'tests/requirements-test.lock',
  'services/api/uv.lock',
  'services/layer1-ingestion/uv.lock',
  'services/layer2-extraction/uv.lock',
  'services/layer3-knowledge/uv.lock',
  'services/layer4-agents/uv.lock',
  'services/layer5-ground-truth/uv.lock',
  'services/layer6-benchmarks/uv.lock',
  'services/layer7-billing/uv.lock',
]);
const ALLOWED_NPM_YARN_LOCKFILE_PATHS = new Set([
  'prototypes/ui-prototype/app/package-lock.json',
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
  (filePath) => (filePath.endsWith('pnpm-lock.yaml') || filePath.endsWith('uv.lock') || filePath.endsWith('requirements-test.lock')) && !ALLOWED_LOCKFILE_PATHS.has(filePath),
);
if (unauthorizedLockfiles.length > 0) {
  fail(`Lockfile churn is only allowed in approved paths. Unauthorized: ${unauthorizedLockfiles.join(', ')}`);
}

checkWorkflowPackageManagerPolicy();
checkPnpmActionSetupVersions();
checkCorepackPnpmInScripts();

console.log('✅ Package manager policy checks passed (pnpm policy + lockfile path guard + workflow YAML enforcement + pnpm setup patterns).');
