import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuthContext } from "@/contexts/AuthContext";
import { setAuthProvider } from "@/test/utils/withAuthProvider";

const mockClerkState = {
  authLoaded: true,
  isSignedIn: false,
  userLoaded: true,
  user: null as { id: string; primaryEmailAddress?: { emailAddress?: string } | null; organizationMemberships?: Array<{ organization: { id: string }; role: string }> } | null,
  organizationLoaded: true,
  organization: null as { id: string; slug?: string | null } | null,
  signOut: vi.fn(async (_options?: { redirectUrl?: string }) => undefined),
};

vi.mock("@clerk/react", () => ({
  useAuth: () => ({
    isLoaded: mockClerkState.authLoaded,
    isSignedIn: mockClerkState.isSignedIn,
    getToken: vi.fn(async () => "tok"),
  }),
  useUser: () => ({
    isLoaded: mockClerkState.userLoaded,
    user: mockClerkState.user,
  }),
  useOrganization: () => ({
    isLoaded: mockClerkState.organizationLoaded,
    organization: mockClerkState.organization,
  }),
  useClerk: () => ({
    signOut: mockClerkState.signOut,
  }),
}));

function Probe() {
  const { isAuthenticated, isLoading, currentTenantSlug, logout, user } = useAuthContext();
  return (
    <div>
      <div data-testid="auth">{isAuthenticated ? "yes" : "no"}</div>
      <div data-testid="loading">{isLoading ? "yes" : "no"}</div>
      <div data-testid="tenant">{currentTenantSlug ?? "none"}</div>
      <div data-testid="role">{user?.role ?? "none"}</div>
      <button type="button" onClick={() => void logout()}>
        logout
      </button>
    </div>
  );
}

function renderProbe() {
  return render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
}

describe("Auth behavior invariants", () => {
  let savedProvider: string | undefined;
  let savedMockAuth: unknown;

  beforeEach(() => {
    savedProvider = (import.meta.env as Record<string, unknown>).VITE_AUTH_PROVIDER as
      | string
      | undefined;
    savedMockAuth = (import.meta.env as Record<string, unknown>).VITE_ENABLE_MOCK_AUTH;

    mockClerkState.authLoaded = true;
    mockClerkState.userLoaded = true;
    mockClerkState.isSignedIn = false;
    mockClerkState.organizationLoaded = true;
    mockClerkState.user = null;
    mockClerkState.organization = null;
    mockClerkState.signOut.mockClear();
  });

  afterEach(() => {
    cleanup();
    setAuthProvider(savedProvider);
    (import.meta.env as Record<string, unknown>).VITE_ENABLE_MOCK_AUTH = savedMockAuth;
  });

  it("fails closed in Clerk mode: mock auth flag must not make signed-out users authenticated", () => {
    setAuthProvider("clerk");
    (import.meta.env as Record<string, unknown>).VITE_ENABLE_MOCK_AUTH = "true";

    mockClerkState.authLoaded = true;
    mockClerkState.isSignedIn = false;

    renderProbe();

    expect(screen.getByTestId("loading").textContent).toBe("no");
    expect(screen.getByTestId("auth").textContent).toBe("no");
  });

  it("allows mock auth in non-Clerk mode for dev-only local workflows", () => {
    setAuthProvider("legacy");
    (import.meta.env as Record<string, unknown>).VITE_ENABLE_MOCK_AUTH = "true";

    mockClerkState.authLoaded = false;
    mockClerkState.isSignedIn = false;

    renderProbe();

    expect(screen.getByTestId("loading").textContent).toBe("no");
    expect(screen.getByTestId("auth").textContent).toBe("yes");
  });

  it("uses Clerk's signOut hook from render context in Clerk mode", async () => {
    setAuthProvider("clerk");
    mockClerkState.authLoaded = true;
    mockClerkState.userLoaded = true;
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_1", slug: "acme" };
    mockClerkState.user = {
      id: "user_1",
      primaryEmailAddress: { emailAddress: "alice@example.com" },
      organizationMemberships: [
        { organization: { id: "org_1" }, role: "org:admin" },
      ],
    };

    renderProbe();

    await userEvent.click(screen.getByRole("button", { name: "logout" }));

    expect(mockClerkState.signOut).toHaveBeenCalledWith({ redirectUrl: "/" });
    expect(screen.getByTestId("role").textContent).toBe("tenant_admin");
  });

  it("keeps signed-in Clerk auth loading until active organization state resolves", () => {
    setAuthProvider("clerk");
    mockClerkState.authLoaded = true;
    mockClerkState.userLoaded = true;
    mockClerkState.isSignedIn = true;
    mockClerkState.organizationLoaded = false;
    mockClerkState.organization = null;
    mockClerkState.user = {
      id: "user_1",
      primaryEmailAddress: { emailAddress: "alice@example.com" },
      organizationMemberships: [],
    };

    renderProbe();

    expect(screen.getByTestId("loading").textContent).toBe("yes");
    expect(screen.getByTestId("auth").textContent).toBe("yes");
  });

  it("falls back to Clerk organization id when the active organization has no slug", () => {
    setAuthProvider("clerk");
    mockClerkState.authLoaded = true;
    mockClerkState.userLoaded = true;
    mockClerkState.isSignedIn = true;
    mockClerkState.organizationLoaded = true;
    mockClerkState.organization = { id: "org_without_slug", slug: null };
    mockClerkState.user = {
      id: "user_1",
      primaryEmailAddress: { emailAddress: "alice@example.com" },
      organizationMemberships: [
        { organization: { id: "org_without_slug" }, role: "org:member" },
      ],
    };

    renderProbe();

    expect(screen.getByTestId("loading").textContent).toBe("no");
    expect(screen.getByTestId("auth").textContent).toBe("yes");
    expect(screen.getByTestId("tenant").textContent).toBe("org_without_slug");
    expect(screen.getByTestId("role").textContent).toBe("analyst");
  });

  it("never elevates the role from a membership that does not match the active org", () => {
    setAuthProvider("clerk");
    mockClerkState.authLoaded = true;
    mockClerkState.userLoaded = true;
    mockClerkState.isSignedIn = true;
    mockClerkState.organizationLoaded = true;
    // The active org is NOT part of the user's memberships — a hostile or
    // transiently stale state. The user's own (unrelated) membership claims
    // org:admin, but the active org must not inherit that role by
    // cross-matching.
    mockClerkState.organization = { id: "org_active", slug: "active" };
    mockClerkState.user = {
      id: "user_1",
      primaryEmailAddress: { emailAddress: "alice@example.com" },
      organizationMemberships: [
        { organization: { id: "org_other" }, role: "org:admin" },
      ],
    };

    renderProbe();

    // Signed in with the active org as the tenant, but the role falls back to
    // the baseline analyst — an unmatched membership is never treated as a
    // grant for the current org.
    expect(screen.getByTestId("auth").textContent).toBe("yes");
    expect(screen.getByTestId("tenant").textContent).toBe("active");
    expect(screen.getByTestId("role").textContent).toBe("analyst");
  });
});
