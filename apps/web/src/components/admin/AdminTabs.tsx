/**
 * AdminTabs — Standardized horizontal tab navigation for admin pages.
 *
 * Replaces the repeated raw <button> tab implementations across admin pages.
 */
import { cn } from "@/lib/utils";
import { getTabA11yIds } from "./AdminTabPanel";

export interface AdminTab {
  id: string;
  label: string;
  icon?: React.ReactNode;
  count?: number;
}

export interface AdminTabsProps {
  tabs: AdminTab[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export function AdminTabs({ tabs, activeTab, onChange, className }: AdminTabsProps) {
  return (
    <div
      className={cn("flex items-center gap-1 border-b border-border", className)}
      role="tablist"
      aria-label="Admin page tabs"
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const { tabButtonId, panelId } = getTabA11yIds(tab.id);
        return (
          <button
            key={tab.id}
            id={tabButtonId}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={panelId}
            tabIndex={isActive ? 0 : -1}
            onKeyDown={(e) => {
              if (!tabs.length) return;
              if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
              e.preventDefault();

              const currentIndex = tabs.findIndex((t) => t.id === tab.id);
              if (currentIndex < 0) return;

              const nextIndex =
                e.key === "Home"
                  ? 0
                  : e.key === "End"
                    ? tabs.length - 1
                    : e.key === "ArrowRight"
                      ? (currentIndex + 1) % tabs.length
                      : (currentIndex - 1 + tabs.length) % tabs.length;

              const nextId = tabs[nextIndex]?.id;
              if (!nextId) return;

              onChange(nextId);
              document.getElementById(getTabA11yIds(nextId).tabButtonId)?.focus();
            }}
            onClick={() => onChange(tab.id)}
            className={cn(
              "relative px-4 py-2.5 vf-text-body-s font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
            )}
            aria-controls={panelId}
            onClick={() => onChange(tab.id)}
            className={cn(
              "relative px-4 py-2.5 vf-text-body-s font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
            )}
          >
            <span className="flex items-center gap-2">
              {tab.icon}
              {tab.label}
              {tab.count !== undefined && (
                <span
                  className={cn(
                    "px-1.5 py-0.5 rounded vf-text-micro",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "bg-muted text-muted-foreground"
                  )}
                >
                  {tab.count}
                </span>
              )}
            </span>
            {isActive && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t-full" />
            )}
          </button>
        );
      })}
    </div>
  );
}
