#!/usr/bin/env npx tsx
import { execSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..', '..', '..');
const OPENAPI_DIR = resolve(ROOT, 'contracts', 'openapi');
const OUTPUT_DIR = resolve(ROOT, 'packages', 'platform-contract', 'src', 'typescript', 'generated');
const WEB_APP_DIR = resolve(ROOT, 'apps', 'web');
const WEB_OUTPUT_DIR = resolve(WEB_APP_DIR, 'src', 'api', 'generated');

const SPECS = [
  'fabric-4l-api.json',
  'layer1-ingestion.json',
  'layer2-extraction.json',
  'layer3-knowledge.json',
  'layer4-agents.json',
  'layer5-ground-truth.json',
  'layer6-benchmarks.json',
  'signals.json',
];

const requestedSpecs = [];
for (let index = 2; index < process.argv.length; index += 1) {
  const arg = process.argv[index];
  if (arg === '--spec') {
    const spec = process.argv[index + 1];
    if (!spec) {
      throw new Error('Missing value for --spec');
    }
    requestedSpecs.push(spec);
    index += 1;
    continue;
  }
  throw new Error(`Unsupported argument: ${arg}`);
}

if (requestedSpecs.length > 0) {
  const unknownSpecs = requestedSpecs.filter((spec) => !SPECS.includes(spec));
  if (unknownSpecs.length > 0) {
    throw new Error(`Unknown OpenAPI spec(s): ${unknownSpecs.join(', ')}`);
  }
}

const selectedSpecs = requestedSpecs.length === 0
  ? SPECS
  : SPECS.filter((spec) => requestedSpecs.includes(spec));

if (!existsSync(OUTPUT_DIR)) mkdirSync(OUTPUT_DIR, { recursive: true });
if (!existsSync(WEB_OUTPUT_DIR)) mkdirSync(WEB_OUTPUT_DIR, { recursive: true });


const WEB_LAYER_DIRS = {
  fabric_4l_api: 'fabric',
  layer1_ingestion: 'l1',
  layer2_extraction: 'l2',
  layer3_knowledge: 'l3',
  layer4_agents: 'l4',
  layer5_ground_truth: 'l5',
  layer6_benchmarks: 'l6',
  signals: 'signals',
};

function writeFileAtomic(filePath, content) {
  const tmpPath = `${filePath}.tmp-${process.pid}-${Date.now()}`;
  writeFileSync(tmpPath, content, { encoding: 'utf-8' });
  renameSync(tmpPath, filePath);
}

/**
 * Replace the opaque `JsonValue: unknown;` that openapi-typescript emits for an
 * empty JSON schema with a stable, recursive JSON value type. This keeps the
 * generated contract deterministic and prevents the broken self-referencing
 * output that requires manual patching.
 */
function fixJsonValue(content) {
  if (!content.includes('JsonValue: unknown;')) {
    return content;
  }
  const alias = 'type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };';
  return `${alias}\n${content.replace('JsonValue: unknown;', 'JsonValue: JsonValue;')}`;
}

const exports = [];
const webExports = [];
for (const spec of SPECS) {
  const key = spec.replace('.json', '').replace(/-/g, '_');
  const out = join(OUTPUT_DIR, `${key}.ts`);
  if (selectedSpecs.includes(spec)) {
    execSync(`npx --no-install openapi-typescript "${join(OPENAPI_DIR, spec)}" -o "${out}"`, {
      cwd: WEB_APP_DIR,
      stdio: 'pipe',
    });
    const content = fixJsonValue(readFileSync(out, 'utf8'));
    writeFileAtomic(out, `// @generated from contracts/openapi/${spec}\n` + content);

    const webDir = WEB_LAYER_DIRS[key];
    if (webDir) {
      const webLayerDir = join(WEB_OUTPUT_DIR, webDir);
      if (!existsSync(webLayerDir)) mkdirSync(webLayerDir, { recursive: true });
      const webOut = join(webLayerDir, 'index.ts');
      writeFileAtomic(webOut, [
        '// @generated — This file is auto-generated from the OpenAPI spec.',
        '// Do not edit manually. Run `pnpm run generate:types` to regenerate.',
        `// Source: contracts/openapi/${spec}`,
        content,
      ].join('\n'));
    }
  }

  exports.push(`export * as ${key} from './${key}.js';`);

  const webDir = WEB_LAYER_DIRS[key];
  if (webDir) {
    webExports.push(`export * as ${webDir} from './${webDir}';`);
  }
}

writeFileSync(join(OUTPUT_DIR, 'index.ts'), `// @generated\n${exports.join('\n')}\n`);


writeFileSync(join(WEB_OUTPUT_DIR, 'index.ts'), [
  '// @generated — Barrel export for all generated API types.',
  '// Do not edit manually. Run `pnpm run generate:types` to regenerate.',
  '',
  ...webExports,
  '',
].join('\n'));
