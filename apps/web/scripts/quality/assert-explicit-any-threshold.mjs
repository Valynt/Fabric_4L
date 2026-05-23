#!/usr/bin/env node
import { promises as fs } from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(process.cwd());
const TARGET_DIRS = ['src', 'test'];
const THRESHOLD = 100;
const FILE_RE = /\.(ts|tsx)$/;
const ANY_RE = /\bany\b/g;

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (['node_modules', 'dist', 'coverage'].includes(entry.name)) continue;
      files.push(...await walk(full));
      continue;
    }
    if (entry.isFile() && FILE_RE.test(entry.name)) files.push(full);
  }
  return files;
}

let total = 0;
for (const relativeDir of TARGET_DIRS) {
  const absoluteDir = path.join(ROOT, relativeDir);
  const files = await walk(absoluteDir);
  for (const file of files) {
    const text = await fs.readFile(file, 'utf8');
    const matches = text.match(ANY_RE);
    total += matches ? matches.length : 0;
  }
}

if (total >= THRESHOLD) {
  console.error(`[any-threshold] Found ${total} matches for \\bany\\b in apps/web/{src,test}. Threshold is < ${THRESHOLD}.`);
  process.exit(1);
}

console.log(`[any-threshold] OK: ${total} matches (threshold < ${THRESHOLD}).`);
