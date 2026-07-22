/**
 * HarnessRunDetail — Drill-down sheet for a single HarnessRun.
 *
 * Shows: run metadata, state machine progress, checkpoints,
 * human gates (with approve/reject actions), and validation outcomes.
 */

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
  ShieldCheck,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import type { ClaimValidationResult, HarnessRun, HumanGate, ValidationState, ValidationSummary } from "@/api/harness";
import { TERMINAL_STATES, isTerminalState } from "@/api/harness";
import {
  useDecideGate,
  useHarnessCheckpoints,
  useHarnessGates,
  useHarnessRun,
  useHarnessValidation,
  useTransitionHarnessRun,
} from "@/hooks/useHarness";

// ── Constants ─────────────────────────────────────────────────────────────────

const STATE_ORDER = [
  "INIT",
  "RESOLVE_CONTEXT",
  "LOAD_VALUE_PACK",
  "RETRIEVE_KNOWLEDGE",
  "GENERATE_HYPOTHESES",
  "MATCH_EVIDENCE",
  "QUANTIFY_IMPACT",
  "VALIDATE_CLAIMS",
  "HUMAN_REVIEW",
  "PUBLISH_OUTPUT",
  "DONE",
] as const;

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusColor(status: string): string {
  switch (status) {
    case "completed": return "bg-success/100/15 text-success border-success/20";
    case "running":   return "bg-primary/100/15 text-primary border-primary/20";
    case "failed":    return "bg-destructive/100/15 text-destructive border-destructive/20";
    case "cancelled": return "bg-muted/15 text-muted-foreground border-border";
    case "waiting_for_human": return "bg-warning/100/15 text-warning border-warning/20";
    default:          return "bg-muted text-muted-foreground border-border";
  }
}

function gateStatusColor(status: string): string {
  switch (status) {
    case "approved": return "bg-success/100/15 text-success";
    case "rejected": return "bg-destructive/100/15 text-destructive";
    case "expired":  return "bg-muted/15 text-muted-foreground";
    case "modified": return "bg-primary/100/15 text-primary";
    default:         return "bg-warning/100/15 text-warning"; // pending
  }
}

function validationStateColor(state: ValidationState): string {
  switch (state) {
    case "passed":               return "text-success";
    case "failed":               return "text-destructive";
    case "needs_review":         return "text-warning";
    case "insufficient_evidence": return "text-muted-foreground";
  }
}

function validationStateBadgeClass(state: ValidationState): string {
  switch (state) {
    case "passed":               return "bg-success/100/15 text-success border-success/20";
    case "failed":               return "bg-destructive/100/15 text-destructive border-destructive/20";
    case "needs_review":         return "bg-warning/100/15 text-warning border-warning/20";
    case "insufficient_evidence": return "bg-muted text-muted-foreground border-border";
  }
}

function validationStateLabel(state: ValidationState): string {
  switch (state) {
    case "passed":               return "Passed";
    case "failed":               return "Failed";
    case "needs_review":         return "Needs Review";
    case "insufficient_evidence": return "Insufficient Evidence";
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ValidationSection({
  results,
  summary,
}: {
  results: ClaimValidationResult[];
  summary: ValidationSummary | null;
}) {
  const [expanded, setExpanded] = useState(false);

  // Derive aggregate state for the badge
  const aggregateState: ValidationState =
    !summary || summary.total === 0
      ? "insufficient_evidence"
      : summary.failed > 0
      ? "failed"
      : summary.needs_review > 0 || summary.insufficient_evidence > 0
      ? "needs_review"
      : "passed";

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={cn("text-xs", validationStateBadgeClass(aggregateState))}
          >
            {validationStateLabel(aggregateState)}
          </Badge>
          {summary && summary.total > 0 && (
            <span className="text-xs text-muted-foreground">
              {summary.passed}/{summary.total} passed
            </span>
          )}
        </div>
        {results.length > 0 && (
          <button type="button"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            {expanded ? "Hide" : "Show"} claims
          </button>
        )}
      </div>

      {results.length === 0 && (
        <p className="text-xs text-muted-foreground italic">No claims validated yet.</p>
      )}

      {expanded && results.length > 0 && (
        <div className="space-y-1.5 mt-2">
          {results.map((r) => (
            <div
              key={r.id}
              className="rounded border border-border bg-muted/30 px-3 py-2 text-xs"
            >
              <div className="flex items-center justify-between gap-2 mb-0.5">
                <span className="font-mono truncate vf-text-caption text-muted-foreground">
                  {r.claim_id}
                </span>
                <Badge
                  variant="outline"
                  className={cn("vf-text-micro shrink-0", validationStateBadgeClass(r.validation_state))}
                >
                  {validationStateLabel(r.validation_state)}
                </Badge>
              </div>
              <div className="flex items-center gap-3 text-muted-foreground">
                <span>Confidence: {Math.round(r.confidence * 100)}%</span>
                {r.reason && <span className="truncate">{r.reason}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StateProgress({ currentState, status }: { currentState: string; status: string }) {
  const currentIdx = STATE_ORDER.indexOf(currentState as typeof STATE_ORDER[number]);
  const isFailed = status === "failed" || status === "cancelled";

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {STATE_ORDER.map((state, idx) => {
        const done = idx < currentIdx;
        const active = idx === currentIdx && !isFailed;
        const failed = idx === currentIdx && isFailed;
        return (
          <div key={state} className="flex items-center gap-1">
            <div
              className={cn(
                "h-2 w-2 rounded-full",
                done   && "bg-success/100",
                active && "bg-primary/100 animate-pulse",
                failed && "bg-destructive/100",
                !done && !active && !failed && "bg-muted",
              )}
              title={state}
            />
            {idx < STATE_ORDER.length - 1 && (
              <div className={cn("h-px w-3", done ? "bg-emerald-300" : "bg-muted")} />
            )}
          </div>
        );
      })}
      <span className="ml-2 text-xs text-muted-foreground font-mono">{currentState}</span>
    </div>
  );
}

function GateRow({ gate, runId }: { gate: HumanGate; runId: string }) {
  const decide = useDecideGate();
  const isPending = gate.status === "pending";

  return (
    <div className="flex items-start justify-between gap-3 py-2">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{gate.gate_type.replace(/_/g, " ")}</span>
          <Badge variant="outline" className={cn("text-xs", gateStatusColor(gate.status))}>
            {gate.status}
          </Badge>
        </div>
        {gate.decision_reason && (
          <p className="text-xs text-muted-foreground mt-0.5 truncate">{gate.decision_reason}</p>
        )}
        {gate.decision_by && (
          <p className="text-xs text-muted-foreground">by {gate.decision_by}</p>
        )}
        <p className="text-xs text-muted-foreground">{formatDate(gate.created_at)}</p>
      </div>
      {isPending && (
        <div className="flex gap-1.5 shrink-0">
          <Button type="button"
            size="sm"
            variant="outline"
            className="h-7 text-xs text-success border-success/20 hover:bg-success/10"
            disabled={decide.isPending}
            onClick={() => decide.mutate({ gateId: gate.id, runId, decision: "approved" })}
          >
            {decide.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : "Approve"}
          </Button>
          <Button type="button"
            size="sm"
            variant="outline"
            className="h-7 text-xs text-destructive border-destructive/20 hover:bg-destructive/10"
            disabled={decide.isPending}
            onClick={() => decide.mutate({ gateId: gate.id, runId, decision: "rejected" })}
          >
            Reject
          </Button>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface HarnessRunDetailProps {
  runId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function HarnessRunDetail({ runId, isOpen, onClose }: HarnessRunDetailProps) {
  const { data: run, isLoading: runLoading } = useHarnessRun(runId ?? undefined);
  const { data: checkpointsData } = useHarnessCheckpoints(runId ?? undefined);
  const { data: gatesData } = useHarnessGates(runId ?? undefined);
  const { data: validationData } = useHarnessValidation(runId ?? undefined);
  const transition = useTransitionHarnessRun();

  const checkpoints = checkpointsData?.items ?? [];
  const gates = gatesData?.items ?? [];
  const pendingGates = gates.filter((g) => g.status === "pending");

  function handleResume() {
    if (!run) return;
    const nextIdx = STATE_ORDER.indexOf(run.current_state as typeof STATE_ORDER[number]) + 1;
    const nextState = STATE_ORDER[nextIdx];
    if (nextState) {
      transition.mutate({ runId: run.id, data: { to_state: nextState } });
    }
  }

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-xl flex flex-col gap-0 p-0">
        <SheetHeader className="px-6 pt-6 pb-4 border-b">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <SheetTitle className="text-base font-semibold truncate">
                {run?.workflow_type?.replace(/_/g, " ") ?? "Harness Run"}
              </SheetTitle>
              {run && (
                <p className="text-xs text-muted-foreground font-mono mt-0.5 truncate">
                  {run.id}
                </p>
              )}
            </div>
            <Button type="button" variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={onClose} aria-label="Close">
              <X className="h-4 w-4" />
            </Button>
          </div>
        </SheetHeader>

        {runLoading && (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {run && (
          <ScrollArea className="flex-1">
            <div className="px-6 py-4 space-y-5">

              {/* Status + state progress */}
              <section>
                <div className="flex items-center gap-2 mb-3">
                  <Badge variant="outline" className={cn("text-xs", statusColor(run.status))}>
                    {run.status.replace(/_/g, " ")}
                  </Badge>
                  {run.account_id && (
                    <span className="text-xs text-muted-foreground">Account: {run.account_id}</span>
                  )}
                </div>
                <StateProgress currentState={run.current_state} status={run.status} />
              </section>

              <Separator />

              {/* Metadata */}
              <section>
                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                  Details
                </h3>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                  <dt className="text-muted-foreground">Initiated by</dt>
                  <dd className="font-medium">{run.initiated_by}</dd>
                  <dt className="text-muted-foreground">Trace ID</dt>
                  <dd className="font-mono text-xs truncate">{run.trace_id}</dd>
                  <dt className="text-muted-foreground">Created</dt>
                  <dd>{formatDate(run.created_at)}</dd>
                  <dt className="text-muted-foreground">Updated</dt>
                  <dd>{formatDate(run.updated_at)}</dd>
                  {run.value_pack_id && (
                    <>
                      <dt className="text-muted-foreground">Value pack</dt>
                      <dd className="font-mono text-xs">{run.value_pack_id}</dd>
                    </>
                  )}
                </dl>
              </section>

              {/* Control actions */}
              {!isTerminalState(run.current_state) && (
                <>
                  <Separator />
                  <section>
                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                      Actions
                    </h3>
                    <div className="flex gap-2">
                      {run.status === "failed" && (
                        <Button type="button"
                          size="sm"
                          variant="outline"
                          disabled={transition.isPending}
                          onClick={() =>
                            transition.mutate({
                              runId: run.id,
                              data: { to_state: run.current_state, human_override: true },
                            })
                          }
                        >
                          {transition.isPending ? (
                            <Loader2 className="h-3 w-3 animate-spin mr-1" />
                          ) : null}
                          Retry
                        </Button>
                      )}
                      {run.status === "running" && (
                        <Button type="button"
                          size="sm"
                          variant="outline"
                          disabled={transition.isPending}
                          onClick={handleResume}
                        >
                          Resume
                        </Button>
                      )}
                    </div>
                  </section>
                </>
              )}

              {/* Human gates */}
              {gates.length > 0 && (
                <>
                  <Separator />
                  <section>
                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      Human Gates
                      {pendingGates.length > 0 && (
                        <Badge className="ml-1 h-4 px-1.5 vf-text-micro bg-warning/100">
                          {pendingGates.length} pending
                        </Badge>
                      )}
                    </h3>
                    <div className="divide-y">
                      {gates.map((gate) => (
                        <GateRow key={gate.id} gate={gate} runId={run.id} />
                      ))}
                    </div>
                  </section>
                </>
              )}

              {/* Checkpoints */}
              {checkpoints.length > 0 && (
                <>
                  <Separator />
                  <section>
                    <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      Checkpoints ({checkpoints.length})
                    </h3>
                    <div className="space-y-1.5">
                      {checkpoints.map((chk) => (
                        <div
                          key={chk.id}
                          className="flex items-center justify-between text-sm py-1"
                        >
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
                            <span className="font-mono text-xs">{chk.state_name}</span>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(chk.created_at)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </section>
                </>
              )}

              {/* Validation */}
              <>
                <Separator />
                <section>
                  <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Claim Validation
                  </h3>
                  <ValidationSection
                    results={validationData?.results ?? []}
                    summary={validationData?.summary ?? null}
                  />
                </section>
              </>

            </div>
          </ScrollArea>
        )}
      </SheetContent>
    </Sheet>
  );
}
