import { cn } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

export interface TabItem {
  id: string;
  label: string;
  icon?: LucideIcon;
}

interface TabNavProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  orientation?: "vertical" | "horizontal";
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
        className
      )}
      aria-label="Section navigation"
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
              "relative flex items-center gap-3 rounded-lg text-sm transition-all",
              isVertical ? "w-full pl-3 pr-3 py-2.5" : "px-4 py-2",
              isActive
                ? isVertical
                  ? "bg-primary/10 text-primary font-semibold"
                  : "bg-primary/10 text-primary font-semibold"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            {isVertical && isActive && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-primary" />
            )}
            {tab.icon && <tab.icon className={cn("shrink-0", isVertical ? "w-4 h-4" : "w-4 h-4")} />}
            <span className={isVertical ? "text-left" : ""}>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
