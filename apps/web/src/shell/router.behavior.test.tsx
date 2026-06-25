import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import {
  RootRedirect,
  LegacyFlatRedirect,
  LegacyIntelligenceRedirect,
  LEGACY_FLAT_ROUTE_MAP,
} from "./router";
import { useAuthContext } from "@/contexts/AuthContext";
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

  it("legacy mode: unauthenticated root renders the public landing page", () => {
    setAuthProvider("legacy");
    mockAuthContext.isAuthenticated = false;
    renderRedirect();
    expect(screen.getByRole("heading", { name: /Turn account evidence/i, level: 1 })).toBeInTheDocument();
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

  it("legacy mode: remains on root while auth context is loading", () => {
    setAuthProvider("legacy");
    mockAuthContext.isLoading = true;
    renderRedirect();

    expect(screen.getByTestId("location").textContent).toBe("/");
    expect(screen.queryByTestId("home-page")).not.toBeInTheDocument();
    expect(screen.queryByTestId("login-page")).not.toBeInTheDocument();
  });

  it("clerk mode: signed-out root renders the public landing page", () => {
    setAuthProvider("clerk");
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = false;
    renderRedirect();
    expect(screen.getByRole("heading", { name: /Turn account evidence/i, level: 1 })).toBeInTheDocument();
  });

  it("clerk mode: signed-in user is redirected to /home", () => {
    setAuthProvider("clerk");
    mockClerkAuth.isLoaded = true;
    mockClerkAuth.isSignedIn = true;
    renderRedirect();
    expect(screen.getByTestId("home-page")).toBeInTheDocument();
  });

  it("clerk mode: remains on root while Clerk auth is loading", () => {
    setAuthProvider("clerk");
    mockClerkAuth.isLoaded = false;
    mockClerkAuth.isSignedIn = true;
    renderRedirect();

    expect(screen.getByTestId("location").textContent).toBe("/");
    expect(screen.queryByTestId("home-page")).not.toBeInTheDocument();
    expect(screen.queryByTestId("signin-page")).not.toBeInTheDocument();
  });
});

describe("Legacy flat-route redirects", () => {
  afterEach(() => {
    cleanup();
    setAuthProvider(undefined);
    vi.mocked(useAuthContext).mockReturnValue(mockAuthContext);
  });

  function renderWithPath(
    path: string,
    tenantSlug: string | null = "acme",
    options: { isLoading?: boolean } = {},
  ) {
    const ctx = {
      ...mockAuthContext,
      currentTenantSlug: tenantSlug,
      isLoading: options.isLoading ?? false,
    };
    vi.mocked(useAuthContext).mockReturnValue(ctx);
    return render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/login" element={<div data-testid="login-page">login</div>} />
          <Route path="/sign-in" element={<div data-testid="signin-page">signin</div>} />
          <Route path="/home" element={<div data-testid="home-page">home</div>} />
          <Route path="/workspaces" element={<div data-testid="workspaces-page">workspaces</div>} />
          <Route path="/discover/*" element={<LegacyFlatRedirect />} />
          <Route path="/accounts" element={<LegacyFlatRedirect />} />
          <Route path="/library/*" element={<LegacyFlatRedirect />} />
          <Route path="/context/*" element={<LegacyFlatRedirect />} />
          <Route path="/model/*" element={<LegacyFlatRedirect />} />
          <Route path="/governance/*" element={<LegacyFlatRedirect />} />
          <Route path="/settings/governance/*" element={<LegacyFlatRedirect />} />
          <Route
            path="/t/:tenantSlug/accounts"
            element={<div data-testid="accounts-page">accounts</div>}
          />
          <Route
            path="/t/:tenantSlug/accounts/:accountId/intelligence/:tabId"
            element={<div data-testid="intelligence-page">intelligence</div>}
          />
          <Route
            path="/t/:tenantSlug/context/ingestion/jobs"
            element={<div data-testid="jobs-page">jobs</div>}
          />
          <Route
            path="/t/:tenantSlug/context/extraction"
            element={<div data-testid="extraction-page">extraction</div>}
          />
          <Route
            path="/t/:tenantSlug/context/ontology/graph"
            element={<div data-testid="graph-page">graph</div>}
          />
          <Route
            path="/t/:tenantSlug/context/value-trees/explorer"
            element={<div data-testid="value-trees-page">value trees</div>}
          />
          <Route
            path="/t/:tenantSlug/context/agents"
            element={<div data-testid="agents-page">agents</div>}
          />
          <Route
            path="/t/:tenantSlug/context/models"
            element={<div data-testid="models-page">models</div>}
          />
          <Route
            path="/t/:tenantSlug/governance/traces"
            element={<div data-testid="governance-traces-page">traces</div>}
          />
          <Route
            path="/t/:tenantSlug/governance/benchmarks"
            element={<div data-testid="benchmarks-page">benchmarks</div>}
          />
          <Route
            path="/t/:tenantSlug/settings/governance/health"
            element={<div data-testid="settings-health-page">health</div>}
          />
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    );
  }

  it("/login redirects to /sign-in", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<Navigate to="/sign-in" replace />} />
          <Route path="/sign-in" element={<div data-testid="signin-page">signin</div>} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByTestId("signin-page")).toBeInTheDocument();
  });

  it.each(["/dashboard", "/blog"])("%s redirects to /home", (path) => {
    render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/dashboard" element={<Navigate to="/home" replace />} />
          <Route path="/blog" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<div data-testid="home-page">home</div>} />
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    );

    expect(screen.getByTestId("home-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/home");
  });

  it("/discover/jobs redirects to canonical tenant-scoped ingestion jobs", () => {
    renderWithPath("/discover/jobs");
    expect(screen.getByTestId("jobs-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/t/acme/context/ingestion/jobs");
  });

  it("/accounts redirects to canonical tenant-scoped accounts", () => {
    renderWithPath("/accounts");
    expect(screen.getByTestId("accounts-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/t/acme/accounts");
  });

  it("/accounts waits for tenant context instead of bouncing home while auth is loading", () => {
    renderWithPath("/accounts", null, { isLoading: true });
    expect(screen.getByTestId("location").textContent).toBe("/accounts");
    expect(screen.queryByTestId("home-page")).not.toBeInTheDocument();
  });

  it("/accounts redirects signed-in Clerk users without tenant context to workspace selection", () => {
    setAuthProvider("clerk");
    renderWithPath("/accounts", null);
    expect(screen.getByTestId("workspaces-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/workspaces");
  });

  it("/library/models redirects to canonical tenant-scoped models", () => {
    renderWithPath("/library/models");
    expect(screen.getByTestId("models-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/t/acme/context/models");
  });

  it("/context/extraction redirects to canonical tenant-scoped extraction", () => {
    renderWithPath("/context/extraction");
    expect(screen.getByTestId("extraction-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/t/acme/context/extraction");
  });

  it("/context/ontology/graph redirects to canonical tenant-scoped graph", () => {
    renderWithPath("/context/ontology/graph");
    expect(screen.getByTestId("graph-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/t/acme/context/ontology/graph");
  });

  it("/context/value-trees/explorer redirects to canonical tenant-scoped value trees", () => {
    renderWithPath("/context/value-trees/explorer");
    expect(screen.getByTestId("value-trees-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/t/acme/context/value-trees/explorer");
  });

  it("/context/agents redirects to canonical tenant-scoped agent workflows", () => {
    renderWithPath("/context/agents");
    expect(screen.getByTestId("agents-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/t/acme/context/agents");
  });

  it("/governance/traces redirects to canonical tenant-scoped governance traces", () => {
    renderWithPath("/governance/traces");
    expect(screen.getByTestId("governance-traces-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/t/acme/governance/traces");
  });

  it("/governance/benchmarks redirects to canonical tenant-scoped benchmarks", () => {
    renderWithPath("/governance/benchmarks");
    expect(screen.getByTestId("benchmarks-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/t/acme/governance/benchmarks");
  });

  it("/settings/governance/health redirects to canonical tenant-scoped settings health", () => {
    renderWithPath("/settings/governance/health");
    expect(screen.getByTestId("settings-health-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/t/acme/settings/governance/health");
  });

  it("falls back to /workspaces when tenant slug is unavailable in Clerk mode", () => {
    renderWithPath("/discover/jobs", null);
    expect(screen.getByTestId("workspaces-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe("/workspaces");
  });

  it.each(Object.entries(LEGACY_FLAT_ROUTE_MAP))(
    "%s redirects to %s",
    (legacyPath, canonicalPathTemplate) => {
      renderWithPath(legacyPath);
      expect(screen.getByTestId("location").textContent).toBe(
        canonicalPathTemplate.replace("{tenantSlug}", "acme")
      );
    }
  );
});

describe("Legacy intelligence redirect", () => {
  afterEach(() => cleanup());

  function renderIntelligence(path: string, tenantSlug: string | null = "acme") {
    const ctx = { ...mockAuthContext, currentTenantSlug: tenantSlug };
    vi.mocked(useAuthContext).mockReturnValue(ctx);
    return render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/home" element={<div data-testid="home-page">home</div>} />
          <Route
            path="/intelligence/:accountId/:tabId"
            element={<LegacyIntelligenceRedirect />}
          />
          <Route
            path="/t/:tenantSlug/accounts/:accountId/intelligence/:tabId"
            element={<div data-testid="intelligence-page">intelligence</div>}
          />
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    );
  }

  it("/intelligence/:accountId/:tabId redirects to canonical account-scoped intelligence", () => {
    renderIntelligence("/intelligence/acc-123/signals");
    expect(screen.getByTestId("intelligence-page")).toBeInTheDocument();
    expect(screen.getByTestId("location").textContent).toBe(
      "/t/acme/accounts/acc-123/intelligence/signals"
    );
  });

  it("falls back to /home when tenant slug is unavailable", () => {
    renderIntelligence("/intelligence/acc-123/signals", null);
    expect(screen.getByTestId("home-page")).toBeInTheDocument();
  });
});
