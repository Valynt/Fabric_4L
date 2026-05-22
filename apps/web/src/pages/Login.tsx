import { safeAsync } from '@/lib/async';
/**
 * Login Page — OIDC Authentication Entry Point
 *
 * Centered single-column card design with Apple/Google SSO.
 *
 * Codemap coverage:
 *  Trace 1 — Frontend Login Initiation: SSO buttons → AuthContext.initiateLogin()
 *  Trace 2 — OIDC Callback: code+state → handleCallback() → JWT + role
 *  Trace 3 — Role Normalization: handled by AuthContext → userTierStore
 *
 * Flow:
 * 1a. Email/password — available for local dev/test bypass only
 * 1b. SSO button → initiateLogin(tenantSlug) → IdP redirect (Trace 1)
 * 2.  /login/callback → handleCallback(code, state) → JWT exchange (Trace 2)
 * 3.  Role sync → userTierStore.setUserRole() (Trace 3)
 * 4.  Redirect to stored destination or /home
 */

import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuthContext } from '../contexts/AuthContext';
import { useNavigation } from '@/hooks';
import { LoginForm } from '../components/login-form';
import { getSSOTenantSlug } from '../config/auth';
import { sessionService } from '../services/sessionService';

export default function Login() {
  const { navigateTo } = useNavigation();
  const [searchParams] = useSearchParams();
  const auth = useAuthContext();
  const {
    isAuthenticated, isLoading,
    initiateLogin, handleCallback,
  } = auth;

  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // ── Trace 2: OIDC Callback handling ──────────────────────────────────────
  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const redirect = searchParams.get('redirect');
    const signup = searchParams.get('signup');

    // Show success message after signup redirect
    if (signup === 'success') {
      setSuccessMessage('Account created successfully. Please sign in.');
      // Clean up URL
      navigateTo('login', undefined, { replace: true });
    }

    // Preserve intended destination before IdP redirect
    if (redirect && !code) {
      sessionService.setPostLoginRedirect(redirect);
    }

    if (code && state) {
      safeAsync(handleCallbackFlow(code, state), "login.callback");
    }
  }, [searchParams]);

  // Skip login if already authenticated (Skill §3: "Skip login if session valid")
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      const redirect = sessionService.consumePostLoginRedirect();
      navigateTo(redirect ? redirect as string : 'home');
    }
  }, [isAuthenticated, isLoading]);

  /**
   * Trace 2: Exchange authorization code for JWT.
   * AuthContext.handleCallback validates CSRF state against sessionStorage,
   * calls AuthClient.exchangeCodeForTokens, persists session, and syncs role.
   */
  const handleCallbackFlow = async (code: string, state: string) => {
    setIsLoggingIn(true);
    setError(null);

    try {
      const success = await handleCallback(code, state);
      if (success) {
        const redirect = sessionService.consumePostLoginRedirect();
        navigateTo(redirect ? redirect as string : 'home');
      } else {
        setError('Authentication failed. Please try again.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setIsLoggingIn(false);
    }
  };

  /**
   * Email/password handler.
   * Development and test builds may use the local auth shortcut for instant auth.
   * Production builds are SSO-only until backend email/password auth is available.
   */
  const handleLogin = useCallback(async (_email: string, _password: string) => {
    setIsLoggingIn(true);
    setError(null);

    try {
      if (import.meta.env.DEV || import.meta.env.MODE === 'test') {
        auth.devBypass?.();
        navigateTo('home');
        return;
      }

      setError('Email/password sign-in is disabled in production. Continue with SSO.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoggingIn(false);
    }
  }, [auth, navigateTo]);

  /**
   * Trace 1: SSO button → OIDC redirect.
   * Maps provider key ("apple" | "google") to a tenant slug, then calls
   * AuthContext.initiateLogin(tenantSlug) which:
   *   1c. Calls AuthClient.initiateLogin() → fetch /auth/oidc/{tenant}/login
   *   1e. Stores CSRF state in sessionStorage
   *   1f. Redirects browser to IdP authorization URL
   */
  const handleSSOProvider = useCallback(async (provider: string) => {
    setIsLoggingIn(true);
    setError(null);

    const tenantSlug = getSSOTenantSlug(provider);
    if (!tenantSlug) {
      setError(`SSO provider "${provider}" is not configured.`);
      setIsLoggingIn(false);
      return;
    }

    try {
      await initiateLogin(tenantSlug);
      // Browser will redirect to IdP — page unloads here
    } catch (err) {
      setIsLoggingIn(false);
      if (err instanceof Error && err.message.toLowerCase().includes('not found')) {
        setError(`SSO provider not found. Please contact your administrator.`);
      } else {
        setError(err instanceof Error ? err.message : 'Could not connect to SSO provider. Try again or use email/password.');
      }
    }
  }, [initiateLogin]);

  const devOnlyLoginFormProps = import.meta.env.DEV || import.meta.env.MODE === 'test'
    ? {
        onDevBypass: () => {
          auth.devBypass?.();
          navigateTo('home');
        },
      }
    : {};

  // Show loading state while checking auth or handling callback
  if (isLoading || isLoggingIn) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-muted">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
          <p className="text-muted-foreground" role="status">
            {isLoggingIn ? 'Authenticating...' : 'Loading...'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-muted p-6 md:p-10">
      <div className="w-full max-w-sm">
        <LoginForm
          onLogin={handleLogin}
          onSSOProvider={handleSSOProvider}
          {...devOnlyLoginFormProps}
          isLoading={isLoggingIn}
          error={error}
          successMessage={successMessage}
        />
      </div>
    </div>
  );
}
