/**
 * Intelligence Page - Production Implementation
 *
 * Uses real API data from Layer 4 Intelligence service.
 * Sections without API support have been removed.
 */
import { useNavigation } from "@/hooks/useNavigation";
import { useAccountBriefing } from "@/hooks/useIntelligence";
import {
  Building2, Users, AlertTriangle, Sparkles, ArrowRight,
  Target, Globe, Briefcase, BarChart3, CheckCircle2, Shield
} from "lucide-react";
import { StatCard, StatusBadgeBlock as StatusBadge, SectionCard } from "@/components/blocks";
import { WorkflowLayout } from "../components/WorkflowLayout";
import { useWorkflowStore } from "../store/workflowStore";
import { STEPS } from "../constants";


export default function Intelligence() {
  const { navigateTo } = useNavigation();
  const { setCurrentStep, setEnrichedEntities } = useWorkflowStore();
  const { prospect } = useWorkflowStore();
  // Use account ID from prospect if available
  const accountId = prospect?.companyId || null;
  
  // Fetch real intelligence data from API
  const { data: briefing, isLoading, error } = useAccountBriefing(accountId);
  
  const handleContinue = () => {
    if (briefing?.signals?.recent) {
      setEnrichedEntities(briefing.signals.recent.map((signal, index) => ({
        id: signal.id,
        name: signal.text,
        type: "pain_signal",
        confidence: 0.8, // Default confidence since API doesn't provide it
      })));
    }
    setCurrentStep(STEPS.AI_MODEL);
    navigateTo('/workflow/ai-model');
  };

  return (
    <WorkflowLayout>
      <main className="w-full space-y-4" aria-label="Prospect Intelligence">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-foreground">Prospect Intelligence</h1>
            <p className="text-sm text-muted-foreground mt-0.5">AI-enriched profile for Meridian Automotive — auto-generated from CRM, public data, and your ontology.</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 rounded-lg border border-primary/20">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
              <span className="text-xs text-primary font-medium">AI-Enriched</span>
            </div>
            <button onClick={handleContinue} className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:bg-primary/90 shadow-lg shadow-primary/25">
              <ArrowRight className="w-4 h-4" /> Generate AI Value Model
            </button>
          </div>
        </header>

        {/* Stats */}
        <section className="grid grid-cols-4 gap-3">
          <StatCard label="Company" value={briefing?.account_name || prospect?.companyName || "Loading..."} sub={briefing?.enrichment?.financials ? "Financial data available" : "No financial data"} icon={Building2} iconClassName="text-primary" iconBgClassName="bg-primary/10" />
          <StatCard label="Signals" value={briefing?.signals.total || 0} sub={Object.keys(briefing?.signals.by_category || {}).length + " categories"} icon={BarChart3} iconClassName="text-emerald-500" iconBgClassName="bg-emerald-500/10" />
          <StatCard label="Hypotheses" value={briefing?.hypotheses.total || 0} sub={`${briefing?.hypotheses.top_hypotheses?.length || 0} top`} icon={Target} iconClassName="text-purple-400" iconBgClassName="bg-purple-400/10" />
          <StatCard label="Evidence" value={briefing?.evidence.matching_case_studies || 0} sub="case studies matched" icon={Shield} iconClassName="text-amber-500" iconBgClassName="bg-amber-500/10" />
        </section>

        {/* Tabs */}
        <nav className="flex gap-2" aria-label="Intelligence sections">
          <button
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground"
          >
            Pain Signals
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary-foreground/20 text-primary-foreground">{briefing?.signals.total || 0}</span>
          </button>
          <div className="ml-auto flex items-center gap-1.5 px-3 py-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            <span className="text-xs text-emerald-500 font-medium">AI-Enriched</span>
          </div>
        </nav>

        {/* Pain Signals */}
        {isLoading ? (
          <SectionCard title="Loading Intelligence Data">
            <div className="p-8 text-center text-muted-foreground">Loading account briefing...</div>
          </SectionCard>
        ) : error ? (
          <SectionCard title="Error Loading Intelligence">
            <div className="p-8 text-center text-destructive">Failed to load intelligence data. Please try again.</div>
          </SectionCard>
        ) : (
          <SectionCard title="Detected Pain Signals" description="AI-sourced signals from earnings calls, job postings, regulatory filings, and news">
            <div className="divide-y divide-border/60">
              {briefing?.signals.recent?.length ? (
                briefing.signals.recent.map((signal) => (
                  <div key={signal.id} className="flex items-center gap-4 px-6 py-3.5 hover:bg-muted/50 transition-colors">
                    <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
                      <AlertTriangle className="w-4 h-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-foreground">{signal.text}</p>
                      <p className="text-[10px] text-muted-foreground/60 mt-0.5">Category: {signal.category}</p>
                    </div>
                    <div className="w-24 shrink-0">
                      <span className="text-[10px] text-muted-foreground">
                        Detected {signal.detected_at ? new Date(signal.detected_at).toLocaleDateString() : "N/A"}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-muted-foreground">No pain signals detected for this account.</div>
              )}
            </div>
          </SectionCard>
        )}
      </main>
    </WorkflowLayout>
  );
}
