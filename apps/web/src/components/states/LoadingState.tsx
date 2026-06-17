/**
 * LoadingState — Minimalist centered loading state
 *
 * Use for route-level loading states within page shells.
 */
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingStateProps {
  message?: string;
  className?: string;
  fullPage?: boolean;
}

export function LoadingState({ 
  message = "Loading…", 
  className,
  fullPage = false 
}: LoadingStateProps) {
  return (
    <div 
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn(
        "flex flex-col items-center justify-center gap-3 text-center",
        fullPage ? "min-h-[60vh]" : "py-16",
        className
      )}
    >
      <Loader2 size={24} className="animate-spin text-muted-foreground/70" aria-hidden="true" />
      <span className="text-sm text-muted-foreground">{message}</span>
    </div>
  );
}

export default LoadingState;
