import { describe, expect, it, vi } from "vitest";
import { resolveCapabilityDecision, getCapabilitiesForRole, fetchEffectivePermissions, describeDenialReason, buildFallbackDecision } from "./access";
import { apiClient } from "@/api/client";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

describe("getCapabilitiesForRole", () => {
  it("returns capabilities for a known role", () => {
    const caps = getCapabilitiesForRole("super_admin");
    expect(caps.has("personal")).toBe(true);
    expect(caps.has("governance")).toBe(true);
    expect(caps.has("super_admin")).toBe(true);
    expect(caps.size).toBe(6);
  });

  it("normalizes role casing and whitespace", () => {
    const caps = getCapabilitiesForRole(" SUPER_ADMIN ");
    expect(caps.has("super_admin")).toBe(true);
    expect(caps.size).toBe(6);
  });

  it("returns fallback for unknown role", () => {
    const caps = getCapabilitiesForRole("unknown_role");
    expect(caps.has("personal")).toBe(true);
    expect(caps.size).toBe(1);
  });

  it("handles null and undefined by defaulting to user role", () => {
    expect(getCapabilitiesForRole(null).has("personal")).toBe(true);
    expect(getCapabilitiesForRole(undefined).has("personal")).toBe(true);
    expect(getCapabilitiesForRole("").has("personal")).toBe(true);
  });
});

describe("fetchEffectivePermissions", () => {
  it("fetches capabilities from API", async () => {
    const mockData = {
      capabilities: {
        personal: { allowed: true, reasons: [], source: "server" },
      },
    };
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockData } as any);

    const result = await fetchEffectivePermissions();

    expect(apiClient.get).toHaveBeenCalledWith("l4", "/me/permissions");
    expect(result).toEqual(mockData);
  });
});

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

describe("buildFallbackDecision", () => {
  it("allows when role has capability", () => {
    const decision = buildFallbackDecision("super_admin", "team");
    expect(decision).toEqual({ allowed: true, reasons: [], source: "fallback" });
  });

  it("denies when role lacks capability", () => {
    const decision = buildFallbackDecision("viewer", "team");
    expect(decision).toEqual({ allowed: false, reasons: ["missing_role"], source: "fallback" });
  });
});

describe("describeDenialReason", () => {
  it("returns correct description for each reason", () => {
    expect(describeDenialReason("missing_role")).toBe("Missing required role");
    expect(describeDenialReason("scope_mismatch")).toBe("Tenant/workspace scope mismatch");
    expect(describeDenialReason("feature_disabled")).toBe("Feature flag is disabled for this tenant");
    expect(describeDenialReason("super_admin_only")).toBe("This path is restricted to super admins");
  });
});
