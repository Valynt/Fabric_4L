/**
 * AdminTabPanel — Accessible tab panel wrapper for admin pages.
 *
 * Pairs with AdminTabs to provide proper tabpanel semantics.
 */
import { cn } from "@/lib/utils";

export interface AdminTabPanelProps {
  tabId: string;
  activeTab: string;
  children: React.ReactNode;
  className?: string;
}

export function getTabA11yIds(tabId: string) {
  return {
    tabButtonId: `admin-tab-${tabId}`,
    panelId: `admin-panel-${tabId}`,
  };
}

export function AdminTabPanel({
  tabId,
  activeTab,
  children,
  className,
}: AdminTabPanelProps) {
  const { tabButtonId, panelId } = getTabA11yIds(tabId);
  const isActive = activeTab === tabId;

  return (
    <div
      id={panelId}
      role="tabpanel"
      aria-labelledby={tabButtonId}
      tabIndex={0}
      hidden={!isActive}
      className={cn(className)}
    >
      {isActive ? children : null}
    </div>
  );
}
