import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const projectRoot = new URL('../..', import.meta.url).pathname;
const distRoots = [join(projectRoot, 'dist/public'), join(projectRoot, 'dist')].filter(existsSync);

if (distRoots.length === 0) {
  console.error('Production bundle not found. Run pnpm run build before this assertion.');
  process.exit(1);
}

const blockedMarkers = [
  'devBypass',
  'VITE_AUTH_BYPASS',
  'Development Bypass',
  'sarah-chen-001',
  'axiom-robotics',
  'VITE_ENABLE_MOCK_FALLBACK',
  'ENABLE_MOCK_FALLBACK',
];

const textExtensions = new Set([
  '.css', '.html', '.js', '.json', '.map', '.mjs', '.svg', '.txt', '.xml',
]);

function extensionOf(path) {
  const match = /\.[^.]+$/.exec(path);
  return match ? match[0] : '';
}

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) {
      walk(path, files);
    } else if (textExtensions.has(extensionOf(path))) {
      files.push(path);
    }
  }
  return files;
}

const violations = [];
for (const root of distRoots) {
  for (const file of walk(root)) {
    const body = readFileSync(file, 'utf8');
    for (const marker of blockedMarkers) {
      if (body.includes(marker)) {
        violations.push(`${relative(projectRoot, file)} contains ${marker}`);
      }
    }
  }
}

if (violations.length > 0) {
  console.error('Production auth bypass material was found in the built bundle:');
  for (const violation of violations) {
    console.error(`- ${violation}`);
  }
  process.exit(1);
}

console.log('Production bundle contains no development auth bypass markers.');
