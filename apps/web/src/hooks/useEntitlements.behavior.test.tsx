import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { apiGet } from "@/api/typedClient";
import { useEntitlements } from "./useEntitlements";

vi.mock("@/api/typedClient", () => ({ apiGet: vi.fn() }));

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    {children}
  </QueryClientProvider>
);

describe("useEntitlements behavior invariants", () => {
  beforeEach(() => vi.clearAllMocks());

  // ───────────────────────────────────────────────────────────────────────────
  // Allowed behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user with all required entitlements is allowed access", async () => {
    vi.mocked(apiGet).mockResolvedValueOnce({
      data: {
        decisions: {
          "feature.a": { allowed: true, reason: "ok" },
          "feature.b": { allowed: true, reason: "ok" },
        },
      },
    } as never);

    const { result } = renderHook(() => useEntitlements(["feature.a", "feature.b"]), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.entitlementsMet).toBe(true);
    expect(result.current.isError).toBe(false);
  });

  it("user with single required entitlement is allowed access", async () => {
    vi.mocked(apiGet).mockResolvedValueOnce({
      data: {
        decisions: {
          "feature.a": { allowed: true, reason: "ok" },
        },
      },
    } as never);

    const { result } = renderHook(() => useEntitlements(["feature.a"]), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.entitlementsMet).toBe(true);
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Denied behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user with missing required entitlement is denied access", async () => {
    vi.mocked(apiGet).mockResolvedValueOnce({
      data: {
        decisions: {
          "feature.a": { allowed: true, reason: "ok" },
        },
      },
    } as never);

    const { result } = renderHook(() => useEntitlements(["feature.a", "feature.b"]), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.entitlementsMet).toBe(false);
  });

  it("user with explicitly denied entitlement is denied access", async () => {
    vi.mocked(apiGet).mockResolvedValueOnce({
      data: {
        decisions: {
          "feature.a": { allowed: false, reason: "plan_limit" },
        },
      },
    } as never);

    const { result } = renderHook(() => useEntitlements(["feature.a"]), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.entitlementsMet).toBe(false);
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Failure mode
  // ───────────────────────────────────────────────────────────────────────────
  it("network error fails closed with denied access", async () => {
    vi.mocked(apiGet).mockRejectedValueOnce(new Error("network failure"));

    const { result } = renderHook(() => useEntitlements(["feature.a"]), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.entitlementsMet).toBe(false);
    expect(result.current.isError).toBe(true);
  });

  it("empty entitlement list defaults to allowed without API call", async () => {
    const { result } = renderHook(() => useEntitlements([]), { wrapper });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.entitlementsMet).toBe(true);
    expect(apiGet).not.toHaveBeenCalled();
  });
});
