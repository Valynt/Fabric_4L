#!/usr/bin/env node
/**
 * Frontend release-confidence verifier.
 *
 * This script intentionally runs gates in dependency order so engineers get a
 * fast, actionable failure before expensive workflow suites. Use
 * FRONTEND_VERIFY_MODE=full to include the broad validation E2E suite in CI.
 */
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, "..", "..");
const mode = process.env.FRONTEND_VERIFY_MODE || "standard";
const pnpmCommand = "pnpm";

const gates = [
  ["Workflow matrix", [pnpmCommand, ["run", "test:workflow-matrix"]]],
  ["Frontend hygiene", [pnpmCommand, ["run", "test:frontend-hygiene"]]],
  ["TypeScript", [pnpmCommand, ["run", "check"]]],
  ["Contract tests", [pnpmCommand, ["run", "test:contracts"]]],
  ["Trust-boundary parser guard", [pnpmCommand, ["run", "test:trust-boundaries"]]],
  ["Unit/component tests", [pnpmCommand, ["run", "test"]]],
  ["Store coverage threshold", [pnpmCommand, ["run", "test:coverage:stores"]]],
  ["Critical E2E guard", [pnpmCommand, ["run", "test:e2e:guard"]]],
  ["Production build", [pnpmCommand, ["run", "build"]]],
  ["Bundle budget", [pnpmCommand, ["run", "test:bundle-budget"]]],
];

if (mode === "full") {
  gates.splice(5, 0, [
    "P0 workflow validation",
    [pnpmCommand, ["run", "test:e2e:validation:p0"]],
  ]);
  gates.splice(6, 0, [
    "Broad workflow validation",
    [pnpmCommand, ["run", "test:e2e:validation"]],
  ]);
}

for (const [label, [command, args]] of gates) {
  console.log(`\n## ${label}`);
  const spawnCommand = process.platform === "win32" ? "cmd.exe" : command;
  const spawnArgs =
    process.platform === "win32"
      ? ["/d", "/s", "/c", `${command} ${args.join(" ")}`]
      : args;
  const result = spawnSync(spawnCommand, spawnArgs, {
    cwd: webRoot,
    stdio: "inherit",
    shell: false,
    env: process.env,
  });

  if (result.error) {
    console.error(`${label} could not start: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) {
    console.error(`${label} failed with exit code ${result.status}.`);
    process.exit(result.status || 1);
  }
}

console.log(`\nFrontend verification passed in ${mode} mode.`);
