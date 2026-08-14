/**
 * MobilePersistentSidebar — Persistent icon-rail for viewports < 768px
 *
 * Design constraints:
 *   • No hamburger trigger, no sheet overlay — sidebar is always visible
 *   • 80px fixed width (w-20) to maximize screen real estate for content
 *   • Touch targets >= 44px (min-h-[56px] on nav buttons)
 *   • AccountPicker is pinned at top, user menu at bottom
 *   • Respects prefers-reduced-motion
 */

import { useState, useMemo, useCallback, useEffect } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { cn } from "@/lib/utils";
import { usePrefersReducedMotion } from "@/hooks/useAccessibility";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { AccountPicker } from "./AccountPicker";
import {
  ChevronDown,
  ChevronRight,
  Wrench,
  LogOut,
  User,
} from "lucide-react";
import type { NavItem, UserTier } from "@/navigation/navigationService";
import type { Account } from "@/hooks/useAccounts";
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface MobilePersistentSidebarProps {
  currentTier: UserTier;
  effectiveTier: UserTier;
  onTierChange: (tier: UserTier) => void;
  isAdvancedModeEnabled: boolean;
  onAdvancedModeToggle: (enabled: boolean) => void;
  navItems: NavItem[];
  accounts: Account[];
  selectedAccountId: string | null;
  onSelectAccount: (accountId: string) => void;
  isAccountsLoading?: boolean;
  accountsError?: Error | null;
  onCreateAccount?: () => void;
  user?: { name?: string; email?: string } | null;
  onSignOut?: () => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

import {
  resolveWorkspacePath,
  isItemVisible,
  isRouteActive,
} from "@/navigation/navigationService";

// ── Sub-components ────────────────────────────────────────────────────────────

interface MobileNavItemProps {
  item: NavItem;
  currentTier: UserTier;
  accountId: string | null;
  depth?: number;
}

function MobileNavItem({ item, currentTier, accountId, depth = 0 }: MobileNavItemProps) {
  const authorization = useAuthorizationSnapshot();
  const location = useLocation().pathname;
  const { tenantSlug } = useParams<{ tenantSlug: string }>();
  const resolvedPath = useMemo(() => resolveWorkspacePath(item.path, accountId, tenantSlug), [item.path, accountId, tenantSlug]);
  const isActive = isRouteActive(location, resolvedPath);
  const [open, setOpen] = useState(isActive);
  useEffect(() => { setOpen(isActive); }, [isActive]);

  const visibleChildren = useMemo(
    () => item.children?.filter(child => isItemVisible(child, currentTier) && authorization.hasEveryPermission([`tier:${child.tier}:access`])),
    [authorization, item.children, currentTier]
  );
  const hasVisibleChildren = visibleChildren && visibleChildren.length > 0;

  const handleClick = useCallback((e: React.MouseEvent) => {
    if (hasVisibleChildren) {
      e.preventDefault();
      setOpen(o => !o);
    }
  }, [hasVisibleChildren]);

  if (depth > 0) {
    return (
      <Link to={resolvedPath}>
        <div className={cn(
          "flex items-center gap-2 px-2 py-1.5 rounded-md vf-text-micro font-medium transition-colors select-none cursor-pointer",
          isActive ? "bg-sidebar-accent text-sidebar-accent-foreground" : "text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
        )}>
          <span className="truncate">{item.label}</span>
        </div>
      </Link>
    );
  }

  return (
    <div className="w-full">
      <Link to={resolvedPath}>
        <button type="button"
          onClick={handleClick}
          className={cn(
            "flex flex-col items-center justify-center gap-0.5 w-full py-2.5 px-1 rounded-lg transition-colors",
            "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground active:bg-sidebar-accent",
            "focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-sidebar-ring",
            isActive ? "bg-sidebar-accent text-sidebar-accent-foreground" : "text-sidebar-foreground/70",
            "min-h-[56px]"
          )}
          aria-current={isActive ? "page" : undefined}
          aria-expanded={hasVisibleChildren ? open : undefined}
        >
          <span className={cn("shrink-0", isActive ? "text-sidebar-primary" : "text-sidebar-foreground/60")}>
            {item.icon || <div className="size-4" />}
          </span>
          <span className="vf-text-micro font-medium leading-tight text-center px-0.5 truncate max-w-full">
            {item.label}
          </span>
          {hasVisibleChildren && (
            <span className="vf-text-micro text-sidebar-foreground/40">
              {open ? <ChevronDown size={8} /> : <ChevronRight size={8} />}
            </span>
          )}
        </button>
      </Link>

      {hasVisibleChildren && open && (
        <div className="px-1 pb-1 space-y-0.5">
          {visibleChildren.map(child => (
            <MobileNavItem key={child.path} item={child} currentTier={currentTier} accountId={accountId} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export function MobilePersistentSidebar({
  currentTier,
  effectiveTier,
  isAdvancedModeEnabled,
  onAdvancedModeToggle,
  navItems,
  accounts,
  selectedAccountId,
  onSelectAccount,
  isAccountsLoading,
  accountsError,
  onCreateAccount,
  user,
  onSignOut,
}: MobilePersistentSidebarProps) {
  const authorization = useAuthorizationSnapshot();
  const prefersReducedMotion = usePrefersReducedMotion();

  const visibleNavItems = useMemo(
    () => navItems.filter(item => isItemVisible(item, effectiveTier) && authorization.hasEveryPermission([`tier:${item.tier}:access`])),
    [authorization, navItems, effectiveTier]
  );

  const handleAdvancedToggle = useCallback(() => {
    onAdvancedModeToggle(!isAdvancedModeEnabled);
  }, [isAdvancedModeEnabled, onAdvancedModeToggle]);

  return (
    <nav
      className={cn(
        "flex flex-col h-svh w-20 shrink-0 bg-sidebar border-r border-sidebar-border z-20",
        !prefersReducedMotion && "transition-colors duration-200"
      )}
      aria-label="Mobile navigation"
    >
      {/* Account Picker */}
      <div className="shrink-0 p-1.5 border-b border-sidebar-border">
        <AccountPicker
          accounts={accounts}
          selectedAccountId={selectedAccountId}
          onSelectAccount={onSelectAccount}
          onCreateAccount={onCreateAccount}
          isLoading={isAccountsLoading}
          error={accountsError}
          variant="compact"
        />
      </div>

      {/* Navigation Items */}
      <ScrollArea className="flex-1 min-h-0">
        <nav className="flex flex-col items-center gap-0.5 p-1.5" aria-label="Main">
          {visibleNavItems.map(item => (
            <MobileNavItem
              key={item.id}
              item={item}
              currentTier={currentTier}
              accountId={selectedAccountId}
            />
          ))}
        </nav>
      </ScrollArea>

      {/* Footer: Tier + User */}
      <div className="shrink-0 border-t border-sidebar-border p-1.5 space-y-1.5">
        {currentTier !== "admin" && (
          <div className="flex flex-col items-center gap-1">
            <button type="button"
              onClick={handleAdvancedToggle}
              className={cn(
                "flex items-center justify-center w-full py-1.5 rounded-md vf-text-micro font-medium transition-colors",
                isAdvancedModeEnabled
                  ? "bg-accent/10 text-accent"
                  : "bg-muted text-muted-foreground hover:bg-sidebar-accent"
              )}
              aria-pressed={isAdvancedModeEnabled}
              title={isAdvancedModeEnabled ? "Advanced mode on" : "Advanced mode off"}
            >
              <Wrench size={10} className="mr-1" />
              {isAdvancedModeEnabled ? "Adv" : "Std"}
            </button>
          </div>
        )}

        {user && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button type="button"
                className="flex flex-col items-center justify-center w-full py-2 rounded-lg transition-colors hover:bg-sidebar-accent focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-sidebar-ring"
                aria-label={`User menu for ${user.name || user.email}`}
              >
                <Avatar className="size-7">
                  <AvatarFallback className="bg-sidebar-primary text-sidebar-primary-foreground vf-text-micro font-bold">
                    {user.name?.charAt(0)?.toUpperCase() || <User size={12} />}
                  </AvatarFallback>
                </Avatar>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent side="right" align="end" className="w-56">
              <div className="px-2 py-1.5">
                <p className="text-sm font-medium">{user.name || "User"}</p>
                <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              </div>
              {onSignOut && (
                <DropdownMenuItem onClick={onSignOut} className="text-destructive focus:text-destructive cursor-pointer">
                  <LogOut size={14} className="mr-2" />Sign out
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </nav>
  );
}

export default MobilePersistentSidebar;
