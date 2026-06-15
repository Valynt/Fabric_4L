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
import { Navigate, useLocation } from "react-router-dom";

import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";

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
  if (param.startsWith("/") && !param.startsWith("//")) {
    return param;
  }
  return null;
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
  const urls = getClerkUrls();

  // Under legacy auth there is no ClerkProvider mounted and no Clerk session
  // to consult. Render a legacy-compatible placeholder that redirects to the
  // legacy login route so the app does not crash on the Clerk <SignIn />
  // component.
  if (!isClerkAuthEnabled()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <Navigate to="/login" replace />
      </div>
    );
  }

  return <ClerkSignInInner />;
}
