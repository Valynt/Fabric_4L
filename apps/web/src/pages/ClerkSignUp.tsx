/**
 * Sign-up page that hosts Clerk's <SignUp /> component. See ClerkSignIn.tsx
 * for routing rationale.
 */
import { SignUp } from "@clerk/react";
import { Link } from "react-router-dom";

import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";

export default function ClerkSignUpPage() {
  const urls = getClerkUrls();

  if (!isClerkAuthEnabled()) {
    return (
      <div className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-4 p-6 text-center">
        <h1 className="text-xl font-semibold">Clerk sign-up is disabled</h1>
        <p className="text-sm text-muted-foreground">
          This deployment is using the legacy authentication provider.
        </p>
        <Link
          to="/signup"
          className="text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          Go to legacy sign-up
        </Link>
      </div>
    );
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
