/**
 * Unit tests for the edit-decision validation schema (FE-RAIL-006, §9.9).
 * The schema is parameterized by the projection's recommended values; departing
 * from them without a rationale must fail on the `rationale` path.
 */

import { describe, expect, it } from "vitest";

import { buildEditDecisionSchema } from "../components/editDecisionSchema";

const schema = buildEditDecisionSchema(340, 280);

const validBase = {
  workingHours: 340,
  alternativeHours: 280,
  alternativeScope: "Upside scenario only",
  rationale: "",
};

describe("buildEditDecisionSchema", () => {
  it("accepts values identical to the recommendation without a rationale", () => {
    const result = schema.safeParse(validBase);
    expect(result.success).toBe(true);
  });

  it("accepts a departure when a rationale is supplied", () => {
    const result = schema.safeParse({
      ...validBase,
      workingHours: 320,
      rationale: "CFO asked for a conservative target.",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a departure without a rationale on the rationale path", () => {
    const result = schema.safeParse({ ...validBase, workingHours: 320 });
    expect(result.success).toBe(false);
    if (!result.success) {
      const issue = result.error.issues.find((i) => i.path.join(".") === "rationale");
      expect(issue?.message).toBe(
        "A rationale is required when the edit departs from Flo's recommendation.",
      );
    }
  });

  it("treats a whitespace-only rationale as missing (trim before refine)", () => {
    const result = schema.safeParse({ ...validBase, workingHours: 320, rationale: "   " });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(
        result.error.issues.some((i) => i.path.join(".") === "rationale"),
      ).toBe(true);
    }
  });

  it("flags a departure on the alternative target alone", () => {
    const result = schema.safeParse({ ...validBase, alternativeHours: 300 });
    expect(result.success).toBe(false);
  });

  it("rejects a non-integer working target", () => {
    const result = schema.safeParse({ ...validBase, workingHours: 340.5 });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(
        result.error.issues.some(
          (i) => i.message === "Working target must be a whole number of hours.",
        ),
      ).toBe(true);
    }
  });

  it("rejects a non-positive working target", () => {
    expect(schema.safeParse({ ...validBase, workingHours: 0 }).success).toBe(false);
    expect(schema.safeParse({ ...validBase, workingHours: -5 }).success).toBe(false);
  });

  it("rejects an unreasonably large working target", () => {
    const result = schema.safeParse({ ...validBase, workingHours: 100_001 });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(
        result.error.issues.some(
          (i) => i.message === "Working target is unreasonably large.",
        ),
      ).toBe(true);
    }
  });

  it("bounds the scope note and rationale lengths", () => {
    expect(
      schema.safeParse({ ...validBase, alternativeScope: "x".repeat(201) }).success,
    ).toBe(false);
    expect(
      schema.safeParse({ ...validBase, rationale: "x".repeat(2_001) }).success,
    ).toBe(false);
    expect(
      schema.safeParse({ ...validBase, rationale: "x".repeat(2_000) }).success,
    ).toBe(true);
  });
});
