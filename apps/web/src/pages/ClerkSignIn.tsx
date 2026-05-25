/**
 * Sign-in page that hosts Clerk's <SignIn /> component.
 *
 * Mounted at /sign-in/* (Clerk needs a wildcard so it can render its own
 * sub-routes for password reset, MFA challenges, etc.). This page is only
 * useful when AUTH_PROVIDER=clerk; under legacy mode it renders a friendly
 * notice and a link to the legacy /login route.
 */
import { SignIn } from "@clerk/react";

import { ClerkDisabledNotice } from "@/auth/ClerkDisabledNotice";
import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";

export default function ClerkSignInPage() {
  const urls = getClerkUrls();

  if (!isClerkAuthEnabled()) {
    return <ClerkDisabledNotice action="sign-in" legacyRoute="/login" />;
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
