import { cn } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  iconClassName?: string;
  iconBgClassName?: string;
  sub?: string;
  subClassName?: string;
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
            iconBgClassName ?? "bg-muted"
          )}
        >
          <Icon className={cn("w-4 h-4", iconClassName ?? "text-muted-foreground")} />
        </div>
        <span className="text-[10px] text-muted-foreground uppercase font-medium tracking-wider">
          {label}
        </span>
      </div>
      <p className="text-2xl font-bold text-card-foreground">{value}</p>
      {sub && <p className={cn("text-[10px] mt-0.5", subClassName ?? "text-muted-foreground/60")}>{sub}</p>}
    </div>
  );
}
