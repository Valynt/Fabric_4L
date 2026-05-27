import { useState } from "react";
import {
  Home, BookOpen, Compass, Box, GitBranch, Truck, ShieldCheck,
  Settings, Search, Bell, Send, Bot, Sparkles,
  CheckCircle2, ArrowRight, X,
  Flame, Target, Users, TrendingUp,
  Building2, Factory, Briefcase, FileText,
  RefreshCw, Circle
} from "lucide-react";

/* ─── Pain Signals Data with UNIQUE detail per signal ─── */
interface PainSignal {
  id: number; label: string; category: string;
  confidence: number; impact: string; color: string;
  hypothesis: string; findings: string[];
  rootCauses: { label: string; pct: number }[];
  evidence: { type: string; title: string; relevance: number; match: "high" | "medium" }[];
}

const painSignals: PainSignal[] = [
  { id: 1, label: "Production Downtime", category: "OPERATIONAL", confidence: 94, impact: "$2.4M/yr", color: "bg-rose-500",
    hypothesis: "Meridian may be facing a widening operational performance gap driven by recurring unplanned downtime across its plant network. If confirmed, aging equipment, changeover inefficiency, and material-related interruptions are likely suppressing throughput, reducing labor productivity, and increasing cost pressure across EV and ICE operations.",
    findings: ["Unplanned downtime averaging 4.2 hours/week across 3 plants", "Root causes confirmed via maintenance logs and operator interviews"],
    rootCauses: [{ label: "Aging equipment", pct: 45 }, { label: "Changeover delays", pct: 30 }, { label: "Material shortages", pct: 25 }],
    evidence: [{ type: "Case Study", title: "Continental AG", relevance: 95, match: "high" }, { type: "Benchmark", title: "Tier 1 Auto Average", relevance: 88, match: "high" }, { type: "ROI Calculator", title: "Labor Efficiency", relevance: 82, match: "medium" }],
  },
  { id: 2, label: "Labor Shortage — Welders", category: "WORKFORCE", confidence: 91, impact: "12% capacity", color: "bg-amber-500",
    hypothesis: "Meridian's welding operations are capacity-constrained by a structural shortage of certified welders. This gap is forcing overtime escalation, temp staffing dependency, and quality compromises that compound across the EV battery tray and structural component lines.",
    findings: ["42 welder positions unfilled across 3 plants", "Average time-to-fill: 89 days (industry avg: 34 days)", "Overtime hours up 34% YoY"],
    rootCauses: [{ label: "Skills gap", pct: 40 }, { label: "Competition", pct: 35 }, { label: "Geographic", pct: 25 }],
    evidence: [{ type: "Benchmark", title: "Welding Skills Gap 2026", relevance: 92, match: "high" }, { type: "Case Study", title: "Magna Steyr", relevance: 87, match: "high" }],
  },
  { id: 3, label: "Quality Defect Rate", category: "QUALITY", confidence: 88, impact: "$890K/yr", color: "bg-orange-500",
    hypothesis: "Quality metrics are degrading with PPM increasing 20% in two quarters. Weld porosity and dimensional variance are the primary drivers, suggesting either process drift, equipment calibration issues, or incoming material quality problems.",
    findings: ["PPM increased from 342 to 412 over 2 quarters", "Warranty returns correlated with 3 specific defect clusters"],
    rootCauses: [{ label: "Weld porosity", pct: 38 }, { label: "Dimensional variance", pct: 27 }, { label: "Surface finish", pct: 21 }, { label: "Other", pct: 14 }],
    evidence: [{ type: "Case Study", title: "Bosch Automotive", relevance: 91, match: "high" }, { type: "Tool", title: "Pareto Defect Analyzer", relevance: 85, match: "medium" }],
  },
  { id: 4, label: "Energy Cost Surge", category: "COST", confidence: 85, impact: "$1.1M/yr", color: "bg-red-500",
    hypothesis: "Industrial electricity rates have surged 34% in Meridian's operating regions, creating a direct margin compression event. Plant 2 specifically exceeds energy efficiency benchmarks by 18%, suggesting both external market pressure and internal efficiency gaps.",
    findings: ["Industrial electricity rates up 34% across all 3 plant locations", "Plant 2 exceeds energy benchmark by 18%"],
    rootCauses: [{ label: "Rate increase", pct: 55 }, { label: "Inefficient equipment", pct: 30 }, { label: "Air leaks", pct: 15 }],
    evidence: [{ type: "Benchmark", title: "Industrial Energy Index 2026", relevance: 90, match: "high" }, { type: "Case Study", title: "Aptiv Energy Optimization", relevance: 83, match: "medium" }],
  },
  { id: 5, label: "Supplier Delays", category: "SUPPLY CHAIN", confidence: 82, impact: "3–5 day slip", color: "bg-yellow-500",
    hypothesis: "Three critical suppliers are consistently missing delivery windows, creating a cascade of production scheduling disruptions. On-time delivery has dropped to 76% and safety stock is depleted for 2 SKUs, exposing Meridian to line-down risk.",
    findings: ["3 of 12 critical suppliers miss delivery windows consistently", "On-time delivery rate dropped to 76% (from 91%)", "Safety stock depleted for 2 critical SKUs"],
    rootCauses: [{ label: "Supplier capacity", pct: 42 }, { label: "Logistics", pct: 33 }, { label: "Forecast accuracy", pct: 25 }],
    evidence: [{ type: "Benchmark", title: "Auto Supplier OTIF 2026", relevance: 86, match: "high" }, { type: "Case Study", title: "ZF Friedrichshafen", relevance: 79, match: "medium" }],
  },
  { id: 6, label: "Regulatory Compliance", category: "RISK", confidence: 78, impact: "Audit risk", color: "bg-violet-500",
    hypothesis: "New EPA emissions reporting requirements for 2026 create a compliance gap. Current data collection is manual and fragmented across 3 systems, creating audit risk and potential penalties of up to $50K per facility per violation.",
    findings: ["New EPA reporting requirements effective Jan 2026", "Data collection spans 3 disconnected systems", "Penalty exposure: $50K/facility/violation"],
    rootCauses: [{ label: "Manual processes", pct: 50 }, { label: "System fragmentation", pct: 35 }, { label: "Lack of automation", pct: 15 }],
    evidence: [{ type: "Tool", title: "EPA Compliance Checker", relevance: 94, match: "high" }, { type: "Benchmark", title: "Tier 1 Compliance Rates", relevance: 80, match: "medium" }],
  },
];

const stakeholders = [
  { initials: "PC", name: "Patricia Chen", title: "VP Manufacturing Ops", role: "Economic Buyer", score: 95, color: "bg-emerald-500" },
  { initials: "MR", name: "Michael Ross", title: "Plant Manager", role: "Technical Evaluator", score: 78, color: "bg-blue-500" },
  { initials: "LW", name: "Lisa Wang", title: "CFO", role: "Financial Approver", score: 72, color: "bg-purple-500" },
  { initials: "JT", name: "James Torres", title: "Engineering Dir", role: "User Champion", score: 68, color: "bg-sky-500" },
];

const agentMessages = [
  { id: 1, agent: "ValuePilot", avatar: "VP", avatarColor: "bg-primary", message: "I've analyzed Meridian Automotive against our manufacturing ontology. Here's what I found:", type: "chat", timestamp: "10:23 AM" },
  { id: 2, agent: "ValuePilot", avatar: "VP", avatarColor: "bg-primary", message: null, type: "process", process: { steps: [{ label: "Loading CRM context", status: "done" }, { label: "Evaluating competitive landscape", status: "done" }, { label: "Risk Assessment", status: "done" }, { label: "Synthesizing findings", status: "done" }] }, timestamp: "10:23 AM" },
  { id: 3, agent: "ValuePilot", avatar: "VP", avatarColor: "bg-primary", message: "Ontology match: 73% — Manufacturing v3.2 with Automotive extension. 6 pain signals detected. Ready to model.", type: "summary", timestamp: "10:24 AM" },
  { id: 4, agent: "ValuePilot", avatar: "VP", avatarColor: "bg-primary", message: "Would you like me to generate a value driver tree, or do you want to explore the pain signals first?", type: "prompt", timestamp: "10:24 AM" },
];

function ProcessStep({ label, status }: { label: string; status: string }) {
  return (
    <div className="flex items-center gap-2 py-1">
      {status === "done" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />}
      {status === "active" && <RefreshCw className="w-3.5 h-3.5 text-primary animate-spin shrink-0" />}
      {status === "pending" && <Circle className="w-3.5 h-3.5 text-muted-foreground/40 shrink-0" />}
      <span className={`text-xs ${status === "done" ? "text-foreground" : status === "active" ? "text-primary" : "text-muted-foreground/50"}`}>{label}</span>
    </div>
  );
}

/* ─── Drill Down Panel ─── */
function DrillDownPanel({ signal, onClose }: { signal: PainSignal; onClose: () => void }) {
  return (
    <div className="h-full flex flex-col">
      <div className="px-5 py-4 border-b border-border flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg ${signal.color} flex items-center justify-center`}>
          <FileText className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-base font-semibold text-foreground">{signal.label}</h2>
        </div>
        <span className={`text-[10px] px-2.5 py-1 rounded-full font-semibold text-white ${signal.color}`}>{signal.category}</span>
        <button onClick={onClose} className="w-7 h-7 rounded-lg hover:bg-muted flex items-center justify-center ml-1"><X className="w-4 h-4 text-muted-foreground" /></button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 border border-border rounded-xl text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Confidence</p>
            <p className="text-xl font-bold text-foreground">{signal.confidence}%</p>
          </div>
          <div className="p-3 border border-border rounded-xl text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Impact</p>
            <p className="text-xl font-bold text-foreground">{signal.impact}</p>
          </div>
          <div className="p-3 border border-border rounded-xl text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Trend</p>
            <p className="text-xl font-bold text-emerald-600">↑ Active</p>
          </div>
        </div>

        <section>
          <h3 className="text-xs font-semibold text-foreground mb-2">Executive Hypothesis</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">{signal.hypothesis}</p>
        </section>

        <section>
          <h3 className="text-xs font-semibold text-foreground mb-3">Signal Analysis</h3>
          <ul className="space-y-1.5 mb-4">
            {signal.findings.map((f, i) => (
              <li key={i} className="text-xs text-muted-foreground flex items-start gap-2"><span className="text-primary mt-0.5">•</span>{f}</li>
            ))}
          </ul>
          <div className="space-y-2">
            {signal.rootCauses.map((rc) => (
              <div key={rc.label} className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground w-28 text-right shrink-0">{rc.label}</span>
                <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden"><div className={`h-full rounded-full ${signal.color}`} style={{ width: `${rc.pct}%` }} /></div>
                <span className="text-xs font-medium text-foreground w-8 shrink-0">{rc.pct}%</span>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h3 className="text-xs font-semibold text-foreground mb-3">Company Context</h3>
          <div className="grid grid-cols-5 gap-2">
            {[{ icon: Building2, label: "Revenue", value: "$4.2B" }, { icon: Users, label: "Employees", value: "12,000" }, { icon: Factory, label: "Plants", value: "3" }, { icon: Briefcase, label: "Assembly", value: "34" }, { icon: Target, label: "Vehicle", value: "EV+ICE" }].map((item) => (
              <div key={item.label} className="flex flex-col items-center text-center p-2 border border-border rounded-lg">
                <item.icon className="w-4 h-4 text-muted-foreground mb-1" />
                <p className="text-sm font-bold text-foreground">{item.value}</p>
                <p className="text-[9px] text-muted-foreground">{item.label}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h3 className="text-xs font-semibold text-foreground mb-3">Evidence Matches</h3>
          <div className="space-y-2">
            {signal.evidence.map((e) => (
              <div key={e.title} className="flex items-center gap-3 p-3 border border-border rounded-xl hover:border-primary/30 transition-colors cursor-pointer group">
                <span className={`text-[9px] px-2 py-0.5 rounded-full font-medium border ${e.match === "high" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-amber-50 text-amber-700 border-amber-200"}`}>{e.match === "high" ? "High match" : "Medium match"}</span>
                <span className="text-[9px] text-muted-foreground">{e.type}</span>
                <div className="flex-1 min-w-0"><p className="text-xs font-medium text-foreground truncate">{e.title}</p></div>
                <span className="text-xs font-bold text-foreground">{e.relevance}%</span>
                <ArrowRight className="w-3.5 h-3.5 text-muted-foreground/0 group-hover:text-muted-foreground transition-colors" />
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="border-t border-border p-4 flex items-center gap-3 shrink-0">
        <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-border rounded-xl text-xs font-medium text-foreground hover:bg-muted transition-colors">View full analysis <ArrowRight className="w-3 h-3" /></button>
        <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-foreground text-background rounded-xl text-xs font-semibold hover:bg-foreground/90 transition-colors"><Sparkles className="w-3.5 h-3.5" /> Add to model</button>
      </div>
    </div>
  );
}

export default function AgentMockup() {
  const [chatInput, setChatInput] = useState("");
  const [agentExpanded, setAgentExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState<"chat" | "options">("chat");
  const [drillDownSignal, setDrillDownSignal] = useState<PainSignal | null>(null);

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      {/* HEADER */}
      <header className="h-12 border-b border-border flex items-center justify-between px-3 shrink-0 bg-card">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center"><Sparkles className="w-3.5 h-3.5 text-primary-foreground" /></div>
            <span className="text-sm font-bold text-foreground">ValuePilot</span>
          </div>
          <div className="h-4 w-px bg-border" />
          <div className="relative">
            <Search className="w-3 h-3 text-muted-foreground absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input placeholder="Search entities, domains, cases..." className="pl-7 pr-3 py-1 w-64 text-[11px] bg-muted rounded-md border border-input focus:outline-none focus:ring-1 focus:ring-ring" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">Admin mode</span>
          <button className="w-7 h-7 rounded-md hover:bg-muted flex items-center justify-center"><Bell className="w-3.5 h-3.5 text-muted-foreground" /></button>
          <div className="w-6 h-6 rounded-full bg-foreground flex items-center justify-center text-[9px] font-bold text-background">SC</div>
        </div>
      </header>

      {/* BODY */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Icon Sidebar */}
        <aside className="w-12 border-r border-border bg-card flex flex-col items-center py-3 gap-1 shrink-0">
          {[{ icon: Home, active: false }, { icon: BookOpen, active: false }, { icon: Compass, active: false }, { icon: Box, active: false }, { icon: GitBranch, active: true }, { icon: Truck, active: false }, { icon: ShieldCheck, active: false }, { icon: Settings, active: false }].map((item, i) => (
            <button key={i} className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${item.active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-muted"}`}>
              <item.icon className="w-4 h-4" />
            </button>
          ))}
        </aside>

        {/* Backdrop */}
        {drillDownSignal && (
          <div className="absolute inset-0 bg-black/20 z-10" style={{ left: 48 }} onClick={() => setDrillDownSignal(null)} />
        )}

        {/* Main Content */}
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Title Bar */}
          <div className="h-14 border-b border-border flex items-center justify-between px-5 bg-card shrink-0">
            <div className="flex items-baseline gap-3">
              <h1 className="text-lg font-bold text-foreground">Intelligence</h1>
              <span className="text-sm text-muted-foreground">—</span>
              <span className="text-base font-bold text-primary">Meridian Automotive Components</span>
              <span className="text-[10px] px-2 py-0.5 bg-primary/10 text-primary rounded-full font-medium">Manufacturing · $4.2B</span>
            </div>
            <div className="flex items-center gap-2">
              <button className="px-3 py-1.5 text-[11px] font-medium border border-border rounded-lg hover:bg-muted transition-colors">Select Prospect</button>
              <button className="px-3 py-1.5 text-[11px] font-semibold bg-foreground text-background rounded-lg hover:bg-foreground/90 transition-colors flex items-center gap-1.5"><Sparkles className="w-3 h-3" /> Ready to model</button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-5">
            <div className="max-w-3xl mx-auto space-y-5">

              {/* Pain Signals — ORIGINAL SIMPLE LIST */}
              <section className="bg-card border border-border rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Flame className="w-4 h-4 text-rose-500" />
                    <h2 className="text-sm font-semibold text-foreground">Pain Signals</h2>
                  </div>
                  <span className="text-[10px] text-muted-foreground">6 detected · sorted by confidence</span>
                </div>
                <div className="space-y-1">
                  {painSignals.map((s) => (
                    <div key={s.id} className={`flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer group ${drillDownSignal?.id === s.id ? "bg-primary/5 border border-primary/20" : "border border-transparent"}`}>
                      <div className={`w-1 h-8 rounded-full ${s.color}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-foreground">{s.label}</span>
                          <span className="text-[9px] px-1.5 py-0.5 bg-muted rounded-full text-muted-foreground">{s.category}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-right">
                        <div>
                          <div className="text-[10px] text-muted-foreground">Confidence</div>
                          <div className="text-xs font-semibold text-foreground">{s.confidence}%</div>
                        </div>
                        <div>
                          <div className="text-[10px] text-muted-foreground">Impact</div>
                          <div className="text-xs font-semibold text-foreground">{s.impact}</div>
                        </div>
                        <button
                          onClick={() => setDrillDownSignal(drillDownSignal?.id === s.id ? null : s)}
                          className={`w-7 h-7 rounded-lg border flex items-center justify-center transition-all shrink-0 ${drillDownSignal?.id === s.id ? "bg-primary border-primary text-primary-foreground" : "border-border opacity-0 group-hover:opacity-100 hover:bg-primary hover:border-primary hover:text-primary-foreground text-muted-foreground"}`}
                        >
                          {drillDownSignal?.id === s.id ? <X className="w-3.5 h-3.5" /> : <ArrowRight className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* Stakeholder Map */}
              <section className="bg-card border border-border rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-primary" />
                    <h2 className="text-sm font-semibold text-foreground">Stakeholder Map</h2>
                  </div>
                  <span className="text-[10px] text-muted-foreground">4 mapped from CRM + enrichment</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {stakeholders.map((s) => (
                    <div key={s.initials} className="flex items-center gap-3 p-3 rounded-lg border border-border hover:border-primary/30 transition-colors">
                      <div className={`w-8 h-8 rounded-full ${s.color} flex items-center justify-center text-[10px] font-bold text-white`}>{s.initials}</div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-foreground">{s.name}</p>
                        <p className="text-[10px] text-muted-foreground">{s.title}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-[10px] text-muted-foreground">{s.role}</p>
                        <p className="text-xs font-bold text-foreground">{s.score}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* Ontology Match */}
              <section className="bg-card border border-border rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-emerald-500" />
                    <h2 className="text-sm font-semibold text-foreground">Ontology Match</h2>
                  </div>
                  <span className="text-[10px] text-muted-foreground">Manufacturing v3.2 · Automotive extension</span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] text-muted-foreground">Match Score</span>
                      <span className="text-sm font-bold text-foreground">73%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden"><div className="h-full bg-emerald-500 rounded-full" style={{ width: "73%" }} /></div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-[10px] text-muted-foreground">48 drivers</p>
                    <p className="text-[10px] text-muted-foreground">32 formulas</p>
                  </div>
                </div>
              </section>

            </div>
          </div>
        </main>

        {/* Right Panel */}
        <aside className="border-l border-border bg-card flex flex-col shrink-0 relative z-20 transition-all duration-300" style={{ width: drillDownSignal ? 680 : agentExpanded ? 360 : 40 }}>
          {drillDownSignal ? (
            <DrillDownPanel signal={drillDownSignal} onClose={() => setDrillDownSignal(null)} />
          ) : (
            <>
              <div className="h-10 border-b border-border flex items-center justify-between px-3 shrink-0">
                {agentExpanded ? (
                  <>
                    <div className="flex items-center gap-2"><Bot className="w-4 h-4 text-primary" /><span className="text-xs font-semibold text-foreground">Agent Stream</span></div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => setActiveTab("chat")} className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${activeTab === "chat" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"}`}>Chat</button>
                      <button onClick={() => setActiveTab("options")} className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${activeTab === "options" ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground"}`}>Options</button>
                      <button onClick={() => setAgentExpanded(false)} className="w-6 h-6 rounded hover:bg-muted flex items-center justify-center ml-1"><X className="w-3 h-3 text-muted-foreground" /></button>
                    </div>
                  </>
                ) : (
                  <button onClick={() => setAgentExpanded(true)} className="w-full h-full flex items-center justify-center hover:bg-muted transition-colors"><Bot className="w-4 h-4 text-primary" /></button>
                )}
              </div>
              {agentExpanded && (
                <>
                  <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
                    {agentMessages.map((msg) => (
                      <div key={msg.id} className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <div className={`w-5 h-5 rounded-full ${msg.avatarColor} flex items-center justify-center text-[8px] font-bold text-primary-foreground`}>{msg.avatar}</div>
                          <span className="text-[10px] font-medium text-foreground">{msg.agent}</span>
                          <span className="text-[9px] text-muted-foreground ml-auto">{msg.timestamp}</span>
                        </div>
                        {msg.message && <div className={`ml-7 text-xs leading-relaxed ${msg.type === "prompt" ? "text-primary font-medium" : "text-foreground"}`}>{msg.message}</div>}
                        {msg.type === "process" && msg.process && <div className="ml-7 bg-muted/60 rounded-lg p-3 border border-border/60">{msg.process.steps.map((step, i) => <ProcessStep key={i} label={step.label} status={step.status} />)}</div>}
                        {msg.type === "summary" && (
                          <div className="ml-7 flex items-center gap-2 mt-1 flex-wrap">
                            <div className="flex items-center gap-1.5 px-2 py-1 bg-emerald-50 border border-emerald-200 rounded-full"><TrendingUp className="w-3 h-3 text-emerald-600" /><span className="text-[10px] font-medium text-emerald-700">73% match</span></div>
                            <div className="flex items-center gap-1.5 px-2 py-1 bg-amber-50 border border-amber-200 rounded-full"><Flame className="w-3 h-3 text-amber-600" /><span className="text-[10px] font-medium text-amber-700">6 signals</span></div>
                          </div>
                        )}
                      </div>
                    ))}
                    <div className="ml-7 space-y-1.5 pt-1">
                      <button className="w-full flex items-center gap-2 px-3 py-2 bg-primary/5 border border-primary/20 rounded-lg text-xs text-primary hover:bg-primary/10 transition-colors text-left"><Sparkles className="w-3.5 h-3.5" /> Generate value driver tree</button>
                      <button className="w-full flex items-center gap-2 px-3 py-2 bg-muted border border-border rounded-lg text-xs text-foreground hover:bg-muted/80 transition-colors text-left"><Flame className="w-3.5 h-3.5 text-rose-500" /> Explore pain signals</button>
                    </div>
                  </div>
                  <div className="border-t border-border p-3 shrink-0">
                    <div className="relative">
                      <input value={chatInput} onChange={(e) => setChatInput(e.target.value)} placeholder="Build with AI..." className="w-full pl-3 pr-9 py-2 bg-muted rounded-lg border border-input text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" />
                      <button className="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5 rounded bg-primary flex items-center justify-center hover:bg-primary/90 transition-colors"><Send className="w-2.5 h-2.5 text-primary-foreground" /></button>
                    </div>
                    <p className="text-[9px] text-muted-foreground mt-1.5 text-center">AI can make mistakes. Verify critical data.</p>
                  </div>
                </>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
