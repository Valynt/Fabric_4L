import { Link, useLocation, useParams } from "react-router-dom";
import { cn } from "@/lib/utils";

const ENABLE_EXPERIMENTAL_DRIVER_TABS =
  import.meta.env.VITE_ENABLE_DRIVER_TREE_EXPERIMENTAL_TABS === "true";

const TABS = [
  { key: "trees", label: "Trees" },
  { key: "evidence", label: "Evidence" },
  ...(ENABLE_EXPERIMENTAL_DRIVER_TABS
    ? [
        { key: "alternatives", label: "Alternatives" },
        { key: "solution-cost", label: "Solution Cost" },
      ]
    : []),
] as const;

interface DriverTreeShellProps {
  children: React.ReactNode;
}

export default function DriverTreeShell({ children }: DriverTreeShellProps) {
  const { tenantSlug = "", accountId = "" } = useParams<{
    tenantSlug: string;
    accountId: string;
  }>();
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const activeSubTab = searchParams.get("sub") ?? "trees";

  return (
    <div className="flex flex-col h-full">
      <div
        className="flex border-b border-border px-6"
        role="tablist"
        aria-label="Driver Tree sections"
      >
        {TABS.map((tab) => {
          const to = `/t/${tenantSlug}/accounts/${accountId}/studio/driver-tree?sub=${tab.key}`;
          const isActive = activeSubTab === tab.key;
          return (
            <Link
              key={tab.key}
              to={to}
              role="tab"
              aria-selected={isActive}
              className={cn(
                "px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors",
                isActive
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
      <div className="flex-1 overflow-y-auto p-6">{children}</div>
    </div>
  );
}
