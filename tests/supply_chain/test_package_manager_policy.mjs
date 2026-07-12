#!/usr/bin/env node

import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  classifyWorkflowLine,
  checkWorkflowFile,
  ALLOWED_LOCKFILE_PATHS,
  ALLOWED_NPM_YARN_LOCKFILE_PATHS,
  NPM_GLOBAL_EXCEPTION_MARKER,
} from '../../scripts/ci/check_package_manager_policy.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function testClassifyAllowed() {
  const allowed = [
    'npm publish --access public',
    '  npm publish',
    'run: npm publish --access public',
    // Global npm install when the line carries the exception marker.
    `npm install -g foo  # ${NPM_GLOBAL_EXCEPTION_MARKER}`,
  ];
  for (const line of allowed) {
    const result = classifyWorkflowLine(line);
    assert.strictEqual(result, 'allowed', `Expected allowed: ${line}`);
  }
}

function testPnpmCommandsAreNeutral() {
  // pnpm commands are neither denied nor explicitly flagged as allowed;
  // they simply do not trigger the npm/yarn policy.
  const pnpmLines = [
    'pnpm install --frozen-lockfile',
    'pnpm add -D typescript',
    'pnpm add -g @apidevtools/swagger-cli',
    'pnpm exec playwright install',
  ];
  for (const line of pnpmLines) {
    const result = classifyWorkflowLine(line);
    assert.strictEqual(result, 'neutral', `Expected neutral for pnpm command: ${line}`);
  }
}

function testClassifyDenied() {
  const denied = [
    { line: 'npm ci', reason: 'npm ci' },
    { line: 'npm install', reason: 'npm install' },
    { line: 'npm install --legacy-peer-deps', reason: 'npm install' },
    { line: 'npm i', reason: 'npm i' },
    { line: 'npm i express', reason: 'npm i' },
    { line: 'yarn install', reason: 'yarn install' },
    { line: 'yarn add lodash', reason: 'yarn add' },
    { line: 'run: npm ci', reason: 'npm ci' },
  ];
  for (const { line, reason } of denied) {
    const result = classifyWorkflowLine(line);
    assert.notStrictEqual(result, 'neutral', `Expected non-neutral for: ${line}`);
    assert.notStrictEqual(result, 'allowed', `Expected non-allowed for: ${line}`);
    assert.strictEqual(result.reason, reason, `Expected reason ${reason} for: ${line}`);
  }
}

function testGlobalInstallWithoutMarkerIsDenied() {
  const line = 'npm install -g @apidevtools/swagger-cli';
  const result = classifyWorkflowLine(line);
  assert.notStrictEqual(result, 'neutral', `Expected non-neutral: ${line}`);
  assert.notStrictEqual(result, 'allowed', `Expected non-allowed: ${line}`);
  assert.strictEqual(result.reason, 'npm install', `Expected denied as npm install: ${line}`);
}

function testGlobalInstallWithMarkerIsAllowed() {
  const line = `npm install -g @apidevtools/swagger-cli  # ${NPM_GLOBAL_EXCEPTION_MARKER}`;
  const result = classifyWorkflowLine(line);
  assert.strictEqual(result, 'allowed', `Expected allowed with exception marker: ${line}`);
}

function testFixtures() {
  const allowedFile = path.join(__dirname, 'fixtures', 'allowed-npm-usage.yml');
  const allowedViolations = checkWorkflowFile(allowedFile);
  assert.deepStrictEqual(
    allowedViolations,
    [],
    `Allowed fixture produced unexpected violations: ${allowedViolations.join('; ')}`,
  );

  const deniedFile = path.join(__dirname, 'fixtures', 'denied-npm-usage.yml');
  const deniedViolations = checkWorkflowFile(deniedFile);
  const expectedDeniedReasons = [
    'npm ci',
    'npm install',
    'npm install',
    'npm i',
    'npm i',
    'yarn install',
    'yarn add',
    'npm install',
    'npm install',
  ];
  assert.strictEqual(
    deniedViolations.length,
    expectedDeniedReasons.length,
    `Expected ${expectedDeniedReasons.length} violations in denied fixture, got ${deniedViolations.length}: ${deniedViolations.join('; ')}`,
  );
}

function testLockfileAllowlists() {
  assert.ok(ALLOWED_LOCKFILE_PATHS.has('pnpm-lock.yaml'));
  assert.ok(ALLOWED_LOCKFILE_PATHS.has('apps/web/pnpm-lock.yaml'));
  assert.ok(!ALLOWED_LOCKFILE_PATHS.has('docs/archive/frontend-root-2026-05-02/source-snapshot/pnpm-lock.yaml'));
  assert.ok(ALLOWED_NPM_YARN_LOCKFILE_PATHS.has('prototypes/ui-prototype/app/package-lock.json'));
}

function run() {
  testClassifyAllowed();
  testClassifyDenied();
  testPnpmCommandsAreNeutral();
  testGlobalInstallWithoutMarkerIsDenied();
  testGlobalInstallWithMarkerIsAllowed();
  testFixtures();
  testLockfileAllowlists();
  console.log('✅ Package manager policy checker tests passed');
}

run();
