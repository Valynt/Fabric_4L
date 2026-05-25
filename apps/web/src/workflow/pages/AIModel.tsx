import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useNavigation } from "@/hooks/useNavigation";
import {
  BrainCircuit, CheckCircle2, XCircle, RefreshCw, Sparkles, ArrowRight,
  TrendingUp, Shield, Zap, Star
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/blocks";
import { WorkflowLayout } from "../components/WorkflowLayout";
import { WorkflowStatusBanner } from "../components/WorkflowStatusBanner";
import { useWorkflowStore } from "../store/workflowStore";
import { STEPS } from "../constants";
import { useHarnessRun } from "@/hooks/useHarness";
import { cn } from "@/lib/utils";

interface AIHypothesis {
  id: string; useCase: string; hypothesis: string;
  expectedValue: string; confidence: number; status: "suggested" | "approved" | "modified" | "rejected";
  matchedPain: string; evidenceCount: number;
}

const initialHypotheses: AIHypothesis[] = [
  { id: "h1", useCase: "Reduce Labor Dependency in Assembly", hypothesis: "IF Forge X1 cobot workcells augment 85 assemblers THEN labor cost drops $6.2M annually with 3-shift coverage", expectedValue: "$6.20M", confidence: 94, status: "suggested", matchedPain: "340 unfilled positions, 18% turnover", evidenceCount: 5 },
  { id: "h2", useCase: "Eliminate Torque Defects", hypothesis: "IF AI torque control with real-time feedback THEN defect rate drops 72% eliminating warranty exposure", expectedValue: "$3.80M", confidence: 91, status: "suggested", matchedPain: "3 major customer complaints on torque", evidenceCount: 4 },
  { id: "h3", useCase: "Increase Throughput on 3 Shifts", hypothesis: "IF cobot-paced cells with predictive maintenance THEN cycle time drops 23% and uptime hits 96%", expectedValue: "$2.90M", confidence: 87, status: "suggested", matchedPain: "Capacity constraints, missing OEM deliveries", evidenceCount: 4 },
  { id: "h4", useCase: "Reduce Ergonomic Injuries", hypothesis: "IF cobots handle repetitive/heavy tasks + exo integration THEN recordable injuries drop 65%", expectedValue: "$1.40M", confidence: 78, status: "suggested", matchedPain: "14 ergonomic injuries, OSHA above avg", evidenceCount: 3 },
  { id: "h5", useCase: "Cut Changeover Time for Mixed-Model", hypothesis: "IF adaptive mixed-model software THEN EV-to-ICE changeover drops from 45 to 8 minutes", expectedValue: "$580K", confidence: 72, status: "suggested", matchedPain: "45-min changeover hurting agility", evidenceCount: 3 },
];

// ── Workflow status badge helpers ─────────────────────────────────────────────

function runStatusBadgeClass(status: string): string {
  switch (status) {
    case "completed":        return "bg-emerald-500/15 text-emerald-700 border-emerald-200";
    case "running":          return "bg-blue-500/15 text-blue-700 border-blue-200";
    case "failed":           return "bg-red-500/15 text-red-700 border-red-200";
    case "waiting_for_human": return "bg-amber-500/15 text-amber-700 border-amber-200";
    case "cancelled":        return "bg-muted/15 text-muted-foreground border-border";
    default:                 return "bg-muted text-muted-foreground border-border";
  }
}

export default function AIModel() {
  const { navigateTo } = useNavigation();
  const { setCurrentStep } = useWorkflowStore();
  const [searchParams] = useSearchParams();
  const [hypotheses, setHypotheses] = useState<AIHypothesis[]>(initialHypotheses);
  const [generating, setGenerating] = useState(false);

  // Read optional harness run ID from query params (?runId=...)
  const runId = searchParams.get("runId") ?? undefined;
  const { data: harnessRun } = useHarnessRun(runId);

  const updateStatus = (id: string, status: AIHypothesis["status"]) => {
    setHypotheses((prev) => prev.map((h) => h.id === id ? { ...h, status } : h));
  };

  const approved = hypotheses.filter((h) => h.status === "approved" || h.status === "modified");
  const totalValue = approved.reduce((s, h) => s + parseFloat(h.expectedValue.replace(/[$MK]/g, "")), 0);
  const avgConfidence = approved.length > 0 ? Math.round(approved.reduce((s, h) => s + h.confidence, 0) / approved.length) : 0;

  const handleRegenerate = () => { setGenerating(true); setTimeout(() => setGenerating(false), 1200); };
  void generating;

  const handleContinue = () => {
    setCurrentStep(STEPS.DRIVER_TREE);
    navigateTo('/workflow/driver-tree');
  };

  return (
    <WorkflowLayout>
      <main className="w-full space-y-4" aria-label="AI Generated Value Model">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <BrainCircuit className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">AI-Generated Value Model</h1>
              <p className="text-sm text-muted-foreground">ValuePilot analyzed Meridian&apos;s profile and generated 5 hypotheses.</p>
              {harnessRun && (
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-muted-foreground">Workflow:</span>
                  <Badge
                    variant="outline"
                    className={cn("text-xs", runStatusBadgeClass(harnessRun.status))}
                  >
                    {harnessRun.status.replace(/_/g, " ")}
                  </Badge>
                  <span className="text-xs font-mono text-muted-foreground truncate max-w-32">
                    {harnessRun.current_state}
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleRegenerate} className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-lg text-sm text-muted-foreground hover:bg-muted">
              <RefreshCw className={`w-4 h-4 ${generating ? "animate-spin" : ""}`} /> Regenerate
            </button>
            <button onClick={handleContinue} className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:bg-primary/90 shadow-lg shadow-primary/25">
              <ArrowRight className="w-4 h-4" /> Build Driver Tree
            </button>
          </div>
        </header>

        {/* Live workflow status — sourced from the most recent harness run */}
        <WorkflowStatusBanner className="mb-1" />

        <section className="grid grid-cols-4 gap-3">
          <StatCard label="AI Hypotheses" value={hypotheses.length} sub="Generated" icon={Sparkles} iconClassName="text-primary" iconBgClassName="bg-primary/10" />
          <StatCard label="Approved" value={approved.length} sub={`${hypotheses.length - approved.length} pending`} icon={CheckCircle2} iconClassName="text-emerald-500" iconBgClassName="bg-emerald-500/10" />
          <StatCard label="Approved Value" value={`$${totalValue.toFixed(1)}M`} sub="Annual potential" icon={TrendingUp} iconClassName="text-purple-400" iconBgClassName="bg-purple-400/10" />
          <StatCard label="Avg Confidence" value={`${avgConfidence}%`} sub="Of approved items" icon={Star} iconClassName="text-amber-500" iconBgClassName="bg-amber-500/10" />
        </section>

        <section className="space-y-3" aria-label="Hypotheses">
          {hypotheses.map((h) => {
            return (
              <article
                key={h.id}
                className={`bg-card rounded-xl border-2 transition-all ${
                  h.status === "approved" ? "border-emerald-500/30" : h.status === "rejected" ? "border-border opacity-60" : "border-border hover:border-primary/50"
                }`}
              >
                <div className="p-5">
                  <div className="flex items-start gap-4">
                    <div className="shrink-0">
                      <div className="relative w-12 h-12">
                        <svg className="w-12 h-12 -rotate-90" viewBox="0 0 48 48">
                          <circle cx="24" cy="24" r="20" fill="none" stroke="oklch(var(--muted))" strokeWidth="4" />
                          <circle cx="24" cy="24" r="20" fill="none" stroke={h.confidence >= 80 ? "oklch(0.696 0.17 145)" : h.confidence >= 60 ? "oklch(0.75 0.17 80)" : "oklch(0.637 0.207 25)"} strokeWidth="4" strokeDasharray={`${h.confidence * 1.26} 126`} strokeLinecap="round" />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                          <span className="text-xs font-bold text-card-foreground">{h.confidence}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h2 className="font-semibold text-card-foreground text-sm">{h.useCase}</h2>
                        {h.status !== "suggested" && (
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${h.status === "approved" ? "bg-emerald-500/10 text-emerald-500" : "bg-muted text-muted-foreground"}`}>{h.status}</span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground italic mb-2">&ldquo;{h.hypothesis}&rdquo;</p>

                      <div className="flex items-center gap-4 mb-3 flex-wrap">
                        <span className="flex items-center gap-1 text-xs font-semibold text-primary">
                          <TrendingUp className="w-3.5 h-3.5" />{h.expectedValue} annual
                        </span>
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Zap className="w-3.5 h-3.5 text-amber-500" />{h.matchedPain}
                        </span>
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Shield className="w-3.5 h-3.5" />{h.evidenceCount} evidence items
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {h.status === "suggested" ? (
                          <>
                            <button onClick={() => updateStatus(h.id, "approved")} className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 text-emerald-500 rounded-lg text-xs font-medium hover:bg-emerald-500/20">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Approve
                            </button>
                            <button onClick={() => updateStatus(h.id, "modified")} className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 text-primary rounded-lg text-xs font-medium hover:bg-primary/20">
                              <RefreshCw className="w-3.5 h-3.5" /> Modify
                            </button>
                            <button onClick={() => updateStatus(h.id, "rejected")} className="flex items-center gap-1.5 px-3 py-1.5 bg-muted text-muted-foreground rounded-lg text-xs font-medium hover:bg-muted/80">
                              <XCircle className="w-3.5 h-3.5" /> Skip
                            </button>
                          </>
                        ) : h.status === "approved" ? (
                          <span className="flex items-center gap-1.5 text-xs text-emerald-500 font-medium"><CheckCircle2 className="w-3.5 h-3.5" /> Approved — will build driver tree</span>
                        ) : (
                          <span className="flex items-center gap-1.5 text-xs text-muted-foreground/60"><XCircle className="w-3.5 h-3.5" /> Skipped</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </section>

        {/* Demo data notice */}
        <p className="text-xs text-muted-foreground/60 text-center pt-1">
          Hypotheses are demo data — backend model generation is not yet wired.
        </p>
      </main>
    </WorkflowLayout>
  );
}
