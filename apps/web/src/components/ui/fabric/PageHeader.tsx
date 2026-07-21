import { ChevronRight, Home } from "lucide-react";
import { cn } from "@/lib/utils";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  className?: string;
}

export function PageHeader({ title, subtitle, actions, breadcrumbs, className }: PageHeaderProps) {
  return (
    <div className={cn("mb-6 border-b border-border pb-5 sm:pb-6", className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="mb-3 flex flex-wrap items-center gap-1.5 vf-text-body-s text-muted-foreground" aria-label="Breadcrumb">
          <Home className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          {breadcrumbs.map((crumb, i) => (
            <span key={crumb.href ?? crumb.label ?? i} className="flex items-center gap-1.5">
              <ChevronRight className="h-3 w-3 shrink-0" aria-hidden="true" />
              {crumb.href ? (
                <a href={crumb.href} className="hover:text-foreground transition-colors">
                  {crumb.label}
                </a>
              ) : (
                <span className="text-foreground font-medium">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}
      <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex-1 min-w-0">
          <h1 className="vf-display-m font-semibold text-foreground">
            {title}
          </h1>
          {subtitle && (
            <p className="vf-text-body-m text-muted-foreground mt-1">
              {subtitle}
            </p>
          )}
        </div>
        {actions && (
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-shrink-0 sm:justify-end sm:gap-3">{actions}</div>
        )}
      </div>
    </div>
  );
}
