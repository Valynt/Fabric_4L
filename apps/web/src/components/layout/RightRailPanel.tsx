/**
 * RightRailPanel — Consistent right sidebar panel for detail views
 *
 * UI Contract (Data):
 *   - `title` : Panel title
 *   - `status` : Optional status badge or indicator
 *   - `onClose` : Callback when close button clicked
 *   - `children` : Panel content
 *   - `footer` : Optional action footer
 *   - `isLoading` : Show loading state
 *
 * UI Contract (Rendering):
 *   - Sticky positioning on desktop (md:sticky md:top-8)
 *   - Full height with scrollable content
 *   - Header with title, status, and close button
 *   - Action footer when provided
 *   - Loading skeleton when isLoading is true
 *
 * Responsive Behavior:
 *   - Desktop: Fixed width panel, sticky positioning
 *   - Tablet/Mobile: Should be wrapped in Sheet/Drawer by parent
 */
import { X, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

export interface RightRailPanelProps {
  title: string;
  status?: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  isLoading?: boolean;
  className?: string;
}

export function RightRailPanel({ 
  title, 
  status, 
  onClose, 
  children, 
  footer,
  isLoading,
  className 
}: RightRailPanelProps) {
  return (
    <div className={cn(
      "h-full flex flex-col bg-card border border-border rounded-lg md:h-[calc(100vh-200px)] md:sticky md:top-8",
      className
    )}>
      {/* Header */}
      <div className="p-4 border-b border-border flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-foreground leading-tight">{title}</h3>
          {status && <div className="mt-1">{status}</div>}
        </div>
        <button 
          onClick={onClose}
          className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors flex-shrink-0"
          aria-label="Close panel"
        >
          <X size={16} />
        </button>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <div className="space-y-3 pt-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          </div>
        ) : (
          children
        )}
      </div>
      
      {/* Footer */}
      {footer && (
        <div className="p-4 border-t border-border bg-muted/30">
          {footer}
        </div>
      )}
    </div>
  );
}
