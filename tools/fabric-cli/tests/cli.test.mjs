import assert from "node:assert/strict";
import test from "node:test";

import { main, USAGE } from "../bin/fabric.mjs";

const MANIFEST = {
  schema_version: 1,
  tasks: {
    verify: { kind: "make_delegate", target: "verify" },
  },
};

function outputBuffer() {
  let output = "";
  return {
    stream: { write: (chunk) => (output += chunk) },
    value: () => output,
  };
}

test("list prints manifest tasks without starting a child process", async () => {
  const output = outputBuffer();
  let called = false;
  const exitCode = await main(["list"], {
    manifest: MANIFEST,
    stdout: output.stream,
    runner: async () => {
      called = true;
      return { code: 0 };
    },
  });

  assert.equal(exitCode, 0);
  assert.equal(output.value(), "TASK\tROUTE\tTARGET\nverify\tmake_delegate\tverify\n");
  assert.equal(called, false);
});

test("help prints canonical usage", async () => {
  const output = outputBuffer();
  assert.equal(await main(["--help"], { manifest: MANIFEST, stdout: output.stream }), 0);
  assert.equal(output.value(), USAGE);
});
