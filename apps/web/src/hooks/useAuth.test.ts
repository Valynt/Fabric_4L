/**
 * useAuth Hook Tests
 *
 * Comprehensive tests for authentication operations including:
 * - useAuth: Authentication state and CSRF header helper
 * - useRequireAuth: Protected route redirects
 * - useAuthRedirect: 401 handling
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { createWrapper, createWrapperWithRouterPath } from '../test-utils';
import { useAuth, useRequireAuth, useAuthRedirect } from './useAuth';
import { useAuthContext, type UserInfo } from '../contexts/AuthContext';
import {
  authContextFixtures,
  userFixtures,
  csrfFixtures,
  pathFixtures,
} from '../test/fixtures/authFixtures';
import { setupCookieMock, csrfCookieHelpers } from '../test/utils/cookieMock';

// Mock react-router-dom at top level
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual as object,
    useNavigate: () => mockNavigate,
  };
});

// Mock the AuthContext
vi.mock('../contexts/AuthContext', async () => {
  const actual = await vi.importActual<typeof import('../contexts/AuthContext')>('../contexts/AuthContext');
  return {
    ...actual,
    useAuthContext: vi.fn(),
  };
});

const mockedUseAuthContext = vi.mocked(useAuthContext);

describe('useAuth', () => {
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

  describe('getCsrfHeaders', () => {
    it('returns X-CSRF-Token header when cookie is present', () => {
      mockedUseAuthContext.mockReturnValue(authContextFixtures.authenticated());

      // Set the CSRF cookie using the cookie mock utility
      csrfCookieHelpers.setCsrfToken(csrfFixtures.validToken, cookieMock);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.getCsrfHeaders()).toEqual({
        'X-CSRF-Token': csrfFixtures.validToken,
      });
    });

    it('returns empty object when CSRF cookie is absent', () => {
      mockedUseAuthContext.mockReturnValue(authContextFixtures.unauthenticated());

      // Ensure no CSRF token is set
      csrfCookieHelpers.clearCsrfToken(cookieMock);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.getCsrfHeaders()).toEqual({});
    });

    it('getAuthHeaders is no longer exposed — auth is cookie-based', () => {
      mockedUseAuthContext.mockReturnValue(authContextFixtures.unauthenticated());

      const wrapper = createWrapper();
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect((result.current as Record<string, unknown>).getAuthHeaders).toBeUndefined();
    });
  });

  describe('auth state exposure', () => {
    it('exposes all auth context values', () => {
      const mockUser = userFixtures.standard();
      const authState = authContextFixtures.authenticated(mockUser);

      mockedUseAuthContext.mockReturnValue(authState);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.accessToken).toBeNull();
      expect(result.current.logout).toBe(authState.logout);
      expect(result.current.initiateLogin).toBe(authState.initiateLogin);
      expect(result.current.handleCallback).toBe(authState.handleCallback);
      expect(result.current.refreshToken).toBe(authState.refreshToken);
    });

    it('handles loading state', () => {
      mockedUseAuthContext.mockReturnValue(authContextFixtures.loading());

      const wrapper = createWrapper();
      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.isAuthenticated).toBe(false);
    });
  });
});

describe('useRequireAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it('redirects to login when not authenticated and not loading', async () => {
    mockedUseAuthContext.mockReturnValue(authContextFixtures.unauthenticated());

    const wrapper = createWrapperWithRouterPath(pathFixtures.protected);
    renderHook(() => useRequireAuth(), { wrapper });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(pathFixtures.login, expect.anything());
    });
  });

  it('does not redirect when authenticated', async () => {
    const mockUser = userFixtures.standard();
    mockedUseAuthContext.mockReturnValue(authContextFixtures.authenticated(mockUser));

    const wrapper = createWrapperWithRouterPath(pathFixtures.protected);
    renderHook(() => useRequireAuth(), { wrapper });

    // Verify navigation is not triggered (with timeout for effect to run)
    await waitFor(() => expect(mockNavigate).not.toHaveBeenCalled(), {
      timeout: 100,
    });
  });

  it('does not redirect while auth state is loading', async () => {
    mockedUseAuthContext.mockReturnValue(authContextFixtures.loading());

    const wrapper = createWrapperWithRouterPath(pathFixtures.protected);
    renderHook(() => useRequireAuth(), { wrapper });

    // Verify navigation is not triggered while loading (with timeout for effect to run)
    await waitFor(() => expect(mockNavigate).not.toHaveBeenCalled(), {
      timeout: 100,
    });
  });

  it('waits for loading to complete before checking auth', async () => {
    const mockUser = userFixtures.standard();

    // Start with loading state
    mockedUseAuthContext.mockReturnValue(authContextFixtures.loading());

    const wrapper = createWrapperWithRouterPath(pathFixtures.protected);
    const { rerender } = renderHook(() => useRequireAuth(), { wrapper });

    // Initially should not redirect (still loading)
    expect(mockNavigate).not.toHaveBeenCalled();

    // Simulate auth state resolving to unauthenticated
    mockedUseAuthContext.mockReturnValue(authContextFixtures.unauthenticated());

    rerender();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(pathFixtures.login, expect.anything());
    });
  });
});

describe('useAuthRedirect', () => {
  const mockLogout = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
    mockLogout.mockClear();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it('handleUnauthorized clears auth and redirects to login', () => {
    const mockUser = userFixtures.standard({ tenantId: 't1', tenantSlug: 'tenant' });
    mockedUseAuthContext.mockReturnValue({
      ...authContextFixtures.authenticated(mockUser),
      logout: mockLogout,
    });

    const wrapper = createWrapper();
    const { result } = renderHook(() => useAuthRedirect(), { wrapper });

    result.current.handleUnauthorized();

    expect(mockLogout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith(pathFixtures.login, expect.anything());
  });

  it('handleUnauthorized can be called multiple times', () => {
    const mockUser = userFixtures.standard({ tenantId: 't1', tenantSlug: 'tenant' });
    mockedUseAuthContext.mockReturnValue({
      ...authContextFixtures.authenticated(mockUser),
      logout: mockLogout,
    });

    const wrapper = createWrapper();
    const { result } = renderHook(() => useAuthRedirect(), { wrapper });

    result.current.handleUnauthorized();
    result.current.handleUnauthorized();
    result.current.handleUnauthorized();

    expect(mockLogout).toHaveBeenCalledTimes(3);
    expect(mockNavigate).toHaveBeenCalledTimes(3);
    expect(mockNavigate).toHaveBeenCalledWith(pathFixtures.login, expect.anything());
  });
});
