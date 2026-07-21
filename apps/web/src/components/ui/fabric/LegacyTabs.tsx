/**
 * LegacyTabs — Simple string-based tab bar.
 *
 * Use shadcn Tabs (`@/components/ui/tabs`) for new code.
 * This component is kept for existing callers that pass string arrays.
 * Migrated from WfPrimitives shim.
 */
import { cn } from "@/lib/utils";

export interface LegacyTabsProps {
  tabs: string[];
  active: string;
  onChange: (t: string) => void;
}

export function Tabs({ tabs, active, onChange }: LegacyTabsProps) {
  return (
    <div className="mb-4 flex overflow-x-auto border-b border-border" role="tablist" aria-label="Section tabs">
      {tabs.map((tab) => (
        <button type="button"
          key={tab}
          onClick={() => onChange(tab)}
          role="tab"
          aria-selected={active === tab}
          tabIndex={active === tab ? 0 : -1}
          className={cn(
            "-mb-px shrink-0 border-b-2 px-4 py-2 vf-text-body-s font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            active === tab
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
