#!/usr/bin/env node

import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { execSync } from 'node:child_process';
import path from 'node:path';

const LOCKFILE_PATTERN = /(\/(?:package-lock\.json|yarn\.lock)$|^(?:package-lock\.json|yarn\.lock)$|\/(?:pnpm-lock\.yaml|uv\.lock)$|^(?:pnpm-lock\.yaml|uv\.lock)$)/;
const ALLOWED_LOCKFILE_PATHS = new Set([
  'pnpm-lock.yaml',
  'apps/web/pnpm-lock.yaml',
  'services/layer1-ingestion/uv.lock',
  'services/layer2-extraction/uv.lock',
  'services/layer3-knowledge/uv.lock',
  'services/layer4-agents/uv.lock',
  'services/layer5-ground-truth/uv.lock',
  'services/layer6-benchmarks/uv.lock',
  // NOTE: archive snapshots under docs/archive/ are historical evidence and are
  // intentionally excluded from active lockfile/sbom surfaces. They must not be
  // built or deployed. Do not add archive paths here without changing the
  // archive support policy documented in docs/reference/contributor-dependency-workflows.md.
]);
const ALLOWED_NPM_YARN_LOCKFILE_PATHS = new Set([
  'prototypes/ui-prototype/app/package-lock.json',
]);

// Explicit command classification for npm/yarn usage in workflow YAML.
// Project dependency installation MUST go through pnpm. The only npm command
// permitted without an inline exception marker is `npm publish`, because it is
// a registry operation rather than a project dependency install.
const DENIED_NPM_YARN_COMMANDS = [
  {
    name: 'npm ci',
    regex: /(?:^|\s)npm\s+ci(?:\s|$)/i,
  },
  {
    name: 'npm install',
    regex: /(?:^|\s)npm\s+install(?:\s+|$)/i,
  },
  {
    name: 'npm i',
    regex: /(?:^|\s)npm\s+i(?:\s+|$)/i,
  },
  {
    name: 'yarn install',
    regex: /(?:^|\s)yarn\s+install(?:\s|$)/i,
  },
  {
    name: 'yarn add',
    regex: /(?:^|\s)yarn\s+add(?:\s|$)/i,
  },
];

const ALLOWED_NPM_COMMANDS = [
  {
    name: 'npm publish',
    regex: /(?:^|\s)npm\s+publish(?:\s|$)/i,
  },
];

// Marker that exempts a single workflow step from the npm global-install rule.
// Use only when no pnpm/Corepack equivalent exists and document the reason.
const NPM_GLOBAL_EXCEPTION_MARKER = 'NPM-GLOBAL-EXCEPTION';

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

function stripYamlComment(line) {
  // Very conservative: ignore # preceded by whitespace or at start.
  return line.replace(/\s#.*$/, '').trim();
}

function lineHasAllowedNpmCommand(line) {
  return ALLOWED_NPM_COMMANDS.some(({ regex }) => regex.test(line));
}

function lineHasGlobalExceptionMarker(line) {
  return line.includes(NPM_GLOBAL_EXCEPTION_MARKER);
}

// Returns true only if the line is an npm install/i command with a -g/--global flag.
function lineIsGlobalNpmInstall(line) {
  return /(?:^|\s)npm\s+(?:install|i)(?:\s|$)/i.test(line) && /(?:^|\s)(?:-g|--global)(?:\s|$)/.test(line);
}

function classifyWorkflowLine(line) {
  const stripped = stripYamlComment(line);
  if (!stripped) return 'neutral';

  // Registry publish is the one npm operation we allow unconditionally.
  if (lineHasAllowedNpmCommand(stripped)) return 'allowed';

  // The global-install exception marker only permits actual global npm installs
  // (npm install -g / npm i -g). It must not bypass project dependency installs
  // like npm ci or non-global npm install.
  if (lineHasGlobalExceptionMarker(line) && lineIsGlobalNpmInstall(stripped)) return 'allowed';

  for (const { name, regex } of DENIED_NPM_YARN_COMMANDS) {
    if (regex.test(stripped)) {
      return { type: 'denied', reason: name };
    }
  }

  return 'neutral';
}

function isStepMetadataLine(line) {
  const dedented = line.replace(/^[ \t]+/, '');
  return /^(?:-\s+name:|uses:|if:|with:|env:|runs-on:|needs:|permissions:|strategy:|matrix:|outputs:|steps:|jobs:|on:|name:)\s/.test(dedented);
}

function checkWorkflowFile(filePath) {
  const violations = [];
  const text = readFileSync(filePath, 'utf8');
  const lines = text.split(/\r?\n/);

  // Collect per-step context so a step-level NPM-GLOBAL-EXCEPTION marker
  // exempts its run lines.
  let currentStepHasException = false;

  for (let idx = 0; idx < lines.length; idx += 1) {
    const rawLine = lines[idx];
    const dedented = rawLine.replace(/^[ \t]+/, '');

    // Heuristic step boundary: a top-level `- name:`, `- uses:`, or `- run:`
    // indicates a new step and resets exception context.
    if (/^-\s+(?:name|uses|run):/.test(dedented)) {
      currentStepHasException = false;
    }
    if (lineHasGlobalExceptionMarker(rawLine)) {
      currentStepHasException = true;
    }

    // Skip YAML metadata keys; we only care about shell commands.
    if (isStepMetadataLine(rawLine)) continue;

    const classification = classifyWorkflowLine(rawLine);
    if (classification !== 'neutral' && classification !== 'allowed') {
      // A step-level NPM-GLOBAL-EXCEPTION marker only exempts global npm installs,
      // not project dependency commands like npm ci or non-global npm install.
      if (currentStepHasException && lineIsGlobalNpmInstall(rawLine.replace(/^[ \t]+/, ''))) continue;
      violations.push(`${filePath}:${idx + 1}: ${classification.reason}: ${rawLine.trim()}`);
    }
  }

  return violations;
}

function checkWorkflowPackageManagerPolicy(workflowsDir = '.github/workflows') {
  const violations = [];
  for (const file of walkFiles(workflowsDir)) {
    if (!file.endsWith('.yml') && !file.endsWith('.yaml')) continue;
    violations.push(...checkWorkflowFile(file));
  }
  if (violations.length > 0) {
    fail(`Forbidden package-manager usage found in workflow YAML:\n${violations.join('\n')}`);
  }
}

function checkStaticPolicies() {
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
}

function checkLockfilePaths() {
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
}

function main() {
  const fixturesDirArg = process.argv.find((arg) => arg.startsWith('--fixtures-dir='));
  const workflowsDir = fixturesDirArg ? fixturesDirArg.split('=')[1] : '.github/workflows';

  checkStaticPolicies();
  checkLockfilePaths();
  checkWorkflowPackageManagerPolicy(workflowsDir);

  console.log('✅ Package manager policy checks passed (pnpm policy + lockfile path guard + workflow YAML enforcement).');
}

export {
  ALLOWED_LOCKFILE_PATHS,
  ALLOWED_NPM_YARN_LOCKFILE_PATHS,
  classifyWorkflowLine,
  checkWorkflowFile,
  lineIsGlobalNpmInstall,
  NPM_GLOBAL_EXCEPTION_MARKER,
};

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
