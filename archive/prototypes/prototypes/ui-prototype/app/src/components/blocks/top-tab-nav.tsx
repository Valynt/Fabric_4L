import { cn } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

export interface TopTabItem {
  id: string;
  label: string;
  icon?: LucideIcon;
}

interface TopTabNavProps {
  tabs: TopTabItem[];
  activeTab: string;
  onChange: (id: string) => void;
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
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            role="tab"
            aria-selected={isActive}
            className={cn(
              "relative flex items-center gap-1.5 px-3 py-2 text-[13px] font-medium transition-colors",
              "-mb-px",
              isActive
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground/70"
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
