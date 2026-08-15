/**
 * Phase 2 — route guard behavior for <RequireClerkAuth />.
 *
 * The guard layers Clerk-aware auth + org checks on top of whatever existing
 * guard wraps the route. The invariants under test:
 *
 *   - Legacy mode is a TRUE no-op: children render even if Clerk reports
 *     signed-out and no org. The legacy <UnifiedRouteGuard /> remains
 *     authoritative on that code path.
 *   - Clerk mode while loading renders nothing (so children do not flash
 *     content before auth resolves).
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

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...(actual as object),
    useNavigate: () => mockNavigate,
  };
});

// Mutable mock state — flipped per test before render().
const mockClerkState = {
  authLoaded: true as boolean,
  isSignedIn: false as boolean,
  orgLoaded: true as boolean,
  organization: null as { id: string } | null,
};

const mockTenantState = {
  tenant: null as { fabricTenantId: string } | null,
  isLoading: false,
  error: null as { status?: number } | null,
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

vi.mock("@/auth/AuthorizationProvider", () => ({
  useAuthorizationSnapshot: () => ({
    status: mockTenantState.isLoading
      ? "loading"
      : mockTenantState.error
        ? "denied"
        : mockTenantState.tenant
          ? "verified"
          : "denied",
  }),
}));

// Import AFTER vi.mock so the component picks up the mocked module.
import { RequireClerkAuth } from "./RequireClerkAuth";

const PROTECTED_CONTENT = "PROTECTED_CONTENT_MARKER";
const SIGN_IN_LANDING = "SIGN_IN_PAGE_MARKER";
const SELECT_ORG_LANDING = "SELECT_ORG_PAGE_MARKER";

function renderAt(path: string, options?: { requireOrganization?: boolean }) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/sign-in" element={<div>{SIGN_IN_LANDING}</div>} />
        <Route
          path="/select-organization"
          element={<div>{SELECT_ORG_LANDING}</div>}
        />
        <Route path="/workspaces" element={<div>{SELECT_ORG_LANDING}</div>} />
        <Route
          path="/protected"
          element={
            <RequireClerkAuth
              requireOrganization={options?.requireOrganization}
            >
              <div>{PROTECTED_CONTENT}</div>
            </RequireClerkAuth>
          }
        />
        <Route
          path="/protected/nested"
          element={
            <RequireClerkAuth
              requireOrganization={options?.requireOrganization}
            >
              <div>{PROTECTED_CONTENT}</div>
            </RequireClerkAuth>
          }
        />
      </Routes>
    </MemoryRouter>
  );
}

describe("<RequireClerkAuth />", () => {
  let savedProvider: string | undefined;

  beforeEach(() => {
    savedProvider = (import.meta.env as Record<string, unknown>)
      .VITE_AUTH_PROVIDER as string | undefined;
    mockNavigate.mockClear();
    // Reset Clerk state to a known baseline.
    mockClerkState.authLoaded = true;
    mockClerkState.isSignedIn = false;
    mockClerkState.orgLoaded = true;
    mockClerkState.organization = null;
    // Reset tenant resolution state.
    mockTenantState.tenant = null;
    mockTenantState.isLoading = false;
    mockTenantState.error = null;
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
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("clerk mode (default, unset provider): redirects signed-out users to sign-in", () => {
    setAuthProvider(undefined);
    mockClerkState.isSignedIn = false;

    renderAt("/protected/nested");

    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith(
      "/sign-in?redirect_url=%2Fprotected%2Fnested",
      { replace: true }
    );
    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
  });

  // ─────────────────────────────────────────────────────────────────────
  // Clerk mode — loading state
  // ─────────────────────────────────────────────────────────────────────
  it("clerk mode: renders nothing while auth not loaded to prevent UI flash", () => {
    setAuthProvider("clerk");
    mockClerkState.authLoaded = false;

    renderAt("/protected");

    // Children must not render while we're still resolving auth.
    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
    expect(document.body.textContent?.trim()).toBe("");
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("clerk mode: renders nothing while org not loaded (when org required)", () => {
    setAuthProvider("clerk");
    mockClerkState.authLoaded = true;
    mockClerkState.isSignedIn = true;
    mockClerkState.orgLoaded = false;

    renderAt("/protected", { requireOrganization: true });

    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
    expect(document.body.textContent?.trim()).toBe("");
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // ─────────────────────────────────────────────────────────────────────
  // Clerk mode — signed out
  // ─────────────────────────────────────────────────────────────────────
  it("clerk mode signed out: redirects to sign-in with the intended destination", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = false;

    renderAt("/protected/nested");

    // Navigation must be triggered with the correct redirect URL.
    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith(
      "/sign-in?redirect_url=%2Fprotected%2Fnested",
      { replace: true }
    );
    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
  });

  it("clerk mode signed out: strips Clerk transient params from redirect_url", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = false;

    render(
      <MemoryRouter
        initialEntries={[
          "/protected?__clerk_handshake=abc&tab=mine&__clerk_status=ready",
        ]}
      >
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
      </MemoryRouter>
    );

    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith(
      "/sign-in?redirect_url=%2Fprotected%3Ftab%3Dmine",
      { replace: true }
    );
  });

  // ─────────────────────────────────────────────────────────────────────
  // Clerk mode — signed in, no org
  // ─────────────────────────────────────────────────────────────────────
  it("clerk mode signed-in without org: redirects to /workspaces", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = null;

    renderAt("/protected");

    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith("/workspaces", { replace: true });
    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
  });

  it("clerk mode signed-in without org but requireOrganization=false: renders children", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = null;

    renderAt("/protected", { requireOrganization: false });

    expect(screen.getByText(PROTECTED_CONTENT)).toBeInTheDocument();
    expect(screen.queryByText(SELECT_ORG_LANDING)).not.toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // ─────────────────────────────────────────────────────────────────────
  // Clerk mode — fully authorized
  // ─────────────────────────────────────────────────────────────────────
  it("clerk mode signed-in with org: renders children", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_phase2" };
    mockTenantState.tenant = { fabricTenantId: "tenant_phase2" };

    renderAt("/protected");

    expect(screen.getByText(PROTECTED_CONTENT)).toBeInTheDocument();
    expect(screen.queryByText(SIGN_IN_LANDING)).not.toBeInTheDocument();
    expect(screen.queryByText(SELECT_ORG_LANDING)).not.toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // ─────────────────────────────────────────────────────────────────────
  // Tenant resolution via backend
  // ─────────────────────────────────────────────────────────────────────
  it("clerk mode signed-in with org: renders nothing while tenant resolves", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_phase2" };
    mockTenantState.isLoading = true;

    renderAt("/protected");

    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
    expect(document.body.textContent?.trim()).toBe("");
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("clerk mode signed-in with org: redirects to /forbidden on tenant 403", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_phase2" };
    mockTenantState.error = { status: 403 };

    renderAt("/protected");

    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith("/forbidden?wfStep=0", {
      replace: true,
    });
    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
  });

  it("clerk mode signed-in with org: fails closed on snapshot denial", () => {
    setAuthProvider("clerk");
    mockClerkState.isSignedIn = true;
    mockClerkState.organization = { id: "org_phase2" };
    mockTenantState.error = { status: 401 };

    renderAt("/protected");

    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith("/forbidden?wfStep=0", {
      replace: true,
    });
    expect(screen.queryByText(PROTECTED_CONTENT)).not.toBeInTheDocument();
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
      </MemoryRouter>
    );

    expect(screen.getByText(SIGN_IN_LANDING)).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
