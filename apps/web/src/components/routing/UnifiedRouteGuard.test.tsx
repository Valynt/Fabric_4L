import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthContext } from "@/contexts/AuthContext";
import { setAuthProvider } from "@/test/utils/withAuthProvider";

const state = vi.hoisted(() => ({
  authz: "loading" as "loading" | "verified" | "denied" | "expired",
  signedIn: true,
}));
vi.mock("react-router-dom", () => ({
  Navigate: ({
    to,
    state: navState,
  }: {
    to: string;
    state?: { from?: string };
  }) => (
    <div>
      redirect:{to}:{navState?.from}
    </div>
  ),
  useLocation: () => ({ pathname: "/t/tenant-a/accounts", search: "?tab=all" }),
  useParams: () => ({ tenantSlug: "tenant-a" }),
  useMatches: () => [
    {
      handle: {
        accessPolicy: {
          requiresAuth: true,
          tenantScoped: true,
          fallbackRoute: "/home",
          analyticsRouteId: "accounts",
        },
      },
    },
  ],
}));
vi.mock("@clerk/react", () => ({
  useAuth: () => ({ isLoaded: true, isSignedIn: state.signedIn }),
}));
vi.mock("@/hooks/useFeatureFlags", () => ({
  useFeatureFlags: () => ({ flagsEnabled: true }),
}));
vi.mock("@/hooks/useAuthorizationSnapshot", () => ({
  useAuthorizationSnapshot: () =>
    state.authz === "verified"
      ? {
          status: "verified",
          permissions: [],
          entitlements: [],
          snapshot: {
            tenantMember: true,
            accountIds: [],
            permissions: [],
            entitlements: [],
          },
        }
      : { status: state.authz, permissions: [], entitlements: [] },
}));

import { UnifiedRouteGuard } from "./UnifiedRouteGuard";

function renderGuard(fallback?: React.ReactNode, authenticated = true) {
  return render(
    <AuthContext.Provider
      value={{
        isAuthenticated: authenticated,
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
      <UnifiedRouteGuard fallback={fallback}>
        <div>protected</div>
      </UnifiedRouteGuard>
    </AuthContext.Provider>
  );
}

describe("UnifiedRouteGuard", () => {
  afterEach(() => {
    state.authz = "loading";
    state.signedIn = true;
    setAuthProvider("legacy");
  });
  it("renders verification without protected children while loading", () => {
    renderGuard();
    expect(screen.getByText("Verifying access...")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });
  it("renders children only when allowed", () => {
    state.authz = "verified";
    renderGuard();
    expect(screen.getByText("protected")).toBeInTheDocument();
  });
  it("renders supplied fallback on denial", () => {
    state.authz = "denied";
    renderGuard(<div>fallback</div>);
    expect(screen.getByText("fallback")).toBeInTheDocument();
  });
  it("renders in-place denial and preserves attempted URL", () => {
    state.authz = "denied";
    const view = renderGuard();
    expect(screen.getByText("Access denied")).toBeInTheDocument();
    expect(
      view.container.querySelector(
        '[data-attempted-url="/t/tenant-a/accounts?tab=all"]'
      )
    ).toBeTruthy();
  });
  it("renders expired session without protected children", () => {
    state.authz = "expired";
    renderGuard();
    expect(screen.getByText("Session expired")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });
  it("redirects unauthenticated users with return URL", () => {
    renderGuard(undefined, false);
    expect(
      screen.getByText("redirect:/sign-in:/t/tenant-a/accounts?tab=all")
    ).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
  });
});
