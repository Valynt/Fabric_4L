/**
 * StatCard — Compact metric display with icon, label, value, and optional sub-text.
 *
 * UI Contract (Data):
 *   - `label`  : uppercase descriptor (e.g. "TOTAL ACCOUNTS")
 *   - `value`  : primary metric (string or number)
 *   - `icon`   : LucideIcon rendered inside a tinted background circle
 *   - `sub`    : optional secondary line (e.g. "+12% vs last quarter")
 *
 * UI Contract (Rendering):
 *   - Always renders a bordered card with consistent padding
 *   - Icon background and text color are independently customisable
 *   - Sub-text inherits muted styling unless overridden via `subClassName`
 *
 * Extracted from: _ui-prototype/app/src/components/blocks/stat-card.tsx
 */
import { cn } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

export interface StatCardProps {
  /** Uppercase descriptor label */
  label: string;
  /** Primary metric value */
  value: string | number;
  /** Lucide icon component */
  icon: LucideIcon;
  /** Override icon foreground colour */
  iconClassName?: string;
  /** Override icon background colour */
  iconBgClassName?: string;
  /** Optional secondary line below the value */
  sub?: string;
  /** Override sub-text colour */
  subClassName?: string;
  /** Additional wrapper classes */
  className?: string;
}

export function StatCard({
  label,
  value,
  icon: Icon,
  iconClassName,
  iconBgClassName,
  sub,
  subClassName,
  className,
}: StatCardProps) {
  return (
    <div className={cn("bg-card rounded-xl border border-border p-4", className)}>
      <div className="flex items-center gap-2 mb-2">
        <div
          className={cn(
            "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
            iconBgClassName ?? "bg-muted",
          )}
        >
          <Icon className={cn("w-4 h-4", iconClassName ?? "text-muted-foreground")} />
        </div>
        <span className="text-xs text-muted-foreground uppercase font-medium tracking-wider">
          {label}
        </span>
      </div>
      <p className="text-2xl font-bold text-card-foreground">{value}</p>
      {sub && (
        <p className={cn("text-xs mt-0.5", subClassName ?? "text-muted-foreground/60")}>
          {sub}
        </p>
      )}
    </div>
  );
}
