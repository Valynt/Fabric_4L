#!/usr/bin/env node
/**
 * Frontend release-confidence verifier.
 *
 * This script intentionally runs gates in dependency order so engineers get a
 * fast, actionable failure before expensive workflow suites. Use
 * FRONTEND_VERIFY_MODE=full to include the broad validation E2E suite in CI.
 */
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { runTask } from "../lib/task-runner.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, "..", "..");
const mode = process.env.FRONTEND_VERIFY_MODE || "standard";

const TASK_REGISTRY = {
  standard: [
    task("Workflow matrix", "pnpm", ["run", "test:workflow-matrix"]),
    task("Workflow contracts", "pnpm", ["run", "test:workflow-contracts"]),
    task("Route inventory", "pnpm", ["run", "test:route-inventory"]),
    task("Frontend hygiene", "pnpm", ["run", "test:frontend-hygiene"]),
    task("UI design readiness", "pnpm", ["run", "test:ui-readiness"]),
    task("TypeScript", "pnpm", ["run", "check"]),
    task("Contract tests", "pnpm", ["run", "test:contracts"]),
    task("Trust-boundary parser guard", "pnpm", ["run", "test:trust-boundaries"]),
    task("Unit/component tests", "pnpm", ["run", "test"]),
    task("Store coverage threshold", "pnpm", ["run", "test:coverage:stores"]),
    task("Critical E2E guard", "pnpm", ["run", "test:e2e:guard"]),
    task("Production build", "pnpm", ["run", "build"]),
    task("Bundle budget", "pnpm", ["run", "test:bundle-budget"]),
  ],
  full: [
    task("Workflow matrix", "pnpm", ["run", "test:workflow-matrix"]),
    task("Workflow contracts", "pnpm", ["run", "test:workflow-contracts"]),
    task("Route inventory", "pnpm", ["run", "test:route-inventory"]),
    task("Frontend hygiene", "pnpm", ["run", "test:frontend-hygiene"]),
    task("UI design readiness", "pnpm", ["run", "test:ui-readiness"]),
    task("TypeScript", "pnpm", ["run", "check"]),
    task("Contract tests", "pnpm", ["run", "test:contracts"]),
    task("P0 workflow validation", "pnpm", ["run", "test:e2e:validation:p0"]),
    task("P1 workflow validation", "pnpm", ["run", "test:e2e:validation:p1"]),
    task("Broad workflow validation", "pnpm", ["run", "test:e2e:validation"]),
    task("Trust-boundary parser guard", "pnpm", ["run", "test:trust-boundaries"]),
    task("Unit/component tests", "pnpm", ["run", "test"]),
    task("Store coverage threshold", "pnpm", ["run", "test:coverage:stores"]),
    task("Critical E2E guard", "pnpm", ["run", "test:e2e:guard"]),
    task("Production build", "pnpm", ["run", "build"]),
    task("Bundle budget", "pnpm", ["run", "test:bundle-budget"]),
  ],
};

const gates = TASK_REGISTRY[mode] || TASK_REGISTRY.standard;

for (const gate of gates) {
  console.log(`\n## ${gate.label}`);
  const result = runTask(gate, { cwd: webRoot, env: process.env });
  if (result.error) {
    console.error(`${gate.label} could not start: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) {
    console.error(`${gate.label} failed with exit code ${result.status}.`);
    process.exit(result.status || 1);
  }
}

console.log(`\nFrontend verification passed in ${mode} mode.`);

function task(label, command, args) {
  return { label, command, args };
}
