/**
 * Tests for the canonical Clerk org → Fabric tenant resolution hook.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

const mockGetToken = vi.fn(async () => "clerk-token");
const mockUseAuth = vi.fn(() => ({
  isLoaded: true,
  isSignedIn: true,
  getToken: mockGetToken,
}));
const mockUseOrganization = vi.fn(() => ({
  isLoaded: true,
  organization: { id: "org_1" },
}));

vi.mock("@clerk/react", () => ({
  useAuth: () => mockUseAuth(),
  useOrganization: () => mockUseOrganization(),
}));

vi.mock("@/auth/clerkConfig", () => ({
  isClerkAuthEnabled: () => true,
}));

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
    mockApiGet.mockReset();
    mockGetToken.mockReset();
    mockGetToken.mockResolvedValue("clerk-token");
    mockUseAuth.mockReturnValue({
      isLoaded: true,
      isSignedIn: true,
      getToken: mockGetToken,
    });
    mockUseOrganization.mockReturnValue({
      isLoaded: true,
      organization: { id: "org_1" },
    });
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
});
