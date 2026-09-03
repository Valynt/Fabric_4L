import assert from "node:assert/strict";
import test from "node:test";

import {
  DelegationError,
  MAX_DELEGATION_DEPTH,
  UsageError,
  extendDelegationStack,
  parseCliArgs,
  parseDelegationStack,
} from "../lib/dispatch.mjs";

test("parseCliArgs accepts canonical task forwarding", () => {
  assert.deepEqual(
    parseCliArgs([
      "web:typecheck",
      "--from",
      "make:verify",
      "--",
      "--configuration=ci",
      "a value",
    ]),
    {
      action: "run",
      task: "web:typecheck",
      caller: "make:verify",
      forwardedArgs: ["--configuration=ci", "a value"],
    },
  );
});

test("parseCliArgs accepts the delimiter preserved by pnpm 10", () => {
  assert.deepEqual(parseCliArgs(["--", "list"]), { action: "list" });
  assert.deepEqual(parseCliArgs(["--", "lint", "--", "--fix"]), {
    action: "run",
    task: "lint",
    caller: null,
    forwardedArgs: ["--fix"],
  });
});

test("parseCliArgs rejects unknown options and undelimited arguments", () => {
  assert.throws(() => parseCliArgs(["lint", "--watch"]), UsageError);
  assert.throws(() => parseCliArgs(["lint", "extra"]), UsageError);
  assert.throws(() => parseCliArgs(["list", "--json"]), UsageError);
});

test("parseCliArgs rejects invalid task and caller tokens", () => {
  assert.throws(() => parseCliArgs(["../verify"]), UsageError);
  assert.throws(() => parseCliArgs(["-verify"]), UsageError);
  assert.throws(
    () => parseCliArgs(["verify", "--from", "make:../../verify"]),
    UsageError,
  );
  assert.throws(
    () => parseCliArgs(["verify", "--from", "nx:verify"]),
    UsageError,
  );
});

test("parseDelegationStack rejects malformed and non-array input", () => {
  assert.throws(() => parseDelegationStack("not-json"), DelegationError);
  assert.throws(() => parseDelegationStack("{}"), DelegationError);
  assert.throws(
    () => parseDelegationStack(JSON.stringify(["other:verify"])),
    DelegationError,
  );
});

test("parseDelegationStack rejects duplicate entries", () => {
  const raw = JSON.stringify(["fabric:verify", "fabric:verify"]);
  assert.throws(() => parseDelegationStack(raw), /duplicate fabric:verify/);
});

test("delegation stack rejects cycles and excessive depth", () => {
  assert.throws(
    () => extendDelegationStack(["fabric:verify"], "verify"),
    /repeat fabric:verify/,
  );

  const fullStack = Array.from(
    { length: MAX_DELEGATION_DEPTH },
    (_, index) => `fabric:task-${index}`,
  );
  assert.throws(
    () => extendDelegationStack(fullStack, "one-more"),
    /exceed depth 16/,
  );
});
