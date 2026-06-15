/**
 * Organization selection / creation gate.
 *
 * The gateway requires an active Clerk org id to mint a
 * ValuePact AuthContext envelope. Users without an active org cannot reach
 * tenant-scoped routes; we send them here to pick or create one.
 */
import { OrganizationList } from "@clerk/react";
import { useOrganization } from "@clerk/react";
import { Navigate } from "react-router-dom";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";

const POST_ORG_REDIRECT_URL = "/home";

export default function SelectOrganizationPage() {
  // Clerk hooks may only be called inside <ClerkProvider>. In legacy mode the
  // workspace-selection concept does not exist, so redirect home immediately
  // without rendering the inner component that calls Clerk hooks.
  if (!isClerkAuthEnabled()) {
    return <Navigate to={POST_ORG_REDIRECT_URL} replace />;
  }
  return <SelectOrganizationInner />;
}

function SelectOrganizationInner() {
  const postOrgRedirectUrl = POST_ORG_REDIRECT_URL;
  const { isLoaded: orgLoaded, organization } = useOrganization();

  if (orgLoaded && organization) {
    return <Navigate to={postOrgRedirectUrl} replace />;
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center p-6">
      <header className="text-center">
        <h1 className="text-2xl font-semibold">Choose a workspace</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Pick an existing workspace or create a new one to continue.
        </p>
      </header>

      <div className="mt-8 w-full max-w-md">
        <OrganizationList
          hidePersonal
          afterSelectOrganizationUrl={postOrgRedirectUrl}
          afterCreateOrganizationUrl={postOrgRedirectUrl}
        />
      </div>
    </div>
  );
}
