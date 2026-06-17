import { afterEach, describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { setAuthProvider } from "@/test/utils/withAuthProvider";

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
vi.mock("@/stores", () => ({ useUserTierStore: () => ({ canAccessRoute: () => true }) }));

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
    mockUseMatches.mockReturnValue([{ handle: { accessPolicy: { requiresAuth: true, fallbackRoute: "/home", tenantScoped: true, accountScoped: true, requiredEntitlements: ["feature.a"] } } }]);
  });

  it("redirects when account acl denies", () => {
    renderGuard();
    expect(screen.getByText("redirect:/t/tenant-a/accounts")).toBeInTheDocument();
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
});
