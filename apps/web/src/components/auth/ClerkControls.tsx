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

type UserButtonProps = ComponentProps<typeof UserButton>;
type OrganizationSwitcherProps = ComponentProps<typeof OrganizationSwitcher>;
type SignInProps = ComponentProps<typeof SignIn>;
type SignUpProps = ComponentProps<typeof SignUp>;
type OrganizationProfileProps = ComponentProps<typeof OrganizationProfile>;

export function FabricUserButton(
  props: UserButtonProps
): ReactElement | null {
  if (!isClerkAuthEnabled()) {
    return null;
  }
  return (
    <UserButton
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
  props: OrganizationSwitcherProps
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
  props: SignInProps
): ReactElement | null {
  if (!isClerkAuthEnabled()) {
    return null;
  }
  return (
    <SignIn
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
  props: SignUpProps
): ReactElement | null {
  if (!isClerkAuthEnabled()) {
    return null;
  }
  return (
    <SignUp
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
  props: OrganizationProfileProps
): ReactElement | null {
  if (!isClerkAuthEnabled()) {
    return null;
  }
  return (
    <OrganizationProfile
      appearance={{
        elements: {
          card: "shadow-xl border border-border bg-card text-card-foreground rounded-xl",
        },
      }}
      {...props}
    />
  );
}
