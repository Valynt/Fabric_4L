/**
 * Regression guard: ensures any mermaid version resolved in a lockfile
 * is not vulnerable (CVE-2026-41148, CVE-2026-41150, CVE-2026-41159,
 * GHSA-ghcm-xqfw-q4vr — all patched in mermaid >=11.15.0).
 *
 * If this test fails, a vulnerable mermaid version has re-entered the
 * dependency tree. Fix by ensuring pnpm.overrides contains
 * `"mermaid": ">=11.15.0 <12.0.0"` in both root package.json and
 * apps/web/package.json, then re-run pnpm install.
 */
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const __dirname = dirname(fileURLToPath(import.meta.url));

const MINIMUM_SAFE_MERMAID = [11, 15, 0] as const;

function parseSemver(version: string): [number, number, number] {
  const parts = version.split(".").map(Number);
  if (parts.length < 3 || parts.some(Number.isNaN)) {
    throw new Error(`Cannot parse semver: ${version}`);
  }
  return [parts[0], parts[1], parts[2]];
}

function isAtLeast(
  actual: [number, number, number],
  minimum: readonly [number, number, number],
): boolean {
  for (let i = 0; i < 3; i++) {
    if (actual[i] > minimum[i]) return true;
    if (actual[i] < minimum[i]) return false;
  }
  return true; // equal
}

function assertLockfileClean(lockfilePath: string, label: string): void {
  const lockfile = readFileSync(lockfilePath, "utf-8");
  const mermaidVersionPattern = /^\s{2}mermaid@(\d+\.\d+\.\d+):/gm;
  const resolvedVersions: string[] = [];
  let match: RegExpExecArray | null;

  while ((match = mermaidVersionPattern.exec(lockfile)) !== null) {
    resolvedVersions.push(match[1]);
  }

  const vulnerableVersions = resolvedVersions.filter((v) => {
    try {
      return !isAtLeast(parseSemver(v), MINIMUM_SAFE_MERMAID);
    } catch {
      return false;
    }
  });

  expect(
    vulnerableVersions,
    `Vulnerable mermaid version(s) in ${label}: ${vulnerableVersions.join(", ")}. ` +
      `All resolved versions must be >=11.15.0. ` +
      `Ensure pnpm.overrides contains "mermaid": ">=11.15.0 <12.0.0" and re-run pnpm install.`,
  ).toHaveLength(0);
}

describe("dependency version security gates", () => {
  it("mermaid resolves to >=11.15.0 when present in root pnpm-lock.yaml", () => {
    assertLockfileClean(
      resolve(__dirname, "../../../../pnpm-lock.yaml"),
      "root pnpm-lock.yaml",
    );
  });

  it("mermaid resolves to >=11.15.0 when present in apps/web/pnpm-lock.yaml", () => {
    assertLockfileClean(
      resolve(__dirname, "../../../../apps/web/pnpm-lock.yaml"),
      "apps/web/pnpm-lock.yaml",
    );
  });
});
