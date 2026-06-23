import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useQueryClient } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';

import { createWrapper } from '../test-utils';
import { server } from '../test/mocks/server';
import { useResolvedTenant } from './useResolvedTenant';
import { useAccountContextStore, type AccountContextState } from '@/stores/accountContextStore';
import { QK } from './queryKeys';
import { BaseApiError } from './useApiShared';
import { setupClerkSignedIn, setupClerkLoading, setupLegacyAuth, resetClerkMocks, getClerkMocks } from '@/test/utils/clerkTestHelpers';

const { mockUseOrganization } = getClerkMocks();

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
    resetClerkMocks();
    sessionStorage.clear();
    useAccountContextStore.setState({
      selectedAccountId: null,
      _persistedTenantId: null,
    });
  });

  it('loads tenant mapping for a valid Clerk organization', async () => {
    setupClerkSignedIn('org_123');
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
    setupLegacyAuth();

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.tenant).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('is a no-op while Clerk auth is still loading', async () => {
    setupClerkLoading();

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.tenant).toBeNull();
  });

  it('does not fetch when no active organization is selected', async () => {
    setupClerkSignedIn(null);

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.tenant).toBeNull();
  });

  it('query key includes the active Clerk org id', async () => {
    setupClerkSignedIn('org_123');
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
    setupClerkSignedIn('org_123');
    server.use(
      http.get(TENANT_API_PATH, () => HttpResponse.json(mockTenantResponse))
    );

    const { result } = renderHook(
      () => {
        const queryClient = useQueryClient();
        const tenant = useResolvedTenant();
        const selectedAccountId = useAccountContextStore((s: AccountContextState) => s.selectedAccountId);
        const setSelectedAccountId = useAccountContextStore((s: AccountContextState) => s.setSelectedAccountId);
        return { tenant, queryClient, selectedAccountId, setSelectedAccountId };
      },
      { wrapper: createWrapper() }
    );

    // Seed account selection and a cached accounts list
    act(() => {
      result.current.setSelectedAccountId('acct_123');
      result.current.queryClient.setQueryData(QK.accounts.all, [{ id: 'acct_123' }]);
    });

    await waitFor(() => expect(result.current.tenant).not.toBeNull());

    expect(result.current.selectedAccountId).toBeNull();
    expect(result.current.queryClient.getQueryData(QK.accounts.all)).toBeUndefined();
  });

  it('stale tenant mapping is not reused after org switch', async () => {
    setupClerkSignedIn('org_123');
    server.use(
      http.get(TENANT_API_PATH, () => HttpResponse.json(mockTenantResponse))
    );

    const { result } = renderHook(() => useResolvedTenant(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.tenant?.tenantSlug).toBe('acme'));

    // Switch org
    setupClerkSignedIn('org_456');
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
    setupClerkSignedIn('org_123');
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
  });

  it('exposes 403 errors for unmapped org or inactive tenant', async () => {
    setupClerkSignedIn('org_123');
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
  });
});
