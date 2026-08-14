import { describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";

const authorization = vi.hoisted(() => ({
  status: "verified",
  snapshot: { entitlements: ["feature.a"] },
  hasEveryEntitlement: vi.fn((required: string[]) =>
    required.every(value => value === "feature.a")
  ),
}));
vi.mock("@/auth/AuthorizationProvider", () => ({
  useAuthorizationSnapshot: () => authorization,
}));
import { useEntitlements } from "./useEntitlements";

describe("useEntitlements compatibility selector", () => {
  it("selects grants only from the authorization snapshot provider", () => {
    const { result } = renderHook(() => useEntitlements(["feature.a"]));
    expect(result.current.entitlementsMet).toBe(true);
    expect(authorization.hasEveryEntitlement).toHaveBeenCalledWith([
      "feature.a",
    ]);
  });

  it("fails closed when the provider is denied", () => {
    authorization.status = "denied";
    authorization.hasEveryEntitlement.mockReturnValueOnce(false);
    const { result } = renderHook(() => useEntitlements(["feature.a"]));
    expect(result.current.entitlementsMet).toBe(false);
    expect(result.current.isError).toBe(true);
  });
});
