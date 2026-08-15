import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const authorization = vi.hoisted(() => ({
  status: "verified" as "verified" | "loading" | "denied" | "expired",
  granted: new Set<string>(),
  hasEveryEntitlement: (required: string[]) =>
    authorization.status === "verified" &&
    required.every(value => authorization.granted.has(value)),
}));

vi.mock("@/auth/AuthorizationProvider", () => ({
  useAuthorizationSnapshot: () => authorization,
}));

import { useEntitlements } from "./useEntitlements";

describe("useEntitlements behavior invariants", () => {
  beforeEach(() => {
    authorization.status = "verified";
    authorization.granted = new Set(["feature.a", "feature.b"]);
  });

  it("allows a verified snapshot with all required entitlements", () => {
    expect(
      renderHook(() => useEntitlements(["feature.a", "feature.b"])).result
        .current.entitlementsMet
    ).toBe(true);
  });

  it("allows a verified snapshot with one required entitlement", () => {
    expect(
      renderHook(() => useEntitlements(["feature.a"])).result.current
        .entitlementsMet
    ).toBe(true);
  });

  it("denies a verified snapshot missing a required entitlement", () => {
    expect(
      renderHook(() => useEntitlements(["missing"])).result.current
        .entitlementsMet
    ).toBe(false);
  });

  it("denies while authorization is loading", () => {
    authorization.status = "loading";
    expect(
      renderHook(() => useEntitlements(["feature.a"])).result.current
        .entitlementsMet
    ).toBe(false);
  });

  it("denies when snapshot resolution fails", () => {
    authorization.status = "denied";
    const result = renderHook(() => useEntitlements(["feature.a"])).result
      .current;
    expect(result.entitlementsMet).toBe(false);
    expect(result.isError).toBe(true);
  });

  it("requires a verified snapshot even when no entitlements are requested", () => {
    authorization.status = "expired";
    expect(
      renderHook(() => useEntitlements([])).result.current.entitlementsMet
    ).toBe(false);
  });
});
