/**
 * AdminStatCard — Standardized metric card for admin page stats rows.
 */
import { cn } from "@/lib/utils";

export type AdminStatColor = "default" | "success" | "warning" | "destructive" | "primary";

export interface AdminStatCardProps {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  color?: AdminStatColor;
  className?: string;
}

const COLOR_MAP: Record<AdminStatColor, string> = {
  default: "text-muted-foreground",
  success: "text-success",
  warning: "text-warning",
  destructive: "text-destructive",
  primary: "text-primary",
};

export function AdminStatCard({
  label,
  value,
  icon,
  color = "default",
  className,
}: AdminStatCardProps) {
  return (
    <div
      className={cn(
        "bg-card border border-border rounded-xl px-4 py-3",
        className
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        {icon && <span className={COLOR_MAP[color]}>{icon}</span>}
        <span className="vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">
          {label}
        </span>
      </div>
      <p
        className={cn(
          "text-2xl font-extrabold",
          COLOR_MAP[color],
          color === "default" && "text-foreground"
        )}
      >
        {value}
      </p>
    </div>
  );
}

export interface AdminStatsRowProps {
  children: React.ReactNode;
  className?: string;
  columns?: 2 | 3 | 4 | 5 | 6;
}

export function AdminStatsRow({
  children,
  className,
  columns = 4,
}: AdminStatsRowProps) {
  const gridCols = {
    2: "grid-cols-2",
    3: "grid-cols-3",
    4: "grid-cols-4",
    5: "grid-cols-5",
    6: "grid-cols-6",
  }[columns];

  return (
    <div
      className={cn(
        "grid gap-4 mb-6",
        gridCols,
        className
      )}
    >
      {children}
    </div>
  );
}
