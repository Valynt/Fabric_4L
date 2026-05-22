
import {
  Home,
  Building2,
  Radar,
  Target,
  GitBranch,
  FileText,
  TrendingUp,
  FlaskConical,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import { NAV_SCHEMA } from "@/navigation/navSchema";

interface LeftNavigationProps {
  collapsed: boolean;
  onToggle: () => void;
}

const NAV_ICONS = {
  home: Home,
  accounts: Building2,
  intelligence: Radar,
  "intel-signals": Radar,
  "intel-opportunities": Target,
  "intel-drivers": GitBranch,
  "intel-evidence": FileText,
  "intel-scenarios": FlaskConical,
  "intel-business-case": FileText,
  "intel-realization": TrendingUp,
} as const;

export function LeftNavigation({
  collapsed,
  onToggle,
}: LeftNavigationProps) {
  const { pathname } = useLocation();
  const accountMatch = pathname.match(/\/(?:intelligence|studio|hypothesis|drivers|calculator|value-case|realization)\/([^/]+)/);
  const accountId = accountMatch?.[1] || null;

  const navItems = NAV_SCHEMA
    .filter((item) => item.id === "home" || item.id === "accounts")
    .map((item) => ({ ...item, path: item.path }))
    .concat(
      (NAV_SCHEMA.find((item) => item.id === "intelligence")?.children ?? [])
        .filter((item) => [
          "intel-signals",
          "intel-opportunities",
          "intel-drivers",
          "intel-evidence",
          "intel-scenarios",
          "intel-business-case",
          "intel-realization",
        ].includes(item.id))
        .map((item) => ({
          ...item,
          path: accountId ? item.path.replace(":accountId", accountId) : "/accounts",
        }))
    );

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
        {navItems.map((item) => {
          const Icon = NAV_ICONS[item.id as keyof typeof NAV_ICONS] ?? Radar;

          return (
            <NavLink
              key={item.path}
              to={item.path}
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
