/**
 * Sign-up page that hosts Clerk's <SignUp /> component.
 *
 * If a user is already signed in, this page redirects to the post-sign-in
 * landing URL *before* mounting <SignUp />. Clerk's <SignUp /> cannot render
 * for an already-authenticated single-session app and would otherwise emit a
 * development notice and perform an internal redirect.
 */
import { SignUp, useAuth } from "@clerk/react";
import { Navigate } from "react-router-dom";

import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";

function ClerkSignUpInner() {
  const urls = getClerkUrls();
  const { isLoaded, isSignedIn } = useAuth();

  // Avoid flashing <SignUp /> (and its notice) before Clerk resolves session.
  if (!isLoaded) {
    return null;
  }

  if (isSignedIn) {
    return <Navigate to={urls.afterSignInUrl} replace />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <SignUp
        routing="path"
        path={urls.signUpUrl}
        signInUrl={urls.signInUrl}
        fallbackRedirectUrl={urls.afterSignUpUrl}
      />
    </div>
  );
}

export default function ClerkSignUpPage() {
  const urls = getClerkUrls();

  // Under legacy auth there is no ClerkProvider mounted. Redirect to the
  // legacy sign-in route to avoid a runtime crash from <SignUp />.
  if (!isClerkAuthEnabled()) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <Navigate to="/login" replace />
      </div>
    );
  }

  return <ClerkSignUpInner />;
}
