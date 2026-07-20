import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { createWrapper } from "@/test-utils";
import { useTenantMembershipClerk, useTenantMembershipLegacy } from "./useTenantMembership";
import { useOrganization } from "@clerk/react";
import { useAuthContext } from "@/contexts/AuthContext";

vi.mock("@clerk/react", () => ({ useOrganization: vi.fn() }));
vi.mock("@/contexts/AuthContext", () => ({ useAuthContext: vi.fn() }));

const mockUseOrganization = vi.mocked(useOrganization);
const mockUseAuthContext = vi.mocked(useAuthContext);

function renderTenantMembershipLegacy(tenantSlug: string | undefined) {
  return renderHook(() => useTenantMembershipLegacy(tenantSlug), {
    wrapper: createWrapper(),
  });
}

function renderTenantMembershipClerk(tenantSlug: string | undefined) {
  return renderHook(() => useTenantMembershipClerk(tenantSlug), {
    wrapper: createWrapper(),
  });
}

describe("useTenantMembership behavior invariants", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuthContext.mockReturnValue({ user: null, isLoading: false } as never);
    mockUseOrganization.mockReturnValue({ organization: null, isLoaded: true } as never);
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Allowed behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user with matching legacy tenant slug is confirmed as member", () => {
    mockUseAuthContext.mockReturnValue({
      user: { tenantSlug: "acme" },
      isLoading: false,
    } as never);

    const { result } = renderTenantMembershipLegacy("acme");

    expect(result.current.isMemberOfTenant).toBe(true);
    expect(result.current.isLoading).toBe(false);
  });

  it("user with matching clerk organization is confirmed as member", () => {
    mockUseOrganization.mockReturnValue({
      organization: { id: "org_1", slug: "acme" },
      isLoaded: true,
    } as never);

    const { result } = renderTenantMembershipClerk("acme");

    expect(result.current.isMemberOfTenant).toBe(true);
    expect(result.current.isLoading).toBe(false);
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Denied behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user with mismatched legacy tenant slug is denied membership", () => {
    mockUseAuthContext.mockReturnValue({
      user: { tenantSlug: "other-tenant" },
      isLoading: false,
    } as never);

    const { result } = renderTenantMembershipLegacy("acme");

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it("user with matching clerk organization id is confirmed when slug is absent", () => {
    mockUseOrganization.mockReturnValue({
      organization: { id: "org_without_slug", slug: null },
      isLoaded: true,
    } as never);

    const { result } = renderTenantMembershipClerk("org_without_slug");

    expect(result.current.isMemberOfTenant).toBe(true);
    expect(result.current.isLoading).toBe(false);
  });

  it("user with mismatched clerk organization is denied membership", () => {
    mockUseOrganization.mockReturnValue({
      organization: { slug: "other-tenant" },
      isLoaded: true,
    } as never);

    const { result } = renderTenantMembershipClerk("acme");

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it("membership is denied when no tenant slug is provided", () => {
    const { result } = renderTenantMembershipLegacy(undefined);

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Failure mode
  // ───────────────────────────────────────────────────────────────────────────
  it("returns loading state while clerk organization is resolving", () => {
    mockUseOrganization.mockReturnValue({
      organization: null,
      isLoaded: false,
    } as never);

    const { result } = renderTenantMembershipClerk("acme");

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(true);
  });

  it("returns loading state while legacy auth user is resolving", () => {
    mockUseAuthContext.mockReturnValue({
      user: null,
      isLoading: true,
    } as never);

    const { result } = renderTenantMembershipLegacy("acme");

    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(true);
  });
});
