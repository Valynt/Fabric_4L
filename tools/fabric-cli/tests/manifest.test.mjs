import assert from "node:assert/strict";
import test from "node:test";

import {
  ManifestError,
  formatTaskList,
  loadManifest,
  validateManifest,
} from "../lib/dispatch.mjs";

const VALID_MANIFEST = {
  schema_version: 1,
  tasks: {
    verify: { kind: "make_delegate", target: "verify" },
    lint: { kind: "nx", target: "root:lint" },
  },
};

test("validateManifest accepts Nx and Make routes", () => {
  assert.equal(validateManifest(VALID_MANIFEST), VALID_MANIFEST);
});

test("validateManifest fails closed on malformed route data", () => {
  assert.throws(
    () => validateManifest({ schema_version: 2, tasks: {} }),
    ManifestError,
  );
  assert.throws(
    () =>
      validateManifest({
        schema_version: 1,
        tasks: { lint: { kind: "shell", target: "echo unsafe" } },
      }),
    ManifestError,
  );
  assert.throws(
    () =>
      validateManifest({
        schema_version: 1,
        tasks: { lint: { kind: "nx", target: "invalid" } },
      }),
    ManifestError,
  );
  assert.throws(
    () =>
      validateManifest({
        schema_version: 1,
        tasks: { lint: { kind: "make_delegate", target: "-f" } },
      }),
    ManifestError,
  );
});

test("loadManifest reports invalid JSON", async () => {
  await assert.rejects(
    loadManifest("ignored", { readFileImpl: async () => "{" }),
    /cannot parse task manifest/,
  );
});

test("repository manifest exposes the Phase B task set", async () => {
  const manifest = await loadManifest(new URL("../tasks.json", import.meta.url));
  assert.equal(Object.keys(manifest.tasks).length, 20);
  assert.deepEqual(manifest.tasks["check-conflict-markers"], {
    kind: "nx",
    target: "fabric-task-runner:check-conflict-markers",
  });
  assert.deepEqual(manifest.tasks.verify, {
    kind: "make_delegate",
    target: "verify",
  });
});

test("formatTaskList is stable and sorted", () => {
  assert.equal(
    formatTaskList(VALID_MANIFEST),
    [
      "TASK\tROUTE\tTARGET",
      "lint\tnx\troot:lint",
      "verify\tmake_delegate\tverify",
      "",
    ].join("\n"),
  );
});
