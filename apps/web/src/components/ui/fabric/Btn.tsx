/**
 * Btn — Compact button with legacy variant names.
 *
 * Wraps shadcn Button with a simplified variant API used across the app.
 * Migrated from WfPrimitives shim.
 *
 * Variant mapping:
 *   primary  → default
 *   ghost    → ghost
 *   outline  → outline
 *   danger   → destructive
 */
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export interface BtnProps {
  children: ReactNode;
  variant?: "primary" | "ghost" | "outline" | "danger";
  /** Forwarded to the underlying Button size prop. */
  size?: "default" | "sm" | "lg" | "icon";
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  className?: string;
  disabled?: boolean;
  "aria-label"?: string;
}

const VARIANT_MAP = {
  primary: "default",
  ghost: "ghost",
  outline: "outline",
  danger: "destructive",
} as const;

export function Btn({
  children,
  variant = "ghost",
  size = "sm",
  onClick,
  className,
  disabled,
  "aria-label": ariaLabel,
}: BtnProps) {
  return (
    <Button
      onClick={onClick}
      disabled={disabled}
      variant={VARIANT_MAP[variant]}
      size={size}
      className={cn("vf-text-body-s font-semibold", className)}
      aria-label={ariaLabel}
    >
      {children}
    </Button>
  );
}
