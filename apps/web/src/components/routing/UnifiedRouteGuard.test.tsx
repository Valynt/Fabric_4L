import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { RouteAccessPolicy } from "@/routes/types";

const authorization = vi.hoisted(() => ({
  status: "verified" as "loading" | "verified" | "denied" | "expired",
  reason: undefined as
    | "malformed"
    | "mismatch"
    | "unavailable"
    | "unauthenticated"
    | undefined,
  hasEveryPermission: vi.fn(() => true),
  hasEveryEntitlement: vi.fn(() => true),
  hasTenantMembership: vi.fn(() => true),
  hasAccountAccess: vi.fn(() => true),
}));
const authState = vi.hoisted(() => ({
  isAuthenticated: true,
  isLoading: false,
}));
const routeState = vi.hoisted(() => ({
  params: { tenantSlug: "tenant-a", accountId: "acc-1" } as {
    tenantSlug?: string;
    accountId?: string;
  },
  matches: [] as Array<{ handle?: { accessPolicy?: RouteAccessPolicy } }>,
}));
const featureFlags = vi.hoisted(() => ({ flagsEnabled: true }));

vi.mock("react-router-dom", () => ({
  Navigate: ({ to }: { to: string }) => <div>redirect:{to}</div>,
  useLocation: () => ({ pathname: "/protected", search: "?view=detail" }),
  useParams: () => routeState.params,
  useMatches: () => routeState.matches,
}));
vi.mock("@/auth/AuthorizationProvider", () => ({
  useAuthorizationSnapshot: () => authorization,
}));
vi.mock("@/contexts/AuthContext", () => ({
  useAuthContext: () => authState,
}));
vi.mock("@/hooks/useFeatureFlags", () => ({
  useFeatureFlags: () => featureFlags,
}));
vi.mock("@/components", () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => children,
}));

import { UnifiedRouteGuard } from "./UnifiedRouteGuard";

const policy = (overrides: Partial<RouteAccessPolicy> = {}): RouteAccessPolicy => ({
  requiresAuth: true,
  tenantScoped: false,
  fallbackRoute: "/explicit-fallback",
  analyticsRouteId: "test.protected",
  ...overrides,
});

function renderGuard(accessPolicy: RouteAccessPolicy | null = policy()) {
  routeState.matches = accessPolicy
    ? [{ handle: { accessPolicy } }]
    : [{ handle: {} }];
  return render(
    <UnifiedRouteGuard>
      <div>protected</div>
    </UnifiedRouteGuard>
  );
}

function expectProtectedContentHidden() {
  expect(screen.queryByText("protected")).not.toBeInTheDocument();
}

describe("UnifiedRouteGuard verified authorization", () => {
  afterEach(() => {
    window.localStorage.clear();
    authState.isAuthenticated = true;
    authState.isLoading = false;
    authorization.status = "verified";
    authorization.reason = undefined;
    authorization.hasEveryPermission.mockReset().mockReturnValue(true);
    authorization.hasEveryEntitlement.mockReset().mockReturnValue(true);
    authorization.hasTenantMembership.mockReset().mockReturnValue(true);
    authorization.hasAccountAccess.mockReset().mockReturnValue(true);
    routeState.params = { tenantSlug: "tenant-a", accountId: "acc-1" };
    routeState.matches = [];
    featureFlags.flagsEnabled = true;
  });

  it("hides protected content while authentication is loading", () => {
    authState.isLoading = true;
    renderGuard();

    expect(screen.getByRole("status")).toHaveTextContent("Verifying access...");
    expectProtectedContentHidden();
  });

  it("redirects unauthenticated users to sign-in", () => {
    authState.isAuthenticated = false;
    renderGuard();

    expect(screen.getByText("redirect:/sign-in")).toBeInTheDocument();
    expectProtectedContentHidden();
  });

  it("fails closed when route policy metadata is absent", () => {
    authState.isAuthenticated = false;
    renderGuard(null);

    expect(screen.getByText("redirect:/sign-in")).toBeInTheDocument();
    expectProtectedContentHidden();
  });

  it("hides protected content while the snapshot is loading", () => {
    authorization.status = "loading";
    renderGuard();

    expect(screen.getByRole("status")).toHaveTextContent("Verifying access...");
    expectProtectedContentHidden();
  });

  it.each(["denied", "expired"] as const)(
    "fails closed with the explicit fallback for a %s snapshot",
    status => {
      authorization.status = status;
      authorization.reason = status === "denied" ? "mismatch" : undefined;
      renderGuard();

      expect(
        screen.getByText("redirect:/explicit-fallback")
      ).toBeInTheDocument();
      expectProtectedContentHidden();
    }
  );

  it("distinguishes snapshot verification errors from access denial", () => {
    authorization.status = "denied";
    authorization.reason = "unavailable";
    renderGuard();

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Unable to verify access. Please try again."
    );
    expect(screen.queryByText(/redirect:/)).not.toBeInTheDocument();
    expectProtectedContentHidden();
  });

  it("does not check requiredTier from route policy (A1 authorization snapshot only)", () => {
    localStorage.setItem(
      "user-tier-storage",
      JSON.stringify({ state: { currentTier: "admin" } })
    );
    renderGuard(policy({ requiredTier: "admin" }));

    expect(screen.queryByText(/redirect:/)).not.toBeInTheDocument();
    expect(screen.getByText("protected")).toBeInTheDocument();
    expect(authorization.hasEveryPermission).not.toHaveBeenCalledWith([
      "tier:admin:access",
    ]);
  });

  it("uses verified tenant and exact account scope", () => {
    authorization.hasAccountAccess.mockReturnValue(false);
    renderGuard(policy({ tenantScoped: true, accountScoped: true }));

    expect(authorization.hasTenantMembership).toHaveBeenCalledWith("tenant-a");
    expect(authorization.hasAccountAccess).toHaveBeenCalledWith("acc-1");
    expect(
      screen.getByText("redirect:/explicit-fallback")
    ).toBeInTheDocument();
    expectProtectedContentHidden();
  });

  it("fails closed when a required scope parameter is missing", () => {
    routeState.params = { tenantSlug: "tenant-a" };
    renderGuard(policy({ tenantScoped: true, accountScoped: true }));

    expect(authorization.hasAccountAccess).not.toHaveBeenCalled();
    expect(
      screen.getByText("redirect:/explicit-fallback")
    ).toBeInTheDocument();
    expectProtectedContentHidden();
  });

  it("uses snapshot all-of checks for permissions and entitlements", () => {
    authorization.hasEveryEntitlement.mockReturnValue(false);
    renderGuard(
      policy({
        requiredPermissions: ["account:read", "account:write"],
        requiredEntitlements: ["billing.manage", "exports.enabled"],
      })
    );

    expect(authorization.hasEveryPermission).toHaveBeenCalledWith([
      "account:read",
      "account:write",
    ]);
    expect(authorization.hasEveryEntitlement).toHaveBeenCalledWith([
      "billing.manage",
      "exports.enabled",
    ]);
    expect(
      screen.getByText("redirect:/explicit-fallback")
    ).toBeInTheDocument();
    expectProtectedContentHidden();
  });

  it("does not let a feature flag grant missing snapshot permission", () => {
    featureFlags.flagsEnabled = true;
    authorization.hasEveryPermission.mockReturnValue(false);
    renderGuard(
      policy({
        requiredPermissions: ["admin:read"],
        requiredFeatureFlags: ["admin-ui"],
      })
    );

    expect(
      screen.getByText("redirect:/explicit-fallback")
    ).toBeInTheDocument();
    expectProtectedContentHidden();
  });

  it("lets a feature flag further restrict verified access", () => {
    featureFlags.flagsEnabled = false;
    renderGuard(policy({ requiredFeatureFlags: ["new-workspace"] }));

    expect(
      screen.getByText("redirect:/explicit-fallback")
    ).toBeInTheDocument();
    expectProtectedContentHidden();
  });

  it("renders protected content only after every policy check passes", () => {
    renderGuard(
      policy({
        tenantScoped: true,
        accountScoped: true,
        requiredTier: "advanced",
        requiredPermissions: ["account:read"],
        requiredEntitlements: ["workspace.enabled"],
        requiredFeatureFlags: ["workspace-ui"],
      })
    );

    expect(screen.getByText("protected")).toBeInTheDocument();
    expect(screen.queryByText(/redirect:/)).not.toBeInTheDocument();
  });
});
