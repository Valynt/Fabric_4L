/**
 * IntelligenceWorkspaceTabs — Horizontal tab navigation bar
 *
 * Renders the persistent workspace tab bar. The five core value-case views
 * (Overview · Signals · Drivers · Evidence · Stakeholders) lead and are always
 * visible; advanced tabs follow after a divider. Every tab is a deep-linkable,
 * route-driven button so only the active tab's content swaps.
 */
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  getCoreTabDefs,
  getSecondaryTabDefs,
  getTabOrDefault,
} from "./workspaceTabRegistry";
import { useWorkspaceContext } from "./hooks/useWorkspaceContext";
import { workspacePath } from "./workspaceRoutes";
import type { WorkspaceTabDef } from "./types";

export default function IntelligenceWorkspaceTabs() {
  const { tenantSlug, accountId, tabId } = useWorkspaceContext();
  const activeTab = getTabOrDefault(tabId);
  const coreTabs = getCoreTabDefs();
  const secondaryTabs = getSecondaryTabDefs();

  const renderTab = (tab: WorkspaceTabDef, emphasized: boolean) => (
    <Link key={tab.id} to={workspacePath(tenantSlug ?? "", accountId ?? "", tab.id)}>
      <button
        role="tab"
        aria-selected={activeTab === tab.id}
        title={tab.description}
        className={cn(
          "px-3 py-2.5 font-semibold border-b-2 -mb-px transition-colors whitespace-nowrap",
          emphasized ? "vf-text-caption" : "vf-text-micro",
          activeTab === tab.id
            ? "border-primary text-primary"
            : "border-transparent text-muted-foreground hover:text-foreground"
        )}
      >
        {tab.label}
      </button>
    </Link>
  );

  return (
    <div
      className="flex items-stretch border-b border-border px-6 overflow-x-auto"
      role="tablist"
    >
      {coreTabs.map((tab) => renderTab(tab, true))}
      {secondaryTabs.length > 0 && (
        <span
          aria-hidden="true"
          className="mx-2 my-2 w-px shrink-0 self-center bg-border"
        />
      )}
      {secondaryTabs.map((tab) => renderTab(tab, false))}
    </div>
  );
}
