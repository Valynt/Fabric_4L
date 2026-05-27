import { useState } from "react";
import { Save, RotateCcw, CheckCircle2, AlertTriangle } from "lucide-react";
import { SectionCard, ProgressBar } from "@/components/blocks";

const levers = [
  { id: "l1", name: "Avoided Hires (positions)", base: 85, min: 60, max: 120, valA: 75, valB: 85, unit: "heads", annual: 4250000, conf: 94 },
  { id: "l2", name: "Defect Reduction (%)", base: 72, min: 50, max: 85, valA: 65, valB: 72, unit: "%", annual: 3800000, conf: 91 },
  { id: "l3", name: "Cycle Time Improvement (%)", base: 23, min: 15, max: 30, valA: 18, valB: 23, unit: "%", annual: 2100000, conf: 87 },
  { id: "l4", name: "Uptime Improvement (%)", base: 5, min: 3, max: 8, valA: 4, valB: 5, unit: "pts", annual: 800000, conf: 82 },
  { id: "l5", name: "Injury Reduction (%)", base: 65, min: 40, max: 80, valA: 55, valB: 65, unit: "%", annual: 1400000, conf: 78 },
  { id: "l6", name: "Changeover Time Saved (min)", base: 37, min: 20, max: 45, valA: 30, valB: 37, unit: "min", annual: 580000, conf: 72 },
];

export default function ValueCalculator() {
  const [values, setValues] = useState<Record<string, { a: number; b: number }>>(
    Object.fromEntries(levers.map((l) => [l.id, { a: l.valA, b: l.valB }]))
  );
  const [scenario, setScenario] = useState<"A" | "B" | "C">("B");

  const update = (id: string, field: "a" | "b", val: number) => {
    setValues((p) => ({ ...p, [id]: { ...p[id], [field]: val } }));
  };

  const totalA = levers.reduce((s, l) => s + l.annual * (values[l.id].a / l.base), 0);
  const totalB = levers.reduce((s, l) => s + l.annual * (values[l.id].b / l.base), 0);
  const totalC = levers.reduce((s, l) => s + l.annual * 1.25, 0);
  const totals = { A: totalA, B: totalB, C: totalC };
  const current = totals[scenario];

  return (
    <main className="max-w-7xl mx-auto space-y-4" aria-label="Value Calculator">
      <header className="flex items-center justify-between">
        <div><h1 className="text-xl font-bold text-foreground">Value Calculator</h1><p className="text-sm text-muted-foreground mt-0.5">Prospect-specific scenario modeling. AI pre-filled from Meridian profile.</p></div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-lg text-sm text-muted-foreground hover:bg-muted"><RotateCcw className="w-4 h-4" /> Reset</button>
          <button className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-lg text-sm text-muted-foreground hover:bg-muted"><Save className="w-4 h-4" /> Save</button>
        </div>
      </header>

      {/* Scenario Cards */}
      <section className="flex gap-3">
        {(["A", "B", "C"] as const).map((s) => (
          <button key={s} onClick={() => setScenario(s)} className={`flex-1 px-5 py-4 rounded-xl border text-left transition-all ${scenario === s ? "border-primary bg-primary/5 shadow-sm" : "border-border bg-card hover:border-border/80"}`}>
            <span className={`text-sm font-semibold ${scenario === s ? "text-primary" : "text-foreground"}`}>{s === "A" ? "Conservative" : s === "B" ? "Expected" : "Optimistic"}</span>
            {s === "B" && <span className="text-[10px] px-1.5 py-0.5 bg-primary text-primary-foreground rounded-full ml-2">Base</span>}
            <p className="text-2xl font-bold text-card-foreground mt-1">${(totals[s] / 1_000_000).toFixed(2)}M</p>
            <p className="text-xs text-muted-foreground">Annual value</p>
          </button>
        ))}
      </section>

      <div className="flex gap-4">
        <SectionCard title="Value Levers — AI Pre-filled" description="Drag to adjust" className="flex-1"
          action={<span className="text-xs text-muted-foreground/60">Confidence indicators</span>}
        >
          <div className="divide-y divide-border/40">
            {levers.map((l) => {
              const val = scenario === "A" ? values[l.id].a : scenario === "B" ? values[l.id].b : l.base * 1.2;
              const leverTotal = l.annual * (val / l.base);
              return (
                <div key={l.id} className="px-5 py-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {l.conf >= 80 ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> : <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />}
                      <span className="text-sm font-medium text-foreground">{l.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-muted-foreground/60">Base: {l.base}{l.unit}</span>
                      <span className="text-sm font-bold text-primary">{val.toFixed(0)}{l.unit}</span>
                      <span className="text-xs font-mono text-muted-foreground w-16 text-right">${(leverTotal / 1_000_000).toFixed(2)}M</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] text-muted-foreground/60 w-8 text-right">{l.min}</span>
                    <input type="range" min={l.min} max={l.max} value={val} onChange={(e) => update(l.id, scenario === "A" ? "a" : "b", parseInt(e.target.value))} className="flex-1 accent-primary" />
                    <span className="text-[10px] text-muted-foreground/60 w-8">{l.max}</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground/60 ml-5 mt-1">Confidence: {l.conf}%</p>
                </div>
              );
            })}
          </div>
        </SectionCard>

        <aside className="w-72 shrink-0 space-y-4">
          <div className="bg-card rounded-xl border border-border p-4 text-center">
            <p className="text-3xl font-bold text-primary">${(current / 1_000_000).toFixed(2)}M</p>
            <p className="text-xs text-muted-foreground">Total Annual Value</p>
            <div className="space-y-1 text-xs mt-3 pt-3 border-t border-border/60">
              <div className="flex justify-between"><span className="text-muted-foreground">vs. Conservative</span><span className="font-medium text-emerald-500">+${((current - totalA) / 1_000_000).toFixed(2)}M</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">vs. Optimistic</span><span className="font-medium text-muted-foreground">-${((totalC - current) / 1_000_000).toFixed(2)}M gap</span></div>
            </div>
          </div>

          <SectionCard title="By Lever">
            <div className="p-4 space-y-3">
              {levers.map((l) => {
                const val = scenario === "A" ? values[l.id].a : scenario === "B" ? values[l.id].b : l.base * 1.2;
                const pct = (l.annual * (val / l.base) / current) * 100;
                return (
                  <div key={l.id}>
                    <div className="flex justify-between mb-1"><span className="text-xs text-muted-foreground">{l.name.split(" (")[0]}</span><span className="text-xs font-semibold">{pct.toFixed(0)}%</span></div>
                    <ProgressBar value={pct} max={100} size="sm" />
                  </div>
                );
              })}
            </div>
          </SectionCard>

          <div className="bg-card rounded-xl border border-border p-4">
            <h4 className="text-sm font-semibold text-foreground mb-2">Confidence Range</h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span className="text-muted-foreground">Low</span><span className="font-mono font-semibold text-foreground">${(totalA / 1_000_000).toFixed(2)}M</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Expected</span><span className="font-mono font-semibold text-primary">${(totalB / 1_000_000).toFixed(2)}M</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">High</span><span className="font-mono font-semibold text-foreground">${(totalC / 1_000_000).toFixed(2)}M</span></div>
            </div>
            <div className="mt-2 h-2 rounded-full overflow-hidden flex"><div className="flex-1 bg-amber-500/30" /><div className="flex-1 bg-primary" /><div className="flex-1 bg-emerald-500/30" /></div>
          </div>
        </aside>
      </div>
    </main>
  );
}
