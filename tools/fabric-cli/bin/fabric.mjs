#!/usr/bin/env node

import { pathToFileURL } from "node:url";
import {
  FabricError,
  dispatch,
  formatTaskList,
  loadManifest,
  parseCliArgs,
} from "../lib/dispatch.mjs";

const MANIFEST_URL = new URL("../tasks.json", import.meta.url);

export const USAGE = `Usage:
  fabric list
  fabric <task> [--from make:<caller>] [-- <task-args...>]

Tasks not yet migrated use the Make compatibility bridge unless
FABRIC_LEGACY_MODE=error is set.
`;

export async function main(argv = process.argv.slice(2), options = {}) {
  const stdout = options.stdout ?? process.stdout;
  const manifest =
    options.manifest ?? (await loadManifest(options.manifestPath ?? MANIFEST_URL));
  const parsed = parseCliArgs(argv);

  if (parsed.action === "help") {
    stdout.write(USAGE);
    return 0;
  }
  if (parsed.action === "list") {
    stdout.write(formatTaskList(manifest));
    return 0;
  }

  return dispatch({
    ...parsed,
    manifest,
    cwd: options.cwd ?? process.cwd(),
    env: options.env ?? process.env,
    runner: options.runner,
    resolveNxBinary: options.resolveNxBinary,
    nodePath: options.nodePath,
    makeCommand: options.makeCommand,
  });
}

function isEntrypoint() {
  if (!process.argv[1]) {
    return false;
  }
  return pathToFileURL(process.argv[1]).href === import.meta.url;
}

if (isEntrypoint()) {
  try {
    process.exitCode = await main();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`fabric: ${message}\n`);
    process.exitCode =
      error instanceof FabricError && Number.isInteger(error.exitCode) ? error.exitCode : 1;
  }
}
