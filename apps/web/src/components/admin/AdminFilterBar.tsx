/**
 * AdminFilterBar — Search + filter chips + actions for admin pages.
 */
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

export interface FilterChip {
  value: string;
  label: string;
}

export interface AdminFilterBarProps {
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  chips?: FilterChip[];
  chipValue?: string;
  onChipChange?: (value: string) => void;
  filters?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export function AdminFilterBar({
  searchPlaceholder = "Search...",
  searchValue,
  onSearchChange,
  chips,
  chipValue,
  onChipChange,
  filters,
  actions,
  className,
}: AdminFilterBarProps) {
  const hasSearch = searchValue !== undefined || onSearchChange;
  const hasActiveFilter =
    (searchValue && searchValue.length > 0) ||
    (chipValue && chipValue !== "all");

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-3 mb-4",
        className
      )}
    >
      {hasSearch && (
        <div className="relative flex-1 max-w-sm min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={(e) => onSearchChange?.(e.target.value)}
            className="h-9 pl-9 pr-9 text-sm bg-card border-border"
            aria-label={searchPlaceholder}
          />
          {searchValue && (
            <button
              type="button"
              onClick={() => onSearchChange?.("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}

      {chips && chips.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          {chips.map((chip) => {
            const active = chipValue === chip.value;
            return (
              <button
                key={chip.value}
                type="button"
                onClick={() => onChipChange?.(chip.value)}
                aria-pressed={active}
                className={cn(
                  "vf-text-caption px-2.5 py-1.5 rounded-full border capitalize transition-colors font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  active
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-card text-muted-foreground border-border hover:border-primary"
                )}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
      )}

      {filters && <div className="flex items-center gap-2 flex-wrap">{filters}</div>}

      {actions && (
        <div className="flex items-center gap-2 ml-auto flex-wrap">
          {actions}
        </div>
      )}

      {hasActiveFilter && (
        <button
          type="button"
          onClick={() => {
            onSearchChange?.("");
            onChipChange?.("all");
          }}
          className="vf-text-caption text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
