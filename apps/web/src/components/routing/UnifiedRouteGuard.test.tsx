import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { setAuthProvider } from "@/test/utils/withAuthProvider";

const mockUserTierStore = vi.hoisted(() => ({
  canAccessRoute: vi.fn(() => true),
  isRehydrated: true,
}));
const mockUseParams = vi.fn(() => ({ tenantSlug: "tenant-a", accountId: "acc-1" }));
const mockUseMatches = vi.fn(() => [{ handle: { accessPolicy: { requiresAuth: true, fallbackRoute: "/home", tenantScoped: true, accountScoped: true, requiredEntitlements: ["feature.a"] } } }]);
const mockClerkAuth = {
  isLoaded: true,
  isSignedIn: true,
};

vi.mock("react-router-dom", () => ({
  Navigate: ({ to }: { to: string }) => <div>redirect:{to}</div>,
  useLocation: () => ({ pathname: "/t/tenant-a/a/acc-1", search: "" }),
  useParams: () => mockUseParams(),
  useMatches: () => mockUseMatches(),
}));
vi.mock("@clerk/react", () => ({ useAuth: () => mockClerkAuth }));
vi.mock("@/hooks/useTenantMembership", () => ({ useTenantMembership: () => ({ isMemberOfTenant: true, isLoading: false }) }));
vi.mock("@/hooks/useAccountAccess", () => ({ useAccountAccess: () => ({ hasAccountAccess: false, isLoading: false, isError: false }) }));
vi.mock("@/hooks/useUserPermissions", () => ({ useUserPermissions: () => ({ hasPermissions: true, isLoading: false }) }));
vi.mock("@/hooks/useFeatureFlags", () => ({ useFeatureFlags: () => ({ flagsEnabled: true, isLoading: false }) }));
vi.mock("@/hooks/useEntitlements", () => ({ useEntitlements: () => ({ entitlementsMet: false, isLoading: false, isError: false }) }));
vi.mock("@/stores", () => ({ useUserTierStore: () => mockUserTierStore }));

import { UnifiedRouteGuard } from "./UnifiedRouteGuard";
import { AuthContext } from "@/contexts/AuthContext";

function renderGuard() {
  return render(
    <AuthContext.Provider
      value={{
        isAuthenticated: true,
        isLoading: false,
        user: null,
        currentTenantSlug: "tenant-a",
        accessToken: null,
        initiateLogin: vi.fn(),
        handleCallback: vi.fn(async () => true),
        logout: vi.fn(),
        refreshToken: vi.fn(async () => true),
      }}
    >
      <UnifiedRouteGuard><div>protected</div></UnifiedRouteGuard>
    </AuthContext.Provider>
  );
}

describe("UnifiedRouteGuard deny behavior", () => {
  afterEach(() => {
    setAuthProvider("legacy");
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = true;
    mockUserTierStore.canAccessRoute.mockReturnValue(true);
    mockUserTierStore.isRehydrated = true;
    mockUseMatches.mockReturnValue([{ handle: { accessPolicy: { requiresAuth: true, fallbackRoute: "/home", tenantScoped: true, accountScoped: true, requiredEntitlements: ["feature.a"] } } }]);
  });

  it("redirects when account acl denies", () => {
    renderGuard();
    expect(screen.getByText("redirect:/t/tenant-a/accounts")).toBeInTheDocument();
  });

  it("waits for tier-store rehydration before evaluating protected route access", () => {
    mockUserTierStore.isRehydrated = false;
    mockUserTierStore.canAccessRoute.mockReturnValue(false);
    mockUseMatches.mockReturnValue([{ handle: { accessPolicy: { requiresAuth: true, fallbackRoute: "/home", requiredTier: "admin" } } }]);

    renderGuard();

    expect(screen.getByText("Verifying access...")).toBeInTheDocument();
    expect(screen.queryByText("redirect:/home")).not.toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });

  it("uses Clerk signed-in state in Clerk mode instead of stale legacy-compatible context", () => {
    setAuthProvider("clerk");
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = true;
    mockUseMatches.mockReturnValue([{ handle: { accessPolicy: { requiresAuth: true, fallbackRoute: "/home", tenantScoped: false } } }]);

    render(
      <AuthContext.Provider
        value={{
          isAuthenticated: false,
          isLoading: false,
          user: null,
          currentTenantSlug: null,
          accessToken: null,
          initiateLogin: vi.fn(),
          handleCallback: vi.fn(async () => true),
          logout: vi.fn(),
          refreshToken: vi.fn(async () => true),
        }}
      >
        <UnifiedRouteGuard><div>protected</div></UnifiedRouteGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByText("protected")).toBeInTheDocument();
    expect(screen.queryByText("redirect:/sign-in")).not.toBeInTheDocument();
  });

  it("fails closed for guarded routes without access policy metadata", () => {
    mockUseMatches.mockReturnValue([{ handle: {} }]);

    render(
      <AuthContext.Provider
        value={{
          isAuthenticated: false,
          isLoading: false,
          user: null,
          currentTenantSlug: null,
          accessToken: null,
          initiateLogin: vi.fn(),
          handleCallback: vi.fn(async () => true),
          logout: vi.fn(),
          refreshToken: vi.fn(async () => true),
        }}
      >
        <UnifiedRouteGuard><div>protected</div></UnifiedRouteGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByText("redirect:/sign-in")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });
});
