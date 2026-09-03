#!/usr/bin/env node

import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { execSync } from 'node:child_process';
import path from 'node:path';

const CANONICAL_PNPM_VERSION = '10.34.5';
const CANONICAL_PNPM_SPEC = `pnpm@${CANONICAL_PNPM_VERSION}`;
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
const WORKFLOW_DIRS = ['.github/workflows', '.depot/workflows'];
const WORKFLOW_FORBIDDEN_PM_PATTERN = /(^|[^a-z])(?:npm|yarn)(?:\s|$)/i;
const UNSUPPORTED_PNPM_ACTION_PATTERN = /pnpm\/action-setup@v2(?:\.\d+)?\b/;
const COREPACK_PNPM_PATTERN = /\bcorepack\s+pnpm\b/;
const VERSION_LINE_PATTERN = /^\s*version:\s*(.+?)\s*$/;
const PNPM_VERSION_ENV_PATTERN = /^\s*PNPM_VERSION\s*:\s*(.+?)\s*$/;
const WORKFLOW_PNPM_SPEC_PATTERN = /\bpnpm@\d+\.\d+\.\d+\b/;

const CANONICAL_TEXT_SURFACES = [
  {
    file: '.tool-versions',
    matcher: /^pnpm\s+(\d+\.\d+\.\d+)$/m,
    description: '.tool-versions pnpm pin',
  },
  {
    file: '.npmrc',
    matcher: /^package-manager=pnpm@(\d+\.\d+\.\d+)$/m,
    description: '.npmrc package-manager pin',
  },
  {
    file: '.codex/setup.sh',
    matcher: /corepack use pnpm@(\d+\.\d+\.\d+)/,
    description: '.codex/setup.sh pnpm pin',
  },
  {
    file: '.codex/setup.ps1',
    matcher: /corepack use pnpm@(\d+\.\d+\.\d+)/,
    description: '.codex/setup.ps1 pnpm pin',
  },
  {
    file: '.devcontainer/devcontainer.json',
    matcher: /"pnpmVersion"\s*:\s*"(\d+\.\d+\.\d+)"/,
    description: '.devcontainer/devcontainer.json pnpm pin',
  },
  {
    file: '.devcontainer/post-create.sh',
    matcher: /corepack prepare pnpm@(\d+\.\d+\.\d+) --activate/,
    description: '.devcontainer/post-create.sh pnpm pin',
  },
  {
    file: 'Makefile',
    matcher: /corepack prepare pnpm@(\d+\.\d+\.\d+) --activate/,
    description: 'Makefile bootstrap pnpm pin',
  },
  {
    file: 'apps/web/Dockerfile',
    matcher: /pnpm@(\d+\.\d+\.\d+)/g,
    description: 'apps/web/Dockerfile pnpm pin',
  },
  {
    file: 'apps/web/Dockerfile.dev',
    matcher: /corepack prepare pnpm@(\d+\.\d+\.\d+) --activate/,
    description: 'apps/web/Dockerfile.dev pnpm pin',
  },
  {
    file: 'apps/web/Dockerfile.playwright',
    matcher: /corepack prepare pnpm@(\d+\.\d+\.\d+) --activate/,
    description: 'apps/web/Dockerfile.playwright pnpm pin',
  },
  {
    file: 'apps/web/scripts/playwright-docker-entrypoint.sh',
    matcher: /corepack prepare pnpm@(\d+\.\d+\.\d+) --activate/,
    description: 'apps/web Playwright entrypoint pnpm pin',
  },
  {
    file: 'tools/ci/security-suite/Dockerfile',
    matcher: /ARG PNPM_VERSION=(\d+\.\d+\.\d+)/,
    description: 'security-suite Dockerfile pnpm pin',
  },
  {
    file: '.github/actions/setup-fabric-ci/action.yml',
    matcher: /pnpm-version:\s*(?:\n|.)*?default:\s*['"](\d+\.\d+\.\d+)['"]/,
    description: '.github setup-fabric-ci default pnpm pin',
  },
  {
    file: '.depot/actions/setup-fabric-ci/action.yml',
    matcher: /pnpm-version:\s*(?:\n|.)*?default:\s*['"](\d+\.\d+\.\d+)['"]/,
    description: '.depot setup-fabric-ci default pnpm pin',
  },
];

function fail(message) {
  console.error(`❌ ${message}`);
  process.exit(1);
}

function loadJson(filePath) {
  return JSON.parse(readFileSync(filePath, 'utf8'));
}

function readRequiredText(filePath, description) {
  if (!existsSync(filePath)) {
    fail(`${description} is missing (${filePath}).`);
  }
  return readFileSync(filePath, 'utf8');
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

function* workflowFiles() {
  for (const dir of WORKFLOW_DIRS) {
    yield* walkFiles(dir);
  }
}

function requireCanonicalVersion(description, filePath, version) {
  if (version !== CANONICAL_PNPM_VERSION) {
    fail(`${description} in ${filePath} must match canonical pnpm ${CANONICAL_PNPM_VERSION}; found ${version}.`);
  }
}

function collectVersions(filePath, matcher, description) {
  const text = readRequiredText(filePath, description);
  if (matcher.global) {
    const versions = [...text.matchAll(matcher)].map((match) => match[1]);
    if (versions.length === 0) {
      fail(`${description} is missing a pnpm version pin (${filePath}).`);
    }
    return versions;
  }
  const match = text.match(matcher);
  if (!match) {
    fail(`${description} is missing a pnpm version pin (${filePath}).`);
  }
  return [match[1]];
}

function checkCanonicalVersionSurfaces() {
  const rootPkg = loadJson('package.json');
  if (rootPkg.packageManager !== CANONICAL_PNPM_SPEC) {
    fail(`Root package.json must pin ${CANONICAL_PNPM_SPEC} in packageManager.`);
  }
  if (rootPkg.scripts?.preinstall !== 'node scripts/enforce-package-manager.cjs') {
    fail('Root package.json must enforce pnpm via scripts.preinstall.');
  }

  const webPkg = loadJson('apps/web/package.json');
  if (webPkg.packageManager !== CANONICAL_PNPM_SPEC) {
    fail(`apps/web/package.json must pin ${CANONICAL_PNPM_SPEC} in packageManager.`);
  }
  if (webPkg.scripts?.preinstall !== 'node ./scripts/enforce-package-manager.cjs') {
    fail('apps/web/package.json must enforce pnpm via scripts.preinstall.');
  }

  for (const surface of CANONICAL_TEXT_SURFACES) {
    for (const version of collectVersions(surface.file, surface.matcher, surface.description)) {
      requireCanonicalVersion(surface.description, surface.file, version);
    }
  }
}

function checkWorkflowPackageManagerPolicy() {
  const violations = [];
  for (const file of workflowFiles()) {
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
  for (const file of workflowFiles()) {
    if (!file.endsWith('.yml') && !file.endsWith('.yaml')) continue;
    const lines = readFileSync(file, 'utf8').split(/\r?\n/);
    for (let idx = 0; idx < lines.length; idx += 1) {
      const line = lines[idx];
      if (UNSUPPORTED_PNPM_ACTION_PATTERN.test(line)) {
        violations.push(`${file}:${idx + 1}: ${line.trim()}`);
        continue;
      }
      if (line.includes('uses: pnpm/action-setup@')) {
        for (let lookahead = idx + 1; lookahead < lines.length; lookahead += 1) {
          const candidate = lines[lookahead];
          const trimmed = candidate.trim();
          if (trimmed.startsWith('#')) continue;
          if (/^\s*-\s/.test(candidate)) break;
          if (VERSION_LINE_PATTERN.test(candidate)) {
            violations.push(`${file}:${lookahead + 1}: ${trimmed}`);
          }
        }
      }
      if (line.includes('uses: ./.github/actions/setup-fabric-ci') || line.includes('uses: ./.depot/actions/setup-fabric-ci')) {
        for (let lookahead = idx + 1; lookahead < lines.length; lookahead += 1) {
          const candidate = lines[lookahead];
          const trimmed = candidate.trim();
          if (trimmed.startsWith('#')) continue;
          if (/^\s*-\s/.test(candidate)) break;
          if (/^\s*pnpm-version:\s*/.test(candidate)) {
            violations.push(`${file}:${lookahead + 1}: ${trimmed}`);
          }
        }
      }
      if (PNPM_VERSION_ENV_PATTERN.test(line) || WORKFLOW_PNPM_SPEC_PATTERN.test(line)) {
        violations.push(`${file}:${idx + 1}: ${line.trim()}`);
      }
    }
  }
  if (violations.length > 0) {
    fail(
      `Workflows must not hard-code a pnpm version; use the canonical repo pin via packageManager or the shared setup-fabric-ci defaults instead: ${violations.join(' | ')}`,
    );
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

checkCanonicalVersionSurfaces();

// A deleted lockfile (file no longer present on disk) is a removal, not lockfile
// churn. Churn means adding or modifying a lockfile, so ignore deletions here.
const changedLockfiles = getChangedFiles()
  .filter((filePath) => existsSync(filePath))
  .filter((filePath) => LOCKFILE_PATTERN.test(filePath));
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

console.log(
  `✅ Package manager policy checks passed (canonical pnpm ${CANONICAL_PNPM_VERSION} + lockfile path guard + workflow YAML enforcement + pnpm setup patterns).`,
);
