import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useTenantMembershipClerk } from "./useTenantMembership";

const authorization = vi.hoisted(() => ({
  status: "verified" as "verified" | "loading" | "denied",
  hasTenantMembership: vi.fn<(tenantSlug?: string) => boolean>(),
}));

vi.mock("@/auth/AuthorizationProvider", () => ({
  useAuthorizationSnapshot: () => authorization,
}));

describe("useTenantMembership critical behavior", () => {
  beforeEach(() => {
    authorization.status = "verified";
    authorization.hasTenantMembership.mockReset();
  });

  it("allows the exact tenant asserted by the verified snapshot", () => {
    authorization.hasTenantMembership.mockImplementation(
      tenantSlug => tenantSlug === "acme"
    );

    const { result } = renderHook(() => useTenantMembershipClerk("acme"));

    expect(result.current.isMemberOfTenant).toBe(true);
    expect(result.current.isLoading).toBe(false);
  });

  it("denies a tenant not asserted by the verified snapshot", () => {
    authorization.hasTenantMembership.mockReturnValue(false);

    const { result } = renderHook(() => useTenantMembershipClerk("hostile"));

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it("fails closed after snapshot resolution is denied", () => {
    authorization.status = "denied";
    authorization.hasTenantMembership.mockReturnValue(false);

    const { result } = renderHook(() => useTenantMembershipClerk("acme"));

    expect(result.current).toEqual({
      isMemberOfTenant: false,
      isLoading: false,
    });
  });
});
