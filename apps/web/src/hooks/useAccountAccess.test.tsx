import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAccountAccess } from "./useAccountAccess";

const authorization = vi.hoisted(() => ({
  status: "verified" as "verified" | "loading" | "denied" | "expired",
  hasAccountAccess: vi.fn(() => true),
}));

vi.mock("@/auth/AuthorizationProvider", () => ({
  useAuthorizationSnapshot: () => authorization,
}));

describe("useAccountAccess", () => {
  beforeEach(() => {
    authorization.status = "verified";
    authorization.hasAccountAccess.mockReset().mockReturnValue(true);
  });

  it("denies when the verified snapshot resolution fails", () => {
    authorization.status = "denied";
    authorization.hasAccountAccess.mockReturnValue(false);
    const { result } = renderHook(() => useAccountAccess("acc-1", "tenant-a"));
    expect(result.current.hasAccountAccess).toBe(false);
    expect(result.current.isError).toBe(true);
  });

  it("delegates exact account access to the verified snapshot", () => {
    authorization.hasAccountAccess.mockReturnValue(false);
    const { result } = renderHook(() => useAccountAccess("acc-1", "tenant-a"));
    expect(authorization.hasAccountAccess).toHaveBeenCalledWith("acc-1");
    expect(result.current.hasAccountAccess).toBe(false);
    expect(result.current.isError).toBe(false);
  });
});
