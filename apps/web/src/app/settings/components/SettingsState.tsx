import type React from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { Button, type ButtonProps } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SettingsQueryStateProps<TData> {
  data: TData | undefined;
  isLoading: boolean;
  error: Error | null;
  loadingLabel: string;
  errorTitle?: string;
  emptyLabel?: string;
  children: (data: TData) => React.ReactNode;
}

export function SettingsQueryState<TData>({
  data,
  isLoading,
  error,
  loadingLabel,
  errorTitle = "Failed to load settings",
  emptyLabel,
  children,
}: SettingsQueryStateProps<TData>) {
  if (isLoading) {
    return (
      <div className="mt-4 inline-flex items-center gap-2 rounded-md border p-4 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        {loadingLabel}
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-4 flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-medium">{errorTitle}</p>
          <p className="mt-1 text-xs">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return emptyLabel ? (
      <p className="mt-4 rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground">
        {emptyLabel}
      </p>
    ) : null;
  }

  return <>{children(data)}</>;
}

interface SettingsMetric {
  label: string;
  value: React.ReactNode;
}

export function SettingsMetricGrid({
  metrics,
  className,
}: {
  metrics: SettingsMetric[];
  className?: string;
}) {
  return (
    <div className={cn("mt-4 grid gap-3 sm:grid-cols-2", className)}>
      {metrics.map((metric) => (
        <div key={metric.label} className="rounded-md border p-4">
          <p className="text-xs text-muted-foreground">{metric.label}</p>
          <p className="mt-1 text-sm font-medium">{metric.value}</p>
        </div>
      ))}
    </div>
  );
}

interface SettingsSaveButtonProps extends Omit<ButtonProps, "type"> {
  isPending: boolean;
  pendingLabel?: string;
  children: React.ReactNode;
}

export function SettingsSaveButton({
  isPending,
  pendingLabel = "Saving...",
  children,
  className,
  disabled,
  ...props
}: SettingsSaveButtonProps) {
  return (
    <Button
      type="button"
      size="sm"
      disabled={disabled || isPending}
      className={cn("text-xs", className)}
      {...props}
    >
      {isPending ? pendingLabel : children}
    </Button>
  );
}
