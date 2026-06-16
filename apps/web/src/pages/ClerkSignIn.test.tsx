/**
 * Behavior contract for <ClerkSignInPage />.
 *
 * The page must not mount Clerk's <SignIn /> for an already-authenticated
 * user (single-session apps emit a development notice and redirect). Instead
 * it redirects to the post-sign-in landing URL itself, keeping the
 * home <-> sign-in transition clean.
 *
 * Invariants under test:
 *   - Signed-in user redirects to afterSignInUrl and does NOT mount <SignIn />.
 *   - Signed-in user with a safe internal `redirect_url` is sent there.
 *   - Signed-in user with an unsafe/external `redirect_url` falls back to
 *     afterSignInUrl (no open redirect).
 *   - Signed-out user renders <SignIn />.
 *   - While Clerk is loading, neither <SignIn /> nor a redirect occurs.
 *   - Legacy mode renders the local login surface and does not bounce between
 *     `/sign-in` and `/login`.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const mockAuthState = {
  isLoaded: true as boolean,
  isSignedIn: false as boolean,
};

const mockClerkConfig = {
  clerkEnabled: true as boolean,
};

const mockUrls = {
  signInUrl: "/sign-in",
  signUpUrl: "/sign-up",
  afterSignInUrl: "/home",
  afterSignUpUrl: "/onboarding",
  selectOrgUrl: "/workspaces",
};

vi.mock("@clerk/react", () => ({
  SignIn: () => <div data-testid="clerk-signin" />,
  useAuth: () => ({
    isLoaded: mockAuthState.isLoaded,
    isSignedIn: mockAuthState.isSignedIn,
  }),
}));

vi.mock("@/auth/clerkConfig", () => ({
  getClerkUrls: () => mockUrls,
  isClerkAuthEnabled: () => mockClerkConfig.clerkEnabled,
}));

import ClerkSignInPage from "./ClerkSignIn";

const HOME_MARKER = "HOME_PAGE_MARKER";
const ACCOUNTS_MARKER = "ACCOUNTS_PAGE_MARKER";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/sign-in" element={<ClerkSignInPage />} />
        <Route path="/home" element={<div>{HOME_MARKER}</div>} />
        <Route path="/t/acme/accounts" element={<div>{ACCOUNTS_MARKER}</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("<ClerkSignInPage />", () => {
  beforeEach(() => {
    cleanup();
    mockAuthState.isLoaded = true;
    mockAuthState.isSignedIn = false;
    mockClerkConfig.clerkEnabled = true;
  });

  it("redirects an already signed-in user to afterSignInUrl without mounting <SignIn />", () => {
    mockAuthState.isSignedIn = true;

    renderAt("/sign-in");

    expect(screen.getByText(HOME_MARKER)).toBeInTheDocument();
    expect(screen.queryByTestId("clerk-signin")).not.toBeInTheDocument();
  });

  it("honors a safe internal redirect_url for a signed-in user", () => {
    mockAuthState.isSignedIn = true;

    renderAt("/sign-in?redirect_url=%2Ft%2Facme%2Faccounts");

    expect(screen.getByText(ACCOUNTS_MARKER)).toBeInTheDocument();
    expect(screen.queryByTestId("clerk-signin")).not.toBeInTheDocument();
  });

  it("ignores an external redirect_url and falls back to afterSignInUrl", () => {
    mockAuthState.isSignedIn = true;

    renderAt("/sign-in?redirect_url=https%3A%2F%2Fevil.example.com");

    expect(screen.getByText(HOME_MARKER)).toBeInTheDocument();
    expect(screen.queryByTestId("clerk-signin")).not.toBeInTheDocument();
  });

  it("ignores a protocol-relative redirect_url and falls back to afterSignInUrl", () => {
    mockAuthState.isSignedIn = true;

    renderAt("/sign-in?redirect_url=%2F%2Fevil.example.com");

    expect(screen.getByText(HOME_MARKER)).toBeInTheDocument();
    expect(screen.queryByTestId("clerk-signin")).not.toBeInTheDocument();
  });

  it("renders <SignIn /> for a signed-out user", () => {
    mockAuthState.isSignedIn = false;

    renderAt("/sign-in");

    expect(screen.getByTestId("clerk-signin")).toBeInTheDocument();
    expect(screen.queryByText(HOME_MARKER)).not.toBeInTheDocument();
  });

  it("renders neither <SignIn /> nor a redirect while Clerk is loading", () => {
    mockAuthState.isLoaded = false;
    mockAuthState.isSignedIn = false;

    renderAt("/sign-in");

    expect(screen.queryByTestId("clerk-signin")).not.toBeInTheDocument();
    expect(screen.queryByText(HOME_MARKER)).not.toBeInTheDocument();
  });

  it("renders the local login surface under legacy auth without redirecting", () => {
    mockClerkConfig.clerkEnabled = false;
    mockAuthState.isSignedIn = true; // even if a stale Clerk session reports signed-in

    renderAt("/sign-in");

    expect(screen.getByTestId("login-heading")).toBeInTheDocument();
    expect(screen.queryByTestId("clerk-signin")).not.toBeInTheDocument();
    expect(screen.queryByText(HOME_MARKER)).not.toBeInTheDocument();
  });
});
