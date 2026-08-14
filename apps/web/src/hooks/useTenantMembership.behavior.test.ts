import type { AuthorizationResolution } from "@/auth/authorizationSnapshot";
import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
const resolution = vi.hoisted(() => ({
  current: {
    status: "loading",
    permissions: [],
    entitlements: [],
  } as AuthorizationResolution,
}));
vi.mock("./useAuthorizationSnapshot", () => ({
  useAuthorizationSnapshot: () => resolution.current,
}));
import { useTenantMembershipLegacy } from "./useTenantMembership";

describe("tenant membership fail-closed states", () => {
  it.each(["loading", "denied", "expired"])(
    "does not expose membership for %s",
    status => {
      resolution.current = { status, permissions: [], entitlements: [] };
      const value = renderHook(() => useTenantMembershipLegacy("tenant-a"))
        .result.current;
      expect(value.isMemberOfTenant).toBe(false);
      expect(value.isLoading).toBe(status === "loading");
    }
  );
});
