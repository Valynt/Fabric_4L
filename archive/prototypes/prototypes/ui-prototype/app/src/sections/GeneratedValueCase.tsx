import {
  FileText, Download, Share2, Trophy, TrendingUp, Shield, CheckCircle2,
  AlertTriangle, BarChart3, ArrowRight, Zap, Clock, Printer, BrainCircuit
} from "lucide-react";
import { StatCard, SectionCard, ProgressBar } from "@/components/blocks";

const results = [
  { rank: 1, area: "Labor Cost Reduction", value: "$6.20M", pct: 42, breakdown: [{ label: "Avoided New Hires", amount: "$4.25M", evidence: "NAM Skills Gap Report", conf: 94 }, { label: "Overtime Elimination", amount: "$1.45M", evidence: "BMW Cobot Case Study", conf: 88 }, { label: "Reduced Turnover", amount: "$500K", evidence: "Internal HR Data", conf: 82 }] },
  { rank: 2, area: "Quality Improvement", value: "$3.80M", pct: 26, breakdown: [{ label: "Scrap & Rework", amount: "$1.60M", evidence: "Fraunhofer IPA Study", conf: 92 }, { label: "Warranty Avoided", amount: "$1.50M", evidence: "JD Power Warranty", conf: 80 }, { label: "Recall Prevention", amount: "$700K", evidence: "Industry Analysis", conf: 75 }] },
  { rank: 3, area: "Throughput Gain", value: "$2.90M", pct: 20, breakdown: [{ label: "Cycle Time (23%)", amount: "$2.10M", evidence: "BMW Dingolfing Report", conf: 95 }, { label: "Uptime (91% to 96%)", amount: "$800K", evidence: "Predictive Maint. Data", conf: 82 }] },
  { rank: 4, area: "Safety / Ergonomics", value: "$1.40M", pct: 9, breakdown: [{ label: "Workers Comp", amount: "$850K", evidence: "MIT Manufacturing Review", conf: 90 }, { label: "Lost Productivity", amount: "$550K", evidence: "OSHA 300A Analysis", conf: 78 }] },
  { rank: 5, area: "Mixed-Model Flexibility", value: "$580K", pct: 4, breakdown: [{ label: "Changeover Time", amount: "$380K", evidence: "Axiom Pilot — Magna", conf: 86 }, { label: "WIP Reduction", amount: "$200K", evidence: "Production Engineering", conf: 70 }] },
];

export default function GeneratedValueCase() {
  return (
    <main className="max-w-7xl mx-auto space-y-4" aria-label="Generated Value Case">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center"><FileText className="w-5 h-5 text-primary" /></div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Generated Value Case</h1>
            <p className="text-sm text-muted-foreground">Auto-generated for Meridian Automotive — personalized with prospect data and evidence anchors.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-lg text-sm text-muted-foreground hover:bg-muted"><Printer className="w-4 h-4" /> Print</button>
          <button className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-lg text-sm text-muted-foreground hover:bg-muted"><Download className="w-4 h-4" /> PDF</button>
          <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:bg-primary/90 shadow-lg shadow-primary/25"><Share2 className="w-4 h-4" /> Share</button>
        </div>
      </header>

      {/* KPI Stats */}
      <section className="grid grid-cols-4 gap-3">
        <StatCard label="3-Year Value" value="$44.6M" sub="$33.2M–$55.8M range" icon={Trophy} iconClassName="text-primary" iconBgClassName="bg-primary/10" />
        <StatCard label="ROI" value="285%" sub="$44.6M vs. $15.7M invest" icon={TrendingUp} iconClassName="text-emerald-500" iconBgClassName="bg-emerald-500/10" />
        <StatCard label="Payback" value="12 months" sub="Expected scenario" icon={Clock} iconClassName="text-purple-400" iconBgClassName="bg-purple-400/10" />
        <StatCard label="Confidence" value="82%" sub="Weighted by evidence tiers" icon={Shield} iconClassName="text-amber-500" iconBgClassName="bg-amber-500/10" />
      </section>

      {/* Hero Insight */}
      <section className="bg-primary/5 border border-primary/20 rounded-xl p-6 flex items-center gap-5">
        <div className="w-14 h-14 rounded-xl bg-primary flex items-center justify-center shrink-0"><Trophy className="w-7 h-7 text-primary-foreground" /></div>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <h2 className="text-lg font-bold text-foreground">Labor Cost Reduction is the #1 Value Driver</h2>
            <span className="text-xs px-2.5 py-1 bg-emerald-500/10 text-emerald-500 rounded-full font-semibold">$6.20M / 42% of total</span>
          </div>
          <p className="text-sm text-muted-foreground">Meridian's 340 unfilled assembly positions and 18% production turnover make labor augmentation the highest-value, highest-confidence lever.</p>
        </div>
      </section>

      <div className="flex gap-4">
        <div className="flex-1 space-y-4">
          {/* Ranked Results */}
          {results.map((r) => (
            <SectionCard key={r.area}>
              <div className="p-5">
                <div className="flex items-center gap-3 mb-3">
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${r.rank === 1 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{r.rank}</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h2 className="font-semibold text-foreground">{r.area}</h2>
                      <span className="text-xl font-bold text-primary">{r.value}</span>
                    </div>
                    <ProgressBar value={r.pct} max={100} size="sm" className="mt-1" />
                  </div>
                </div>
                <div className="ml-11 space-y-2">
                  {r.breakdown.map((b) => (
                    <div key={b.label} className="flex items-center justify-between py-2 px-3 bg-muted rounded-lg">
                      <div className="flex items-center gap-2"><Zap className="w-3 h-3 text-amber-500" /><span className="text-xs text-foreground">{b.label}</span></div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono text-muted-foreground">{b.amount}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${b.conf >= 80 ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500"}`}>{b.conf}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </SectionCard>
          ))}

          {/* 3-Year Projection */}
          <SectionCard title="3-Year Value Projection" icon={<BarChart3 className="w-4 h-4" />}>
            <div className="p-5">
              <div className="flex items-end gap-6 h-36 px-4">
                {[
                  { year: "Year 1", c: 9.8, e: 14.9, o: 19.2 },
                  { year: "Year 2", c: 12.1, e: 16.8, o: 20.5 },
                  { year: "Year 3", c: 13.5, e: 18.2, o: 21.8 },
                ].map((y) => (
                  <div key={y.year} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-xs font-semibold text-primary">${y.e}M</span>
                    <div className="flex items-end gap-1" style={{ height: 100 }}>
                      <div className="w-5 bg-amber-500/30 rounded-t" style={{ height: `${(y.c / 25) * 100}px` }} />
                      <div className="w-5 bg-primary rounded-t" style={{ height: `${(y.e / 25) * 100}px` }} />
                      <div className="w-5 bg-emerald-500/30 rounded-t" style={{ height: `${(y.o / 25) * 100}px` }} />
                    </div>
                    <span className="text-xs text-muted-foreground">{y.year}</span>
                  </div>
                ))}
              </div>
              <div className="flex justify-center gap-4 mt-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><div className="w-3 h-3 bg-amber-500/30 rounded" /> Conservative</span>
                <span className="flex items-center gap-1"><div className="w-3 h-3 bg-primary rounded" /> Expected</span>
                <span className="flex items-center gap-1"><div className="w-3 h-3 bg-emerald-500/30 rounded" /> Optimistic</span>
              </div>
            </div>
          </SectionCard>
        </div>

        <aside className="w-72 shrink-0 space-y-4">
          <SectionCard title="Model Quality">
            <div className="p-4">
              <div className="flex justify-center mb-3">
                <div className="relative w-20 h-20">
                  <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
                    <circle cx="40" cy="40" r="34" fill="none" stroke="oklch(var(--muted))" strokeWidth="8" />
                    <circle cx="40" cy="40" r="34" fill="none" stroke="oklch(var(--primary))" strokeWidth="8" strokeDasharray="175 213" strokeLinecap="round" />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center"><span className="text-xl font-bold text-foreground">82</span></div>
                </div>
              </div>
              {[
                { label: "Evidence depth", score: 90 },
                { label: "Formula rigor", score: 88 },
                { label: "Customer relevance", score: 78 },
                { label: "Confidence coverage", score: 72 },
              ].map((s) => (
                <div key={s.label} className="flex items-center gap-2 mb-1.5">
                  <span className="text-[10px] text-muted-foreground flex-1">{s.label}</span>
                  <ProgressBar value={s.score} max={100} size="sm" className="w-12" />
                  <span className="text-[10px] text-muted-foreground w-5 text-right">{s.score}</span>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="AI-Generated Insights">
            <div className="p-4 space-y-2.5">
              {[
                { icon: CheckCircle2, text: "Labor wins across all 3 scenarios (robust)", color: "text-emerald-500" },
                { icon: AlertTriangle, text: "Quality value sensitive to defect % assumption", color: "text-amber-500" },
                { icon: Zap, text: "Flexibility is smallest but fastest to prove (pilot)", color: "text-primary" },
              ].map((insight, i) => (
                <div key={i} className="flex items-start gap-2"><insight.icon className={`w-4 h-4 shrink-0 mt-0.5 ${insight.color}`} /><p className="text-xs text-muted-foreground">{insight.text}</p></div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Recommended Next Steps">
            <div className="p-4 space-y-2">
              {[
                { label: "Schedule Meridian plant tour", priority: "high" },
                { label: "Validate $50K loaded cost assumption", priority: "high" },
                { label: "Magna Steyr reference call", priority: "med" },
                { label: "CFO-focused ROI brief", priority: "med" },
              ].map((a) => (
                <div key={a.label} className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${a.priority === "high" ? "bg-destructive" : "bg-amber-500"}`} />
                  <span className="text-xs text-foreground flex-1">{a.label}</span>
                </div>
              ))}
            </div>
          </SectionCard>

          <div className="bg-primary/5 rounded-xl border border-primary/20 p-4">
            <div className="flex items-center gap-2 mb-2"><BrainCircuit className="w-4 h-4 text-primary" /><h4 className="text-sm font-semibold text-primary">Ready for Decision</h4></div>
            <p className="text-xs text-primary/80 mb-3">This value case is ready for decision evaluation. Open in Decision Studio to compare options.</p>
            <button className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-primary text-primary-foreground rounded-lg text-xs font-medium hover:bg-primary/90">
              <ArrowRight className="w-3.5 h-3.5" /> Open in Decision Studio
            </button>
          </div>
        </aside>
      </div>
    </main>
  );
}
