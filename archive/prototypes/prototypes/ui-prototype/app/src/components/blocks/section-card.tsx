import { cn } from "@/lib/utils";
import { type ReactNode } from "react";

interface SectionCardProps {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}

export function SectionCard({
  title,
  description,
  icon,
  action,
  children,
  className,
  contentClassName,
}: SectionCardProps) {
  return (
    <section className={cn("bg-card rounded-xl border border-border overflow-hidden", className)}>
      {(title || action) && (
        <div className="px-5 py-3 border-b border-border/60 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {icon && <span className="text-muted-foreground">{icon}</span>}
            <div>
              {title && <h3 className="text-sm font-semibold text-foreground">{title}</h3>}
              {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
            </div>
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={cn(contentClassName)}>{children}</div>
    </section>
  );
}
