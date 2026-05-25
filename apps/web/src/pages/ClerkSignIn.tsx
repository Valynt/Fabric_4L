/**
 * Sign-in page that hosts Clerk's <SignIn /> component.
 *
 * Mounted at /sign-in/* so Clerk can render its own sub-routes for
 * password reset, MFA challenges, etc.
 */
import { SignIn } from "@clerk/react";
import { getClerkUrls } from "@/auth/clerkConfig";

export default function ClerkSignInPage() {
  const urls = getClerkUrls();

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
