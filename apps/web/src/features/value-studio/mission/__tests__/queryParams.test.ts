/**
 * Contract tests for the Value Studio URL query-parameter layer (FE-LENS-004,
 * §9 deep links). Parsing must be total: unknown values fall back to defaults,
 * never throw.
 */

import { describe, expect, it } from "vitest";

import { AUDIENCE_LENSES } from "../types";
import { VALUE_STUDIO_FIXTURE_NAMES } from "../fixtures";
import {
  isAudienceLens,
  parseDecisionParam,
  parseFixtureParam,
  parseLensParam,
  VALUE_STUDIO_QUERY_KEYS,
} from "../queryParams";

describe("VALUE_STUDIO_QUERY_KEYS", () => {
  it("exposes the stable query key names", () => {
    expect(VALUE_STUDIO_QUERY_KEYS).toEqual({
      lens: "lens",
      decision: "decision",
      fixture: "fixture",
    });
  });
});

describe("isAudienceLens", () => {
  it("accepts every lens in the canonical lens list", () => {
    for (const lens of AUDIENCE_LENSES) {
      expect(isAudienceLens(lens)).toBe(true);
    }
  });

  it("rejects values outside the canonical lens list", () => {
    expect(isAudienceLens("board")).toBe(false);
    expect(isAudienceLens("")).toBe(false);
  });
});

describe("parseLensParam", () => {
  it("returns the lens for each valid lens value", () => {
    for (const lens of AUDIENCE_LENSES) {
      expect(parseLensParam(lens)).toBe(lens);
    }
  });

  it("falls back to null for an unknown lens", () => {
    expect(parseLensParam("investor")).toBeNull();
  });

  it("falls back to null when the parameter is absent", () => {
    expect(parseLensParam(null)).toBeNull();
  });

  it("falls back to null for an empty value", () => {
    expect(parseLensParam("")).toBeNull();
  });

  it("is case-sensitive (FE-LENS-004 values are lowercase ids)", () => {
    expect(parseLensParam("CFO")).toBeNull();
  });
});

describe("parseFixtureParam", () => {
  it("returns the fixture name for each of the ten named states", () => {
    expect(VALUE_STUDIO_FIXTURE_NAMES).toHaveLength(10);
    for (const name of VALUE_STUDIO_FIXTURE_NAMES) {
      expect(parseFixtureParam(name)).toBe(name);
    }
  });

  it("falls back to null for an unknown fixture name", () => {
    expect(parseFixtureParam("broken")).toBeNull();
  });

  it("falls back to null when the parameter is absent", () => {
    expect(parseFixtureParam(null)).toBeNull();
  });

  it("falls back to null for an empty value", () => {
    expect(parseFixtureParam("")).toBeNull();
  });
});

describe("parseDecisionParam", () => {
  it("passes through a non-empty decision id", () => {
    expect(parseDecisionParam("DISP-01")).toBe("DISP-01");
  });

  it("returns null when the parameter is absent", () => {
    expect(parseDecisionParam(null)).toBeNull();
  });

  it("returns null for an empty value", () => {
    expect(parseDecisionParam("")).toBeNull();
  });
});
