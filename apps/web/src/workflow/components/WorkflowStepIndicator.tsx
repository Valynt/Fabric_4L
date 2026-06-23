import { AlertCircle, CheckCircle2, Circle, Radio } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

export type WorkflowStepStatus = "pending" | "active" | "completed" | "error";

export interface WorkflowStep {
  id: string;
  label: string;
  description?: string;
  status?: WorkflowStepStatus;
}

export interface WorkflowStepIndicatorProps {
  steps: WorkflowStep[];
  activeStepId?: string;
  completedStepIds?: string[];
  isLoading?: boolean;
  error?: string | Error | null;
  ariaLabel?: string;
  className?: string;
}

export const ACCOUNT_WORKFLOW_STEPS: WorkflowStep[] = [
  {
    id: "scope",
    label: "Scope",
    description: "Select account context and workflow inputs",
  },
  {
    id: "intelligence",
    label: "Intelligence",
    description: "Validate signals, hypotheses, and evidence",
  },
  {
    id: "studio",
    label: "Model",
    description: "Build value drivers, assumptions, and scenarios",
  },
  {
    id: "deliverables",
    label: "Deliver",
    description: "Package the business case and executive views",
  },
];

function normalizeError(
  error: WorkflowStepIndicatorProps["error"]
): string | null {
  if (!error) {
    return null;
  }

  return typeof error === "string" ? error : error.message;
}

function getStepStatus(
  step: WorkflowStep,
  activeStepId: string | undefined,
  completedStepIds: Set<string>
): WorkflowStepStatus {
  if (step.status) {
    return step.status;
  }

  if (step.id === activeStepId) {
    return "active";
  }

  if (completedStepIds.has(step.id)) {
    return "completed";
  }

  return "pending";
}

function getStatusLabel(status: WorkflowStepStatus): string {
  switch (status) {
    case "active":
      return "Current step";
    case "completed":
      return "Completed";
    case "error":
      return "Needs attention";
    case "pending":
      return "Pending";
  }
}

function StepStatusIcon({ status }: { status: WorkflowStepStatus }) {
  const iconClassName = "size-3.5 shrink-0";

  if (status === "completed") {
    return (
      <CheckCircle2
        aria-hidden="true"
        className={cn(iconClassName, "text-primary")}
      />
    );
  }

  if (status === "active") {
    return (
      <Radio aria-hidden="true" className={cn(iconClassName, "text-primary")} />
    );
  }

  if (status === "error") {
    return (
      <AlertCircle
        aria-hidden="true"
        className={cn(iconClassName, "text-destructive")}
      />
    );
  }

  return (
    <Circle
      aria-hidden="true"
      className={cn(iconClassName, "text-muted-foreground")}
    />
  );
}

export function WorkflowStepIndicator({
  steps,
  activeStepId,
  completedStepIds = [],
  isLoading = false,
  error = null,
  ariaLabel = "Workflow progress",
  className,
}: WorkflowStepIndicatorProps) {
  const errorMessage = normalizeError(error);

  if (isLoading) {
    return (
      <section
        aria-label={ariaLabel}
        aria-busy="true"
        className={cn("border-b bg-background/95 px-4 py-2", className)}
      >
        <div className="mx-auto flex max-w-screen-2xl items-center gap-2 text-xs text-muted-foreground">
          <Spinner className="size-3.5" />
          <span>Loading workflow progress…</span>
        </div>
      </section>
    );
  }

  if (errorMessage) {
    return (
      <section
        aria-label={ariaLabel}
        className={cn("border-b bg-background/95 px-4 py-2", className)}
      >
        <Alert variant="destructive" className="mx-auto max-w-screen-2xl py-2">
          <AlertDescription className="text-xs">
            Workflow progress unavailable: {errorMessage}
          </AlertDescription>
        </Alert>
      </section>
    );
  }

  if (steps.length === 0) {
    return (
      <section
        aria-label={ariaLabel}
        className={cn("border-b bg-background/95 px-4 py-2", className)}
      >
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-3 rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
          <span>No workflow steps available.</span>
          <Badge variant="outline">Empty</Badge>
        </div>
      </section>
    );
  }

  const completedIds = new Set(completedStepIds);
  const statuses = steps.map(step =>
    getStepStatus(step, activeStepId, completedIds)
  );
  const completedCount = statuses.filter(
    status => status === "completed"
  ).length;
  const activeStep = steps.find((step, index) => statuses[index] === "active");
  const progressValue = Math.round((completedCount / steps.length) * 100);

  return (
    <section className={cn("border-b bg-background/95 px-4 py-2", className)}>
      <nav aria-label={ariaLabel} className="mx-auto max-w-screen-2xl">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <Badge variant="secondary" className="shrink-0">
              Workflow
            </Badge>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">
                {activeStep
                  ? `${activeStep.label} in progress`
                  : "Workflow ready"}
              </p>
              <p className="text-xs text-muted-foreground">
                {completedCount} of {steps.length} steps completed
              </p>
            </div>
          </div>

          <div className="flex min-w-0 flex-1 flex-col gap-2 lg:max-w-3xl">
            <Progress
              aria-label={`${completedCount} of ${steps.length} workflow steps completed`}
              value={progressValue}
              className="h-1.5"
            />
            <ol
              className="flex min-w-0 gap-1 overflow-x-auto"
              aria-label="Workflow steps"
            >
              {steps.map((step, index) => {
                const status = statuses[index];
                const statusLabel = getStatusLabel(status);

                return (
                  <li key={step.id} className="min-w-fit flex-1">
                    <div
                      aria-current={status === "active" ? "step" : undefined}
                      aria-label={`${step.label}: ${statusLabel}`}
                      className={cn(
                        "flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors",
                        status === "active" &&
                          "border-primary bg-primary/10 text-primary",
                        status === "completed" &&
                          "border-primary/30 bg-primary/5 text-foreground",
                        status === "pending" &&
                          "border-border bg-card text-muted-foreground",
                        status === "error" &&
                          "border-destructive/40 bg-destructive/10 text-destructive"
                      )}
                    >
                      <StepStatusIcon status={status} />
                      <span className="truncate font-medium">{step.label}</span>
                      <span className="sr-only">{statusLabel}</span>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      </nav>
    </section>
  );
}
