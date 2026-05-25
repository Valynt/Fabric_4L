/**
 * Auth Context — Clerk-only authentication state
 *
 * Thin wrapper around Clerk's useAuth/useUser hooks that exposes a
 * legacy-compatible interface so existing consumers (UnifiedRouteGuard,
 * AppHeader, settings pages) continue to work without modification.
 */

import { createContext, useContext, useMemo } from 'react';
import { useAuth as useClerkAuth, useUser as useClerkUser, useOrganization } from '@clerk/react';
import { createFeatureLogger } from '@/lib/telemetry';
import { type UserInfo, UserInfoSchema } from '../schemas/auth';

export type { UserInfo } from '../schemas/auth';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserInfo | null;
  currentTenantSlug: string | null;
  accessToken: null;
  initiateLogin: (tenantSlug: string) => Promise<void>;
  handleCallback: (code: string, state: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  devBypass?: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);
const log = createFeatureLogger('auth-context');

function safeNavigate(path: string) {
  if (typeof window !== 'undefined') {
    window.location.href = path;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { isLoaded: authLoaded, isSignedIn } = useClerkAuth();
  const { isLoaded: userLoaded, user: clerkUser } = useClerkUser();
  const { organization } = useOrganization();

  const isLoading = !authLoaded || !userLoaded;

  const user: UserInfo | null = useMemo(() => {
    if (!clerkUser) return null;
    const primaryEmail = clerkUser.primaryEmailAddress?.emailAddress ?? '';
    const mapped: UserInfo = {
      id: clerkUser.id,
      email: primaryEmail,
      role: 'standard',
      tenantId: organization?.id ?? 'default',
      tenantSlug: organization?.slug ?? 'default',
    };
    const parsed = UserInfoSchema.safeParse(mapped);
    return parsed.success ? parsed.data : null;
  }, [clerkUser, organization]);

  const currentTenantSlug = organization?.slug ?? null;

  const initiateLogin = async () => {
    safeNavigate('/sign-in');
  };

  const handleCallback = async () => {
    // Clerk handles OAuth callbacks internally; no-op here
    return true;
  };

  const logout = async () => {
    try {
      const { useClerk } = await import('@clerk/react');
      const clerk = useClerk();
      await clerk.signOut({ redirectUrl: '/' });
    } catch (error) {
      log.error('Sign out failed', { error: String(error) });
      safeNavigate('/');
    }
  };

  const refreshToken = async () => {
    // Clerk handles token refresh automatically
    return true;
  };

  const value: AuthContextType = {
    isAuthenticated: authLoaded && !!isSignedIn,
    isLoading,
    user,
    currentTenantSlug,
    accessToken: null,
    initiateLogin,
    handleCallback,
    logout,
    refreshToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}
