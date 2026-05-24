/**
 * StudioTabs — Horizontal tab navigation for Value Studio workspace
 */
import { useParams, useLocation, Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { getActiveStudioTabDefs, getStudioTabOrDefault } from "./studioTabRegistry";

export default function StudioTabs() {
  const { tenantSlug, accountId, tabId } = useParams<{
    tenantSlug: string;
    accountId: string;
    tabId: string;
  }>();
  const activeTab = getStudioTabOrDefault(tabId);
  const tabs = getActiveStudioTabDefs();

  return (
    <div className="border-b border-border bg-background">
      <nav className="flex px-6 gap-1" aria-label="Value Studio tabs">
        {tabs.map((tab) => (
          <Link
            key={tab.id}
            to={`/t/${tenantSlug}/accounts/${accountId}/studio/${tab.id}`}
            className={cn(
              "relative px-3 py-2.5 text-sm font-medium transition-colors",
              "hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              activeTab === tab.id
                ? "text-foreground after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-primary"
                : "text-muted-foreground"
            )}
            aria-current={activeTab === tab.id ? "page" : undefined}
          >
            {tab.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
