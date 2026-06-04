/**
 * Onboarding page — post sign-up entry point.
 *
 * This is a minimal placeholder that welcomes the user and guides them toward
 * workspace selection. A future iteration should implement the full onboarding
 * flow (team invites, value pack selection, first account creation, etc.).
 */
import { useUser } from "@clerk/react";
import { Button } from "@/components/ui/button";
import { useNavigation } from "@/hooks/useNavigation";

export default function OnboardingPage() {
  const { user } = useUser();
  const { navigateTo } = useNavigation();

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-8 p-6">
      <header className="text-center">
        <h1 className="text-3xl font-semibold tracking-tight">
          Welcome to Fabric4L
        </h1>
        <p className="mt-3 text-base text-muted-foreground">
          {user?.firstName
            ? `Great to have you here, ${user.firstName}.`
            : "Great to have you here."}{" "}
          Let&apos;s get your workspace set up.
        </p>
      </header>

      <div className="w-full rounded-lg border bg-card p-6 shadow-sm">
        <h2 className="text-lg font-medium">Next steps</h2>
        <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
          <li className="flex items-start gap-2">
            <span className="mt-0.5 h-2 w-2 rounded-full bg-primary" />
            Choose or create a workspace
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-0.5 h-2 w-2 rounded-full bg-primary" />
            Invite your team members
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-0.5 h-2 w-2 rounded-full bg-primary" />
            Connect your first data source
          </li>
        </ul>

        <div className="mt-6 flex justify-end">
          <Button onClick={() => navigateTo("workspaces")}>
            Choose a workspace
          </Button>
        </div>
      </div>
    </div>
  );
}
