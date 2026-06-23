#!/usr/bin/env node
/**
 * Static UI design-readiness gate.
 *
 * This intentionally complements Playwright and accessibility runs. It checks
 * release evidence and catches obvious UI debt markers before expensive gates.
 */
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, extname, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const defaultWebRoot = resolve(__dirname, "..", "..");

const criticalE2eFiles = [
  "e2e/journeys/j1-ingestion-to-value-tree.spec.ts",
  "e2e/journeys/j2-intelligence-workspace.spec.ts",
  "e2e/journeys/j3-value-studio-deliverable.spec.ts",
  "e2e/journeys/j6-account-prospect-lifecycle.spec.ts",
  "e2e/journeys/j6-account-tenant-switching.spec.ts",
  "e2e/journeys/j7-value-realization-and-calculation.spec.ts",
  "e2e/journeys/j8-approval-review-gates.spec.ts",
  "e2e/journeys/j9-agent-grounding-governance.spec.ts",
  "e2e/journeys/j10-layer-ui-validation.spec.ts",
  "e2e/journeys/j11-golden-path-business-lifecycle.spec.ts",
  "e2e/journeys/j12-resilience-error-recovery.spec.ts",
  "e2e/journeys/j13-stakeholder-mapping.spec.ts",
  "e2e/journeys/j14-value-pack-governance.spec.ts",
  "e2e/journeys/j15-narrative-proposal.spec.ts",
  "e2e/journeys/j16-collaboration.spec.ts",
  "e2e/journeys/j17-crm-integration.spec.ts",
  "e2e/journeys/j18-search-retrieval.spec.ts",
  "e2e/journeys/j19-notifications-tasks.spec.ts",
  "e2e/journeys/j20-admin-configuration.spec.ts",
  "e2e/journeys/j20-billing-entitlement-gates.spec.ts",
  "e2e/journeys/j21-persona-journeys.spec.ts",
  "e2e/journeys/j22-adversarial-e2e.spec.ts",
  "e2e/journeys/j23-personal-settings.spec.ts",
  "e2e/security/tenant-isolation-validation.spec.ts",
  "e2e/security/deep-link-tenant-isolation-deep.spec.ts",
  "e2e/resilience/operational-resilience.spec.ts",
  "e2e/collaboration/collaboration-notifications-tasks.spec.ts",
  "e2e/integrations/crm-external-integrations.spec.ts",
  "e2e/export-workflows.spec.ts",
  "e2e/personas/persona-journeys.spec.ts",
  "e2e/admin.spec.ts",
  "e2e/admin-system.spec.ts",
  "e2e/contracts/account-scoped-workspaces.spec.ts",
  "e2e/contracts/settings-governance.spec.ts",
  "e2e/value-tree-explorer.spec.ts",
  "e2e/business-case.spec.ts",
  "e2e/business-case-list.spec.ts",
];

const sourceRoots = [
  "src/app",
  "src/components",
  "src/features",
  "src/pages",
  "src/shell",
];

const sourceExtensions = new Set([".ts", ".tsx"]);

const requiredFiles = [
  "docs/ui-design-readiness.md",
  "docs/frontend-workflow-coverage-matrix.md",
  "scripts/quality/assert-ui-readiness.mjs",
  "scripts/quality/verify-frontend.mjs",
  "scripts/security/assert-no-skipped-critical-e2e.mjs",
  "scripts/a11y/axe-critical-scan.mjs",
  "components/states/EmptyState.tsx",
  "components/states/LoadingState.tsx",
  "components/states/ErrorState.tsx",
  "components/layout/PageShell.tsx",
  "components/ui/fabric/PageHeader.tsx",
  "components/ui/fabric/StatusBadge.tsx",
  "components/ui/fabric/DataTable.tsx",
  "components/ui/fabric/LegacyTabs.tsx",
  "components/ui/fabric/FabricDialog.tsx",
].map((path) => (path.startsWith("components/") ? `src/${path}` : path));

const readinessEvidence = [
  { file: "docs/ui-design-readiness.md", pattern: /Readiness Definition/, label: "readiness definition" },
  { file: "docs/ui-design-readiness.md", pattern: /P0 And P1 Expectations/, label: "P0/P1 expectations" },
  { file: "docs/ui-design-readiness.md", pattern: /Loading state[\s\S]*Empty state[\s\S]*Success state[\s\S]*Validation error state[\s\S]*API failure and retry[\s\S]*Unauthorized or restricted state/, label: "critical workflow-state expectations" },
  { file: "docs/ui-design-readiness.md", pattern: /What Blocks Release/, label: "release blockers" },
  { file: "docs/ui-design-readiness.md", pattern: /Acceptable Follow-up/, label: "acceptable follow-up definition" },
  { file: "docs/ui-design-readiness.md", pattern: /Known Gaps/, label: "known gaps" },
  { file: "docs/ui-design-readiness.md", pattern: /test:ui-readiness/, label: "ui readiness command" },
  { file: "docs/frontend-workflow-coverage-matrix.md", pattern: /P0-LAYER-VALIDATION[\s\S]*Loading, empty, error, unauthorized, and success states/, label: "P0 layer state proof" },
  { file: "docs/frontend-workflow-coverage-matrix.md", pattern: /Accessibility proof/, label: "accessibility proof column" },
  { file: "docs/frontend-workflow-coverage-matrix.md", pattern: /Resilience proof/, label: "resilience proof column" },
  { file: "docs/frontend-workflow-coverage-matrix.md", pattern: /test:ui-readiness/, label: "UI readiness gate reference" },
  { file: "package.json", pattern: /"test:ui-readiness"\s*:\s*"node scripts\/quality\/assert-ui-readiness\.mjs"/, label: "package script wiring" },
  { file: "scripts/quality/verify-frontend.mjs", pattern: /UI design readiness[\s\S]*test:ui-readiness/, label: "verify frontend wiring" },
  { file: "package.json", pattern: /test:a11y:components/, label: "component accessibility command" },
  { file: "package.json", pattern: /test:a11y:pages/, label: "page accessibility command" },
  { file: "package.json", pattern: /test:a11y:keyboard-flow/, label: "keyboard accessibility command" },
  { file: "package.json", pattern: /test:e2e:guard/, label: "critical E2E guard command" },
];

const forbiddenE2ePatterns = [
  { pattern: /test\.(skip|fixme)\s*\(/, label: "test.skip/test.fixme" },
  { pattern: /\bjourneyTest\.skip\s*\(/, label: "journeyTest.skip" },
  { pattern: /\bSKIP_BACKEND_TESTS\b/, label: "backend skip valve" },
  { pattern: /placeholder assertion|placeholder-only assertion/i, label: "placeholder-only assertion" },
];

const forbiddenSourcePatterns = [
  { pattern: /TODO_UI/, label: "TODO_UI marker" },
  { pattern: /FIXME_UI/, label: "FIXME_UI marker" },
  { pattern: /PLACEHOLDER_UI/, label: "PLACEHOLDER_UI marker" },
  { pattern: /lorem ipsum/i, label: "lorem ipsum copy" },
  { pattern: /coming soon/i, label: "broad coming soon copy" },
];

function readRequiredFile(webRoot, file, failures) {
  const path = resolve(webRoot, file);
  if (!existsSync(path)) {
    failures.push(`${file} is missing`);
    return "";
  }
  return readFileSync(path, "utf8");
}

function collectSourceFiles(root) {
  if (!existsSync(root)) {
    return [];
  }

  const entries = readdirSync(root);
  const files = [];
  for (const entry of entries) {
    const path = join(root, entry);
    const stats = statSync(path);
    if (stats.isDirectory()) {
      if (entry === "node_modules" || entry === "__snapshots__") {
        continue;
      }
      files.push(...collectSourceFiles(path));
      continue;
    }

    if (!sourceExtensions.has(extname(path))) {
      continue;
    }
    if (/\.(test|spec)\.tsx?$/.test(path) || path.endsWith(".d.ts")) {
      continue;
    }
    files.push(path);
  }
  return files;
}

export function runUiReadinessChecks(webRoot = defaultWebRoot, options = {}) {
  const failures = [];
  const requiredFileList = options.requiredFiles ?? requiredFiles;
  const readinessEvidenceList = options.readinessEvidence ?? readinessEvidence;
  const criticalE2eFileList = options.criticalE2eFiles ?? criticalE2eFiles;
  const sourceRootList = options.sourceRoots ?? sourceRoots;

  for (const file of requiredFileList) {
    readRequiredFile(webRoot, file, failures);
  }

  for (const { file, pattern, label } of readinessEvidenceList) {
    const text = readRequiredFile(webRoot, file, failures);
    if (text && !pattern.test(text)) {
      failures.push(`${file} is missing required ${label}`);
    }
  }

  for (const file of criticalE2eFileList) {
    const text = readRequiredFile(webRoot, file, failures);
    if (!text) {
      continue;
    }
    for (const { pattern, label } of forbiddenE2ePatterns) {
      if (pattern.test(text)) {
        failures.push(`${file} contains forbidden ${label}`);
      }
    }
  }

  for (const sourceRoot of sourceRootList) {
    const files = collectSourceFiles(resolve(webRoot, sourceRoot));
    for (const path of files) {
      const text = readFileSync(path, "utf8");
      for (const { pattern, label } of forbiddenSourcePatterns) {
        if (pattern.test(text)) {
          failures.push(`${relative(webRoot, path)} contains forbidden ${label}`);
        }
      }
    }
  }

  return failures;
}

export function assertUiReadiness(webRoot = defaultWebRoot, options = {}) {
  const failures = runUiReadinessChecks(webRoot, options);
  if (failures.length > 0) {
    const message = [
      "UI design readiness failed.",
      ...failures.map((failure) => ` - ${failure}`),
    ].join("\n");
    const error = new Error(message);
    error.failures = failures;
    throw error;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    assertUiReadiness(process.env.UI_READINESS_WEB_ROOT || defaultWebRoot);
    console.log("UI design readiness passed: release evidence, shared primitives, critical E2E guardrails, and placeholder checks are present.");
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
