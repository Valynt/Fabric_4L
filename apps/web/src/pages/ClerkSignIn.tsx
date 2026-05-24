/**
 * Sign-in page that hosts Clerk's <SignIn /> component.
 *
 * Mounted at /sign-in/* (Clerk needs a wildcard so it can render its own
 * sub-routes for password reset, MFA challenges, etc.). This page is only
 * useful when AUTH_PROVIDER=clerk; under legacy mode it renders a friendly
 * notice and a link to the legacy /login route.
 */
import { SignIn } from "@clerk/react";
import { Link } from "react-router-dom";

import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";

export default function ClerkSignInPage() {
  const urls = getClerkUrls();

  if (!isClerkAuthEnabled()) {
    return (
      <div className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-4 p-6 text-center">
        <h1 className="text-xl font-semibold">Clerk sign-in is disabled</h1>
        <p className="text-sm text-muted-foreground">
          This deployment is using the legacy authentication provider. Use the
          legacy login page instead.
        </p>
        <Link
          to="/login"
          className="text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          Go to legacy login
        </Link>
      </div>
    );
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
