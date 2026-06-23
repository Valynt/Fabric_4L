/**
 * Stepper — Generic multi-step navigation component.
 *
 * Compound component pattern following shadcn/ui conventions.
 * Supports horizontal step indicators with keyboard navigation.
 */

import { createContext, useContext, useCallback, useState } from "react";
import { cn } from "@/lib/utils";
import { Check, Circle, Loader2 } from "lucide-react";

// ── Context ─────────────────────────────────────────────────────────────────

interface StepperContextValue {
  value: string;
  onValueChange: (value: string) => void;
}

const StepperContext = createContext<StepperContextValue | null>(null);

function useStepper() {
  const ctx = useContext(StepperContext);
  if (!ctx) throw new Error("Stepper components must be used inside <Stepper>");
  return ctx;
}

// ── Stepper Root ────────────────────────────────────────────────────────────

interface StepperProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function Stepper({ value, onValueChange, children, className }: StepperProps) {
  return (
    <StepperContext.Provider value={{ value, onValueChange }}>
      <div className={cn("w-full", className)}>{children}</div>
    </StepperContext.Provider>
  );
}

// ── StepperList ─────────────────────────────────────────────────────────────

interface StepperListProps {
  children: React.ReactNode;
  className?: string;
}

export function StepperList({ children, className }: StepperListProps) {
  return (
    <div
      role="tablist"
      aria-label="Step navigation"
      className={cn("flex items-center gap-2", className)}
    >
      {children}
    </div>
  );
}

// ── StepperTrigger ──────────────────────────────────────────────────────────

type StepStatus = "pending" | "active" | "completed";

interface StepperTriggerProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

export function StepperTrigger({ value, children, className }: StepperTriggerProps) {
  const { value: activeValue, onValueChange } = useStepper();

  const status: StepStatus =
    value === activeValue ? "active" : "pending";

  const handleClick = useCallback(() => {
    onValueChange(value);
  }, [onValueChange, value]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onValueChange(value);
      }
    },
    [onValueChange, value]
  );

  return (
    <button
      role="tab"
      aria-selected={status === "active"}
      aria-current={status === "active" ? "step" : undefined}
      tabIndex={status === "active" ? 0 : -1}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        "group flex flex-1 items-center gap-2 py-2 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 rounded-sm",
        status === "active" && "text-primary",
        status === "pending" && "text-muted-foreground hover:text-foreground",
        className
      )}
    >
      <StepperIndicator status={status} />
      <span className="text-sm font-medium">{children}</span>
    </button>
  );
}

// ── StepperIndicator ────────────────────────────────────────────────────────

function StepperIndicator({ status }: { status: StepStatus }) {
  return (
    <span
      className={cn(
        "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border vf-text-micro font-semibold transition-colors",
        status === "active" && "border-primary bg-primary text-primary-foreground",
        status === "pending" && "border-muted-foreground/30 text-muted-foreground",
        status === "completed" && "border-primary bg-primary text-primary-foreground"
      )}
    >
      {status === "completed" ? (
        <Check className="h-3 w-3" />
      ) : status === "active" ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : (
        <Circle className="h-3 w-3" />
      )}
    </span>
  );
}

// ── StepperContent ──────────────────────────────────────────────────────────

interface StepperContentProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

export function StepperContent({ value, children, className }: StepperContentProps) {
  const { value: activeValue } = useStepper();
  const isActive = value === activeValue;

  if (!isActive) return null;

  return (
    <div
      role="tabpanel"
      aria-labelledby={`step-${value}`}
      className={cn("mt-4", className)}
    >
      {children}
    </div>
  );
}

// ── StepperSeparator ────────────────────────────────────────────────────────

export function StepperSeparator({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn("mx-2 h-px flex-1 bg-border", className)}
    />
  );
}
