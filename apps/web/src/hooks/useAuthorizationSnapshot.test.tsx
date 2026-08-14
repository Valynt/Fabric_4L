import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());
vi.mock("@/api/typedClient", () => ({ apiGet }));
import { useAuthorizationSnapshot } from "./useAuthorizationSnapshot";

const response = (tenantSlug: string, expiresAt: string) => ({
  data: {
    tenantId: `id-${tenantSlug}`,
    tenantSlug,
    role: "org:custom",
    expiresAt,
    permissions: ["account:read"],
    entitlements: ["reports"],
    tenantMember: true,
    accountIds: ["account-1"],
  },
});

function wrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe("useAuthorizationSnapshot", () => {
  afterEach(() => {
    vi.useRealTimers();
    apiGet.mockReset();
  });

  it("loses grants at expiry and attempts only one failed refresh", async () => {
    const expiresAt = new Date(Date.now() + 100).toISOString();
    apiGet
      .mockResolvedValueOnce(response("tenant-a", expiresAt))
      .mockRejectedValue(new Error("offline"));
    const hook = renderHook(() => useAuthorizationSnapshot("tenant-a"), {
      wrapper: wrapper(),
    });
    await waitFor(() => expect(hook.result.current.status).toBe("verified"));
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 130));
    });
    await waitFor(() => expect(hook.result.current.status).toBe("expired"));
    expect(hook.result.current.permissions).toEqual([]);
    expect(apiGet).toHaveBeenCalledTimes(2);
  });

  it("treats initial transport failure as denied", async () => {
    apiGet.mockRejectedValue(new Error("offline"));
    const hook = renderHook(() => useAuthorizationSnapshot("tenant-a"), {
      wrapper: wrapper(),
    });
    await waitFor(() => expect(hook.result.current.status).toBe("denied"));
  });

  it("does not reuse old grants when the tenant changes", async () => {
    apiGet.mockImplementation((_layer: string, path: string) =>
      Promise.resolve(
        response(
          path.includes("tenant-b") ? "tenant-b" : "tenant-a",
          new Date(Date.now() + 60_000).toISOString()
        )
      )
    );
    const hook = renderHook(({ tenant }) => useAuthorizationSnapshot(tenant), {
      initialProps: { tenant: "tenant-a" },
      wrapper: wrapper(),
    });
    await waitFor(() => expect(hook.result.current.status).toBe("verified"));
    hook.rerender({ tenant: "tenant-b" });
    expect(hook.result.current.status).toBe("loading");
    expect(hook.result.current.permissions).toEqual([]);
    await waitFor(() => expect(hook.result.current.status).toBe("verified"));
  });
});
