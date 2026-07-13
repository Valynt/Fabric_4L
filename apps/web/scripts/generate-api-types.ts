#!/usr/bin/env npx tsx
import { execSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = resolve(__dirname, '..', '..', '..');

const generator = resolve(repoRoot, 'packages', 'platform-contract', 'scripts', 'generate-openapi-types.mjs');

execSync(`node "${generator}"`, { cwd: repoRoot, stdio: 'inherit' });
