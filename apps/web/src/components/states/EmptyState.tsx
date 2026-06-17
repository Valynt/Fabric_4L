/**
 * EmptyState — Clean empty state with icon, title, and optional action
 *
 * Use when data loads successfully but is empty.
 */
import { Inbox, LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: ReactNode;
  className?: string;
  fullPage?: boolean;
}

export function EmptyState({ 
  title, 
  description, 
  icon: Icon = Inbox,
  action,
  className,
  fullPage = false
}: EmptyStateProps) {
  return (
    <div 
      role="status"
      aria-live="polite"
      className={cn(
        "flex flex-col items-center justify-center gap-3 text-center",
        fullPage ? "min-h-[60vh]" : "py-16",
        className
      )}
    >
      <Icon size={32} className="text-muted-foreground/40" aria-hidden="true" />
      <div className="space-y-1">
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
        {description && (
          <p className="max-w-sm text-xs text-muted-foreground">{description}</p>
        )}
      </div>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
}

export default EmptyState;
