import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockUseParams = vi.fn(() => ({ tenantSlug: "tenant-a", accountId: "acc-1" }));
const mockUseMatches = vi.fn(() => [{ handle: { accessPolicy: { requiresAuth: true, fallbackRoute: "/home", tenantScoped: true, accountScoped: true, requiredEntitlements: ["feature.a"] } } }]);

vi.mock("react-router-dom", () => ({
  Navigate: ({ to }: { to: string }) => <div>redirect:{to}</div>,
  useLocation: () => ({ pathname: "/t/tenant-a/a/acc-1", search: "" }),
  useParams: () => mockUseParams(),
  useMatches: () => mockUseMatches(),
}));
vi.mock("@clerk/react", () => ({ useAuth: () => ({ isLoaded: true, isSignedIn: true }) }));
vi.mock("@/hooks/useTenantMembership", () => ({ useTenantMembership: () => ({ isMemberOfTenant: true, isLoading: false }) }));
vi.mock("@/hooks/useAccountAccess", () => ({ useAccountAccess: () => ({ hasAccountAccess: false, isLoading: false, isError: false }) }));
vi.mock("@/hooks/useUserPermissions", () => ({ useUserPermissions: () => ({ hasPermissions: true, isLoading: false }) }));
vi.mock("@/hooks/useFeatureFlags", () => ({ useFeatureFlags: () => ({ flagsEnabled: true, isLoading: false }) }));
vi.mock("@/hooks/useEntitlements", () => ({ useEntitlements: () => ({ entitlementsMet: false, isLoading: false, isError: false }) }));
vi.mock("@/stores", () => ({ useUserTierStore: () => ({ canAccessRoute: () => true }) }));

import { UnifiedRouteGuard } from "./UnifiedRouteGuard";

describe("UnifiedRouteGuard deny behavior", () => {
  it("redirects when account acl denies", () => {
    render(<UnifiedRouteGuard><div>protected</div></UnifiedRouteGuard>);
    expect(screen.getByText("redirect:/t/tenant-a/accounts")).toBeInTheDocument();
  });
});
