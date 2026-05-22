import { describe, expect, it } from "vitest";
import { resolveCapabilityDecision } from "./access";

describe("resolveCapabilityDecision drift handling", () => {
  it("uses backend deny when local role fallback allows", () => {
    const decision = resolveCapabilityDecision("tenant_admin", "team", {
      team: { allowed: false, reasons: ["feature_disabled"], source: "server" },
    });

    expect(decision.allowed).toBe(false);
    expect(decision.reasons).toEqual(["feature_disabled"]);
    expect(decision.source).toBe("server");
  });

  it("uses backend allow when local role fallback denies", () => {
    const decision = resolveCapabilityDecision("viewer", "team", {
      team: { allowed: true, reasons: [], source: "server" },
    });

    expect(decision.allowed).toBe(true);
    expect(decision.reasons).toEqual([]);
    expect(decision.source).toBe("server");
  });
});
