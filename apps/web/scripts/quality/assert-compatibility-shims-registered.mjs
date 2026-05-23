import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(import.meta.dirname, '../../../..');
const srcRoot = path.resolve(repoRoot, 'apps/web/src');
const registryPath = path.resolve(repoRoot, 'docs/governance/compatibility-debt-registry.md');

const shimMarkers = [
  /\b@deprecated\b/i,
  /backward compatibility/i,
  /compatibility shim/i,
  /legacy compatibility shims/i,
  /\bre-exports?\b.*\b(compatibility|legacy|deprecated)\b/i,
];
const ignoredPatterns = [
  /re-exports?\s+the\s+intelligence\s+workspace/i,
  /re-export\s+types?\s+for\s+convenience/i,
  /re-export\s+from\s+.*for\s+convenience/i,
];

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === 'dist' || entry.name.startsWith('.')) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else if (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx')) out.push(full);
  }
  return out;
}

const registryRaw = fs.readFileSync(registryPath, 'utf8');
const registeredPaths = new Set([...registryRaw.matchAll(/`(apps\/web\/src\/[^`]+)`/g)].map((m) => m[1]));

const findings = [];
for (const file of walk(srcRoot)) {
  const rel = path.relative(repoRoot, file).replaceAll('\\', '/');
  const raw = fs.readFileSync(file, 'utf8');
  const lines = raw.split('\n');
  lines.forEach((line, idx) => {
    if (!shimMarkers.some((pattern) => pattern.test(line))) return;
    if (ignoredPatterns.some((pattern) => pattern.test(line))) return;
    findings.push({ rel, line: idx + 1, text: line.trim() });
  });
}

const missing = findings.filter(({ rel }) => !registeredPaths.has(rel));

if (missing.length > 0) {
  console.error('Compatibility shim markers were found without registry entries:');
  for (const item of missing) {
    console.error(` - ${item.rel}:${item.line} :: ${item.text}`);
  }
  console.error(`\nAdd each path to ${path.relative(repoRoot, registryPath)} before merging.`);
  process.exit(1);
}

console.log(`Compatibility shim registry check passed (${findings.length} marked shim lines across ${new Set(findings.map((f) => f.rel)).size} files).`);
