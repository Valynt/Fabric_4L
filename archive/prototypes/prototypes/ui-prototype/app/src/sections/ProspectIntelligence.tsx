import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Building2, Users, AlertTriangle, Sparkles, ArrowRight,
  Target, Globe, Briefcase, BarChart3, CheckCircle2, Shield
} from "lucide-react";
import { StatCard, SectionCard, ProgressBar } from "@/components/blocks";

const painSignals = [
  { signal: "340 unfilled assembly positions, 18% production turnover", source: "LinkedIn Jobs + HR Data", confidence: 96, icon: Users },
  { signal: "Q4 earnings: 'capacity constraints limiting OEM deliveries'", source: "Earnings Call Transcript", confidence: 92, icon: BarChart3 },
  { signal: "3 major customer complaints on inconsistent torque application", source: "Quality Management System", confidence: 88, icon: AlertTriangle },
  { signal: "14 ergonomic injuries in assembly cells (FY2025)", source: "OSHA 300A Filing", confidence: 85, icon: Shield },
  { signal: "45-min changeover between EV and ICE component lines", source: "Production Engineering Report", confidence: 82, icon: Target },
];

const stakeholderMap = [
  { name: "Patricia Chen", title: "VP Manufacturing Operations", role: "Champion", influence: 90, interest: 95, concern: "Labor shortage + capacity constraints" },
  { name: "Michael Torres", title: "Chief Operating Officer", role: "Decision Maker", influence: 95, interest: 85, concern: "OEM delivery commitments & throughput" },
  { name: "Susan Park", title: "VP Quality & EHS", role: "Influencer", influence: 75, interest: 88, concern: "Defect reduction & injury prevention" },
  { name: "David Kowalski", title: "CFO", role: "Approver", influence: 92, interest: 55, concern: "TCO, ROI, and payback period" },
  { name: "Raj Patel", title: "Plant Manager — Detroit", role: "Influencer", influence: 65, interest: 90, concern: "Line uptime & operator adoption" },
  { name: "Linda Harris", title: "Director, Continuous Improvement", role: "User", influence: 50, interest: 92, concern: "Changeover time & flexibility" },
];

const ontologyMatch = [
  { capability: "Forge X1 Cobot Workcell", relevance: 98, matchedPain: "340 unfilled assembly positions", evidence: 8 },
  { capability: "AI Torque Control", relevance: 94, matchedPain: "Inconsistent torque, 3 complaints", evidence: 6 },
  { capability: "Adaptive Mixed-Model Software", relevance: 90, matchedPain: "45-min EV/ICE changeover", evidence: 5 },
  { capability: "Ergonomic Exoskeleton Integration", relevance: 78, matchedPain: "14 ergonomic injuries", evidence: 4 },
  { capability: "Predictive Maintenance Suite", relevance: 72, matchedPain: "Unplanned downtime on 3 shifts", evidence: 3 },
];

export default function ProspectIntelligence() {
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState<string>("pain");

  const tabButtons = [
    { id: "pain", label: "Pain Signals", count: painSignals.length },
    { id: "stakeholders", label: "Stakeholder Map", count: stakeholderMap.length },
    { id: "ontology", label: "Ontology Match", count: ontologyMatch.length },
  ];

  return (
    <main className="max-w-7xl mx-auto space-y-4" aria-label="Prospect Intelligence">
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
          <button onClick={() => navigate("/ai-model")} className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:bg-primary/90 shadow-lg shadow-primary/25">
            <ArrowRight className="w-4 h-4" /> Generate AI Value Model
          </button>
        </div>
      </header>

      {/* Stats */}
      <section className="grid grid-cols-4 gap-3">
        <StatCard label="Company" value="Meridian Auto" sub="Tier 1 Auto — $4.2B" icon={Building2} iconClassName="text-primary" iconBgClassName="bg-primary/10" />
        <StatCard label="Headcount" value="12,000" sub="3 plants, 2,400 assembly" icon={Globe} iconClassName="text-emerald-500" iconBgClassName="bg-emerald-500/10" />
        <StatCard label="Assembly Lines" value="34" sub="Mixed EV + ICE" icon={Users} iconClassName="text-purple-400" iconBgClassName="bg-purple-400/10" />
        <StatCard label="CRM Opportunity" value="MAC-2026-0417" sub="Stage: Solution — $2.4M" icon={Briefcase} iconClassName="text-amber-500" iconBgClassName="bg-amber-500/10" />
      </section>

      {/* Tabs */}
      <nav className="flex gap-2" aria-label="Intelligence sections">
        {tabButtons.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveSection(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeSection === tab.id ? "bg-primary text-primary-foreground" : "bg-card border border-border text-muted-foreground hover:bg-muted"}`}
          >
            {tab.label}
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${activeSection === tab.id ? "bg-primary-foreground/20 text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{tab.count}</span>
          </button>
        ))}
        <div className="ml-auto flex items-center gap-1.5 px-3 py-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span className="text-xs text-emerald-500 font-medium">Ready to model</span>
        </div>
      </nav>

      {/* Pain Signals */}
      {activeSection === "pain" && (
        <SectionCard title="Detected Pain Signals — Last 90 Days" description="AI-sourced signals from earnings calls, job postings, regulatory filings, and news">
          <div className="divide-y divide-border/60">
            {painSignals.map((p, i) => (
              <div key={i} className="flex items-center gap-4 px-6 py-3.5 hover:bg-muted/50 transition-colors">
                <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
                  <p.icon className="w-4 h-4 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground">{p.signal}</p>
                  <p className="text-[10px] text-muted-foreground/60 mt-0.5">Source: {p.source}</p>
                </div>
                <div className="w-24 shrink-0">
                  <ProgressBar value={p.confidence} max={100} size="sm" />
                  <p className="text-[10px] text-muted-foreground mt-0.5 text-center">{p.confidence}% confidence</p>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Stakeholder Map */}
      {activeSection === "stakeholders" && (
        <SectionCard title="Stakeholder Map — Auto-detected from CRM + LinkedIn">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted border-b border-border">
                  <th className="text-left px-4 py-3 font-semibold text-muted-foreground">Name</th>
                  <th className="text-left px-4 py-3 font-semibold text-muted-foreground">Title</th>
                  <th className="text-left px-4 py-3 font-semibold text-muted-foreground">Role</th>
                  <th className="text-center px-4 py-3 font-semibold text-muted-foreground">Influence</th>
                  <th className="text-center px-4 py-3 font-semibold text-muted-foreground">Interest</th>
                  <th className="text-left px-4 py-3 font-semibold text-muted-foreground">Key Concern</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {stakeholderMap.map((s) => (
                  <tr key={s.name} className="hover:bg-muted/50">
                    <td className="px-4 py-3 font-medium text-foreground">{s.name}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{s.title}</td>
                    <td className="px-4 py-3"><span className="text-[10px] px-2 py-0.5 bg-primary/10 text-primary rounded-full font-medium">{s.role}</span></td>
                    <td className="px-4 py-3"><ProgressBar value={s.influence} max={100} size="sm" className="w-20 mx-auto" /></td>
                    <td className="px-4 py-3"><ProgressBar value={s.interest} max={100} barClassName="bg-emerald-400" size="sm" className="w-20 mx-auto" /></td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{s.concern}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}

      {/* Ontology Match */}
      {activeSection === "ontology" && (
        <SectionCard title="Ontology Match — Axiom Forge X1 vs. Meridian Pains">
          <div className="divide-y divide-border/60">
            {ontologyMatch.map((o) => (
              <div key={o.capability} className="flex items-center gap-4 px-6 py-3.5">
                <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <span className="text-lg font-bold text-primary">{o.relevance}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-foreground">{o.capability}</p>
                  <p className="text-xs text-muted-foreground">Matched to: <span className="text-primary">{o.matchedPain}</span></p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs text-muted-foreground">{o.evidence} evidence items</p>
                  <ProgressBar value={o.relevance} max={100} size="sm" className="w-20 mt-1 ml-auto" />
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </main>
  );
}
