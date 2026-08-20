/**
 * Themed Clerk UI Components & Organization Controls
 *
 * Provides standardized wrappers around Clerk's prebuilt components:
 * - <FabricUserButton />: User profile trigger + multi-session switch & logout
 * - <FabricOrganizationSwitcher />: B2B workspace switcher (personal workspaces hidden)
 * - <FabricSignIn />: Standardized sign-in component
 * - <FabricSignUp />: Standardized sign-up component
 * - <FabricOrganizationProfile />: Workspace & membership management
 */

import {
  OrganizationProfile,
  OrganizationSwitcher,
  SignIn,
  SignUp,
  UserButton,
} from "@clerk/react";
import type { ComponentProps, ReactElement } from "react";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";

interface FabricControlProps {
  className?: string;
}

export function FabricUserButton(
  props: ComponentProps<typeof UserButton> & FabricControlProps
): ReactElement | null {
  if (!isClerkAuthEnabled()) {
    return null;
  }
  return (
    <UserButton
      afterSignOutUrl="/sign-in"
      showName={false}
      appearance={{
        elements: {
          avatarBox: "h-8 w-8 rounded-full ring-1 ring-border shadow-xs",
          userButtonPopoverCard: "shadow-xl border border-border bg-card text-card-foreground rounded-xl",
          userButtonPopoverActionButton: "hover:bg-muted text-foreground transition-colors",
          userButtonPopoverActionButtonText: "font-medium text-sm",
        },
      }}
      {...props}
    />
  );
}

export function FabricOrganizationSwitcher(
  props: ComponentProps<typeof OrganizationSwitcher> & FabricControlProps
): ReactElement | null {
  if (!isClerkAuthEnabled()) {
    return null;
  }
  return (
    <OrganizationSwitcher
      hidePersonal={true}
      afterSelectOrganizationUrl="/home"
      afterCreateOrganizationUrl="/home"
      afterLeaveOrganizationUrl="/select-org"
      appearance={{
        elements: {
          rootBox: "flex items-center",
          organizationSwitcherTrigger:
            "flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors",
          organizationSwitcherPopoverCard:
            "shadow-xl border border-border bg-card text-card-foreground rounded-xl",
        },
      }}
      {...props}
    />
  );
}

export function FabricSignIn(
  props: ComponentProps<typeof SignIn> & FabricControlProps
): ReactElement | null {
  if (!isClerkAuthEnabled()) {
    return null;
  }
  return (
    <SignIn
      routing="path"
      path="/sign-in"
      signUpUrl="/sign-up"
      appearance={{
        elements: {
          card: "shadow-xl border border-border bg-card text-card-foreground rounded-xl",
          formButtonPrimary:
            "bg-primary text-primary-foreground hover:bg-primary/90 font-medium rounded-lg",
        },
      }}
      {...props}
    />
  );
}

export function FabricSignUp(
  props: ComponentProps<typeof SignUp> & FabricControlProps
): ReactElement | null {
  if (!isClerkAuthEnabled()) {
    return null;
  }
  return (
    <SignUp
      routing="path"
      path="/sign-up"
      signInUrl="/sign-in"
      appearance={{
        elements: {
          card: "shadow-xl border border-border bg-card text-card-foreground rounded-xl",
          formButtonPrimary:
            "bg-primary text-primary-foreground hover:bg-primary/90 font-medium rounded-lg",
        },
      }}
      {...props}
    />
  );
}

export function FabricOrganizationProfile(
  props: ComponentProps<typeof OrganizationProfile> & FabricControlProps
): ReactElement | null {
  if (!isClerkAuthEnabled()) {
    return null;
  }
  return (
    <OrganizationProfile
      routing="path"
      path="/organization-profile"
      appearance={{
        elements: {
          card: "shadow-xl border border-border bg-card text-card-foreground rounded-xl",
        },
      }}
      {...props}
    />
  );
}
