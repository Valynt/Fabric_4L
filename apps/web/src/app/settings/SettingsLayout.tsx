/**
 * SettingsLayout — Settings & Configuration Center Shell
 *
 * React Router-native layout. Renders child routes via <Outlet />.
 */
import { useMemo } from "react";
import { Link, Outlet, useLocation, useParams } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  settingsCategories,
  settingsNavigation,
  settingsAccessRules,
  settingsScreens,
  getSettingsCapabilityForPath,
  type SettingsCategoryKey,
} from "./schemas";
import { useSettingsAccess } from "./access";
import {
  User,
  CreditCard,
  Users,
  Database,
  Shield,
  FileText,
  AlertCircle,
  HelpCircle,
} from "lucide-react";

const CATEGORY_ICONS: Record<SettingsCategoryKey, React.ReactNode> = {
  personal: <User className="h-4 w-4" />,
  billing: <CreditCard className="h-4 w-4" />,
  teamAccess: <Users className="h-4 w-4" />,
  dataIntegrations: <Database className="h-4 w-4" />,
  governance: <Shield className="h-4 w-4" />,
};

/**
 * Strip tenant slug prefix from settings pathname
 * @param pathname - Full pathname including tenant slug
 * @returns Pathname with tenant prefix removed
 */
function stripTenantSettingsPrefix(pathname: string): string {
  return pathname.replace(/^\/t\/[^/]+(?=\/settings(?:\/|$))/, "");
}

/**
 * Build settings path with optional tenant slug prefix
 * @param tenantSlug - Optional tenant slug for multi-tenant routing
 * @returns Path builder function that prefixes tenant slug when needed
 */
function useSettingsPathBuilder(tenantSlug: string | undefined) {
  return (path: string) => {
    if (path.startsWith("/personal")) {
      return path;
    }
    return tenantSlug ? `/t/${tenantSlug}${path}` : path;
  };
}

/**
 * Determine active settings category from pathname
 * @param pathname - Current route pathname
 * @returns Active category object or first category as fallback
 */
function useActiveCategory(pathname: string) {
  return useMemo(() => {
    const settingsPath = stripTenantSettingsPrefix(pathname);
    if (settingsPath.startsWith("/settings/workspace") || settingsPath.startsWith("/settings/billing")) {
      return settingsCategories.find((cat) => cat.key === "billing") ?? settingsCategories[0];
    }
    for (const cat of settingsCategories) {
      if (settingsPath.startsWith(cat.basePath)) return cat;
    }
    return settingsCategories[0];
  }, [pathname]);
}

function useActiveSubnav(categoryBasePath: string) {
  return useMemo(() => {
    return (
      settingsNavigation.find((item) => item.path.startsWith(categoryBasePath))
        ?.children ?? []
    );
  }, [categoryBasePath]);
}

function useScreenMeta(pathname: string) {
  return useMemo(() => {
    const settingsPath = stripTenantSettingsPrefix(pathname);
    const screen = settingsScreens.find((s) => settingsPath.startsWith(s.route));
    const category = settingsCategories.find((c) =>
      settingsPath.startsWith(c.basePath)
    );
    const access = category
      ? settingsAccessRules[category.key as keyof typeof settingsAccessRules]
      : undefined;
    return { screen, category, access };
  }, [pathname]);
}

export function SettingsLayout() {
  const { pathname } = useLocation();
  const { tenantSlug } = useParams();
  const buildSettingsPath = useSettingsPathBuilder(tenantSlug);
  const settingsPath = stripTenantSettingsPrefix(pathname);
  const { hasCapability } = useSettingsAccess();
  const activeCategory = useActiveCategory(pathname);
  const visibleCategories = settingsCategories.filter((category) => {
    const accessRule = settingsAccessRules[category.key as keyof typeof settingsAccessRules];
    return hasCapability(accessRule.capability);
  });
  const subnavItems = useActiveSubnav(activeCategory.basePath).filter((item) => {
    const capability = getSettingsCapabilityForPath(item.path);
    return capability ? hasCapability(capability) : true;
  });
  const { screen, access } = useScreenMeta(pathname);

  return (
    <div className="h-full">
      {/* ── Page Header ── */}
      <div className="border-b bg-background px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              Settings / Control Plane
            </h1>
            <p className="text-xs text-muted-foreground">
              Canonical admin surfaces for tenant configuration, access control,
              billing, integrations, and governance.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to={buildSettingsPath("/settings/governance/audit")}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-xs font-medium hover:bg-accent"
            >
              <FileText className="h-3.5 w-3.5" />
              View audit trail
            </Link>
          </div>
        </div>
      </div>

      {/* ── Horizontal Category Tabs ── */}
      <div className="border-b bg-background px-6">
        <nav className="flex gap-1 -mb-px">
          {visibleCategories.map((cat) => {
            const isActive =
              cat.key === "billing"
                ? settingsPath.startsWith("/settings/workspace") || settingsPath.startsWith(cat.basePath)
                : settingsPath.startsWith(cat.basePath);
            return (
              <Link
                key={cat.key}
                to={buildSettingsPath(cat.basePath)}
                prefetch="intent"
                className={cn(
                  "inline-flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-xs font-medium transition-colors",
                  isActive
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                )}
              >
                {CATEGORY_ICONS[cat.key]}
                {cat.label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* ── Content Area: Subnav + Main + Right Rail ── */}
      <div className="flex">
        {/* Left Subnav */}
        <aside className="hidden w-56 shrink-0 border-r bg-muted/30 md:block">
          <div className="py-4 px-3 space-y-0.5">
            {subnavItems.map((item) => {
              const isActive = settingsPath === item.path;
              return (
                <Link
                  key={item.path}
                  to={buildSettingsPath(item.path)}
                  prefetch="intent"
                  className={cn(
                    "flex items-center rounded-md px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-accent font-medium text-accent-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </aside>

        {/* Main Screen Content */}
        <div className="flex-1 p-6">
          {screen && (
            <div className="mb-6">
              <h2 className="text-base font-semibold">{screen.title}</h2>
              <p className="text-sm text-muted-foreground">
                {screen.category}
              </p>
            </div>
          )}
          <Outlet />
        </div>

        {/* Right Rail */}
        <aside className="hidden w-64 shrink-0 border-l bg-muted/20 lg:block">
          <div className="space-y-4 p-4">
            {/* Scope */}
            <div className="rounded-lg border bg-background p-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Scope
              </h3>
              <p className="mt-1 text-sm font-medium capitalize">
                {activeCategory.scope}
              </p>
            </div>

            {/* RBAC Notes */}
            {access && (
              <div className="rounded-lg border bg-background p-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Access
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {access.rule}
                </p>
                {access.allowedRoles && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {access.allowedRoles.map((role) => (
                      <span
                        key={role}
                        className="inline-flex rounded-full border px-2 py-0.5 vf-text-micro font-medium capitalize"
                      >
                        {role.replace("_", " ")}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Warnings */}
            {access && access.restrictions.length > 0 && (
              <div className="rounded-lg border border-warning/20 bg-warning/10 p-3 dark:border-warning/30 dark:bg-warning/20">
                <div className="flex items-start gap-2">
                  <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning dark:text-warning" />
                  <div className="space-y-1">
                    <h3 className="text-xs font-semibold text-warning dark:text-warning">
                      Restrictions
                    </h3>
                    {access.restrictions.map((r: string, i: number) => (
                      <p
                        key={i}
                        className="vf-text-caption text-warning dark:text-warning"
                      >
                        • {r}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Help Text */}
            <div className="rounded-lg border bg-background p-3">
              <div className="flex items-center gap-2">
                <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                <h3 className="text-xs font-semibold text-muted-foreground">
                  Help
                </h3>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Each section owns its own mutation flow. Save and retry actions
                are handled inside the page instead of by a shell-level control.
              </p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
