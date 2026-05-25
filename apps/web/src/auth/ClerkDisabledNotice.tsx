/**
 * Fallback UI shown when Clerk auth is disabled but the user navigates
 * to a Clerk-specific route (e.g., /sign-in, /sign-up).
 */
import { Link } from "react-router-dom";

interface ClerkDisabledNoticeProps {
  action: "sign-in" | "sign-up";
  legacyRoute: string;
}

export function ClerkDisabledNotice({ action, legacyRoute }: ClerkDisabledNoticeProps) {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-xl font-semibold">Clerk {action} is disabled</h1>
      <p className="text-sm text-muted-foreground">
        This deployment is using the legacy authentication provider.
      </p>
      <Link
        to={legacyRoute}
        className="text-sm font-medium text-primary underline-offset-4 hover:underline"
      >
        Go to legacy {action === "sign-in" ? "login" : "sign-up"}
      </Link>
    </div>
  );
}
