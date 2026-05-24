
import { PanelLeftClose, PanelLeftOpen, Search, Bell, User, LogOut, Settings, ChevronDown } from "lucide-react";
import { useMatches, Link } from "react-router-dom";
import { useAuthContext } from "@/contexts/AuthContext";
import { SignInButton, SignUpButton, UserButton, useAuth } from "@clerk/react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
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
  const routeWithMeta = [...matches].reverse().find((m) => {
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
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return { title: formatted, subtitle: "" };
}

function ClerkAuthControl() {
  const { isSignedIn } = useAuth();

  if (isSignedIn) {
    return <UserButton afterSignOutUrl="/" />;
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

function UserMenu() {
  const { user, logout } = useAuthContext();

  if (!user) return null;

  const initials = user.email
    .split("@")[0]
    .split(".")
    .map((n) => n[0]?.toUpperCase())
    .join("")
    .slice(0, 2);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="inline-flex h-9 items-center gap-2 rounded-md border px-2 hover:bg-accent"
          aria-label="User menu"
        >
          <Avatar className="h-6 w-6">
            <AvatarFallback className="text-[10px] bg-primary/10 text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>
          <span className="hidden max-w-[120px] truncate text-sm text-muted-foreground md:inline">
            {user.email.split("@")[0]}
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium">{user.email}</p>
            <p className="text-xs text-muted-foreground capitalize">{user.role}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/personal/profile" className="cursor-pointer">
            <User className="mr-2 h-4 w-4" />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to="/personal/notifications" className="cursor-pointer">
            <Bell className="mr-2 h-4 w-4" />
            Notifications
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to="/personal/preferences" className="cursor-pointer">
            <Settings className="mr-2 h-4 w-4" />
            Preferences
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout} className="cursor-pointer text-destructive focus:text-destructive">
          <LogOut className="mr-2 h-4 w-4" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
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
          aria-label={leftNavCollapsed ? "Expand navigation" : "Collapse navigation"}
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

        <ClerkAuthControl />
      </div>
    </header>
  );
}
