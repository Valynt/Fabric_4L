/**
 * TabNav — Section navigation with vertical and horizontal orientations.
 *
 * UI Contract (Data):
 *   - `tabs`      : ordered list of { id, label, icon? }
 *   - `activeTab` : id of the currently selected tab
 *   - `onChange`   : callback invoked with the new tab id on click
 *
 * UI Contract (Behavior):
 *   - Clicking a tab always calls `onChange(tab.id)` — the parent owns state
 *   - No internal state; fully controlled component
 *
 * UI Contract (Rendering):
 *   - Vertical: 48-unit wide sidebar with left-edge primary indicator bar
 *   - Horizontal: inline flex with primary-tinted active background
 *   - Each button has `role="tab"` and `aria-selected` for accessibility
 *   - Optional Lucide icon rendered before the label
 *
 * Note: This is a simpler, non-Radix alternative to `ui/tabs.tsx`.
 * Use this when you need a sidebar-style vertical tab list or a
 * lightweight horizontal switcher without Radix content panels.
 *
 * Extracted from: _ui-prototype/app/src/components/blocks/tab-nav.tsx
 */
import { cn } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

export interface TabItem {
  /** Unique tab identifier */
  id: string;
  /** Display label */
  label: string;
  /** Optional Lucide icon */
  icon?: LucideIcon;
}

export interface TabNavProps {
  /** Ordered list of tabs */
  tabs: TabItem[];
  /** Currently active tab id */
  activeTab: string;
  /** Selection callback */
  onChange: (id: string) => void;
  /** Layout orientation */
  orientation?: "vertical" | "horizontal";
  /** Additional wrapper classes */
  className?: string;
}

export function TabNav({
  tabs,
  activeTab,
  onChange,
  orientation = "vertical",
  className,
}: TabNavProps) {
  const isVertical = orientation === "vertical";

  return (
    <nav
      className={cn(
        isVertical ? "w-48 shrink-0 space-y-1" : "flex items-center gap-2",
        className,
      )}
      aria-label="Section navigation"
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button type="button"
            key={tab.id}
            onClick={() => onChange(tab.id)}
            role="tab"
            aria-selected={isActive}
            className={cn(
              "relative flex items-center gap-3 rounded-lg text-sm transition-all",
              isVertical ? "w-full pl-3 pr-3 py-2.5" : "px-4 py-2",
              isActive
                ? "bg-primary/10 text-primary font-semibold"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {isVertical && isActive && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full bg-primary" />
            )}
            {tab.icon && <tab.icon className="w-4 h-4 shrink-0" />}
            <span className={isVertical ? "text-left" : ""}>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
