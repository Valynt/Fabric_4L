import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import {
  useTenantMembershipClerk,
  useTenantMembershipLegacy,
} from "./useTenantMembership";

const authorization = vi.hoisted(() => ({
  status: "verified" as "verified" | "loading" | "denied",
  hasTenantMembership: vi.fn<(tenantSlug?: string) => boolean>(),
}));

vi.mock("@/auth/AuthorizationProvider", () => ({
  useAuthorizationSnapshot: () => authorization,
}));

describe("useTenantMembership snapshot selectors", () => {
  beforeEach(() => {
    authorization.status = "verified";
    authorization.hasTenantMembership.mockReset();
    authorization.hasTenantMembership.mockReturnValue(false);
  });

  it.each([useTenantMembershipClerk, useTenantMembershipLegacy])(
    "returns the authoritative snapshot membership decision",
    hook => {
      authorization.hasTenantMembership.mockReturnValue(true);

      const { result } = renderHook(() => hook("acme"));

      expect(authorization.hasTenantMembership).toHaveBeenCalledWith("acme");
      expect(result.current).toEqual({
        isMemberOfTenant: true,
        isLoading: false,
      });
    }
  );

  it("reports loading only while the canonical snapshot is loading", () => {
    authorization.status = "loading";

    const { result } = renderHook(() => useTenantMembershipClerk("acme"));

    expect(result.current).toEqual({
      isMemberOfTenant: false,
      isLoading: true,
    });
  });

  it("fails closed when the snapshot denies membership", () => {
    authorization.status = "denied";

    const { result } = renderHook(() => useTenantMembershipLegacy("acme"));

    expect(result.current).toEqual({
      isMemberOfTenant: false,
      isLoading: false,
    });
  });
});
