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
import {
  useTenantMembershipClerk,
  useTenantMembershipLegacy,
} from "./useTenantMembership";

describe("snapshot tenant membership", () => {
  it.each([useTenantMembershipClerk, useTenantMembershipLegacy])(
    "allows only verified backend membership",
    hook => {
      resolution.current = {
        status: "verified",
        permissions: [],
        entitlements: [],
        snapshot: {
          tenantMember: true,
          permissions: [],
          entitlements: [],
          accountIds: [],
        },
      };
      expect(
        renderHook(() => hook("tenant-a")).result.current.isMemberOfTenant
      ).toBe(true);
      resolution.current = {
        status: "denied",
        permissions: [],
        entitlements: [],
      };
      expect(
        renderHook(() => hook("tenant-a")).result.current.isMemberOfTenant
      ).toBe(false);
    }
  );
});
