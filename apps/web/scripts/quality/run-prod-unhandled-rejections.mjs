#!/usr/bin/env node
/**
 * Run the frontend test suite with strict unhandled rejection handling.
 *
 * Do not set NODE_ENV=production here. React's production build intentionally
 * omits the test-only act() API that Testing Library needs, which turns this
 * gate into an environment failure instead of an unhandled-rejection check.
 */
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, "..", "..");
const vitestBin = resolve(
  webRoot,
  "node_modules",
  ".bin",
  process.platform === "win32" ? "vitest.CMD" : "vitest",
);

const nodeOptions = new Set(
  (process.env.NODE_OPTIONS ?? "")
    .split(/\s+/)
    .map((option) => option.trim())
    .filter(Boolean),
);
nodeOptions.add("--unhandled-rejections=strict");

const command = process.platform === "win32" ? "cmd.exe" : vitestBin;
const args = process.platform === "win32" ? ["/c", vitestBin, "run"] : ["run"];

const result = spawnSync(command, args, {
  cwd: webRoot,
  env: {
    ...process.env,
    NODE_ENV: "test",
    NODE_OPTIONS: [...nodeOptions].join(" "),
  },
  stdio: "inherit",
});

if (result.error) {
  console.error(`Could not start strict unhandled-rejection test gate: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
