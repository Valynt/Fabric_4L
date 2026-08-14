import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const authorization = vi.hoisted(() => ({
  status: "verified" as "loading" | "verified" | "denied" | "expired",
  hasEveryPermission: vi.fn(() => true),
  hasEveryEntitlement: vi.fn(() => true),
  hasTenantMembership: vi.fn(() => true),
  hasAccountAccess: vi.fn(() => true),
}));

const matches = vi.hoisted(() =>
  vi.fn(() => [
    {
      handle: {
        accessPolicy: {
          requiresAuth: true,
          fallbackRoute: "/home",
          requiredTier: "admin",
        },
      },
    },
  ]),
);

vi.mock("react-router-dom", () => ({
  Navigate: ({ to }: { to: string }) => <div>redirect:{to}</div>,
  useLocation: () => ({
    pathname: "/admin",
    search: "",
  }),
  useParams: () => ({
    tenantSlug: "tenant-a",
    accountId: "acc-1",
  }),
  useMatches: () => matches(),
}));

vi.mock("@/auth/AuthorizationProvider", () => ({
  useAuthorizationSnapshot: () => authorization,
}));

vi.mock("@/hooks/useFeatureFlags", () => ({
  useFeatureFlags: () => ({
    flagsEnabled: true,
    isLoading: false,
  }),
}));

import { AuthContext } from "@/contexts/AuthContext";
import { UnifiedRouteGuard } from "./UnifiedRouteGuard";

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
      <UnifiedRouteGuard>
        <div>protected</div>
      </UnifiedRouteGuard>
    </AuthContext.Provider>,
  );
}

describe("UnifiedRouteGuard snapshot authorization", () => {
  afterEach(() => {
    localStorage.clear();
    sessionStorage.clear();

    authorization.status = "verified";
    authorization.hasEveryPermission.mockReset();
    authorization.hasEveryEntitlement.mockReset();
    authorization.hasTenantMembership.mockReset();
    authorization.hasAccountAccess.mockReset();

    authorization.hasEveryPermission.mockReturnValue(true);
    authorization.hasEveryEntitlement.mockReturnValue(true);
    authorization.hasTenantMembership.mockReturnValue(true);
    authorization.hasAccountAccess.mockReturnValue(true);

    matches.mockReset();
    matches.mockReturnValue([
      {
        handle: {
          accessPolicy: {
            requiresAuth: true,
            fallbackRoute: "/home",
            requiredTier: "admin",
          },
        },
      },
    ]);
  });

  it("never lets persisted admin presentation state grant a route", () => {
    localStorage.setItem(
      "user-tier-storage",
      JSON.stringify({
        state: {
          currentTier: "admin",
        },
      }),
    );

    authorization.hasEveryPermission.mockReturnValue(false);

    renderGuard();

    expect(screen.getByText("redirect:/home")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });

  it("does not render protected content while the snapshot is loading", () => {
    authorization.status = "loading";

    renderGuard();

    expect(screen.getByText("Verifying access...")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });

  it("requires exact account scope", () => {
    matches.mockReturnValueOnce([
      {
        handle: {
          accessPolicy: {
            requiresAuth: true,
            fallbackRoute: "/home",
            tenantScoped: true,
            accountScoped: true,
          },
        },
      },
    ]);

    authorization.hasAccountAccess.mockReturnValue(false);

    renderGuard();

    expect(
      screen.getByText("redirect:/t/tenant-a/accounts"),
    ).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });
});