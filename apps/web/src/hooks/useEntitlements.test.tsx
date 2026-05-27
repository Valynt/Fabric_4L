import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { apiGet } from "@/api/typedClient";
import { useEntitlements } from "./useEntitlements";

vi.mock("@/api/typedClient", () => ({ apiGet: vi.fn() }));

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{children}</QueryClientProvider>
);

describe("useEntitlements", () => {
  beforeEach(() => vi.clearAllMocks());

  it("denies by default on network error", async () => {
    vi.mocked(apiGet).mockRejectedValueOnce(new Error("boom"));
    const { result } = renderHook(() => useEntitlements(["feature.a"]), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.entitlementsMet).toBe(false);
    expect(result.current.isError).toBe(true);
  });

  it("denies when a required entitlement is missing or false", async () => {
    vi.mocked(apiGet).mockResolvedValueOnce({ data: { decisions: { "feature.a": { allowed: true, reason: "ok" } } } } as never);
    const { result } = renderHook(() => useEntitlements(["feature.a", "feature.b"]), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.entitlementsMet).toBe(false);
  });
});
