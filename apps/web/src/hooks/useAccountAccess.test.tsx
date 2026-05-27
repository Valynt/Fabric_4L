import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { apiGet } from "@/api/typedClient";
import { useAccountAccess } from "./useAccountAccess";

vi.mock("@/api/typedClient", () => ({ apiGet: vi.fn() }));

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{children}</QueryClientProvider>
);

describe("useAccountAccess", () => {
  beforeEach(() => vi.clearAllMocks());

  it("denies by default on service error", async () => {
    vi.mocked(apiGet).mockRejectedValueOnce(new Error("down"));
    const { result } = renderHook(() => useAccountAccess("acc-1", "tenant-a"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hasAccountAccess).toBe(false);
    expect(result.current.isError).toBe(true);
  });

  it("requires all acl checks to pass", async () => {
    vi.mocked(apiGet).mockResolvedValueOnce({ data: { account_exists: true, tenant_bound: true, principal_allowed: false, reason: "acl_denied" } } as never);
    const { result } = renderHook(() => useAccountAccess("acc-1", "tenant-a"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hasAccountAccess).toBe(false);
    expect(result.current.denyReason).toBe("acl_denied");
  });
});
