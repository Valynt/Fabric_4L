#!/usr/bin/env node
/**
 * Frontend bundle-budget gate.
 *
 * Run after `pnpm run build`. The thresholds are deliberately conservative for
 * the current application baseline so the gate protects against regressions
 * without blocking the first stabilization sprint. Tighten these values as code
 * splitting lands.
 */
import { existsSync, statSync } from 'node:fs';
import { dirname, extname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { walkFiles } from '../lib/fs-scanner.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, '..', '..');
const assetsRoot = resolve(webRoot, 'dist', 'public', 'assets');

const MAX_JS_ASSET_BYTES = Number(process.env.FRONTEND_MAX_JS_ASSET_BYTES || 900 * 1024);
const MAX_CSS_ASSET_BYTES = Number(process.env.FRONTEND_MAX_CSS_ASSET_BYTES || 225 * 1024);
const MAX_TOTAL_ASSET_BYTES = Number(process.env.FRONTEND_MAX_TOTAL_ASSET_BYTES || 3_500 * 1024);

if (!existsSync(assetsRoot)) {
  console.error(`Bundle assets were not found at ${relative(webRoot, assetsRoot)}. Run pnpm run build first.`);
  process.exit(1);
}

const assets = walkFiles(assetsRoot, { skipDotDirectories: false }).map((path) => ({
  path,
  relativePath: relative(webRoot, path),
  ext: extname(path),
  bytes: statSync(path).size,
}));

const failures = [];
for (const asset of assets) {
  if (asset.ext === '.js' && asset.bytes > MAX_JS_ASSET_BYTES) {
    failures.push(`${asset.relativePath} is ${(asset.bytes / 1024).toFixed(1)} KiB, above JS budget ${(MAX_JS_ASSET_BYTES / 1024).toFixed(1)} KiB`);
  }
  if (asset.ext === '.css' && asset.bytes > MAX_CSS_ASSET_BYTES) {
    failures.push(`${asset.relativePath} is ${(asset.bytes / 1024).toFixed(1)} KiB, above CSS budget ${(MAX_CSS_ASSET_BYTES / 1024).toFixed(1)} KiB`);
  }
}

const totalBytes = assets.reduce((sum, asset) => sum + asset.bytes, 0);
if (totalBytes > MAX_TOTAL_ASSET_BYTES) {
  failures.push(`Total asset payload is ${(totalBytes / 1024).toFixed(1)} KiB, above total budget ${(MAX_TOTAL_ASSET_BYTES / 1024).toFixed(1)} KiB`);
}

if (failures.length > 0) {
  console.error('Frontend bundle budget failed.');
  for (const failure of failures) {
    console.error(` - ${failure}`);
  }
  process.exit(1);
}

const largest = assets
  .slice()
  .sort((a, b) => b.bytes - a.bytes)
  .slice(0, 5)
  .map((asset) => `${asset.relativePath} ${(asset.bytes / 1024).toFixed(1)} KiB`)
  .join('; ');

console.log(`Frontend bundle budget passed: ${assets.length} assets, ${(totalBytes / 1024).toFixed(1)} KiB total. Largest: ${largest}`);
