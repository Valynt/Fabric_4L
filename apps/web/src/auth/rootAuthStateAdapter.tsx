import type { ReactNode } from "react";
import { useAuth as useClerkAuth } from "@clerk/react";

import { useAuthContext } from "@/contexts/AuthContext";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";

export interface RootAuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  unauthenticatedRedirectTo: "/login" | "/sign-in";
}

interface RootAuthStateAdapterProps {
  children: (state: RootAuthState) => ReactNode;
}

function LegacyRootAuthStateAdapter({ children }: RootAuthStateAdapterProps) {
  const { isLoading, isAuthenticated } = useAuthContext();

  return (
    <>
      {children({
        isLoading,
        isAuthenticated,
        unauthenticatedRedirectTo: "/login",
      })}
    </>
  );
}

function ClerkRootAuthStateAdapter({ children }: RootAuthStateAdapterProps) {
  const { isLoading: authContextLoading } = useAuthContext();
  const { isLoaded: clerkLoaded, isSignedIn } = useClerkAuth();

  return (
    <>
      {children({
        isLoading: !clerkLoaded || authContextLoading,
        isAuthenticated: clerkLoaded && !!isSignedIn,
        unauthenticatedRedirectTo: "/sign-in",
      })}
    </>
  );
}

export function RootAuthStateAdapter({ children }: RootAuthStateAdapterProps) {
  // Keep Clerk hooks isolated to the Clerk-only branch component so legacy mode
  // can render safely without a mounted ClerkProvider.
  if (!isClerkAuthEnabled()) {
    return <LegacyRootAuthStateAdapter>{children}</LegacyRootAuthStateAdapter>;
  }

  return <ClerkRootAuthStateAdapter>{children}</ClerkRootAuthStateAdapter>;
}
