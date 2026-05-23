/**
 * HorizontalTabWrapper — Tab navigation with URL state management
 *
 * UI Contract (Data):
 *   - `tabs` : Array of tab configurations with id, label, and content
 *   - `defaultTab` : Default tab id if none in URL
 *
 * UI Contract (Behavior):
 *   - Manages tab state in URL search params
 *   - Persists tab selection across navigation
 *   - Renders TabNav in horizontal orientation
 *   - Renders active tab content
 *
 * UI Contract (Rendering):
 *   - Horizontal tab navigation
 *   - Content area below tabs
 *   - URL-based tab state (e.g., ?tab=signals)
 *
 * Use Cases:
 *   - Workspace-level navigation (Signals, Evidence, Stakeholders, Value Drivers)
 *   - Multi-view pages (Summary, Details, Settings)
 *   - Any horizontal tab navigation that needs URL persistence
 */
import { useSearchParams } from "react-router-dom";
import { cn } from "@/lib/utils";
import { TabNav, type TabItem } from "./TabNav";

export interface TabConfig {
  id: string;
  label: string;
  content: React.ReactNode;
}

export interface HorizontalTabWrapperProps {
  tabs: TabConfig[];
  defaultTab?: string;
  className?: string;
}

export function HorizontalTabWrapper({ 
  tabs, 
  defaultTab,
  className 
}: HorizontalTabWrapperProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || defaultTab || tabs[0]?.id;
  
  const activeTabConfig = tabs.find(t => t.id === activeTab) || tabs[0];
  
  const tabItems: TabItem[] = tabs.map(tab => ({
    id: tab.id,
    label: tab.label,
  }));
  
  const handleTabChange = (id: string) => {
    setSearchParams({ tab: id });
  };
  
  return (
    <div className={cn("space-y-4", className)}>
      <TabNav
        tabs={tabItems}
        activeTab={activeTab}
        onChange={handleTabChange}
        orientation="horizontal"
      />
      <div key={activeTab} className="animate-in fade-in duration-200">
        {activeTabConfig?.content}
      </div>
    </div>
  );
}
