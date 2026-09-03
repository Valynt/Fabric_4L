#!/usr/bin/env node
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { validateFrontendApiEnv } from "./frontend-api-env.mjs";

const completeEnv = {
  VITE_API_BASE: "/api/v1",
  VITE_L1_PREFIX: "/ingest",
  VITE_L2_PREFIX: "/extract",
  VITE_L2_5_PREFIX: "/signals",
  VITE_L3_PREFIX: "/graph",
  VITE_L4_PREFIX: "/agents",
  VITE_L5_PREFIX: "/truths",
  VITE_L6_PREFIX: "/benchmarks",
};

describe("frontend API production env validation", () => {
  it("accepts complete legacy route prefix configuration", () => {
    const result = validateFrontendApiEnv(completeEnv, { production: true });

    assert.equal(result.ok, true);
    assert.deepEqual(result.errors, []);
  });

  it("accepts canonical route prefix aliases", () => {
    const result = validateFrontendApiEnv(
      {
        VITE_API_VERSION_PREFIX: "/api/v1",
        VITE_LAYER1_ROUTE_PREFIX: "/ingest",
        VITE_LAYER2_ROUTE_PREFIX: "/extract",
        VITE_LAYER2_5_ROUTE_PREFIX: "/signals",
        VITE_LAYER3_ROUTE_PREFIX: "/graph",
        VITE_LAYER4_ROUTE_PREFIX: "/agents",
        VITE_LAYER5_ROUTE_PREFIX: "/truths",
        VITE_LAYER6_ROUTE_PREFIX: "/benchmarks",
      },
      { production: true }
    );

    assert.equal(result.ok, true);
  });

  it("does not require production-only API config while running dev or test tooling", () => {
    const result = validateFrontendApiEnv({}, { production: false });

    assert.equal(result.ok, true);
  });

  it("fails production validation when any API prefix is missing", () => {
    const { VITE_L4_PREFIX: _missing, ...env } = completeEnv;
    const result = validateFrontendApiEnv(env, {
      production: true,
      source: "test build",
    });

    assert.equal(result.ok, false);
    assert.match(
      result.message,
      /test build is missing required production API environment variables/
    );
    assert.match(result.message, /Layer 4 route prefix/);
    assert.match(result.message, /VITE_LAYER4_ROUTE_PREFIX, VITE_L4_PREFIX/);
  });

  it("rejects production API prefixes that cannot be routed through the gateway", () => {
    const result = validateFrontendApiEnv(
      { ...completeEnv, VITE_API_BASE: "https://api.example.com/api/v1" },
      { production: true }
    );

    assert.equal(result.ok, false);
    assert.match(
      result.message,
      /gateway API version prefix must start with \/;/
    );
  });
});
