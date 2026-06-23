/**
 * ProgressBar — Lightweight determinate progress indicator.
 *
 * UI Contract (Data):
 *   - `value` : current progress (clamped to 0–max)
 *   - `max`   : upper bound (default 100)
 *
 * UI Contract (Rendering):
 *   - Always renders a rounded track with an inner fill bar
 *   - Fill width is a percentage of value/max, clamped to [0, 100]
 *   - Two sizes: "sm" (1.5 unit) and "md" (2 unit)
 *   - Optional centred percentage label below the bar
 *   - Bar colour is customisable via `barClassName` (defaults to primary)
 *
 * Note: This is a simpler alternative to the Radix-based `ui/progress.tsx`.
 * Use this when you need size variants, labels, or custom bar colours
 * without the overhead of the Radix primitive.
 *
 * Extracted from: _ui-prototype/app/src/components/blocks/progress-bar.tsx
 */
import { cn } from "@/lib/utils";

export interface ProgressBarProps {
  /** Current progress value */
  value: number;
  /** Maximum value (default 100) */
  max?: number;
  /** Additional wrapper classes */
  className?: string;
  /** Override bar fill colour */
  barClassName?: string;
  /** Show percentage label below bar */
  showLabel?: boolean;
  /** Bar height variant */
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
          size === "sm" ? "h-1.5" : "h-2",
        )}
      >
        <div
          className={cn("h-full rounded-full transition-all", barClassName ?? "bg-primary")}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <p className="vf-text-micro text-muted-foreground mt-0.5 text-center">
          {Math.round(pct)}%
        </p>
      )}
    </div>
  );
}
