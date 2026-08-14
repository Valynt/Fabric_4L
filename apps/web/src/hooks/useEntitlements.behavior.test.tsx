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

describe("entitlement fail-closed states", () => {
  it.each(["loading", "denied", "expired"])(
    "denies %s snapshot state",
    status => {
      resolution.current = { status, permissions: [], entitlements: [] };
      expect(
        renderHook(() => useEntitlements(["a"])).result.current.entitlementsMet
      ).toBe(false);
    }
  );
});
