import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import {
  DelegationError,
  createDispatchPlan,
  dispatch,
} from "../lib/dispatch.mjs";

const MANIFEST = {
  schema_version: 1,
  tasks: {
    lint: { kind: "nx", target: "root:lint" },
    verify: { kind: "make_delegate", target: "verify" },
  },
};

function recordingRunner(result = { code: 0, signal: null }) {
  const calls = [];
  return {
    calls,
    runner: async (...args) => {
      calls.push(args);
      return result;
    },
  };
}

test("dispatch routes an Nx task through node with cache and daemon disabled", async () => {
  const recorder = recordingRunner({ code: 7, signal: null });
  const nxBinary = path.resolve("node_modules/nx/dist/bin/nx.js");
  const exitCode = await dispatch({
    task: "lint",
    forwardedArgs: ["--configuration=ci", "literal value"],
    manifest: MANIFEST,
    env: { KEEP_ME: "yes" },
    cwd: "/repo",
    runner: recorder.runner,
    resolveNxBinary: () => nxBinary,
    nodePath: "/node",
  });

  assert.equal(exitCode, 7);
  assert.equal(recorder.calls.length, 1);
  const [command, args, options] = recorder.calls[0];
  assert.equal(command, "/node");
  assert.deepEqual(args, [
    nxBinary,
    "run",
    "root:lint",
    "--skip-nx-cache",
    "--",
    "--configuration=ci",
    "literal value",
  ]);
  assert.equal(options.shell, false);
  assert.equal(options.env.NX_DAEMON, "false");
  assert.equal(options.env.NX_NO_CLOUD, "true");
  assert.equal(options.env.KEEP_ME, "yes");
  assert.deepEqual(JSON.parse(options.env.FABRIC_DELEGATION_STACK), ["fabric:lint"]);
});

test("dispatch routes an explicit Make delegate and propagates its exit code", async () => {
  const recorder = recordingRunner({ code: 23, signal: null });
  const exitCode = await dispatch({
    task: "verify",
    forwardedArgs: ["NAME=value with spaces"],
    manifest: MANIFEST,
    env: {},
    runner: recorder.runner,
  });

  assert.equal(exitCode, 23);
  assert.equal(recorder.calls[0][0], "make");
  assert.deepEqual(recorder.calls[0][1], ["verify", "NAME=value with spaces"]);
  assert.equal(recorder.calls[0][2].shell, false);
});

test("unknown valid task uses the Make bridge", async () => {
  const recorder = recordingRunner();
  await dispatch({
    task: "test-layer6",
    forwardedArgs: [],
    manifest: MANIFEST,
    env: {},
    runner: recorder.runner,
  });
  assert.deepEqual(recorder.calls[0].slice(0, 2), ["make", ["test-layer6"]]);
});

test("legacy error mode disables only unknown fallback", async () => {
  const recorder = recordingRunner();
  await assert.rejects(
    dispatch({
      task: "test-layer6",
      forwardedArgs: [],
      manifest: MANIFEST,
      env: { FABRIC_LEGACY_MODE: "error" },
      runner: recorder.runner,
    }),
    DelegationError,
  );
  assert.equal(recorder.calls.length, 0);

  assert.equal(
    await dispatch({
      task: "verify",
      forwardedArgs: [],
      manifest: MANIFEST,
      env: { FABRIC_LEGACY_MODE: "error" },
      runner: recorder.runner,
    }),
    0,
  );
});

test("unknown legacy mode fails closed before starting a process", async () => {
  const recorder = recordingRunner();
  await assert.rejects(
    dispatch({
      task: "lint",
      forwardedArgs: [],
      manifest: MANIFEST,
      env: { FABRIC_LEGACY_MODE: "typo" },
      runner: recorder.runner,
    }),
    /must be unset, delegate, or error/,
  );
  assert.equal(recorder.calls.length, 0);
});

test("Make caller guard rejects a direct delegation cycle", () => {
  assert.throws(
    () =>
      createDispatchPlan({
        task: "verify",
        caller: "make:verify",
        forwardedArgs: [],
        manifest: MANIFEST,
        env: {},
      }),
    /re-enter make:verify/,
  );
});

test("an invalid process result fails closed", async () => {
  await assert.rejects(
    dispatch({
      task: "verify",
      forwardedArgs: [],
      manifest: MANIFEST,
      env: {},
      runner: async () => ({ code: null, signal: null }),
    }),
    /valid exit code/,
  );
});
