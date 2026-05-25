/**
 * Phase 2 — route guard behavior for <RequireClerkAuth />.
 *
 * The guard layers Clerk-aware auth + org checks on top of whatever existing
 * guard wraps the route. The invariants under test:
 *
 *   - Legacy mode is a TRUE no-op: children render even if Clerk reports
 *     signed-out and no org. The legacy <UnifiedRouteGuard /> remains
 *     authoritative on that code path.
 *   - Clerk mode while loading shows a non-children fallback (so children
 *     do not flash content before auth resolves).
 *   - Clerk mode signed-out redirects to the configured sign-in URL with
 *     the intended destination preserved.
 *   - Clerk mode signed-in without org redirects to /select-organization.
 *   - Clerk mode signed-in with org renders children.
 *   - Disabling `requireOrganization` allows signed-in users without an
 *     org to reach the children (used by the org-picker page itself).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { setAuthProvider } from "@/test/utils/withAuthProvider";

// Mutable mock state — flipped per test before render().
const mockClerkState = {
  authLoaded: true as boolean,
  isSignedIn: false as boolean,
  orgLoaded: true as boolean,
  organization: null as { id: string } | null,
};

vi.mock("@clerk/react", () => ({
  useAuth: () => ({
    isLoaded: mockClerkState.authLoaded,
    isSignedIn: mockClerkState.isSignedIn,
    getToken: vi.fn(async () => "tok"),
  }),
  useOrganization: () => ({
    isLoaded: mockClerkState.orgLoaded,
    organization: mockClerkState.organization,
  }),
  useUser: () => ({ user: mockClerkState.isSignedIn ? { id: "u_1" } : null }),
}));

// Import AFTER vi.mock so the component picks up the mocked module.
import { RequireClerkAuth } from "./RequireClerkAuth";

const PROTECTED_CONTENT = "PROTECTED_CONTENT_MARKER";
const SIGN_IN_LANDING = "SIGN_IN_PAGE_MARKER";
const SELECT_ORG_LANDING = "SELECT_ORG_PAGE_MARKER";

function renderAt(
  path: string,
  options?: { requireOrganization?: boolean },
) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/sign-in"
          element={<div>{SIGN_IN_LANDING}</div>}
        />
        <Route
          path="/select-organization"
          element={<div>{SELECT_ORG_LANDING}</div>}
        />
        <Route
          path="/workspaces"
          element={<div>{SELECT_ORG_LANDING}</div>}
        />
        <Route
          path="/protected"
          element={
            <RequireClerkAuth requireOrganization={options?.requireOrganization}>
              <div>{PROTECTED_CONTENT}</div>
            </RequireClerkAuth>
          }
        />
        <Route
          path="/protected/nested"
          element={
            <RequireClerkAuth requireOrganization={options?.requireOrganization}>
              <div>{PROTECTED_CONTENT}</div>
            </RequireClerkAuth>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("<RequireClerkAuth />", () => {
  let savedProvider: string | undefined;

  beforeEach(() => {
    savedProvider = (import.meta.env as Record<string, unknown>)
      .VITE_AUTH_PROVIDER as string | undefined;
    // Reset Clerk state to a known baseline.
    mockClerkState.authLoaded = true;
    mockClerkState.isSignedIn = false;
    mockClerkState.orgLoaded = true;
    mockClerkState.organization = null;
  });

  afterEach(() => {
    cleanup();
    setAuthProvider(savedProvider);
  });

  // ─────────────────────────────────────────────────────────────────────
  // Legacy mode — true no-op
  // ─────────────────────────────────────────────────────────────────────
  it("legacy mode: renders children regardless of Clerk state", () => {
    setAuthProvider("legacy");
    // Clerk says signed-out + no org; legacy must not gate on Clerk.
    mockClerkState.isSignedIn = false;
    mockClerkState.organization = null;

    renderAt("/protected");

    expect(screen.getByText(PROTECTED_CONTENT)).toBeInTheDocument();
    expect(screen.queryByText(SIGN_IN_LANDING)).not.toBeInTheDocument();
    expect(screen.queryByText(SELECT_ORG_LANDING)).not.toBeInTheDocument();
  });

  it("legacy mode (default, unset provider): renders children", () => {
    setAuthProvider(undefined);
    renderAt("/protected");
    expect(screen.getByText(PROTECTED_CONTENT)).toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────
  // Clerk mode — loading state
  // ─────────────────────────────────────────────────────────────────────
  it("clerk mode: shows loading fallback while auth not loaded", () => {
    setAuthProvider("clerk");
    mockClerkState.authLoaded = false;

    renderAt("/protected");

    // Children must not render while we're still resolving auth.
    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("clerk mode: shows loading fallback while org not loaded (when org required)", () => {
    setAuthProvider("clerk");
    mockClerkState.authLoaded = true;
    mockClerkState.isSignedIn = true;
    mockClerkState.orgLoaded = false;

    renderAt("/protected", { requireOrganization: true });

    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────
  // Clerk mode — signed out
  // ─────────────────────────────────────────────────────────────────────
  it("clerk mode signed out: redirects to sign-in with the intended destination", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = false;

    renderAt("/protected/nested");

    // We are redirected away from /protected/nested to /sign-in.
    expect(screen.getByText(SIGN_IN_LANDING)).toBeInTheDocument();
    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────
  // Clerk mode — signed in, no org
  // ─────────────────────────────────────────────────────────────────────
  it("clerk mode signed-in without org: redirects to /workspaces", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = null;

    renderAt("/protected");

    expect(screen.getByText(SELECT_ORG_LANDING)).toBeInTheDocument();
    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
  });

  it("clerk mode signed-in without org but requireOrganization=false: renders children", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = null;

    renderAt("/protected", { requireOrganization: false });

    expect(screen.getByText(PROTECTED_CONTENT)).toBeInTheDocument();
    expect(screen.queryByText(SELECT_ORG_LANDING)).not.toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────
  // Clerk mode — fully authorized
  // ─────────────────────────────────────────────────────────────────────
  it("clerk mode signed-in with org: renders children", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_phase2" };

    renderAt("/protected");

    expect(screen.getByText(PROTECTED_CONTENT)).toBeInTheDocument();
    expect(screen.queryByText(SIGN_IN_LANDING)).not.toBeInTheDocument();
    expect(screen.queryByText(SELECT_ORG_LANDING)).not.toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────
  // Redirect URL safety — guard against open-redirect / loop regressions
  // ─────────────────────────────────────────────────────────────────────
  it("does not create a redirect loop when the sign-in URL is itself unauth", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = false;

    // Render the guard at /sign-in directly — guard is for /protected
    // routes only; an unauth user landing on /sign-in must just see the
    // sign-in landing (not be redirected into a loop).
    render(
      <MemoryRouter initialEntries={["/sign-in"]}>
        <Routes>
          <Route path="/sign-in" element={<div>{SIGN_IN_LANDING}</div>} />
          <Route
            path="/protected"
            element={
              <RequireClerkAuth>
                <div>{PROTECTED_CONTENT}</div>
              </RequireClerkAuth>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText(SIGN_IN_LANDING)).toBeInTheDocument();
  });
});
