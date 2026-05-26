#!/usr/bin/env node

import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '../../../..');

const generatedFiles = [
  'apps/web/src/api/generated/l4/index.ts',
  'apps/web/src/api/generated/l5/index.ts',
];

const violations = [];
for (const rel of generatedFiles) {
  const content = readFileSync(path.join(repoRoot, rel), 'utf8');
  const lines = content.split('\n');
  lines.forEach((line, idx) => {
    const isResponseSchema = /Response:\s*any\b/.test(line);
    if (isResponseSchema) {
      violations.push(`${rel}:${idx + 1}: ${line.trim()}`);
    }
  });
}

if (violations.length > 0) {
  console.error('Found response schemas typed as any in generated API surfaces:');
  for (const violation of violations) {
    console.error(`  - ${violation}`);
  }
  process.exit(1);
}

console.log('Generated response schemas are strongly typed (no `Response: any` entries found).');
