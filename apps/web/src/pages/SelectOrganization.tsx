/**
 * Organization selection / creation gate.
 *
 * The gateway requires an active Clerk org id to mint a
 * ValuePact AuthContext envelope. Users without an active org cannot reach
 * tenant-scoped routes; we send them here to pick or create one.
 */
import { OrganizationList } from "@clerk/react";
import { getClerkUrls } from "@/auth/clerkConfig";

export default function SelectOrganizationPage() {
  const urls = getClerkUrls();

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
          afterSelectOrganizationUrl={urls.afterSignInUrl}
          afterCreateOrganizationUrl={urls.afterSignInUrl}
        />
      </div>
    </div>
  );
}
