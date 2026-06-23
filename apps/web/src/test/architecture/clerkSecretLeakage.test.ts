/**
 * Phase 2 — architecture sentinel test: enforce that the frontend never
 * references Clerk secret keys or non-VITE_ Clerk environment variables.
 *
 * This is a compile-time guard against accidentally importing or
 * hardcoding Clerk secrets in browser code. The frontend MUST only use
 * public-safe Clerk configuration (VITE_ prefixed variables).
 *
 * Violations:
 *   - CLERK_SECRET_KEY
 *   - CLERK_SECRET
 *   - Any non-VITE_ Clerk env var (e.g., CLERK_API_KEY, CLERK_SIGNING_KEY)
 *
 * Allowed:
 *   - VITE_CLERK_PUBLISHABLE_KEY
 *   - VITE_AUTH_PROVIDER
 *   - VITE_CLERK_JWT_TEMPLATE
 *   - VITE_CLERK_SIGN_IN_URL
 *   - VITE_CLERK_SIGN_UP_URL
 *   - VITE_CLERK_AFTER_SIGN_IN_URL
 *   - VITE_CLERK_AFTER_SIGN_UP_URL
 *   - VITE_CLERK_SELECT_ORG_URL
 */
import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "fs";
import { join } from "path";

const WEB_SRC = join(__dirname, "../../../src");

// Forbidden patterns that MUST NOT appear in frontend source.
// We target actual env var access patterns, not comments or test labels.
const FORBIDDEN_PATTERNS = [
  // Direct env var access with non-VITE_ Clerk keys
  /process\.env\.CLERK_SECRET_KEY/,
  /process\.env\.CLERK_SECRET/,
  /import\.meta\.env\.CLERK_SECRET_KEY/,
  /import\.meta\.env\.CLERK_SECRET/,
  // Any other CLERK_ env var accessed via process.env or import.meta.env
  // that is NOT VITE_ prefixed.
  /process\.env\.(?!VITE_)CLERK_[A-Z_]+/,
  /import\.meta\.env\.(?!VITE_)CLERK_[A-Z_]+/,
];

// Explicitly allowed patterns (for documentation).
const ALLOWED_PATTERNS = [
  "VITE_CLERK_PUBLISHABLE_KEY",
  "VITE_AUTH_PROVIDER",
  "VITE_CLERK_JWT_TEMPLATE",
  "VITE_CLERK_SIGN_IN_URL",
  "VITE_CLERK_SIGN_UP_URL",
  "VITE_CLERK_AFTER_SIGN_IN_URL",
  "VITE_CLERK_AFTER_SIGN_UP_URL",
  "VITE_CLERK_SELECT_ORG_URL",
];

const SKIPPED_DIRECTORIES = new Set([
  "node_modules",
  ".git",
  "dist",
  "build",
  ".next",
  ".vitest",
  "coverage",
]);

function shouldIncludeSourceFile(fileName: string, extensions: string[]): boolean {
  const ext = fileName.split(".").pop();
  return Boolean(ext && extensions.includes(ext));
}

function walkDir(dir: string, extensions: string[]): string[] {
  const files: string[] = [];
  const entries = readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (SKIPPED_DIRECTORIES.has(entry.name)) continue;
      files.push(...walkDir(fullPath, extensions));
    } else if (entry.isFile() && shouldIncludeSourceFile(entry.name, extensions)) {
      files.push(fullPath);
    }
  }
  return files;
}

describe("Architecture Sentinel — Clerk Secret Leakage", () => {
  it("frontend source must not contain CLERK_SECRET_KEY or CLERK_SECRET", () => {
    const sourceFiles = walkDir(WEB_SRC, ["ts", "tsx", "js", "jsx"]);
    const violations: { file: string; line: number; pattern: string }[] = [];

    for (const file of sourceFiles) {
      const content = readFileSync(file, "utf-8");
      const lines = content.split("\n");

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // Check each forbidden pattern.
        for (const pattern of FORBIDDEN_PATTERNS) {
          if (pattern.test(line)) {
            violations.push({
              file: file.replace(WEB_SRC, "src"),
              line: i + 1,
              pattern: pattern.toString(),
            });
          }
        }
      }
    }

    if (violations.length > 0) {
      const formatted = violations
        .map((v) => `  ${v.file}:${v.line} — ${v.pattern}`)
        .join("\n");
      throw new Error(
        `Clerk secret leakage detected in frontend source:\n${formatted}\n\n` +
          "Frontend must only use VITE_-prefixed Clerk env vars. " +
          "Secret keys belong on the server only.",
      );
    }

    expect(violations).toHaveLength(0);
  });

  it("documents the allowed VITE_ Clerk env vars", () => {
    // This test is documentation-only; it always passes as long as the
    // ALLOWED_PATTERNS list is non-empty. It serves as a single source
    // of truth for what Clerk env vars are permitted in the frontend.
    expect(ALLOWED_PATTERNS.length).toBeGreaterThan(0);
  });
});
