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
    <div className="flex border-b border-border mb-4" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab}
          onClick={() => onChange(tab)}
          role="tab"
          aria-selected={active === tab}
          className={cn(
            "px-4 py-2 vf-text-body-s font-semibold border-b-2 -mb-px transition-colors",
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
