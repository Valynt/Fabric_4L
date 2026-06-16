import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { createWrapper } from "@/test-utils";
import { useOrganization } from "@clerk/react";
import { useAuthContext } from "@/contexts/AuthContext";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";

vi.mock("@clerk/react", () => ({ useOrganization: vi.fn() }));
vi.mock("@/contexts/AuthContext", () => ({ useAuthContext: vi.fn() }));
vi.mock("@/auth/clerkConfig", () => ({ isClerkAuthEnabled: vi.fn() }));

const mockUseOrganization = vi.mocked(useOrganization);
const mockUseAuthContext = vi.mocked(useAuthContext);
const mockClerkEnabled = vi.mocked(isClerkAuthEnabled);

async function renderTenantMembership(tenantSlug: string | undefined) {
  const { useTenantMembership } = await import("./useTenantMembership");
  return renderHook(() => useTenantMembership(tenantSlug), {
    wrapper: createWrapper(),
  });
}

describe("useTenantMembership behavior invariants", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockUseAuthContext.mockReturnValue({ user: null, isLoading: false } as never);
    mockUseOrganization.mockReturnValue({ organization: null, isLoaded: true } as never);
    mockClerkEnabled.mockReturnValue(false);
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Allowed behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user with matching legacy tenant slug is confirmed as member", async () => {
    mockUseAuthContext.mockReturnValue({
      user: { tenantSlug: "acme" },
      isLoading: false,
    } as never);

    const { result } = await renderTenantMembership("acme");

    expect(result.current.isMemberOfTenant).toBe(true);
    expect(result.current.isLoading).toBe(false);
  });

  it("user with matching clerk organization is confirmed as member", async () => {
    mockClerkEnabled.mockReturnValue(true);
    mockUseOrganization.mockReturnValue({
      organization: { slug: "acme" },
      isLoaded: true,
    } as never);

    const { result } = await renderTenantMembership("acme");

    expect(result.current.isMemberOfTenant).toBe(true);
    expect(result.current.isLoading).toBe(false);
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Denied behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user with mismatched legacy tenant slug is denied membership", async () => {
    mockUseAuthContext.mockReturnValue({
      user: { tenantSlug: "other-tenant" },
      isLoading: false,
    } as never);

    const { result } = await renderTenantMembership("acme");

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it("user with mismatched clerk organization is denied membership", async () => {
    mockClerkEnabled.mockReturnValue(true);
    mockUseOrganization.mockReturnValue({
      organization: { slug: "other-tenant" },
      isLoaded: true,
    } as never);

    const { result } = await renderTenantMembership("acme");

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it("membership is denied when no tenant slug is provided", async () => {
    const { result } = await renderTenantMembership(undefined);

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Failure mode
  // ───────────────────────────────────────────────────────────────────────────
  it("returns loading state while clerk organization is resolving", async () => {
    mockClerkEnabled.mockReturnValue(true);
    mockUseOrganization.mockReturnValue({
      organization: null,
      isLoaded: false,
    } as never);

    const { result } = await renderTenantMembership("acme");

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(true);
  });

  it("returns loading state while legacy auth user is resolving", async () => {
    mockUseAuthContext.mockReturnValue({
      user: null,
      isLoading: true,
    } as never);

    const { result } = await renderTenantMembership("acme");

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(true);
  });
});
