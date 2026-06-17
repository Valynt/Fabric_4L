/**
 * Sign-in page that hosts Clerk's <SignIn /> component.
 *
 * Mounted at /sign-in/* so Clerk can render its own sub-routes for
 * password reset, MFA challenges, etc.
 *
 * If a user is already signed in, this page redirects to the post-sign-in
 * landing URL *before* mounting <SignIn />. Clerk's <SignIn /> cannot render
 * for an already-authenticated single-session app and would otherwise emit a
 * development notice and perform an internal redirect. Guarding here keeps the
 * home <-> sign-in transition clean and avoids that notice.
 */
import { SignIn, useAuth } from "@clerk/react";
import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";
import { LoginForm } from "@/components/login-form";

/**
 * Returns a safe, app-internal redirect target from the `redirect_url` query
 * param, or null when absent/unsafe. Only same-origin absolute paths (starting
 * with a single "/") are allowed to prevent open-redirect to external origins.
 */
function safeRedirectTarget(search: string): string | null {
  const param = new URLSearchParams(search).get("redirect_url");
  if (!param) {
    return null;
  }
  if (!param.startsWith("/") || param.startsWith("//")) {
    return null;
  }

  const url = new URL(param, "http://fabric.local");
  const keysToDelete: string[] = [];
  url.searchParams.forEach((_value, key) => {
    if (key.toLowerCase().startsWith("__clerk_")) {
      keysToDelete.push(key);
    }
  });
  keysToDelete.forEach((key) => url.searchParams.delete(key));

  if (url.pathname.startsWith("/sign-in")) {
    return null;
  }

  const normalizedSearch = url.searchParams.toString();
  const normalized = normalizedSearch ? `${url.pathname}?${normalizedSearch}` : url.pathname;
  return normalized;
}

function ClerkSignInInner() {
  const urls = getClerkUrls();
  const location = useLocation();
  const { isLoaded, isSignedIn } = useAuth();

  // Avoid flashing <SignIn /> (and its notice) before Clerk resolves session.
  if (!isLoaded) {
    return null;
  }

  if (isSignedIn) {
    const target = safeRedirectTarget(location.search) ?? urls.afterSignInUrl;
    return <Navigate to={target} replace />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <SignIn
        routing="path"
        path={urls.signInUrl}
        signUpUrl={urls.signUpUrl}
        fallbackRedirectUrl={urls.afterSignInUrl}
      />
    </div>
  );
}

export default function ClerkSignInPage() {
  const [legacyError, setLegacyError] = useState<string | null>(null);

  // Under legacy auth there is no ClerkProvider mounted and no Clerk session to
  // consult. Render the existing local login surface instead of redirecting
  // between /sign-in and /login.
  if (!isClerkAuthEnabled()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <LoginForm
          className="w-full max-w-md"
          error={legacyError}
          onLogin={async () => {
            setLegacyError("Legacy email and password sign-in is not available in this environment.");
          }}
          onSSOProvider={() => {
            setLegacyError("Single sign-on is not configured for legacy auth in this environment.");
          }}
        />
      </div>
    );
  }

  return <ClerkSignInInner />;
}
