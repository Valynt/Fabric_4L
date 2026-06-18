/**
 * Behavior contract for <ClerkSignInPage />.
 *
 * Invariants under test:
 *   - Signed-in users redirect only after a fresh token check.
 *   - Redirect targets are app-internal and Clerk transient params are stripped.
 *   - Signed-out Clerk users render the custom shadcn-style login surface.
 *   - Email/password and OAuth buttons call Clerk's real custom-flow methods.
 *   - While Clerk is loading, neither the custom login screen nor a redirect occurs.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const mockAuthState = {
  isLoaded: true as boolean,
  isSignedIn: false as boolean,
  getToken: vi.fn(async () => "fresh-token") as ReturnType<typeof vi.fn>,
};

const mockSignOut = vi.fn(async () => undefined);
const mockSetActive = vi.fn(async () => undefined);
const mockSignInCreate = vi.fn(async () => ({
  status: "complete",
  createdSessionId: "sess_123",
})) as ReturnType<typeof vi.fn>;
const mockAuthenticateWithRedirect = vi.fn(async () => undefined) as ReturnType<typeof vi.fn>;

const mockUrls = {
  signInUrl: "/sign-in",
  signUpUrl: "/sign-up",
  afterSignInUrl: "/home",
  afterSignUpUrl: "/onboarding",
  selectOrgUrl: "/workspaces",
};

vi.mock("@clerk/react", () => ({
  AuthenticateWithRedirectCallback: () => <div data-testid="sso-callback" />,
  useAuth: () => ({
    isLoaded: mockAuthState.isLoaded,
    isSignedIn: mockAuthState.isSignedIn,
    getToken: mockAuthState.getToken,
  }),
  useClerk: () => ({
    signOut: mockSignOut,
    setActive: mockSetActive,
    client: {
      signIn: {
        create: mockSignInCreate,
        authenticateWithRedirect: mockAuthenticateWithRedirect,
      },
    },
  }),
}));

vi.mock("@/auth/clerkConfig", () => ({
  getClerkUrls: () => mockUrls,
}));

import ClerkSignInPage from "./ClerkSignIn";
import ClerkSsoCallbackPage from "./ClerkSsoCallback";

const HOME_MARKER = "HOME_PAGE_MARKER";
const ACCOUNTS_MARKER = "ACCOUNTS_PAGE_MARKER";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/sign-in/*" element={<ClerkSignInPage />} />
        <Route path="/sso-callback/*" element={<ClerkSsoCallbackPage />} />
        <Route path="/sign-up" element={<div>SIGN_UP_PAGE_MARKER</div>} />
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
    mockAuthState.getToken = vi.fn(async () => "fresh-token") as ReturnType<typeof vi.fn>;
    mockSignOut.mockClear();
    mockSetActive.mockClear();
    mockSignInCreate.mockReset();
    mockSignInCreate.mockResolvedValue({
      status: "complete",
      createdSessionId: "sess_123",
    });
    mockAuthenticateWithRedirect.mockReset();
    mockAuthenticateWithRedirect.mockResolvedValue(undefined);
  });

  it("redirects an already signed-in user to afterSignInUrl after confirming a fresh token", async () => {
    mockAuthState.isSignedIn = true;

    renderAt("/sign-in");

    expect(await screen.findByText(HOME_MARKER)).toBeInTheDocument();
    expect(mockAuthState.getToken).toHaveBeenCalledWith({ skipCache: true });
    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument();
  });

  it("honors a safe internal redirect_url for a signed-in user with a fresh token", async () => {
    mockAuthState.isSignedIn = true;

    renderAt("/sign-in?redirect_url=%2Ft%2Facme%2Faccounts");

    expect(await screen.findByText(ACCOUNTS_MARKER)).toBeInTheDocument();
    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument();
  });

  it("ignores an external redirect_url and falls back to afterSignInUrl", async () => {
    mockAuthState.isSignedIn = true;

    renderAt("/sign-in?redirect_url=https%3A%2F%2Fevil.example.com");

    expect(await screen.findByText(HOME_MARKER)).toBeInTheDocument();
    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument();
  });

  it("ignores a protocol-relative redirect_url and falls back to afterSignInUrl", async () => {
    mockAuthState.isSignedIn = true;

    renderAt("/sign-in?redirect_url=%2F%2Fevil.example.com");

    expect(await screen.findByText(HOME_MARKER)).toBeInTheDocument();
    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument();
  });

  it("strips Clerk transient params from redirect_url for signed-in users", async () => {
    mockAuthState.isSignedIn = true;

    renderAt("/sign-in?redirect_url=%2Ft%2Facme%2Faccounts%3F__clerk_handshake%3Dabc%26view%3Dmine");

    expect(await screen.findByText(ACCOUNTS_MARKER)).toBeInTheDocument();
    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument();
  });

  it("ignores redirect_url values that point back to /sign-in or /sso-callback", async () => {
    mockAuthState.isSignedIn = true;

    renderAt("/sign-in?redirect_url=%2Fsso-callback%3F__clerk_handshake%3Dabc");

    expect(await screen.findByText(HOME_MARKER)).toBeInTheDocument();
    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument();
  });

  it("does not redirect a stale signed-in state when Clerk cannot mint a fresh token", async () => {
    mockAuthState.isSignedIn = true;
    mockAuthState.getToken = vi.fn(async () => null) as ReturnType<typeof vi.fn>;

    renderAt("/sign-in?redirect_url=%2Fhome");

    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalledWith({ redirectUrl: "/sign-in" });
    });
    expect(screen.queryByText(HOME_MARKER)).not.toBeInTheDocument();
    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument();
  });

  it("does not redirect a stale signed-in state when Clerk token refresh rejects", async () => {
    mockAuthState.isSignedIn = true;
    mockAuthState.getToken = vi.fn(async () => {
      throw new Error("session missing");
    }) as ReturnType<typeof vi.fn>;

    renderAt("/sign-in?redirect_url=%2Fhome");

    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalledWith({ redirectUrl: "/sign-in" });
    });
    expect(screen.queryByText(HOME_MARKER)).not.toBeInTheDocument();
    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument();
  });

  it("renders the custom login screen for a signed-out Clerk user", () => {
    renderAt("/sign-in");

    expect(screen.getByRole("heading", { name: /welcome back/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continue with google/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /apple/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /microsoft/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByTestId("forgot-password-link")).toHaveAttribute("href", "/sign-in/forgot-password");
    expect(screen.getByTestId("signup-link")).toHaveAttribute("href", "/sign-up");
  });

  it("submits email and password through Clerk and redirects after setting the active session", async () => {
    const user = userEvent.setup();

    renderAt("/sign-in?redirect_url=%2Ft%2Facme%2Faccounts");

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "correct horse battery staple");
    await user.click(screen.getByTestId("login-submit"));

    expect(mockSignInCreate).toHaveBeenCalledWith({
      identifier: "alice@example.com",
      password: "correct horse battery staple",
    });
    await waitFor(() => {
      expect(mockSetActive).toHaveBeenCalledWith({ session: "sess_123" });
    });
    expect(await screen.findByText(ACCOUNTS_MARKER)).toBeInTheDocument();
  });

  it("shows a loading state while email sign-in is pending", async () => {
    let resolveCreate: (value: { status: string; createdSessionId: string }) => void = () => undefined;
    mockSignInCreate.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve;
        }),
    );
    const user = userEvent.setup();

    renderAt("/sign-in");

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByTestId("login-submit"));

    expect(screen.getByRole("button", { name: /signing in/i })).toBeDisabled();
    expect(screen.getByTestId("oauth-google")).toBeDisabled();

    resolveCreate({ status: "complete", createdSessionId: "sess_pending" });
    await waitFor(() => {
      expect(mockSetActive).toHaveBeenCalledWith({ session: "sess_pending" });
    });
  });

  it.each([
    ["oauth_google", "oauth-google"],
    ["oauth_apple", "oauth-apple"],
    ["oauth_microsoft", "oauth-microsoft"],
  ] as const)("starts the %s OAuth flow through Clerk", async (strategy, testId) => {
    const user = userEvent.setup();

    renderAt("/sign-in?redirect_url=%2Ft%2Facme%2Faccounts");

    await user.click(screen.getByTestId(testId));

    expect(mockAuthenticateWithRedirect).toHaveBeenCalledWith({
      strategy,
      redirectUrl: "/sso-callback",
      redirectUrlComplete: "/t/acme/accounts",
    });
  });

  it("renders a safe Clerk error message for email sign-in failures", async () => {
    mockSignInCreate.mockRejectedValue({ errors: [{ message: "Invalid email or password." }] });
    const user = userEvent.setup();

    renderAt("/sign-in");

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByTestId("login-submit"));

    expect(await screen.findByTestId("custom-login-error")).toHaveTextContent("Invalid email or password.");
    expect(screen.getByLabelText(/email/i)).toHaveAttribute("aria-invalid", "true");
  });

  it("shows an actionable error when Clerk needs another verification step", async () => {
    mockSignInCreate.mockResolvedValue({
      status: "needs_second_factor",
      createdSessionId: null,
    });
    const user = userEvent.setup();

    renderAt("/sign-in");

    await user.type(screen.getByLabelText(/email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByTestId("login-submit"));

    expect(await screen.findByTestId("custom-login-error")).toHaveTextContent(
      "Additional verification is required to complete sign-in.",
    );
    expect(mockSetActive).not.toHaveBeenCalled();
  });

  it("renders neither the custom login screen nor a redirect while Clerk is loading", () => {
    mockAuthState.isLoaded = false;
    mockAuthState.isSignedIn = false;

    renderAt("/sign-in");

    expect(screen.queryByText(/welcome back/i)).not.toBeInTheDocument();
    expect(screen.queryByText(HOME_MARKER)).not.toBeInTheDocument();
  });

  it("renders the Clerk SSO callback route", () => {
    renderAt("/sso-callback");

    expect(screen.getByTestId("sso-callback")).toBeInTheDocument();
  });
});
