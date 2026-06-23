import {
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  LogOut,
  Settings,
  CreditCard,
} from "lucide-react";
import { useMatches, Link } from "react-router-dom";
import { useAuthContext } from "@/contexts/AuthContext";
import { SignInButton, SignUpButton, useAuth, useUser } from "@clerk/react";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

interface AppHeaderProps {
  leftNavCollapsed: boolean;
  onToggleLeftNav: () => void;
}

interface RouteHandle {
  title?: string;
  category?: string;
}

function useHeaderMeta(): { title: string; subtitle: string } {
  const matches = useMatches();

  // Find the deepest route that has handle metadata
  const routeWithMeta = [...matches].reverse().find(m => {
    const handle = m.handle as RouteHandle | undefined;
    return handle?.title || handle?.category;
  });

  const handle = routeWithMeta?.handle as RouteHandle | undefined;

  if (handle?.title) {
    return {
      title: handle.title,
      subtitle: handle.category || "",
    };
  }

  // Fallback: derive from pathname for routes without handle metadata
  const pathname = matches[matches.length - 1]?.pathname || "/";
  const segments = pathname.split("/").filter(Boolean);
  const lastSegment = segments[segments.length - 1] || "Home";

  const formatted = lastSegment
    .replace(/-/g, " ")
    .replace(/\b\w/g, c => c.toUpperCase());

  return { title: formatted, subtitle: "" };
}

function ClerkAuthControl() {
  if (!isClerkAuthEnabled()) return null;
  return <ClerkAuthControlInner />;
}

function ClerkAuthControlInner() {
  const { isSignedIn } = useAuth();
  const { user: clerkUser } = useUser();
  const { logout } = useAuthContext();
  const { currentTenantSlug } = useAuthContext();

  if (isSignedIn && clerkUser) {
    const displayName =
      clerkUser.firstName ||
      clerkUser.fullName ||
      clerkUser.primaryEmailAddress?.emailAddress?.split("@")[0] ||
      "User";

    const email = clerkUser.primaryEmailAddress?.emailAddress ?? "";

    const initials = displayName
      .split(/[\s.]+/)
      .map(n => n[0]?.toUpperCase())
      .join("")
      .slice(0, 1);

    const billingPath = currentTenantSlug
      ? `/t/${currentTenantSlug}/settings/billing`
      : "/settings";

    return (
      <UserMenuDropdown
        displayName={displayName}
        email={email}
        initials={initials}
        settingsPath="/settings"
        billingPath={billingPath}
        onLogout={logout}
      />
    );
  }

  return (
    <div className="flex items-center gap-2">
      <SignInButton mode="modal">
        <button
          type="button"
          className="inline-flex h-9 items-center justify-center rounded-md border px-4 text-sm font-medium hover:bg-accent"
        >
          Sign in
        </button>
      </SignInButton>
      <SignUpButton mode="modal">
        <button
          type="button"
          className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Sign up
        </button>
      </SignUpButton>
    </div>
  );
}

interface UserMenuDropdownProps {
  displayName: string;
  email: string;
  initials: string;
  settingsPath: string;
  billingPath: string;
  onLogout: () => void;
}

function UserMenuDropdown({
  displayName,
  email,
  initials,
  settingsPath,
  billingPath,
  onLogout,
}: UserMenuDropdownProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="inline-flex h-9 w-9 items-center justify-center rounded-full hover:opacity-80"
          aria-label="User menu"
        >
          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-amber-800 text-sm font-medium text-white">
              {initials}
            </AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-0.5">
            <p className="text-sm font-semibold">{displayName}</p>
            <p className="text-xs text-muted-foreground">{email}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to={settingsPath} className="cursor-pointer">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to={billingPath} className="cursor-pointer">
            <CreditCard className="mr-2 h-4 w-4" />
            Billing
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={onLogout}
          className="cursor-pointer text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 h-4 w-4" />
          Log out
          <DropdownMenuShortcut>⇧⌘Q</DropdownMenuShortcut>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function LegacyUserMenu() {
  const { user, logout, currentTenantSlug } = useAuthContext();

  if (!user) return null;

  const displayName = user.email
    .split("@")[0]
    .split(".")
    .map(n => n.charAt(0).toUpperCase() + n.slice(1))
    .join(" ");

  const initials = displayName
    .split(/[\s.]+/)
    .map(n => n[0]?.toUpperCase())
    .join("")
    .slice(0, 1);

  const billingPath = currentTenantSlug
    ? `/t/${currentTenantSlug}/settings/billing`
    : "/settings";

  return (
    <UserMenuDropdown
      displayName={displayName}
      email={user.email}
      initials={initials}
      settingsPath="/settings"
      billingPath={billingPath}
      onLogout={logout}
    />
  );
}

export function AppHeader({
  leftNavCollapsed,
  onToggleLeftNav,
}: AppHeaderProps) {
  const { title, subtitle } = useHeaderMeta();

  return (
    <header className="z-20 flex h-14 shrink-0 items-center justify-between border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          onClick={onToggleLeftNav}
          className="hidden h-9 w-9 items-center justify-center rounded-md border hover:bg-accent md:inline-flex"
          aria-label={
            leftNavCollapsed ? "Expand navigation" : "Collapse navigation"
          }
        >
          {leftNavCollapsed ? (
            <PanelLeftOpen className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </button>

        <div className="min-w-0">
          <div className="text-sm font-medium">{title}</div>
          {subtitle && (
            <div className="truncate text-xs text-muted-foreground">
              {subtitle}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          className="hidden h-9 items-center gap-2 rounded-md border px-3 text-sm text-muted-foreground hover:bg-accent md:inline-flex"
        >
          <Search className="h-4 w-4" />
          Search
        </button>

        {isClerkAuthEnabled() ? <ClerkAuthControl /> : <LegacyUserMenu />}
      </div>
    </header>
  );
}
