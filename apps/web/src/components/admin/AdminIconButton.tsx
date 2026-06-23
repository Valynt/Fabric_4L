/**
 * AdminIconButton — Standardized icon action buttons for admin table rows.
 *
 * Replaces raw <button> elements with shadcn Button for consistent
 * focus states, tooltips, and accessibility.
 */
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export type AdminIconButtonVariant =
  | "ghost"
  | "primary"
  | "success"
  | "warning"
  | "destructive";

export interface AdminIconButtonProps {
  icon: LucideIcon;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  variant?: AdminIconButtonVariant;
  className?: string;
}

const VARIANT_MAP: Record<AdminIconButtonVariant, string> = {
  ghost: "text-muted-foreground hover:text-foreground hover:bg-muted",
  primary: "text-muted-foreground hover:text-primary hover:bg-primary/10",
  success: "text-muted-foreground hover:text-success hover:bg-success/10",
  warning: "text-muted-foreground hover:text-warning hover:bg-warning/10",
  destructive: "text-muted-foreground hover:text-destructive hover:bg-destructive/10",
};

export function AdminIconButton({
  icon: Icon,
  label,
  onClick,
  disabled,
  variant = "ghost",
  className,
}: AdminIconButtonProps) {
  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClick}
            disabled={disabled}
            aria-label={label}
            className={cn(
              "h-8 w-8 rounded transition-colors focus-visible:ring-2 focus-visible:ring-ring",
              VARIANT_MAP[variant],
              className
            )}
          >
            <Icon className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">
          <span className="vf-text-caption">{label}</span>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export interface AdminIconButtonGroupProps {
  children: React.ReactNode;
  className?: string;
}

export function AdminIconButtonGroup({
  children,
  className,
}: AdminIconButtonGroupProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity focus-within:opacity-100",
        className
      )}
    >
      {children}
    </div>
  );
}
