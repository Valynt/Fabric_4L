import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { createWrapper } from '@/test-utils';
import { useTenantMembershipClerk, useTenantMembershipLegacy } from './useTenantMembership';
import { useOrganization } from '@clerk/react';
import { useAuthContext } from '@/contexts/AuthContext';

vi.mock('@clerk/react', () => ({ useOrganization: vi.fn() }));
vi.mock('@/contexts/AuthContext', () => ({ useAuthContext: vi.fn() }));

const mockUseOrganization = vi.mocked(useOrganization);
const mockUseAuthContext = vi.mocked(useAuthContext);

describe('useTenantMembership', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuthContext.mockReturnValue({ user: null, isLoading: false } as never);
    mockUseOrganization.mockReturnValue({ organization: null, isLoaded: true } as never);
  });

  it('returns membership for legacy auth success path', () => {
    mockUseAuthContext.mockReturnValue({
      user: { tenantSlug: 'acme' },
      isLoading: false,
    } as never);

    const { result } = renderHook(() => useTenantMembershipLegacy('acme'), { wrapper: createWrapper() });
    expect(result.current).toEqual({ isMemberOfTenant: true, isLoading: false });
  });

  it('returns false for missing tenant slug default path', () => {
    const { result } = renderHook(() => useTenantMembershipLegacy(undefined), { wrapper: createWrapper() });
    expect(result.current.isMemberOfTenant).toBe(false);
  });

  it('returns loading + false when clerk is enabled but org is not loaded', () => {
    mockUseOrganization.mockReturnValue({ organization: null, isLoaded: false } as never);

    const { result } = renderHook(() => useTenantMembershipClerk('acme'), { wrapper: createWrapper() });
    expect(result.current).toEqual({ isMemberOfTenant: false, isLoading: true });
  });

  it('returns false on clerk mismatch error path', () => {
    mockUseOrganization.mockReturnValue({
      organization: { slug: 'other-tenant' },
      isLoaded: true,
    } as never);

    const { result } = renderHook(() => useTenantMembershipClerk('acme'), { wrapper: createWrapper() });
    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });
});

describe('useTenantMembership additional edge cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuthContext.mockReturnValue({ user: null, isLoading: false } as never);
    mockUseOrganization.mockReturnValue({ organization: null, isLoaded: true } as never);
  });

  it('clerk membership returns false when tenant slug is missing', () => {
    const { result } = renderHook(() => useTenantMembershipClerk(undefined), { wrapper: createWrapper() });
    expect(result.current.isMemberOfTenant).toBe(false);
  });

  it('legacy membership returns false when there is no authenticated user', () => {
    const { result } = renderHook(() => useTenantMembershipLegacy('acme'), { wrapper: createWrapper() });
    expect(result.current).toEqual({ isMemberOfTenant: false, isLoading: false });
  });
});
