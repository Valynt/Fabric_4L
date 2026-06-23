import type React from "react";
import {
  SettingsMetricGrid,
  SettingsMetric,
  SettingsQueryState,
  SettingsSaveButton,
} from "./SettingsState";

export interface SettingsPageShellProps<TData> {
  title: string;
  description?: string;
  data: TData | undefined;
  isLoading: boolean;
  error: Error | null;
  loadingLabel: string;
  errorTitle?: string;
  emptyLabel?: string;
  metrics?: SettingsMetric[] | ((data: TData) => SettingsMetric[]);
  metricGridClassName?: string;
  readOnly?: boolean;
  dirty?: boolean;
  isPending?: boolean;
  onSave?: () => void;
  saveLabel?: string;
  savePendingLabel?: string;
  children?: React.ReactNode | ((data: TData) => React.ReactNode);
}

export function SettingsPageShell<TData>({
  title,
  description,
  data,
  isLoading,
  error,
  loadingLabel,
  errorTitle,
  emptyLabel,
  metrics,
  metricGridClassName,
  readOnly,
  dirty,
  isPending,
  onSave,
  saveLabel = "Save changes",
  savePendingLabel = "Saving...",
  children,
}: SettingsPageShellProps<TData>) {
  return (
    <div className="space-y-6">
      <section className="rounded-lg border bg-card p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold">{title}</h3>
            {description ? (
              <p className="text-xs text-muted-foreground">{description}</p>
            ) : null}
          </div>
          {onSave && !readOnly && (
            <SettingsSaveButton
              onClick={onSave}
              isPending={isPending ?? false}
              disabled={!dirty}
              pendingLabel={savePendingLabel}
            >
              {saveLabel}
            </SettingsSaveButton>
          )}
        </div>

        <SettingsQueryState
          data={data}
          isLoading={isLoading}
          error={error}
          loadingLabel={loadingLabel}
          errorTitle={errorTitle}
          emptyLabel={emptyLabel}
        >
          {(currentData) => {
            const resolvedMetrics =
              typeof metrics === "function" ? metrics(currentData) : metrics;
            return (
              <div className="mt-4 space-y-6">
                {resolvedMetrics ? (
                  <SettingsMetricGrid
                    metrics={resolvedMetrics}
                    className={metricGridClassName}
                  />
                ) : null}
                {typeof children === "function"
                  ? children(currentData)
                  : children}
              </div>
            );
          }}
        </SettingsQueryState>
      </section>
    </div>
  );
}
