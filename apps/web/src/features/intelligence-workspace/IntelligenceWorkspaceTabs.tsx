/**
 * IntelligenceWorkspaceTabs — Horizontal tab navigation bar
 *
 * Renders all workspace tabs as deep-linkable route-driven buttons.
 */
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { getActiveTabDefs, getTabOrDefault } from "./workspaceTabRegistry";
import { useWorkspaceContext } from "./hooks/useWorkspaceContext";
import { workspacePath } from "./workspaceRoutes";

export default function IntelligenceWorkspaceTabs() {
  const { accountId, tabId } = useWorkspaceContext();
  const activeTab = getTabOrDefault(tabId);
  const tabs = getActiveTabDefs();

  return (
    <div className="flex border-b border-border px-6 overflow-x-auto" role="tablist">
      {tabs.map((tab) => (
        <Link key={tab.id} to={workspacePath(accountId ?? "", tab.id)}>
          <button
            role="tab"
            aria-selected={activeTab === tab.id}
            className={cn(
              "px-3 py-2.5 vf-text-caption font-semibold border-b-2 -mb-px transition-colors whitespace-nowrap",
              activeTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.label}
          </button>
        </Link>
      ))}
    </div>
  );
}
