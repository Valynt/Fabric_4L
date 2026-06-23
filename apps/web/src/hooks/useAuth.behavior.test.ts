/**
 * useAuth behavior invariants — fail-closed contracts for authentication
 * primitives: CSRF header extraction, auth state exposure, and redirect handling.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { createWrapper, createWrapperWithRouterPath } from "@/test-utils";
import { useAuth, useRequireAuth, useAuthRedirect } from "./useAuth";
import { useAuthContext } from "@/contexts/AuthContext";
import { authContextFixtures, userFixtures, csrfFixtures, pathFixtures } from "@/test/fixtures/authFixtures";
import { setupCookieMock, csrfCookieHelpers } from "@/test/utils/cookieMock";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual as object,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("@/contexts/AuthContext", async () => {
  const actual = await vi.importActual<typeof import("@/contexts/AuthContext")>("@/contexts/AuthContext");
  return {
    ...actual,
    useAuthContext: vi.fn(),
  };
});

const mockedUseAuthContext = vi.mocked(useAuthContext);

describe("useAuth behavior invariants", () => {
  let cookieMock: ReturnType<typeof setupCookieMock>;

  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
    cookieMock = setupCookieMock();
  });

  afterEach(() => {
    vi.resetAllMocks();
    cookieMock.uninstall();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Allowed behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("authenticated user with CSRF cookie can obtain CSRF headers", () => {
    mockedUseAuthContext.mockReturnValue(authContextFixtures.authenticated());
    csrfCookieHelpers.setCsrfToken(csrfFixtures.validToken, cookieMock);

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    expect(result.current.getCsrfHeaders()).toEqual({
      "X-CSRF-Token": csrfFixtures.validToken,
    });
  });

  it("authenticated user state is fully exposed to consumers", () => {
    const mockUser = userFixtures.standard();
    const authState = authContextFixtures.authenticated(mockUser);
    mockedUseAuthContext.mockReturnValue(authState);

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.accessToken).toBeNull();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Denied behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user without CSRF cookie is denied CSRF headers", () => {
    mockedUseAuthContext.mockReturnValue(authContextFixtures.unauthenticated());
    csrfCookieHelpers.clearCsrfToken(cookieMock);

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    expect(result.current.getCsrfHeaders()).toEqual({});
  });

  it("getAuthHeaders is not exposed — auth is cookie-based", () => {
    mockedUseAuthContext.mockReturnValue(authContextFixtures.unauthenticated());

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    expect((result.current as Record<string, unknown>).getAuthHeaders).toBeUndefined();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Failure mode
  // ───────────────────────────────────────────────────────────────────────────
  it("loading state is exposed while auth resolves", () => {
    mockedUseAuthContext.mockReturnValue(authContextFixtures.loading());

    const { result } = renderHook(() => useAuth(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.isAuthenticated).toBe(false);
  });
});

describe("useRequireAuth behavior invariants", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Allowed behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("authenticated user is allowed to remain on protected route", async () => {
    const mockUser = userFixtures.standard();
    mockedUseAuthContext.mockReturnValue(authContextFixtures.authenticated(mockUser));

    const wrapper = createWrapperWithRouterPath(pathFixtures.protected);
    renderHook(() => useRequireAuth(), { wrapper });

    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Denied behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("unauthenticated user is redirected to login with return destination", async () => {
    mockedUseAuthContext.mockReturnValue(authContextFixtures.unauthenticated());

    const wrapper = createWrapperWithRouterPath(pathFixtures.protected);
    renderHook(() => useRequireAuth(), { wrapper });

    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(mockNavigate).toHaveBeenCalledWith(pathFixtures.login, expect.anything());
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Failure mode
  // ───────────────────────────────────────────────────────────────────────────
  it("redirect is deferred while auth state is loading", async () => {
    mockedUseAuthContext.mockReturnValue(authContextFixtures.loading());

    const wrapper = createWrapperWithRouterPath(pathFixtures.protected);
    renderHook(() => useRequireAuth(), { wrapper });

    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});

describe("useAuthRedirect behavior invariants", () => {
  const mockLogout = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
    mockLogout.mockClear();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Allowed behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("handleUnauthorized clears session and redirects to login", () => {
    const mockUser = userFixtures.standard({ tenantId: "t1", tenantSlug: "tenant" });
    mockedUseAuthContext.mockReturnValue({
      ...authContextFixtures.authenticated(mockUser),
      logout: mockLogout,
    });

    const { result } = renderHook(() => useAuthRedirect(), { wrapper: createWrapper() });

    result.current.handleUnauthorized();

    expect(mockLogout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith(pathFixtures.login, expect.anything());
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Failure mode
  // ───────────────────────────────────────────────────────────────────────────
  it("handleUnauthorized is idempotent across multiple invocations", () => {
    const mockUser = userFixtures.standard({ tenantId: "t1", tenantSlug: "tenant" });
    mockedUseAuthContext.mockReturnValue({
      ...authContextFixtures.authenticated(mockUser),
      logout: mockLogout,
    });

    const { result } = renderHook(() => useAuthRedirect(), { wrapper: createWrapper() });

    result.current.handleUnauthorized();
    result.current.handleUnauthorized();
    result.current.handleUnauthorized();

    expect(mockLogout).toHaveBeenCalledTimes(3);
    expect(mockNavigate).toHaveBeenCalledTimes(3);
  });
});
