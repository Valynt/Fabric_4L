import { describe, it, expect } from "vitest";
import { getRouteTier, matchRouteTier } from "./userTierStore";

describe("matchRouteTier", () => {
  it("returns the tier for an exact route", () => {
    expect(matchRouteTier("/home")).toBe("standard");
    expect(matchRouteTier("/admin")).toBe("admin");
  });

  it("returns the tier for the longest matching parent prefix", () => {
    expect(matchRouteTier("/admin/content/approvals/extra")).toBe("admin");
  });

  it("returns undefined for unrecognized routes", () => {
    expect(matchRouteTier("/not-a-route")).toBeUndefined();
  });
});

describe("getRouteTier", () => {
  it("matches exact routes", () => {
    expect(getRouteTier("/home")).toBe("standard");
    expect(getRouteTier("/admin")).toBe("admin");
  });

  it("normalizes tenant-scoped paths", () => {
    expect(getRouteTier("/t/acme/accounts/acc-123/intelligence")).toBe("standard");
    expect(getRouteTier("/t/acme/accounts/acc-123/studio")).toBe("advanced");
  });

  it("falls back to parent prefix matching for unknown sub-routes", () => {
    expect(getRouteTier("/admin/content/approvals/extra")).toBe("admin");
  });

  it("returns unknown for completely unrecognized routes", () => {
    expect(getRouteTier("/not-a-route")).toBe("unknown");
  });
});
