import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import path from "node:path";
import { readFile } from "node:fs/promises";

const require = createRequire(import.meta.url);

const TASK_SEGMENT = "[A-Za-z0-9][A-Za-z0-9_.-]*";
const TASK_ID_PATTERN = new RegExp(`^${TASK_SEGMENT}(?::${TASK_SEGMENT})*$`);
const MAKE_TARGET_PATTERN = new RegExp(`^${TASK_SEGMENT}$`);
const NX_TARGET_PATTERN = new RegExp(`^${TASK_SEGMENT}:${TASK_SEGMENT}$`);
const ALLOWED_ROOT_KEYS = new Set(["schema_version", "tasks"]);
const ALLOWED_TASK_KEYS = new Set(["kind", "target"]);

export const MAX_DELEGATION_DEPTH = 16;

export class FabricError extends Error {
  constructor(message, exitCode = 1) {
    super(message);
    this.name = this.constructor.name;
    this.exitCode = exitCode;
  }
}

export class UsageError extends FabricError {
  constructor(message) {
    super(message, 2);
  }
}

export class ManifestError extends FabricError {}

export class DelegationError extends FabricError {}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function rejectUnknownKeys(value, allowedKeys, subject) {
  for (const key of Object.keys(value)) {
    if (!allowedKeys.has(key)) {
      throw new ManifestError(`${subject} has unknown field ${JSON.stringify(key)}`);
    }
  }
}

export function validateTaskId(taskId, subject = "task") {
  if (typeof taskId !== "string" || !TASK_ID_PATTERN.test(taskId)) {
    throw new UsageError(
      `${subject} must contain only ASCII letters, digits, dot, underscore, dash, and colon-separated segments`,
    );
  }
  return taskId;
}

function validateMakeTarget(target, subject) {
  if (typeof target !== "string" || !MAKE_TARGET_PATTERN.test(target)) {
    throw new ManifestError(`${subject} is not a safe Make target`);
  }
  return target;
}

function validateNxTarget(target, subject) {
  if (typeof target !== "string" || !NX_TARGET_PATTERN.test(target)) {
    throw new ManifestError(`${subject} must be an Nx project:target pair`);
  }
  return target;
}

export function validateCaller(caller) {
  if (typeof caller !== "string" || !caller.startsWith("make:")) {
    throw new UsageError("--from must use the form make:<caller>");
  }

  const target = caller.slice("make:".length);
  if (!MAKE_TARGET_PATTERN.test(target)) {
    throw new UsageError("--from caller is not a safe Make target");
  }

  return caller;
}

export function validateManifest(value) {
  if (!isPlainObject(value)) {
    throw new ManifestError("task manifest must be a JSON object");
  }
  rejectUnknownKeys(value, ALLOWED_ROOT_KEYS, "task manifest");

  if (value.schema_version !== 1) {
    throw new ManifestError("task manifest schema_version must be 1");
  }
  if (!isPlainObject(value.tasks)) {
    throw new ManifestError("task manifest tasks must be a JSON object");
  }

  for (const [taskId, route] of Object.entries(value.tasks)) {
    try {
      validateTaskId(taskId, "manifest task ID");
    } catch (error) {
      throw new ManifestError(error.message);
    }

    if (!isPlainObject(route)) {
      throw new ManifestError(`manifest task ${taskId} must be a JSON object`);
    }
    rejectUnknownKeys(route, ALLOWED_TASK_KEYS, `manifest task ${taskId}`);

    if (route.kind === "nx") {
      validateNxTarget(route.target, `manifest task ${taskId} target`);
    } else if (route.kind === "make_delegate") {
      validateMakeTarget(route.target, `manifest task ${taskId} target`);
    } else {
      throw new ManifestError(
        `manifest task ${taskId} kind must be nx or make_delegate`,
      );
    }
  }

  return value;
}

export async function loadManifest(manifestPath, options = {}) {
  const read = options.readFileImpl ?? readFile;
  let source;
  try {
    source = await read(manifestPath, "utf8");
  } catch (error) {
    throw new ManifestError(`cannot read task manifest: ${error.message}`);
  }

  let parsed;
  try {
    parsed = JSON.parse(source);
  } catch (error) {
    throw new ManifestError(`cannot parse task manifest: ${error.message}`);
  }

  return validateManifest(parsed);
}

function validateForwardedArgs(args) {
  for (const value of args) {
    if (typeof value !== "string" || value.includes("\0")) {
      throw new UsageError("forwarded arguments must be NUL-free strings");
    }
  }
  return args;
}

export function parseCliArgs(argv) {
  if (!Array.isArray(argv)) {
    throw new UsageError("arguments must be an array");
  }
  // pnpm 10 preserves the conventional script delimiter, so
  // `pnpm run fabric -- list` arrives as `["--", "list"]`.
  if (argv[0] === "--") {
    argv = argv.slice(1);
  }
  if (argv.length === 0 || argv[0] === "--help" || argv[0] === "-h") {
    return { action: "help" };
  }

  if (argv[0] === "list") {
    if (argv.length !== 1) {
      throw new UsageError("list does not accept options or arguments");
    }
    return { action: "list" };
  }

  const task = validateTaskId(argv[0]);
  let caller = null;
  let forwardedArgs = [];
  let index = 1;

  while (index < argv.length) {
    const value = argv[index];
    if (value === "--") {
      forwardedArgs = argv.slice(index + 1);
      index = argv.length;
      break;
    }
    if (value === "--from") {
      if (caller !== null) {
        throw new UsageError("--from may be specified only once");
      }
      if (index + 1 >= argv.length) {
        throw new UsageError("--from requires make:<caller>");
      }
      caller = validateCaller(argv[index + 1]);
      index += 2;
      continue;
    }
    if (typeof value === "string" && value.startsWith("-")) {
      throw new UsageError(`unknown option ${JSON.stringify(value)}`);
    }
    throw new UsageError(
      `unexpected argument ${JSON.stringify(value)}; task arguments must follow --`,
    );
  }

  validateForwardedArgs(forwardedArgs);
  return { action: "run", task, caller, forwardedArgs };
}

function validateStackEntry(entry) {
  if (typeof entry !== "string") {
    throw new DelegationError("FABRIC_DELEGATION_STACK entries must be strings");
  }

  if (entry.startsWith("fabric:")) {
    const task = entry.slice("fabric:".length);
    if (TASK_ID_PATTERN.test(task)) {
      return entry;
    }
  } else if (entry.startsWith("make:")) {
    const target = entry.slice("make:".length);
    if (MAKE_TARGET_PATTERN.test(target)) {
      return entry;
    }
  }

  throw new DelegationError(
    "FABRIC_DELEGATION_STACK entries must use fabric:<task> or make:<target>",
  );
}

export function parseDelegationStack(rawStack) {
  if (rawStack === undefined) {
    return [];
  }

  let stack;
  try {
    stack = JSON.parse(rawStack);
  } catch (error) {
    throw new DelegationError(`FABRIC_DELEGATION_STACK is malformed JSON: ${error.message}`);
  }

  if (!Array.isArray(stack)) {
    throw new DelegationError("FABRIC_DELEGATION_STACK must be a JSON array");
  }
  if (stack.length > MAX_DELEGATION_DEPTH) {
    throw new DelegationError(
      `FABRIC_DELEGATION_STACK exceeds depth ${MAX_DELEGATION_DEPTH}`,
    );
  }

  const seen = new Set();
  for (const entry of stack) {
    validateStackEntry(entry);
    if (seen.has(entry)) {
      throw new DelegationError(`delegation cycle contains duplicate ${entry}`);
    }
    seen.add(entry);
  }

  return [...stack];
}

export function extendDelegationStack(stack, task, caller = null) {
  const next = [...stack];
  const seen = new Set(next);
  const additions = [];
  if (caller !== null) {
    additions.push(validateCaller(caller));
  }
  additions.push(`fabric:${validateTaskId(task)}`);

  for (const entry of additions) {
    if (seen.has(entry)) {
      throw new DelegationError(`delegation cycle would repeat ${entry}`);
    }
    next.push(entry);
    seen.add(entry);
  }

  if (next.length > MAX_DELEGATION_DEPTH) {
    throw new DelegationError(`delegation would exceed depth ${MAX_DELEGATION_DEPTH}`);
  }
  return next;
}

function routeForTask(manifest, task, legacyMode) {
  if (legacyMode !== undefined && legacyMode !== "delegate" && legacyMode !== "error") {
    throw new DelegationError(
      "FABRIC_LEGACY_MODE must be unset, delegate, or error",
    );
  }
  if (Object.hasOwn(manifest.tasks, task)) {
    return { ...manifest.tasks[task], source: "manifest" };
  }
  if (legacyMode === "error") {
    throw new DelegationError(
      `task ${task} is not in the Fabric manifest and legacy fallback is disabled`,
    );
  }
  return { kind: "make_delegate", target: task, source: "legacy_fallback" };
}

export function createDispatchPlan({
  task,
  caller = null,
  forwardedArgs = [],
  manifest,
  env = process.env,
}) {
  validateTaskId(task);
  validateForwardedArgs(forwardedArgs);
  validateManifest(manifest);

  const stack = parseDelegationStack(env.FABRIC_DELEGATION_STACK);
  const nextStack = extendDelegationStack(stack, task, caller);
  const route = routeForTask(manifest, task, env.FABRIC_LEGACY_MODE);

  if (route.kind === "make_delegate") {
    const makeEntry = `make:${route.target}`;
    if (nextStack.includes(makeEntry)) {
      throw new DelegationError(`delegation cycle would re-enter ${makeEntry}`);
    }
  }

  return { route, stack: nextStack, forwardedArgs: [...forwardedArgs] };
}

export function formatTaskList(manifest) {
  validateManifest(manifest);
  const lines = ["TASK\tROUTE\tTARGET"];
  for (const taskId of Object.keys(manifest.tasks).sort()) {
    const route = manifest.tasks[taskId];
    lines.push(`${taskId}\t${route.kind}\t${route.target}`);
  }
  return `${lines.join("\n")}\n`;
}

export function defaultProcessRunner(command, args, options) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, options);
    child.once("error", reject);
    child.once("close", (code, signal) => resolve({ code, signal }));
  });
}

function normalizeExitCode(result) {
  const code = typeof result === "number" ? result : result?.code;
  if (Number.isInteger(code) && code >= 0 && code <= 255) {
    return code;
  }
  if (result?.signal) {
    throw new FabricError(`child process terminated by signal ${result.signal}`);
  }
  throw new FabricError("child process did not return a valid exit code");
}

function defaultNxBinaryResolver(cwd) {
  return require.resolve("nx/bin/nx.js", { paths: [cwd] });
}

export async function dispatch(options) {
  const {
    cwd = process.cwd(),
    env = process.env,
    runner = defaultProcessRunner,
    resolveNxBinary = defaultNxBinaryResolver,
    nodePath = process.execPath,
    makeCommand = "make",
  } = options;
  const plan = createDispatchPlan(options);
  const childEnv = {
    ...env,
    FABRIC_DELEGATION_STACK: JSON.stringify(plan.stack),
  };

  let command;
  let args;
  if (plan.route.kind === "nx") {
    let nxBinaryPath;
    try {
      nxBinaryPath = resolveNxBinary(cwd);
    } catch (error) {
      throw new FabricError(`cannot resolve the Nx executable: ${error.message}`);
    }
    if (typeof nxBinaryPath !== "string" || !path.isAbsolute(nxBinaryPath)) {
      throw new FabricError("Nx executable resolver did not return an absolute path");
    }
    command = nodePath;
    args = [
      nxBinaryPath,
      "run",
      plan.route.target,
      "--skip-nx-cache",
      ...(plan.forwardedArgs.length > 0 ? ["--", ...plan.forwardedArgs] : []),
    ];
    childEnv.NX_DAEMON = "false";
    childEnv.NX_NO_CLOUD = "true";
  } else {
    command = makeCommand;
    args = [plan.route.target, ...plan.forwardedArgs];
  }

  let result;
  try {
    result = await runner(command, args, {
      cwd,
      env: childEnv,
      shell: false,
      stdio: "inherit",
      windowsHide: true,
    });
  } catch (error) {
    throw new FabricError(`cannot run ${command}: ${error.message}`);
  }
  return normalizeExitCode(result);
}
