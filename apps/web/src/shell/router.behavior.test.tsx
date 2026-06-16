import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { RootRedirect } from "./router";
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
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@clerk/react", () => ({
  useAuth: () => mockClerkAuth,
  useUser: () => ({ isLoaded: true, user: null }),
  useOrganization: () => ({ organization: null }),
}));

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

function renderRedirect() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<div data-testid="login-page">login</div>} />
        <Route path="/sign-in" element={<div data-testid="signin-page">signin</div>} />
        <Route path="/home" element={<div data-testid="home-page">home</div>} />
      </Routes>
      <LocationProbe />
    </MemoryRouter>
  );
}

describe("RootRedirect auth-provider boundary", () => {
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

  it("legacy mode: unauthenticated user is redirected to /login", () => {
    setAuthProvider("legacy");
    mockAuthContext.isAuthenticated = false;
    renderRedirect();
    expect(screen.getByTestId("login-page")).toBeInTheDocument();
  });

  it("legacy mode: authenticated user is redirected to /home", () => {
    setAuthProvider("legacy");
    mockAuthContext.isAuthenticated = true;
    renderRedirect();
    expect(screen.getByTestId("home-page")).toBeInTheDocument();
  });

  it("legacy mode: does not throw when ClerkProvider is absent", () => {
    setAuthProvider("legacy");
    mockAuthContext.isAuthenticated = false;
    expect(() => renderRedirect()).not.toThrow();
  });

  it("clerk mode: signed-out user is redirected to /sign-in", () => {
    setAuthProvider("clerk");
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = false;
    renderRedirect();
    expect(screen.getByTestId("signin-page")).toBeInTheDocument();
  });

  it("clerk mode: signed-in user is redirected to /home", () => {
    setAuthProvider("clerk");
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = true;
    renderRedirect();
    expect(screen.getByTestId("home-page")).toBeInTheDocument();
  });
});
