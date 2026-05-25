import * as React from "react";
import { Link, useSearchParams, useParams } from "react-router-dom";
import { Radar, Building2, BrainCircuit, GitFork, Database, Calculator, FileText, ChevronRight, Sparkles, LucideIcon, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { WORKFLOW_STEPS } from "../types";

type IconName = 'Radar' | 'Building2' | 'BrainCircuit' | 'GitFork' | 'Database' | 'Calculator' | 'FileText';

const iconMap: Record<IconName, LucideIcon> = {
  Radar, Building2, BrainCircuit, GitFork, Database, Calculator, FileText,
};

function getIcon(name: string): LucideIcon {
  return (iconMap as Record<string, LucideIcon>)[name] || Sparkles;
}

function buildStepPath(
  step: typeof WORKFLOW_STEPS[number],
  tenantSlug: string,
  accountId: string
): string {
  return step.canonicalPath
    .replace(':tenantSlug', tenantSlug)
    .replace(':accountId', accountId);
}

export function WorkflowStepIndicator() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { tenantSlug, accountId } = useParams<{ tenantSlug: string; accountId: string }>();
  const mode = searchParams.get('mode');
  const stepParam = searchParams.get('step');
  const currentStep = stepParam ? parseInt(stepParam, 10) : 0;

  if (mode !== 'value-pilot') return null;
  if (!tenantSlug || !accountId) return null;

  const handleClose = () => {
    const next = new URLSearchParams(searchParams);
    next.delete('mode');
    next.delete('step');
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="sticky top-0 z-40 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-12">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
            </div>
            <span className="text-sm font-semibold text-foreground">ValuePilot</span>
          </div>

          <nav aria-label="ValuePilot steps" className="hidden md:flex items-center gap-1">
            {WORKFLOW_STEPS.map((step, idx) => (
              <React.Fragment key={step.path}>
                <Link
                  to={{
                    pathname: buildStepPath(step, tenantSlug, accountId),
                    search: `?mode=value-pilot&step=${idx}`,
                  }}
                  replace
                >
                  <div className={cn(
                    'flex items-center gap-1.5 px-2 py-1 rounded-lg cursor-pointer transition-colors',
                    idx === currentStep ? 'bg-primary/10' : 'hover:bg-muted'
                  )}>
                    {React.createElement(getIcon(step.icon), {
                      className: cn('w-3.5 h-3.5', idx <= currentStep ? 'text-primary' : 'text-muted-foreground')
                    })}
                    <span className={cn('text-xs font-medium hidden lg:block', idx === currentStep ? 'text-foreground' : 'text-muted-foreground')}>
                      {step.label}
                    </span>
                  </div>
                </Link>
                {idx < WORKFLOW_STEPS.length - 1 && <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40" />}
              </React.Fragment>
            ))}
          </nav>

          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg hover:bg-muted transition-colors"
            aria-label="Close ValuePilot mode"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      </div>
    </div>
  );
}
