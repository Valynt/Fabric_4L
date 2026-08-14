import type { AuthorizationResolution } from "@/auth/authorizationSnapshot";
import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
const resolution = vi.hoisted(() => ({
  current: {
    status: "denied",
    permissions: [],
    entitlements: [],
  } as AuthorizationResolution,
}));
vi.mock("./useAuthorizationSnapshot", () => ({
  useAuthorizationSnapshot: () => resolution.current,
}));
vi.mock("@/contexts/AuthContext", () => ({
  useAuthContext: () => ({ currentTenantSlug: "tenant-a" }),
}));
import { useEntitlements } from "./useEntitlements";

describe("snapshot entitlements", () => {
  it("requires every entitlement from a verified snapshot", () => {
    resolution.current = {
      status: "verified",
      permissions: [],
      entitlements: ["a"],
      snapshot: {
        tenantMember: true,
        permissions: [],
        entitlements: ["a"],
        accountIds: [],
      },
    };
    expect(
      renderHook(() => useEntitlements(["a"])).result.current.entitlementsMet
    ).toBe(true);
    expect(
      renderHook(() => useEntitlements(["a", "b"])).result.current
        .entitlementsMet
    ).toBe(false);
  });
});
