import { safeAsync } from '@/lib/async';
/**
 * useAuth Hook — Authentication Operations
 *
 * Simplified interface for auth operations:
 * - Check authentication status
 * - Get CSRF header for mutating requests
 *
 * The session token is delivered via the httpOnly `vf_session` cookie and is
 * sent automatically by the browser. No Authorization header is needed.
 */

import { useAuthContext } from '../contexts/AuthContext';

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const key = `${name}=`;
  const match = document.cookie.split('; ').find((part) => part.startsWith(key));
  return match ? decodeURIComponent(match.slice(key.length)) : null;
}

export function useAuth() {
  const auth = useAuthContext();

  /**
   * Returns the X-CSRF-Token header for POST/PUT/PATCH/DELETE requests.
   * Returns an empty object when no CSRF token cookie is present.
   */
  const getCsrfHeaders = (): Record<string, string> => {
    const token = getCookie('vf_csrf_token');
    if (!token) return {};
    return { 'X-CSRF-Token': token };
  };

  return {
    ...auth,
    getCsrfHeaders,
  };
}

/**
 * useRequireAuth Hook — Redirect to login if not authenticated
 * 
 * Use this in protected route components at the top level.
 * Must follow React Hooks rules (call at component top level, not conditionally).
 * 
 * Example:
 *   function ProtectedPage() {
 *     useRequireAuth();
 *     return <div>Protected content</div>;
 *   }
 */
import { useEffect } from 'react';
import { useNavigation } from '@/hooks/useNavigation';

export function useRequireAuth() {
  const { isLoading, isAuthenticated } = useAuthContext();
  const { navigateTo } = useNavigation();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigateTo('login');
    }
  }, [isLoading, isAuthenticated, navigateTo]);
}

/**
 * Hook for handling 401 responses and redirecting to login
 */
export function useAuthRedirect() {
  const { navigateTo } = useNavigation();
  const { logout } = useAuthContext();

  const handleUnauthorized = () => {
    // logout is async (calls backend to clear cookie) but we navigate
    // immediately — local state is cleared synchronously before the
    // network call, so the redirect is safe without awaiting.
    safeAsync(logout(), "auth.logout");
    navigateTo('login');
  };

  return { handleUnauthorized };
}
