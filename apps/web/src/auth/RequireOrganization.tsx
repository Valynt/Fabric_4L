/**
 * <RequireOrganization /> — Tenant-scoped route guard for Clerk auth.
 *
 * When Clerk is enabled, ensures the user has selected an active organization.
 * Redirects to /workspaces if no org is active. This is a no-op under legacy
 * auth where the concept of Clerk organizations does not exist.
 *
 * Usage: wrap tenant-scoped routes that require an org context.
 */
import { useOrganization, useUser } from "@clerk/react";
import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";

import { isClerkAuthEnabled } from "@/auth/clerkConfig";

interface RequireOrganizationProps {
  children: ReactNode;
}

function RequireOrganizationOrgCheck({ children }: RequireOrganizationProps) {
  if (!isClerkAuthEnabled()) {
    return <>{children}</>;
  }

  const { organization, isLoaded: orgLoaded } = useOrganization();

  if (!orgLoaded) {
    return (
      <div className="flex h-full min-h-[400px] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-primary" />
          <p className="text-sm text-muted-foreground">Verifying organization...</p>
        </div>
      </div>
    );
  }

  if (!organization) {
    return <Navigate to="/workspaces" replace />;
  }

  return <>{children}</>;
}

function RequireOrganizationInner({ children }: RequireOrganizationProps) {
  if (!isClerkAuthEnabled()) {
    return <>{children}</>;
  }

  const { isLoaded: userLoaded, isSignedIn } = useUser();

  if (!userLoaded) {
    return (
      <div className="flex h-full min-h-[400px] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-primary" />
          <p className="text-sm text-muted-foreground">Verifying organization...</p>
        </div>
      </div>
    );
  }

  if (!isSignedIn) {
    return <Navigate to="/sign-in" replace />;
  }

  return <RequireOrganizationOrgCheck>{children}</RequireOrganizationOrgCheck>;
}

export function RequireOrganization(props: RequireOrganizationProps) {
  if (!isClerkAuthEnabled()) {
    return <>{props.children}</>;
  }
  return <RequireOrganizationInner {...props} />;
}
