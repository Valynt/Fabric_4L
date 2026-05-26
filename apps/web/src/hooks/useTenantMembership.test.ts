import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { createWrapper } from '@/test-utils';
import { useTenantMembership } from './useTenantMembership';
import { useOrganization } from '@clerk/react';
import { useAuthContext } from '@/contexts/AuthContext';
import { isClerkAuthEnabled } from '@/auth/clerkConfig';

vi.mock('@clerk/react', () => ({ useOrganization: vi.fn() }));
vi.mock('@/contexts/AuthContext', () => ({ useAuthContext: vi.fn() }));
vi.mock('@/auth/clerkConfig', () => ({ isClerkAuthEnabled: vi.fn() }));

const mockUseOrganization = vi.mocked(useOrganization);
const mockUseAuthContext = vi.mocked(useAuthContext);
const mockClerkEnabled = vi.mocked(isClerkAuthEnabled);

describe('useTenantMembership', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuthContext.mockReturnValue({ user: null, isLoading: false } as never);
    mockUseOrganization.mockReturnValue({ organization: null, isLoaded: true } as never);
    mockClerkEnabled.mockReturnValue(false);
  });

  it('returns membership for legacy auth success path', () => {
    mockUseAuthContext.mockReturnValue({
      user: { tenantSlug: 'acme' },
      isLoading: false,
    } as never);

    const { result } = renderHook(() => useTenantMembership('acme'), { wrapper: createWrapper() });
    expect(result.current).toEqual({ isMemberOfTenant: true, isLoading: false });
  });

  it('returns false for missing tenant slug default path', () => {
    const { result } = renderHook(() => useTenantMembership(undefined), { wrapper: createWrapper() });
    expect(result.current.isMemberOfTenant).toBe(false);
  });

  it('returns loading + false when clerk is enabled but org is not loaded', () => {
    mockClerkEnabled.mockReturnValue(true);
    mockUseOrganization.mockReturnValue({ organization: null, isLoaded: false } as never);

    const { result } = renderHook(() => useTenantMembership('acme'), { wrapper: createWrapper() });
    expect(result.current).toEqual({ isMemberOfTenant: false, isLoading: true });
  });

  it('returns false on clerk mismatch error path', () => {
    mockClerkEnabled.mockReturnValue(true);
    mockUseOrganization.mockReturnValue({
      organization: { slug: 'other-tenant' },
      isLoaded: true,
    } as never);

    const { result } = renderHook(() => useTenantMembership('acme'), { wrapper: createWrapper() });
    expect(result.current.isMemberOfTenant).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });
});
