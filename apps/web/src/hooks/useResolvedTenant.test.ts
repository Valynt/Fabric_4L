import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useQueryClient } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { useAuth, useOrganization } from '@clerk/react';
import { createWrapper } from '../test-utils';
import { server } from '../test/mocks/server';
import { useResolvedTenant } from './useResolvedTenant';
import { useAccountContextStore, type AccountContextState } from '@/stores/accountContextStore';
import { QK } from './queryKeys';
import { BaseApiError } from './useApiShared';
import { isClerkAuthEnabled } from '@/auth/clerkConfig';

// Vitest hoists vi.mock to the top of the file; these must live in the test
// file (not in a helper) so that the module factory is registered before any
// imports are resolved.
vi.mock('@clerk/react', () => ({
  useAuth: vi.fn(() => ({ isLoaded: true, isSignedIn: false, getToken: vi.fn() })),
  useOrganization: vi.fn(() => ({ isLoaded: true, organization: null })),
}));
vi.mock('@/auth/clerkConfig', () => ({
  isClerkAuthEnabled: vi.fn(() => false),
  getClerkUrls: vi.fn(() => ({
    signInUrl: '/sign-in',
    signUpUrl: '/sign-up',
    afterSignInUrl: '/home',
    afterSignUpUrl: '/onboarding',
    selectOrgUrl: '/workspaces',
  })),
}));

// Use vi.mocked() on the imports from THIS file so we get the correct mock
// instances (the ones registered by the vi.mock factories above).
const mockUseAuth = vi.mocked(useAuth);
const mockUseOrganization = vi.mocked(useOrganization);
const mockIsClerkAuthEnabled = vi.mocked(isClerkAuthEnabled);

/** Convenience: set up Clerk mocks for a signed-in user with an active org. */
function localSetupClerkSignedIn(orgId: string | null): void {
  mockIsClerkAuthEnabled.mockReturnValue(true);
  mockUseAuth.mockReturnValue({
    isLoaded: true,
    isSignedIn: true,
    getToken: vi.fn(),
  } as unknown as ReturnType<typeof useAuth>);
  mockUseOrganization.mockReturnValue({
    isLoaded: true,
    organization: orgId ? { id: orgId, slug: 'acme' } : null,
  } as unknown as ReturnType<typeof useOrganization>);
}

/** Convenience: set up Clerk mocks for the loading state. */
function localSetupClerkLoading(): void {
  mockIsClerkAuthEnabled.mockReturnValue(true);
  mockUseAuth.mockReturnValue({
    isLoaded: false,
    isSignedIn: undefined,
    getToken: vi.fn(),
  } as unknown as ReturnType<typeof useAuth>);
  mockUseOrganization.mockReturnValue({
    isLoaded: false,
    organization: undefined,
  } as unknown as ReturnType<typeof useOrganization>);
}

/** Convenience: set up Clerk mocks for legacy (Clerk-disabled) mode. */
function localSetupLegacyAuth(): void {
  mockIsClerkAuthEnabled.mockReturnValue(false);
  mockUseAuth.mockReturnValue({
    isLoaded: true,
    isSignedIn: false,
    getToken: vi.fn(),
  } as unknown as ReturnType<typeof useAuth>);
  mockUseOrganization.mockReturnValue({
    isLoaded: true,
    organization: null,
  } as unknown as ReturnType<typeof useOrganization>);
}

/** Reset all mocks to the safe default (Clerk disabled, signed out). */
function localResetClerkMocks(): void {
  vi.clearAllMocks();
  mockIsClerkAuthEnabled.mockReturnValue(false);
  mockUseAuth.mockReturnValue({
    isLoaded: true,
    isSignedIn: false,
    getToken: vi.fn(),
  } as unknown as ReturnType<typeof useAuth>);
  mockUseOrganization.mockReturnValue({
    isLoaded: true,
    organization: null,
  } as unknown as ReturnType<typeof useOrganization>);
}

const TENANT_API_PATH = '/api/v1/auth/clerk/tenant';

const mockTenantResponse = {
  fabric_tenant_id: 'tenant-123',
  tenant_slug: 'acme',
  clerk_org_id: 'org_123',
  status: 'active',
  roles: ['admin'],
  permissions: ['read:accounts', 'write:accounts'],
};

describe('useResolvedTenant', () => {
  beforeEach(() => {
    localResetClerkMocks();
    sessionStorage.clear();
    useAccountContextStore.setState({
      fabricTenantId: null,
      selectedAccountId: null,
      authorizationStatus: 'unverified',
    });
  });

  it('loads tenant mapping for a valid Clerk organization', async () => {
    localSetupClerkSignedIn('org_123');
    server.use(
      http.get(TENANT_API_PATH, () => HttpResponse.json(mockTenantResponse))
    );

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.tenant).toEqual({
      fabricTenantId: 'tenant-123',
      tenantSlug: 'acme',
      clerkOrgId: 'org_123',
      status: 'active',
      roles: ['admin'],
      permissions: ['read:accounts', 'write:accounts'],
    });
    expect(result.current.error).toBeNull();
  });

  it('is a no-op when Clerk auth is disabled', async () => {
    localSetupLegacyAuth();

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.tenant).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('is a no-op while Clerk auth is still loading', async () => {
    localSetupClerkLoading();

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.tenant).toBeNull();
  });

  it('does not fetch when no active organization is selected', async () => {
    localSetupClerkSignedIn(null);

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.tenant).toBeNull();
  });

  it('query key includes the active Clerk org id', async () => {
    localSetupClerkSignedIn('org_123');
    server.use(
      http.get(TENANT_API_PATH, () => HttpResponse.json(mockTenantResponse))
    );

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.tenant).not.toBeNull());

    const queryClient = result.current;
    // Access is internal; we verify the key is org-specific by changing the org
    // and confirming the hook re-fetches rather than returning cached data.
    mockUseOrganization.mockReturnValue({
      isLoaded: true,
      organization: { id: 'org_456', slug: 'other' },
    } as unknown as ReturnType<typeof useOrganization>);

    server.use(
      http.get(TENANT_API_PATH, () =>
        HttpResponse.json({
          ...mockTenantResponse,
          fabric_tenant_id: 'tenant-456',
          clerk_org_id: 'org_456',
        })
      )
    );

    const { result: nextResult } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(nextResult.current.tenant?.fabricTenantId).toBe('tenant-456')
    );
  });

  it('clears selected account and invalidates account cache on org switch', async () => {
    // Start signed in with org_123 and let the first tenant query resolve.
    localSetupClerkSignedIn('org_123');
    server.use(
      http.get(TENANT_API_PATH, () => HttpResponse.json(mockTenantResponse))
    );

    const { result, rerender } = renderHook(
      () => {
        const queryClient = useQueryClient();
        const tenant = useResolvedTenant();
        const selectedAccountId = useAccountContextStore((s: AccountContextState) => s.selectedAccountId);
        const setSelectedAccountId = useAccountContextStore((s: AccountContextState) => s.setSelectedAccountId);
        return { tenant, queryClient, selectedAccountId, setSelectedAccountId };
      },
      { wrapper: createWrapper() }
    );

        // Wait for the first tenant query to resolve.
    await waitFor(() => expect(result.current.tenant).not.toBeNull());

    // Seed account selection and a cached accounts list to simulate a user
    // who has already selected an account in the previous org.
    // Use await act() to flush all pending effects before checking state.
    await act(async () => {
      result.current.setSelectedAccountId('acct_123');
      result.current.queryClient.setQueryData(QK.accounts.all, [{ id: 'acct_123' }]);
    });

    // Simulate an org switch: update the Clerk mock to return a different org,
    // then re-render the hook so the activeOrgId change is detected.
    localSetupClerkSignedIn('org_456');
    rerender();

    // The org-switch effect should clear the selected account and invalidate
    // the accounts cache.
    await waitFor(() => expect(result.current.selectedAccountId).toBeNull());
    expect(result.current.queryClient.getQueryData(QK.accounts.all)).toBeUndefined();
  });

  it('stale tenant mapping is not reused after org switch', async () => {
    localSetupClerkSignedIn('org_123');
    server.use(
      http.get(TENANT_API_PATH, () => HttpResponse.json(mockTenantResponse))
    );

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.tenant?.tenantSlug).toBe('acme'));

    // Switch org
    localSetupClerkSignedIn('org_456');
    server.use(
      http.get(TENANT_API_PATH, () =>
        HttpResponse.json({
          ...mockTenantResponse,
          fabric_tenant_id: 'tenant-456',
          tenant_slug: 'other',
          clerk_org_id: 'org_456',
        })
      )
    );

    const { result: nextResult } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(nextResult.current.tenant?.tenantSlug).toBe('other')
    );
    expect(nextResult.current.tenant?.fabricTenantId).toBe('tenant-456');
  });

  it('exposes 401 errors for missing/invalid token', async () => {
    localSetupClerkSignedIn('org_123');
    server.use(
      http.get(TENANT_API_PATH, () =>
        HttpResponse.json({ code: 'auth.token_missing', message: 'Authentication required.' }, { status: 401 })
      )
    );

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBeDefined();
    expect(result.current.error).toBeInstanceOf(BaseApiError);
    expect(result.current.error?.name).toBe('BaseApiError');
    expect(result.current.error?.message).toContain('401');
    expect(result.current.error?.statusCode).toBe(401);
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
  });

  it('exposes 403 errors for unmapped org or inactive tenant', async () => {
    localSetupClerkSignedIn('org_123');
    server.use(
      http.get(TENANT_API_PATH, () =>
        HttpResponse.json({ code: 'auth.tenant_unresolved', message: 'Tenant not resolved.' }, { status: 403 })
      )
    );

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBeDefined();
    expect(result.current.error).toBeInstanceOf(BaseApiError);
    expect(result.current.error?.statusCode).toBe(403);
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
  });
});
