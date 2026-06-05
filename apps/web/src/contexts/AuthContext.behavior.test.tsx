import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { AuthProvider, useAuthContext } from "@/contexts/AuthContext";
import { setAuthProvider } from "@/test/utils/withAuthProvider";

const mockClerkState = {
  authLoaded: true,
  isSignedIn: false,
  userLoaded: true,
  user: null as { id: string; primaryEmailAddress?: { emailAddress?: string } | null; organizationMemberships?: Array<{ organization: { id: string }; role: string }> } | null,
  organization: null as { id: string; slug: string } | null,
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
    organization: mockClerkState.organization,
  }),
}));

function Probe() {
  const { isAuthenticated, isLoading } = useAuthContext();
  return (
    <div>
      <div data-testid="auth">{isAuthenticated ? "yes" : "no"}</div>
      <div data-testid="loading">{isLoading ? "yes" : "no"}</div>
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
    mockClerkState.user = null;
    mockClerkState.organization = null;
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
});
