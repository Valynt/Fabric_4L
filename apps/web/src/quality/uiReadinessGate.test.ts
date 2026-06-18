import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

type UiReadinessModule = typeof import("../../scripts/quality/assert-ui-readiness.mjs");

let fixtureRoot: string;

const options = {
  requiredFiles: [
    "docs/ui-design-readiness.md",
    "docs/frontend-workflow-coverage-matrix.md",
    "package.json",
    "src/components/states/EmptyState.tsx",
    "e2e/journeys/critical.spec.ts",
  ],
  readinessEvidence: [
    { file: "docs/ui-design-readiness.md", pattern: /Readiness Definition/, label: "readiness definition" },
    { file: "docs/frontend-workflow-coverage-matrix.md", pattern: /test:ui-readiness/, label: "UI readiness gate reference" },
    { file: "package.json", pattern: /test:ui-readiness/, label: "package script wiring" },
  ],
  criticalE2eFiles: ["e2e/journeys/critical.spec.ts"],
  sourceRoots: ["src/components"],
};

function writeFixtureFile(path: string, text: string) {
  const absolute = join(fixtureRoot, path);
  mkdirSync(dirname(absolute), { recursive: true });
  writeFileSync(absolute, text, "utf8");
}

async function loadGate(): Promise<UiReadinessModule> {
  return import("../../scripts/quality/assert-ui-readiness.mjs");
}

beforeEach(() => {
  fixtureRoot = join(tmpdir(), `vf-ui-readiness-${process.pid}-${Date.now()}`);
  mkdirSync(fixtureRoot, { recursive: true });
  writeFixtureFile("docs/ui-design-readiness.md", "# UI Design Readiness\n\n## Readiness Definition\n");
  writeFixtureFile("docs/frontend-workflow-coverage-matrix.md", "Gate: test:ui-readiness\n");
  writeFixtureFile("package.json", '{"scripts":{"test:ui-readiness":"node scripts/quality/assert-ui-readiness.mjs"}}');
  writeFixtureFile("src/components/states/EmptyState.tsx", "export function EmptyState(){ return null; }\n");
  writeFixtureFile("e2e/journeys/critical.spec.ts", "import { test } from '@playwright/test';\ntest('critical flow', async () => {});\n");
});

afterEach(() => {
  rmSync(fixtureRoot, { recursive: true, force: true });
});

describe("ui readiness gate", () => {
  it("passes when required evidence and release source are clean", async () => {
    const { runUiReadinessChecks } = await loadGate();

    expect(runUiReadinessChecks(fixtureRoot, options)).toEqual([]);
  });

  it("fails closed when required evidence is missing", async () => {
    const { runUiReadinessChecks } = await loadGate();
    writeFixtureFile("docs/frontend-workflow-coverage-matrix.md", "Gate missing\n");

    expect(runUiReadinessChecks(fixtureRoot, options)).toContain(
      "docs/frontend-workflow-coverage-matrix.md is missing required UI readiness gate reference",
    );
  });

  it("fails closed when critical E2E coverage is skipped", async () => {
    const { runUiReadinessChecks } = await loadGate();
    writeFixtureFile("e2e/journeys/critical.spec.ts", "import { test } from '@playwright/test';\ntest.skip('critical flow', async () => {});\n");

    expect(runUiReadinessChecks(fixtureRoot, options)).toContain(
      "e2e/journeys/critical.spec.ts contains forbidden test.skip/test.fixme",
    );
  });

  it("fails closed when release source contains broad placeholder copy", async () => {
    const { runUiReadinessChecks } = await loadGate();
    writeFixtureFile("src/components/states/EmptyState.tsx", "export const copy = 'Coming soon';\n");

    expect(runUiReadinessChecks(fixtureRoot, options).some((failure) => (
      failure.includes("EmptyState.tsx") && failure.includes("forbidden broad coming soon copy")
    ))).toBe(true);
  });
});
