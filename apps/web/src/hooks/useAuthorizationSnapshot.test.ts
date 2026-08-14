import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { parseAuthorizationSnapshot } from "./useAuthorizationSnapshot";

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  auth: {
    isAuthenticated: true,
    isLoading: false,
    currentTenantSlug: "tenant-a",
  },
}));

vi.mock("@/api/typedClient", () => ({ apiGet: mocks.apiGet }));
vi.mock("@/contexts/AuthContext", () => ({
  useAuthContext: () => mocks.auth,
}));

const valid = {
  tenantId: "tenant-id",
  tenantSlug: "tenant-a",
  role: "org:member",
  expiresAt: "2099-01-01T00:00:00.000Z",
  permissions: ["account:read"],
  entitlements: ["feature.a"],
  tenantMember: true,
  accountIds: ["acc-1"],
};

describe("parseAuthorizationSnapshot", () => {
  it("exposes grants only for a current tenant-matched verified snapshot", () => {
    expect(parseAuthorizationSnapshot(valid, "tenant-a").status).toBe(
      "verified"
    );
  });

  it.each([
    "org:owner",
    "org:guest",
    "org:value_engineer",
    "org:sales_leader",
    "org:account_executive",
    "org:customer_success",
    "org:viewer",
    "org:auditor",
  ])("accepts configured Clerk organization role %s", (role) => {
    expect(parseAuthorizationSnapshot({ ...valid, role }, "tenant-a").status).toBe(
      "verified"
    );
  });

  it.each([
    ["missing snapshot", undefined, "denied"],
    ["malformed claims", { ...valid, permissions: "account:read" }, "denied"],
    ["tenant mismatch", valid, "denied", "tenant-b"],
    [
      "expired snapshot",
      { ...valid, expiresAt: "2020-01-01T00:00:00.000Z" },
      "expired",
    ],
  ])("fails closed for %s", (_name, snapshot, status, tenant = "tenant-a") => {
    const result = parseAuthorizationSnapshot(snapshot, tenant);
    expect(result.status).toBe(status);
    expect(result.permissions).toEqual([]);
    expect(result.entitlements).toEqual([]);
  });
});

describe("useAuthorizationSnapshot", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("stops authorizing when the verified snapshot reaches its expiry", async () => {
    vi.useFakeTimers();
    const expiresAt = new Date(Date.now() + 1_000).toISOString();
    mocks.apiGet.mockResolvedValue({
      data: { snapshot: { ...valid, expiresAt } },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children);
    const { useAuthorizationSnapshot } = await import(
      "./useAuthorizationSnapshot"
    );
    const { result } = renderHook(() => useAuthorizationSnapshot("tenant-a"), {
      wrapper,
    });

    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.status).toBe("verified");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_001);
    });

    expect(result.current.status).not.toBe("verified");
    expect(result.current.permissions).toEqual([]);
  });
});
