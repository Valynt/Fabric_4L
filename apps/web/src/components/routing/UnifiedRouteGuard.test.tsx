import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { setAuthProvider } from "@/test/utils/withAuthProvider";

const authz = vi.hoisted(() => ({
  decision: { status: "allowed" } as { status: string; reason?: string },
  snapshot: {
    status: "verified",
    permissions: ["account:read"],
    entitlements: ["feature.a"],
    snapshot: {
      tenantMember: true,
      accountIds: ["acc-1"],
    },
  } as Record<string, unknown>,
  flagsEnabled: true,
}));

const clerk = vi.hoisted(() => ({
  isLoaded: true,
  isSignedIn: true,
}));

const matches = vi.hoisted(() => ({
  value: [
    {
      handle: {
        accessPolicy: {
          requiresAuth: true,
          tenantScoped: true,
          accountScoped: true,
          requiredPermissions: ["account:read"],
          requiredEntitlements: ["feature.a"],
          fallbackRoute: "/home",
          analyticsRouteId: "test",
        },
      },
    },
  ],
}));

vi.mock("react-router-dom", () => ({
  Navigate: ({ to }: { to: string }) => <div>redirect:{to}</div>,
  useLocation: () => ({
    pathname: "/t/tenant-a/accounts/acc-1",
    search: "?tab=x",
  }),
  useParams: () => ({
    tenantSlug: "tenant-a",
    accountId: "acc-1",
  }),
  useMatches: () => matches.value,
}));

vi.mock("@clerk/react", () => ({
  useAuth: () => clerk,
}));

vi.mock("@/hooks/useUserPermissions", () => ({
  useUserPermissions: () => ({
    decision: authz.decision,
    snapshot: authz.snapshot,
  }),
}));

vi.mock("@/hooks/useFeatureFlags", () => ({
  useFeatureFlags: () => ({
    flagsEnabled: authz.flagsEnabled,
  }),
}));

import { AuthContext } from "@/contexts/AuthContext";
import { UnifiedRouteGuard } from "./UnifiedRouteGuard";

function renderGuard(
  options: {
    authenticated?: boolean;
    loading?: boolean;
    fallback?: React.ReactNode;
  } = {},
) {
  return render(
    <AuthContext.Provider
      value={{
        isAuthenticated: options.authenticated ?? true,
        isLoading: options.loading ?? false,
        user: null,
        currentTenantSlug: "tenant-a",
        accessToken: null,
        initiateLogin: vi.fn(),
        handleCallback: vi.fn(async () => true),
        logout: vi.fn(),
        refreshToken: vi.fn(async () => true),
      }}
    >
      <UnifiedRouteGuard fallback={options.fallback}>
        <div>protected</div>
      </UnifiedRouteGuard>
    </AuthContext.Provider>,
  );
}

describe("UnifiedRouteGuard authorization states", () => {
  afterEach(() => {
    setAuthProvider("legacy");

    authz.decision = {
      status: "allowed",
    };

    authz.snapshot = {
      status: "verified",
      permissions: ["account:read"],
      entitlements: ["feature.a"],
      snapshot: {
        tenantMember: true,
        accountIds: ["acc-1"],
      },
    };

    authz.flagsEnabled = true;

    clerk.isLoaded = true;
    clerk.isSignedIn = true;

    matches.value = [
      {
        handle: {
          accessPolicy: {
            requiresAuth: true,
            tenantScoped: true,
            accountScoped: true,
            requiredPermissions: ["account:read"],
            requiredEntitlements: ["feature.a"],
            fallbackRoute: "/home",
            analyticsRouteId: "test",
          },
        },
      },
    ];
  });

  it("renders verification while snapshot resolution is loading", () => {
    authz.decision = {
      status: "loading",
    };

    renderGuard();

    expect(screen.getByText("Verifying access...")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });

  it("denies access when the verified snapshot does not authorize the selected account", () => {
    authz.decision = {
      status: "denied",
      reason: "account_not_authorized",
    };

    authz.snapshot = {
      status: "verified",
      permissions: ["account:read"],
      entitlements: ["feature.a"],
      snapshot: {
        tenantMember: true,
        accountIds: [],
      },
    };

    renderGuard();

    expect(screen.getByText("Access denied")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
    expect(screen.queryByText(/redirect:/)).not.toBeInTheDocument();
  });

  it("preserves the URL and renders access denied after explicit denial", () => {
    authz.decision = {
      status: "denied",
      reason: "snapshot_fetch_failed",
    };

    renderGuard();

    expect(screen.getByText("Access denied")).toBeInTheDocument();
    expect(screen.queryByText(/redirect:/)).not.toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });

  it("honors an explicitly supplied denial fallback", () => {
    authz.decision = {
      status: "denied",
      reason: "missing_permission",
    };

    renderGuard({
      fallback: <div>custom denial</div>,
    });

    expect(screen.getByText("custom denial")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });

  it("requires reauthentication when refresh leaves the snapshot expired", () => {
    authz.decision = {
      status: "expired",
      reason: "snapshot_expired",
    };

    renderGuard();

    expect(
      screen.getByText("Session verification expired"),
    ).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });

  it("redirects unauthenticated users to sign-in", () => {
    renderGuard({
      authenticated: false,
    });

    expect(screen.getByText("redirect:/sign-in")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });

  it("renders children only when snapshot authorization and feature flags allow", () => {
    const { unmount } = renderGuard();

    expect(screen.getByText("protected")).toBeInTheDocument();

    unmount();

    authz.flagsEnabled = false;

    renderGuard();

    expect(screen.getByText("Access denied")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });
});