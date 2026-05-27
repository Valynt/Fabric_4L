import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Database, Search, CheckCircle2, AlertTriangle,
  Sparkles, ArrowRight, Zap, FileText
} from "lucide-react";
import { StatCard, SectionCard, StatusBadge } from "@/components/blocks";

const evidenceItems = [
  { id: "e1", statement: "BMW Group reported 34% cycle time reduction after deploying cobot workcells at Dingolfing plant.", source: "BMW Annual Report 2025", type: "Case Study", tier: "proof" as const, confidence: 95, lever: "Throughput Gain", aiMapped: true },
  { id: "e2", statement: "AI torque control reduced fastening defects by 68% at a Tier 1 seating supplier over 18-month deployment.", source: "Fraunhofer IPA Study 2025", type: "Research", tier: "proof" as const, confidence: 92, lever: "Quality Improvement", aiMapped: true },
  { id: "e3", statement: "Universal Robots: customers see average 12-month payback on cobot assembly deployments in automotive.", source: "Universal Robots ROI Report 2025", type: "Industry Report", tier: "proof" as const, confidence: 88, lever: "Labor Cost Reduction", aiMapped: true },
  { id: "e4", statement: "Cobot-equipped plants saw 41% reduction in ergonomic injuries in MIT manufacturing study (2024).", source: "MIT Sloan Manufacturing Review", type: "Academic", tier: "proof" as const, confidence: 90, lever: "Safety / Ergonomics", aiMapped: true },
  { id: "e5", statement: "Axiom Forge X1 achieved 8-minute changeover in pilot at Magna Steyr Graz (EV-to-ICE components).", source: "Axiom Pilot — Magna Steyr", type: "Pilot Data", tier: "proof" as const, confidence: 86, lever: "Mixed-Model Flexibility", aiMapped: true },
  { id: "e6", statement: "$47K average annual cost per unfilled manufacturing position including overtime and temp labor.", source: "NAM Skills Gap Report 2025", type: "Research", tier: "supporting" as const, confidence: 82, lever: "Labor Cost Reduction", aiMapped: true },
  { id: "e7", statement: "Automotive torque-related recalls cost $2.1M on average per incident in warranty + reputation damage.", source: "JD Power Warranty Study 2025", type: "Research", tier: "supporting" as const, confidence: 80, lever: "Quality Improvement", aiMapped: false },
  { id: "e8", statement: "IFR World Robotics 2025: cobot installations in automotive up 47% YoY, fastest-growing segment.", source: "IFR World Robotics 2025", type: "Industry Data", tier: "supporting" as const, confidence: 78, lever: "Labor Cost Reduction", aiMapped: true },
];

export default function EvidenceMatch() {
  const navigate = useNavigate();
  const [selectedId, setSelectedId] = useState<string | null>("e1");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  const filtered = evidenceItems.filter((e) => {
    if (filter !== "all" && !e.aiMapped) return false;
    if (search && !e.statement.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const selected = evidenceItems.find((e) => e.id === selectedId);
  const aiMappedCount = evidenceItems.filter((e) => e.aiMapped).length;

  return (
    <main className="max-w-7xl mx-auto space-y-4" aria-label="Evidence Match">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center"><Database className="w-5 h-5 text-primary" /></div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Evidence Match</h1>
            <p className="text-sm text-muted-foreground">AI auto-mapped {aiMappedCount} evidence items to your driver tree levers.</p>
          </div>
        </div>
        <button onClick={() => navigate("/calculator")} className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:bg-primary/90 shadow-lg shadow-primary/25">
          <ArrowRight className="w-4 h-4" /> Value Calculator
        </button>
      </header>

      <section className="grid grid-cols-4 gap-3">
        <StatCard label="Total Evidence" value={evidenceItems.length} icon={Database} />
        <StatCard label="AI Mapped" value={aiMappedCount} sub={`${evidenceItems.length - aiMappedCount} unmapped`} icon={Sparkles} iconClassName="text-primary" iconBgClassName="bg-primary/10" />
        <StatCard label="Proof Points" value={evidenceItems.filter((e) => e.tier === "proof").length} icon={CheckCircle2} iconClassName="text-emerald-500" iconBgClassName="bg-emerald-500/10" />
        <StatCard label="Avg Confidence" value={`${Math.round(evidenceItems.reduce((s, e) => s + e.confidence, 0) / evidenceItems.length)}%`} icon={Zap} iconClassName="text-amber-500" iconBgClassName="bg-amber-500/10" />
      </section>

      <div className="flex items-center gap-3">
        <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-lg">
          <Search className="w-4 h-4 text-muted-foreground/60" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search evidence..." className="flex-1 text-sm bg-transparent focus:outline-none text-foreground placeholder:text-muted-foreground/60" />
        </div>
        <div className="flex bg-muted rounded-lg p-0.5">
          <button onClick={() => setFilter("all")} className={`px-3 py-1.5 text-xs font-medium rounded-md ${filter === "all" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"}`}>All</button>
          <button onClick={() => setFilter("mapped")} className={`px-3 py-1.5 text-xs font-medium rounded-md ${filter === "mapped" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"}`}>AI Mapped</button>
        </div>
      </div>

      <div className="flex gap-4">
        <SectionCard className="flex-1" contentClassName="max-h-[480px] overflow-y-auto divide-y divide-border/60">
          <div className="px-4 py-2.5 bg-muted border-b border-border flex items-center justify-between text-xs font-semibold text-muted-foreground">
            <span>Evidence Statement</span>
            <div className="flex items-center gap-6"><span className="w-16 text-center">Tier</span><span className="w-16 text-center">Mapped</span><span className="w-14 text-center">Conf</span></div>
          </div>
          {filtered.map((e) => (
            <button key={e.id} onClick={() => setSelectedId(e.id)} className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${selectedId === e.id ? "bg-primary/5 border-l-2 border-l-primary" : "hover:bg-muted/50"}`}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  {e.aiMapped && <Sparkles className="w-3 h-3 text-primary" />}
                  <p className="text-xs text-foreground line-clamp-2">{e.statement}</p>
                </div>
                <p className="text-[10px] text-muted-foreground/60">{e.source}</p>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium shrink-0 w-16 text-center ${e.tier === "proof" ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : "bg-primary/10 text-primary border-primary/20"}`}>{e.tier}</span>
              <span className="text-[10px] text-muted-foreground w-16 text-center truncate">{e.lever}</span>
              <span className="text-[10px] font-semibold text-foreground w-14 text-center shrink-0">{e.confidence}%</span>
            </button>
          ))}
        </SectionCard>

        <aside className="w-72 shrink-0 space-y-4">
          {selected ? (
            <>
              <SectionCard>
                <div className="p-4 space-y-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <StatusBadge status={selected.tier === "proof" ? "connected" : "active"} label={selected.tier} size="sm" />
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">{selected.type}</span>
                    {selected.aiMapped && <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium flex items-center gap-1"><Sparkles className="w-2.5 h-2.5" /> AI Mapped</span>}
                  </div>
                  <p className="text-sm text-foreground">{selected.statement}</p>
                  <p className="text-xs text-muted-foreground flex items-center gap-1"><FileText className="w-3.5 h-3.5" />{selected.source}</p>
                </div>
              </SectionCard>

              <SectionCard title="Confidence Score">
                <div className="p-4 flex justify-center">
                  <div className="relative w-20 h-20">
                    <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
                      <circle cx="40" cy="40" r="34" fill="none" stroke="oklch(var(--muted))" strokeWidth="8" />
                      <circle cx="40" cy="40" r="34" fill="none" stroke={selected.confidence >= 80 ? "oklch(0.696 0.17 145)" : "oklch(0.75 0.17 80)"} strokeWidth="8" strokeDasharray={`${selected.confidence * 2.14} 213`} strokeLinecap="round" />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center"><span className="text-lg font-bold text-foreground">{selected.confidence}</span></div>
                  </div>
                </div>
              </SectionCard>

              <SectionCard title="AI Mapping">
                <div className="p-4 space-y-2">
                  <div className="flex items-center gap-2"><Zap className="w-3.5 h-3.5 text-amber-500" /><span className="text-xs text-foreground">{selected.lever}</span></div>
                  <div className="mt-3 pt-3 border-t border-border/60 flex gap-2">
                    <button className="flex-1 py-1.5 bg-emerald-500/10 text-emerald-500 rounded-lg text-[10px] font-medium flex items-center justify-center gap-1"><CheckCircle2 className="w-3 h-3" /> Verify</button>
                    <button className="flex-1 py-1.5 bg-muted text-muted-foreground rounded-lg text-[10px] font-medium flex items-center justify-center gap-1"><AlertTriangle className="w-3 h-3" /> Re-score</button>
                  </div>
                </div>
              </SectionCard>
            </>
          ) : (
            <div className="bg-card rounded-xl border border-border p-6 text-center"><Database className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" /><p className="text-sm text-muted-foreground">Select evidence to inspect</p></div>
          )}
        </aside>
      </div>
    </main>
  );
}
