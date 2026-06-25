/**
 * Tests for the canonical Clerk org → Fabric tenant resolution hook.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

import { setupClerkSignedIn, resetClerkMocks, getClerkMocks } from "@/test/utils/clerkTestHelpers";

vi.mock("@clerk/react", () => ({
  useAuth: vi.fn(),
  useOrganization: vi.fn(),
}));

const { useAuth: mockUseAuth, useOrganization: mockUseOrganization } = getClerkMocks();

const mockGetToken = vi.fn<(template?: string) => Promise<string | null>>(async () => "clerk-token");

vi.mock("@/api/typedClient", () => ({
  apiGet: (...args: unknown[]) => mockApiGet(...args),
}));

const mockApiGet = vi.fn();

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

// Import after mocks.
import { useResolvedTenant } from "./useResolvedTenant";

describe("useResolvedTenant", () => {
  beforeEach(() => {
    resetClerkMocks();
    mockApiGet.mockReset();
    mockGetToken.mockReset();
    mockGetToken.mockResolvedValue("clerk-token");
    setupClerkSignedIn("org_1");
    mockUseAuth.mockReturnValue({
      isLoaded: true,
      isSignedIn: true,
      getToken: mockGetToken,
    } as unknown as ReturnType<typeof mockUseAuth>);
    mockUseOrganization.mockReturnValue({
      isLoaded: true,
      organization: { id: "org_1" },
    } as unknown as ReturnType<typeof mockUseOrganization>);
  });

  it("returns resolved tenant when backend mapping succeeds", async () => {
    mockApiGet.mockResolvedValue({
      data: {
        fabric_tenant_id: "ten_1",
        tenant_slug: "acme",
        clerk_org_id: "org_1",
        status: "active",
        roles: ["admin"],
        permissions: ["tenant:read"],
      },
    });

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.tenant).toEqual({
      fabricTenantId: "ten_1",
      tenantSlug: "acme",
      clerkOrgId: "org_1",
      status: "active",
      roles: ["admin"],
      permissions: ["tenant:read"],
    });
    expect(result.current.error).toBeNull();
  });

  it("returns error state on 401", async () => {
    mockApiGet.mockRejectedValue({ response: { status: 401 } });

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.tenant).toBeNull();
    expect(result.current.error).not.toBeNull();
  });

  it("is disabled when not signed in", async () => {
    mockUseAuth.mockReturnValue({
      isLoaded: true,
      isSignedIn: false,
      getToken: mockGetToken,
    });

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.tenant).toBeNull();
    expect(mockApiGet).not.toHaveBeenCalled();
  });

  it("does not send a manual Authorization header", async () => {
    mockApiGet.mockResolvedValue({
      data: {
        fabric_tenant_id: "ten_1",
        tenant_slug: "acme",
        clerk_org_id: "org_1",
        status: "active",
        roles: ["admin"],
        permissions: ["tenant:read"],
      },
    });

    renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mockApiGet).toHaveBeenCalled());
    expect(mockApiGet).toHaveBeenCalledWith("api", "/auth/clerk/tenant");
    expect(mockApiGet).not.toHaveBeenCalledWith(
      "api",
      "/auth/clerk/tenant",
      expect.objectContaining({
        headers: expect.anything(),
      })
    );
  });

  it("does not reuse cached tenant mapping when the active Clerk organization changes", async () => {
    mockApiGet.mockResolvedValueOnce({
      data: {
        fabric_tenant_id: "ten_1",
        tenant_slug: "acme",
        clerk_org_id: "org_1",
        status: "active",
        roles: ["admin"],
        permissions: ["tenant:read"],
      },
    });

    const { result, rerender } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.tenant?.fabricTenantId).toBe("ten_1"));
    expect(mockApiGet).toHaveBeenCalledTimes(1);

    // Simulate a Clerk org switch
    mockApiGet.mockResolvedValueOnce({
      data: {
        fabric_tenant_id: "ten_2",
        tenant_slug: "hooli",
        clerk_org_id: "org_2",
        status: "active",
        roles: ["viewer"],
        permissions: ["tenant:read"],
      },
    });
    mockUseOrganization.mockReturnValue({
      isLoaded: true,
      organization: { id: "org_2" },
    });
    rerender();

    await waitFor(() => expect(result.current.tenant?.fabricTenantId).toBe("ten_2"));
    expect(mockApiGet).toHaveBeenCalledTimes(2);
    expect(result.current.tenant?.clerkOrgId).toBe("org_2");
  });

  it("does not synthesize a manual Authorization header when the token is null", async () => {
    mockGetToken.mockResolvedValue(null);
    mockApiGet.mockResolvedValue({
      data: {
        fabric_tenant_id: "ten_1",
        tenant_slug: "acme",
        clerk_org_id: "org_1",
        status: "active",
        roles: ["admin"],
        permissions: ["tenant:read"],
      },
    });

    renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mockApiGet).toHaveBeenCalled());
    expect(mockApiGet).toHaveBeenCalledWith("api", "/auth/clerk/tenant");
    const calls = mockApiGet.mock.calls;
    for (const call of calls) {
      const maybeConfig = call[2];
      if (maybeConfig && typeof maybeConfig === "object" && "headers" in maybeConfig) {
        const auth = (maybeConfig as { headers?: Record<string, string> }).headers?.Authorization;
        expect(auth).not.toMatch(/^Bearer (null|undefined)$/i);
      }
    }
  });
});
