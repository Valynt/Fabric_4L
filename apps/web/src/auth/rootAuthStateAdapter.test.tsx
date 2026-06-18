import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RootAuthStateAdapter } from "@/auth/rootAuthStateAdapter";
import { setAuthProvider } from "@/test/utils/withAuthProvider";

const mockAuthContext = {
  isAuthenticated: false,
  isLoading: false,
  user: null,
  currentTenantSlug: null,
  accessToken: null,
  initiateLogin: vi.fn(),
  handleCallback: vi.fn(),
  logout: vi.fn(),
  refreshToken: vi.fn(),
};

const mockClerkAuth = {
  isLoaded: true,
  isSignedIn: false,
};

vi.mock("@/contexts/AuthContext", () => ({
  useAuthContext: vi.fn(() => mockAuthContext),
}));

vi.mock("@clerk/react", () => ({
  useAuth: vi.fn(() => mockClerkAuth),
}));

function StateProbe() {
  return (
    <RootAuthStateAdapter>
      {({ isLoading, isAuthenticated, unauthenticatedRedirectTo }) => (
        <>
          <div data-testid="loading">{isLoading ? "yes" : "no"}</div>
          <div data-testid="authenticated">{isAuthenticated ? "yes" : "no"}</div>
          <div data-testid="redirect">{unauthenticatedRedirectTo}</div>
        </>
      )}
    </RootAuthStateAdapter>
  );
}

describe("RootAuthStateAdapter", () => {
  let savedProvider: string | undefined;

  beforeEach(() => {
    savedProvider = (import.meta.env as Record<string, unknown>).VITE_AUTH_PROVIDER as string | undefined;
    mockAuthContext.isAuthenticated = false;
    mockAuthContext.isLoading = false;
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = false;
  });

  afterEach(() => {
    cleanup();
    setAuthProvider(savedProvider);
  });

  it("uses legacy auth context and /login redirect in legacy mode", () => {
    setAuthProvider("legacy");
    mockAuthContext.isAuthenticated = true;

    render(<StateProbe />);

    expect(screen.getByTestId("loading").textContent).toBe("no");
    expect(screen.getByTestId("authenticated").textContent).toBe("yes");
    expect(screen.getByTestId("redirect").textContent).toBe("/login");
  });

  it("normalizes Clerk signed-in state in clerk mode", () => {
    setAuthProvider("clerk");
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = true;

    render(<StateProbe />);

    expect(screen.getByTestId("loading").textContent).toBe("no");
    expect(screen.getByTestId("authenticated").textContent).toBe("yes");
    expect(screen.getByTestId("redirect").textContent).toBe("/sign-in");
  });

  it("fails closed while Clerk auth is still loading", () => {
    setAuthProvider("clerk");
    mockAuthContext.isLoading = false;
    mockClerkAuth.isLoaded = false;
    mockClerkAuth.isSignedIn = true;

    render(<StateProbe />);

    expect(screen.getByTestId("loading").textContent).toBe("yes");
    expect(screen.getByTestId("authenticated").textContent).toBe("no");
    expect(screen.getByTestId("redirect").textContent).toBe("/sign-in");
  });

  it("keeps loading true when AuthContext is loading in clerk mode", () => {
    setAuthProvider("clerk");
    mockAuthContext.isLoading = true;
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = true;

    render(<StateProbe />);

    expect(screen.getByTestId("loading").textContent).toBe("yes");
    expect(screen.getByTestId("authenticated").textContent).toBe("yes");
  });
});
