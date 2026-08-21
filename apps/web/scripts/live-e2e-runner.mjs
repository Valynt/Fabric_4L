#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, "..");

const SCENARIOS = {
  backend: ["pnpm", ["run", "test:e2e:backend"]],
  p0: [
    "playwright",
    [
      "test",
      "--project=backend-integrated",
      "e2e/journeys/j1-golden-path-backend-integrated.spec.ts",
      "e2e/journeys/j11-golden-path-business-lifecycle.spec.ts",
      "e2e/journeys/j20-billing-entitlement-gates.spec.ts",
      "e2e/security/deep-link-tenant-isolation-deep.spec.ts",
    ],
  ],
  "golden-path": [
    "playwright",
    [
      "test",
      "--project=backend-integrated",
      "e2e/journeys/j1-golden-path-backend-integrated.spec.ts",
      "e2e/journeys/j11-golden-path-business-lifecycle.spec.ts",
    ],
  ],
  continuous: [
    "playwright",
    [
      "test",
      "--project=backend-integrated",
      "e2e/journeys/j1-valuepilot-continuous-live.spec.ts",
      "e2e/journeys/j2-multi-role-approval-live.spec.ts",
      "e2e/security/live-tenant-b-denied.spec.ts",
    ],
  ],
};

const args = parseArgs(process.argv.slice(2));
const scenario = args.scenario || "backend";

if (!SCENARIOS[scenario]) {
  fail(`Unknown scenario \"${scenario}\". Expected one of: ${Object.keys(SCENARIOS).join(", ")}.`);
}

const liveEnv = {
  ...process.env,
  VITE_USE_MOCKS: "false",
  VITE_ENABLE_MOCK_FALLBACK: "false",
};

const guard = runCommand("node", ["scripts/live-env-guard.mjs", "test"], liveEnv);
if (guard.status !== 0) {
  process.exit(guard.status || 1);
}

if (args.envCheckOnly) {
  console.log(`[live-e2e-runner] environment checks passed for scenario ${scenario}.`);
  process.exit(0);
}

const liveFrontendUrl = liveEnv.PLAYWRIGHT_LIVE_FRONTEND_URL;
if (!liveFrontendUrl) {
  fail("PLAYWRIGHT_LIVE_FRONTEND_URL is required");
}

const scenarioEnv = {
  ...liveEnv,
  PLAYWRIGHT_BASE_URL: liveFrontendUrl,
};

const guardE2E = runCommand("pnpm", ["run", "test:e2e:guard"], scenarioEnv);
if (guardE2E.status !== 0) {
  process.exit(guardE2E.status || 1);
}

const [command, commandArgs] = SCENARIOS[scenario];
const execution = runCommand(command, commandArgs, scenarioEnv);
process.exit(execution.status || 0);

function parseArgs(argv) {
  const parsed = { envCheckOnly: false };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === "--env-check-only") {
      parsed.envCheckOnly = true;
      continue;
    }
    if (token === "--scenario") {
      parsed.scenario = argv[i + 1];
      i += 1;
      continue;
    }
  }
  return parsed;
}

function runCommand(command, args, env) {
  const spawnCommand = process.platform === "win32" ? "cmd.exe" : command;
  const spawnArgs =
    process.platform === "win32"
      ? ["/d", "/s", "/c", `${command} ${args.join(" ")}`]
      : args;

  const result = spawnSync(spawnCommand, spawnArgs, {
    cwd: webRoot,
    stdio: "inherit",
    shell: false,
    env,
  });

  if (result.error) {
    fail(`Failed to run ${command}: ${result.error.message}`);
  }

  return result;
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
