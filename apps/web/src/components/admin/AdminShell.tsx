/**
 * AdminShell — Consistent wrapper for all admin-tier pages.
 *
 * Enforces:
 * - PageShell layout
 * - max-w-6xl content constraint
 * - Optional header/tabs slots
 * - Breadcrumb support
 * - Responsive stacking on mobile
 */
import { PageShell } from "@/components";
import { PageHeader, type BreadcrumbItem } from "@/components/ui/fabric";
import { cn } from "@/lib/utils";

export interface AdminShellProps {
  children: React.ReactNode;
  className?: string;
  fullWidth?: boolean;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  tabs?: React.ReactNode;
}

export function AdminShell({
  children,
  className,
  fullWidth = false,
  title,
  subtitle,
  actions,
  breadcrumbs,
  tabs,
}: AdminShellProps) {
  return (
    <PageShell fullWidth={fullWidth}>
      <div className={cn("mx-auto px-4 sm:px-6", fullWidth ? "max-w-6xl" : "", className)}>
        <div className="flex flex-col sm:flex-row items-start justify-between gap-4 mb-6">
          <PageHeader
            title={title}
            subtitle={subtitle}
            breadcrumbs={breadcrumbs}
          />
          {actions && (
            <div className="flex items-center gap-2 flex-wrap flex-shrink-0 w-full sm:w-auto">
              {actions}
            </div>
          )}
        </div>
        {tabs && <div className="mb-4 overflow-x-auto">{tabs}</div>}
        {children}
      </div>
    </PageShell>
  );
}
