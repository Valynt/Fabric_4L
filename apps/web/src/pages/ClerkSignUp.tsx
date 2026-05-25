/**
 * Sign-up page that hosts Clerk's <SignUp /> component. See ClerkSignIn.tsx
 * for routing rationale.
 */
import { SignUp } from "@clerk/react";

import { ClerkDisabledNotice } from "@/auth/ClerkDisabledNotice";
import { getClerkUrls, isClerkAuthEnabled } from "@/auth/clerkConfig";

export default function ClerkSignUpPage() {
  const urls = getClerkUrls();

  if (!isClerkAuthEnabled()) {
    return <ClerkDisabledNotice action="sign-up" legacyRoute="/signup" />;
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
