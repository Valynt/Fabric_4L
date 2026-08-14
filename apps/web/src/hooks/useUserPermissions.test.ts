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
import { useUserPermissions } from "./useUserPermissions";

describe("useUserPermissions", () => {
  it("derives permission decisions only from a verified snapshot", () => {
    resolution.current = {
      status: "verified",
      permissions: ["read"],
      entitlements: [],
      snapshot: {
        tenantId: "t",
        tenantSlug: "tenant",
        role: "custom",
        expiresAt: new Date(Date.now() + 1000).toISOString(),
        permissions: ["read"],
        entitlements: [],
        tenantMember: true,
        accountIds: [],
      },
    };
    expect(
      renderHook(() => useUserPermissions(["read"], "tenant")).result.current
        .hasPermissions
    ).toBe(true);
    expect(
      renderHook(() => useUserPermissions(["write"], "tenant")).result.current
        .hasPermissions
    ).toBe(false);
    resolution.current = {
      status: "expired",
      permissions: [],
      entitlements: [],
    };
    expect(
      renderHook(() => useUserPermissions([], "tenant")).result.current
        .hasPermissions
    ).toBe(false);
  });
});
