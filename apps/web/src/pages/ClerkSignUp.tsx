/**
 * Sign-up page that hosts Clerk's <SignUp /> component.
 */
import { SignUp } from "@clerk/react";
import { getClerkUrls } from "@/auth/clerkConfig";

export default function ClerkSignUpPage() {
  const urls = getClerkUrls();

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
