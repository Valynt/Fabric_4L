import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number;
  max?: number;
  className?: string;
  barClassName?: string;
  showLabel?: boolean;
  size?: "sm" | "md";
}

export function ProgressBar({
  value,
  max = 100,
  className,
  barClassName,
  showLabel = false,
  size = "md",
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className={cn("w-full", className)}>
      <div
        className={cn(
          "bg-muted rounded-full overflow-hidden",
          size === "sm" ? "h-1.5" : "h-2"
        )}
      >
        <div
          className={cn("h-full rounded-full transition-all", barClassName ?? "bg-primary")}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && <p className="text-[10px] text-muted-foreground mt-0.5 text-center">{Math.round(pct)}%</p>}
    </div>
  );
}
