/**
 * AIModelStatus — LLM provider and enrichment governance status panel.
 *
 * Displays the active LLM provider, per-task model assignments, and the
 * enrichment governance flags (llm_enrichment, customer_facing_allowed,
 * human_review_required) for a given agent workflow result.
 *
 * UI Contract (Data):
 *   - `provider`      : active provider name ("together" | "openai" | "anthropic")
 *   - `models`        : task → model name mapping from harness.runtime.yaml
 *   - `enrichment`    : AgentResult governance flags (optional — shows skeleton if absent)
 *   - `className`     : additional wrapper classes
 *
 * UI Contract (Rendering):
 *   - Provider badge with colour-coded status
 *   - Model assignment table (reasoning / extraction / narrative)
 *   - Governance flags row with icons
 *   - Degraded reason shown when customer_facing_allowed=false
 */

import { cn } from "@/lib/utils";
import {
  BrainCircuit,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Eye,
  EyeOff,
  UserCheck,
  Cpu,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AIModelAssignments {
  reasoning?: string;
  extraction?: string;
  narrative?: string;
  embedding?: string;
}

export interface AIEnrichmentStatus {
  llm_enrichment: boolean;
  customer_facing_allowed: boolean;
  human_review_required: boolean;
  degraded_reason?: string | null;
  model_used?: string | null;
  prompt_tokens?: number;
  completion_tokens?: number;
  confidence?: number;
}

export interface AIModelStatusProps {
  /** Active provider name */
  provider: "together" | "openai" | "anthropic" | string;
  /** Per-task model assignments */
  models?: AIModelAssignments;
  /** Enrichment governance flags from AgentResult */
  enrichment?: AIEnrichmentStatus | null;
  /** Additional wrapper classes */
  className?: string;
}

// ---------------------------------------------------------------------------
// Provider display config
// ---------------------------------------------------------------------------

const PROVIDER_CONFIG: Record<string, { label: string; colour: string }> = {
  together:  { label: "Together.ai",  colour: "text-violet-400 bg-violet-400/10" },
  openai:    { label: "OpenAI",       colour: "text-emerald-400 bg-emerald-400/10" },
  anthropic: { label: "Anthropic",    colour: "text-amber-400 bg-amber-400/10" },
};

const TASK_LABELS: Record<keyof AIModelAssignments, string> = {
  reasoning:  "Reasoning",
  extraction: "Extraction",
  narrative:  "Narrative",
  embedding:  "Embedding",
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ModelRow({ task, model }: { task: string; model: string }) {
  // Shorten long model names for display
  const short = model.includes("/") ? model.split("/").pop()! : model;
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border/50 last:border-0">
      <span className="text-xs text-muted-foreground capitalize">{task}</span>
      <span
        className="text-xs font-mono text-foreground/80 truncate max-w-48"
        title={model}
      >
        {short}
      </span>
    </div>
  );
}

function GovernanceFlag({
  icon: Icon,
  label,
  active,
  activeClass,
  inactiveClass,
}: {
  icon: typeof CheckCircle2;
  label: string;
  active: boolean;
  activeClass: string;
  inactiveClass: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
        active ? activeClass : inactiveClass,
      )}
    >
      <Icon className="w-3 h-3 shrink-0" />
      {label}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function AIModelStatus({
  provider,
  models,
  enrichment,
  className,
}: AIModelStatusProps) {
  const providerCfg = PROVIDER_CONFIG[provider] ?? {
    label: provider,
    colour: "text-muted-foreground bg-muted",
  };

  const taskEntries = models
    ? (Object.entries(models) as [keyof AIModelAssignments, string][]).filter(
        ([, v]) => v && v !== "null",
      )
    : [];

  return (
    <div
      className={cn(
        "bg-card border border-border rounded-xl p-4 space-y-4",
        className,
      )}
      aria-label="AI Model Status"
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <BrainCircuit className="w-4 h-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-foreground">LLM Provider</p>
          <p className="text-xs text-muted-foreground">Active model configuration</p>
        </div>
        <span
          className={cn(
            "text-[10px] font-semibold px-2 py-0.5 rounded-full",
            providerCfg.colour,
          )}
        >
          {providerCfg.label}
        </span>
      </div>

      {/* Model assignments */}
      {taskEntries.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-1.5 flex items-center gap-1">
            <Cpu className="w-3 h-3" /> Model Assignments
          </p>
          <div className="bg-muted/30 rounded-lg px-3 py-1">
            {taskEntries.map(([task, model]) => (
              <ModelRow
                key={task}
                task={TASK_LABELS[task] ?? task}
                model={model}
              />
            ))}
          </div>
        </div>
      )}

      {/* Enrichment governance */}
      {enrichment != null && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-1">
            <UserCheck className="w-3 h-3" /> Enrichment Governance
          </p>

          <div className="flex flex-wrap gap-1.5">
            <GovernanceFlag
              icon={enrichment.llm_enrichment ? CheckCircle2 : XCircle}
              label="LLM Enriched"
              active={enrichment.llm_enrichment}
              activeClass="bg-emerald-500/10 text-emerald-500"
              inactiveClass="bg-muted text-muted-foreground"
            />
            <GovernanceFlag
              icon={enrichment.customer_facing_allowed ? Eye : EyeOff}
              label="Customer-Facing"
              active={enrichment.customer_facing_allowed}
              activeClass="bg-emerald-500/10 text-emerald-500"
              inactiveClass="bg-amber-500/10 text-amber-500"
            />
            <GovernanceFlag
              icon={enrichment.human_review_required ? AlertTriangle : CheckCircle2}
              label="Human Review"
              active={enrichment.human_review_required}
              activeClass="bg-amber-500/10 text-amber-500"
              inactiveClass="bg-muted text-muted-foreground"
            />
          </div>

          {/* Degraded reason */}
          {enrichment.degraded_reason && (
            <p className="text-[10px] text-amber-500 bg-amber-500/5 border border-amber-500/20 rounded-lg px-2.5 py-1.5">
              ⚠ {enrichment.degraded_reason}
            </p>
          )}

          {/* Token / confidence row */}
          {(enrichment.model_used ||
            enrichment.prompt_tokens != null ||
            enrichment.confidence != null) && (
            <div className="flex items-center gap-3 text-[10px] text-muted-foreground pt-0.5">
              {enrichment.model_used && (
                <span className="font-mono truncate max-w-[140px]" title={enrichment.model_used}>
                  {enrichment.model_used.includes("/")
                    ? enrichment.model_used.split("/").pop()
                    : enrichment.model_used}
                </span>
              )}
              {enrichment.prompt_tokens != null && enrichment.completion_tokens != null && (
                <span>
                  {(enrichment.prompt_tokens + enrichment.completion_tokens).toLocaleString()} tokens
                </span>
              )}
              {enrichment.confidence != null && (
                <span className="ml-auto font-semibold text-foreground/70">
                  {Math.round(enrichment.confidence * 100)}% conf
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Skeleton when no enrichment data yet */}
      {enrichment == null && (
        <div className="space-y-1.5 animate-pulse">
          <div className="h-3 bg-muted rounded w-3/4" />
          <div className="h-3 bg-muted rounded w-1/2" />
        </div>
      )}
    </div>
  );
}
