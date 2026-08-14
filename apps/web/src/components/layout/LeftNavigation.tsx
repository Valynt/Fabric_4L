
import {
  Home,
  Building2,
  Radar,
  Lightbulb,
  FileText,
  Wrench,
  GitBranch,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { NavLink, useLocation, useParams } from "react-router-dom";
import { NAV_SCHEMA } from "@/navigation/navSchema";
import { AccountPicker } from "@/components/navigation/AccountPicker";
import { useAuthContext } from "@/contexts/AuthContext";
import { useAccounts } from "@/hooks";
import { useAccountContextStore } from "@/stores/accountContextStore";
import type { UserTier } from "@/hooks";
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";

interface LeftNavigationProps {
  collapsed: boolean;
  onToggle: () => void;
  currentTier?: UserTier;
  currentTenantSlug?: string | null;
}

const NAV_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  home: Home,
  accounts: Building2,
  intelligence: Radar,
  studio: Lightbulb,
  deliverables: FileText,
  "context-engine": Wrench,
  governance: GitBranch,
  "personal-settings": Settings,
  "tenant-settings": Settings,
};

function isItemVisible(itemTier: UserTier, userTier: UserTier): boolean {
  if (userTier === "admin") return true;
  if (userTier === "advanced") return itemTier !== "admin";
  if (userTier === "unknown") return itemTier === "standard";
  return itemTier === "standard";
}

function resolveNavPath(path: string, tenantSlug: string | undefined, accountId: string | null): string {
  let resolvedPath = path;
  if (tenantSlug) {
    resolvedPath = resolvedPath.replace(":tenantSlug", tenantSlug);
  }
  if (accountId) {
    resolvedPath = resolvedPath.replace(":accountId", accountId);
  }
  // Fallback for unresolved account-scoped paths
  if (resolvedPath.includes(":accountId")) {
    resolvedPath = tenantSlug ? `/t/${tenantSlug}/accounts` : "/accounts";
  }
  // Fallback for unresolved tenant-only paths
  if (resolvedPath.includes(":tenantSlug")) {
    resolvedPath = "/accounts";
  }
  return resolvedPath;
}

export function LeftNavigation({
  collapsed,
  onToggle,
  currentTier = "standard",
  currentTenantSlug,
}: LeftNavigationProps) {
  const { pathname } = useLocation();
  const { tenantSlug, accountId: urlAccountId } = useParams<{ tenantSlug: string; accountId: string }>();
  const selectedAccountId = useAccountContextStore(state => state.selectedAccountId);
  const setSelectedAccountId = useAccountContextStore(state => state.setSelectedAccountId);
  const { isAuthenticated, isLoading: authLoading } = useAuthContext();
  const authorization = useAuthorizationSnapshot();

  const accountId = urlAccountId ?? null;
  const resolvedTenantSlug = tenantSlug ?? currentTenantSlug ?? undefined;
  const shouldLoadAccounts = !authLoading && isAuthenticated && Boolean(resolvedTenantSlug);
  const { data: accountsData, isLoading: accountsLoading, error: accountsError } = useAccounts(
    { page_size: 100 },
    { enabled: shouldLoadAccounts, suppressAuthRedirect: true }
  );
  const accounts = accountsData?.items ?? [];

  const navItems = NAV_SCHEMA.reduce((acc, item) => {
    if (isItemVisible(item.tier, currentTier) && authorization.hasEveryPermission([`tier:${item.tier}:access`])) {
      acc.push({ ...item, path: resolveNavPath(item.path, resolvedTenantSlug, accountId) });
    }
    return acc;
  }, [] as Array<typeof NAV_SCHEMA[number] & { path: string }>);

  return (
    <aside
      aria-label="Primary sidebar"
      className={[
        "hidden h-screen shrink-0 border-r bg-muted/30 transition-all duration-300 md:flex md:flex-col",
        collapsed ? "w-16" : "w-64",
      ].join(" ")}
    >
      <div className="flex h-14 shrink-0 items-center justify-between border-b px-3">
        {!collapsed && (
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold">Value Engine</div>
            <div className="truncate text-xs text-muted-foreground">
              Fabric_4L
            </div>
          </div>
        )}

        <button
          type="button"
          onClick={onToggle}
          className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent"
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav aria-label="Primary navigation" className="flex-1 space-y-1 overflow-y-auto p-2">
        {!collapsed && (
          <div className="mb-2 border-b pb-2">
            <AccountPicker
              accounts={accounts}
              selectedAccountId={selectedAccountId}
              onSelectAccount={setSelectedAccountId}
              isLoading={accountsLoading}
              error={accountsError}
              variant="full"
            />
          </div>
        )}

        {navItems.map((item) => {
          const Icon = NAV_ICONS[item.id] ?? Radar;

          const isFallbackPath =
            item.path === "/accounts" || item.path === `/t/${tenantSlug}/accounts`;
          const sectionActive =
            !collapsed &&
            !isFallbackPath &&
            Boolean(item.children?.length) &&
            pathname.startsWith(item.path);

          const visibleChildren = sectionActive
            ? (item.children ?? []).reduce((acc, child) => {
                if (isItemVisible(child.tier, currentTier) && authorization.hasEveryPermission([`tier:${child.tier}:access`])) {
                  acc.push({ ...child, path: resolveNavPath(child.path, tenantSlug, accountId) });
                }
                return acc;
              }, [] as Array<NonNullable<typeof item.children>[number] & { path: string }>)
            : [];

          return (
            <div key={item.id}>
              <NavLink
                to={item.path}
                end={item.path.endsWith("/intelligence")}
                className={({ isActive }) =>
                  [
                    "flex h-10 items-center rounded-md px-3 text-sm transition-colors hover:bg-accent",
                    collapsed ? "justify-center" : "gap-3",
                    isActive
                      ? "bg-accent font-medium text-accent-foreground"
                      : "text-muted-foreground",
                  ].join(" ")
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </NavLink>

              {visibleChildren.length > 0 && (
                <div className="mt-0.5 space-y-0.5 border-l border-border pl-3 ml-5">
                  {visibleChildren.map((child) => (
                    <NavLink
                      key={child.id}
                      to={child.path}
                      className={({ isActive }) =>
                        [
                          "flex h-8 items-center rounded-md px-3 text-xs transition-colors hover:bg-accent",
                          isActive
                            ? "bg-accent font-medium text-accent-foreground"
                            : "text-muted-foreground",
                        ].join(" ")
                      }
                    >
                      <span className="truncate">{child.label}</span>
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="border-t p-2">
        <div
          className={[
            "rounded-md bg-background p-2",
            collapsed ? "text-center" : "",
          ].join(" ")}
        >
          <div className="text-xs font-medium">{collapsed ? "SC" : "Sarah Chen"}</div>
          {!collapsed && (
            <div className="truncate text-xs text-muted-foreground">
              sarah.chen@axiomrobotics.com
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
