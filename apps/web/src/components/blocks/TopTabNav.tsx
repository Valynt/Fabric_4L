/**
 * TopTabNav — Horizontal underline tabs for subsection switching.
 *
 * UI Contract (Data):
 *   - `tabs`      : ordered list of { id, label, icon? }
 *   - `activeTab` : id of the currently selected tab
 *   - `onChange`   : callback invoked with the new tab id on click
 *
 * UI Contract (Behavior):
 *   - Fully controlled — parent owns `activeTab` state
 *   - Clicking a tab always calls `onChange(tab.id)`
 *
 * UI Contract (Rendering):
 *   - Horizontal bar with bottom border
 *   - Active tab has bold foreground text and a 2px primary underline
 *   - Inactive tabs are muted with hover transition
 *   - Optional Lucide icon at 60% opacity before the label
 *   - The underline sits flush with the bottom border via negative margin
 *
 * Extracted from: _ui-prototype/app/src/components/blocks/top-tab-nav.tsx
 */
import { cn } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

export interface TopTabItem {
  /** Unique tab identifier */
  id: string;
  /** Display label */
  label: string;
  /** Optional Lucide icon */
  icon?: LucideIcon;
}

export interface TopTabNavProps {
  /** Ordered list of tabs */
  tabs: TopTabItem[];
  /** Currently active tab id */
  activeTab: string;
  /** Selection callback */
  onChange: (id: string) => void;
  /** Additional wrapper classes */
  className?: string;
}

export function TopTabNav({ tabs, activeTab, onChange, className }: TopTabNavProps) {
  return (
    <nav
      className={cn("flex items-center gap-1 border-b border-border", className)}
      aria-label="Subsection tabs"
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
              "relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors",
              "-mb-px",
              isActive
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground/70",
            )}
          >
            {tab.icon && <tab.icon className="w-3.5 h-3.5 opacity-60" />}
            {tab.label}
            {isActive && (
              <span className="absolute bottom-0 left-2 right-2 h-[2px] bg-primary rounded-full" />
            )}
          </button>
        );
      })}
    </nav>
  );
}
