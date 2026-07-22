import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

export interface FilterBarProps {
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  onClearSearch?: () => void;
  filters?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
  activeFilterCount?: number;
}

export function FilterBar({
  searchPlaceholder = "Search...",
  searchValue,
  onSearchChange,
  onClearSearch,
  filters,
  actions,
  className,
  activeFilterCount,
}: FilterBarProps) {
  return (
    <div className={cn("flex flex-wrap items-center gap-3 p-4 border-b border-border bg-card", className)}>
      {(searchValue !== undefined || onSearchChange) && (
        <div className="relative flex-1 max-w-sm min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={(e) => onSearchChange?.(e.target.value)}
            className="h-8 pl-9 pr-9 text-sm"
          />
          {searchValue && (
            <button type="button"
              onClick={onClearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}
      {filters && <div className="flex items-center gap-2 flex-wrap">{filters}</div>}
      {activeFilterCount !== undefined && activeFilterCount > 0 && (
        <span className="vf-text-caption px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground font-medium">
          {activeFilterCount} active
        </span>
      )}
      {actions && <div className="flex items-center gap-2 ml-auto">{actions}</div>}
    </div>
  );
}
