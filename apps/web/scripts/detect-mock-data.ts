#!/usr/bin/env tsx
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';

interface Rule {
  id: string;
  description: string;
  regex: RegExp;
}

interface Violation {
  file: string;
  line: number;
  ruleId: string;
  description: string;
  content: string;
}

interface AllowlistEntry {
  path: string;
  reason: string;
  ruleId?: string;
  line?: number;
}

interface AllowlistConfig {
  entries: AllowlistEntry[];
}

const TARGET_DIRECTORIES = ['client/src/pages', 'client/src/components'];
const ALLOWLIST_CONFIG_PATH = path.normalize('scripts/mock-data-allowlist.json');

const APPROVED_MOCK_FOLDERS = new Set([
  path.normalize('client/src/test/mocks'),
  path.normalize('test/mocks'),
]);

const EXCLUDED_PATH_PATTERNS = [
  /\.test\.[jt]sx?$/i,
  /\.spec\.[jt]sx?$/i,
  /\.stories\.[jt]sx?$/i,
  /__tests__/i,
  /__mocks__/i,
  /\/fixtures?\//i,
  /\/mocks?\//i,
  /\/_deprecated\//i,
];

const SOURCE_FILE_PATTERN = /\.[jt]sx?$/i;
const INLINE_ALLOW_COMMENT = 'mock-scan: allow';

const RULES: Rule[] = [
  {
    id: 'mockData-identifier',
    description: 'mockData identifier usage is disallowed in production UI code',
    regex: /\bmockData\b/i,
  },
  {
    id: 'testData-identifier',
    description: 'testData identifier usage is disallowed in production UI code',
    regex: /\btestData\b/i,
  },
  {
    id: 'dummy-prefix',
    description: 'dummy* identifiers are disallowed in production UI code',
    regex: /\bdummy[A-Za-z0-9_]*\b/i,
  },
  {
    id: 'dot-mock-import',
    description: '.mock imports are disallowed in production UI code',
    regex: /^\s*import\s+.+?from\s+['"][^'"]*\.mock(?:\.[^'"]+)?['"]/i,
  },
  {
    id: 'hardcoded-array-literal',
    description:
      'hardcoded array literals with mock-style identifiers are disallowed in production UI code',
    regex:
      /^\s*(?:const|let|var)\s+[A-Za-z_$][\w$]*(?:mock|test|dummy|fake|sample|fixture|stub)[A-Za-z0-9_$]*\s*=\s*\[/i,
  },
  {
    id: 'hardcoded-object-literal',
    description:
      'hardcoded object literals with mock-style identifiers are disallowed in production UI code',
    regex:
      /^\s*(?:const|let|var)\s+[A-Za-z_$][\w$]*(?:mock|test|dummy|fake|sample|fixture|stub)[A-Za-z0-9_$]*\s*=\s*\{/i,
  },
];

function loadAllowlist(root: string): AllowlistEntry[] {
  const configPath = path.join(root, ALLOWLIST_CONFIG_PATH);

  try {
    const raw = readFileSync(configPath, 'utf8');
    const parsed = JSON.parse(raw) as AllowlistConfig;
    if (!Array.isArray(parsed.entries)) {
      return [];
    }

    return parsed.entries
      .filter((entry) => typeof entry.path === 'string' && typeof entry.reason === 'string')
      .map((entry) => ({
        ...entry,
        path: path.normalize(entry.path),
      }));
  } catch {
    return [];
  }
}

function shouldSkipFile(relativePath: string): boolean {
  const normalized = path.normalize(relativePath);

  for (const approved of APPROVED_MOCK_FOLDERS) {
    if (normalized === approved || normalized.startsWith(`${approved}${path.sep}`)) {
      return true;
    }
  }

  return EXCLUDED_PATH_PATTERNS.some((pattern) => pattern.test(normalized));
}

function collectFiles(directory: string): string[] {
  const output: string[] = [];

  for (const entry of readdirSync(directory)) {
    const fullPath = path.join(directory, entry);
    const stat = statSync(fullPath);

    if (stat.isDirectory()) {
      output.push(...collectFiles(fullPath));
      continue;
    }

    if (stat.isFile() && SOURCE_FILE_PATTERN.test(fullPath)) {
      output.push(fullPath);
    }
  }

  return output;
}

function isAllowlisted(violation: Violation, root: string, allowlist: AllowlistEntry[]): boolean {
  const relative = path.normalize(path.relative(root, violation.file));

  return allowlist.some((entry) => {
    if (entry.path !== relative) {
      return false;
    }

    if (entry.ruleId && entry.ruleId !== violation.ruleId) {
      return false;
    }

    if (entry.line && entry.line !== violation.line) {
      return false;
    }

    return true;
  });
}

function scanFile(filePath: string): Violation[] {
  const content = readFileSync(filePath, 'utf8');
  const lines = content.split(/\r?\n/);
  const violations: Violation[] = [];

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index] ?? '';

    if (line.includes(INLINE_ALLOW_COMMENT)) {
      continue;
    }

    for (const rule of RULES) {
      if (!rule.regex.test(line)) {
        continue;
      }

      const previousLine = lines[index - 1] ?? '';
      if (previousLine.includes(INLINE_ALLOW_COMMENT)) {
        continue;
      }

      violations.push({
        file: filePath,
        line: index + 1,
        ruleId: rule.id,
        description: rule.description,
        content: line.trim(),
      });
    }
  }

  return violations;
}

function main(): void {
  const root = process.cwd();
  const allViolations: Violation[] = [];
  const allowlist = loadAllowlist(root);

  for (const relativeDir of TARGET_DIRECTORIES) {
    const absoluteDir = path.join(root, relativeDir);

    let files: string[] = [];
    try {
      files = collectFiles(absoluteDir);
    } catch {
      continue;
    }

    for (const absoluteFilePath of files) {
      const relativeFilePath = path.relative(root, absoluteFilePath);

      if (shouldSkipFile(relativeFilePath)) {
        continue;
      }

      allViolations.push(...scanFile(absoluteFilePath));
    }
  }

  const actionableViolations = allViolations.filter((violation) => !isAllowlisted(violation, root, allowlist));

  if (actionableViolations.length === 0) {
    console.log('✅ Mock data scanner passed: no disallowed patterns found.');
    return;
  }

  const ordered = actionableViolations.sort((a, b) => {
    const aPath = path.relative(root, a.file);
    const bPath = path.relative(root, b.file);
    if (aPath === bPath) {
      return a.line - b.line;
    }
    return aPath.localeCompare(bPath);
  });

  console.error(`❌ Mock data scanner found ${ordered.length} disallowed pattern(s):`);
  for (const violation of ordered) {
    const relativePath = path.relative(root, violation.file);
    console.error(`- ${relativePath}:${violation.line} [${violation.ruleId}] ${violation.description}`);
    console.error(`  ↳ ${violation.content}`);
  }

  console.error('');
  console.error('Remediation options:');
  console.error('1) Replace mock/test literals with API-backed data flows.');
  console.error(`2) Move valid test/mocks into approved folders: ${[...APPROVED_MOCK_FOLDERS].join(', ')}.`);
  console.error(`3) Add a scoped allowlist entry in ${ALLOWLIST_CONFIG_PATH} with a reason.`);
  console.error(`4) Use '${INLINE_ALLOW_COMMENT} <reason>' only for narrowly justified line-level exceptions.`);
  process.exit(1);
}

main();
