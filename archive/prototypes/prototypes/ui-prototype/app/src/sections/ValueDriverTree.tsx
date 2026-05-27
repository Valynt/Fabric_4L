import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus, ChevronDown, ChevronRight, Trash2, GripVertical,
  CheckCircle2, Sparkles, ArrowRight
} from "lucide-react";
import { SectionCard } from "@/components/blocks";

interface TreeNode {
  id: string; label: string; value: string; formula: string;
  children: TreeNode[]; expanded: boolean; type: "goal" | "driver" | "lever";
  source: string; aiGenerated: boolean;
}

const initialTree: TreeNode = {
  id: "root", label: "Total Annual Value Impact", value: "$14.87M", formula: "SUM(drivers)",
  type: "goal", expanded: true, source: "AI Model", aiGenerated: true,
  children: [
    {
      id: "d1", label: "Labor Cost Reduction", value: "$6.20M", formula: "Avoided_hires + Overtime_elim + Turnover_cost",
      type: "driver", expanded: true, source: "Hypothesis h1", aiGenerated: true,
      children: [
        { id: "l1", label: "Avoided New Hires (85 positions)", value: "$4.25M", formula: "85 x $50K loaded cost", type: "lever", expanded: false, source: "h1", aiGenerated: true, children: [] },
        { id: "l2", label: "Overtime Elimination", value: "$1.45M", formula: "120K hrs x $12.10/hr overtime", type: "lever", expanded: false, source: "h1", aiGenerated: true, children: [] },
        { id: "l3", label: "Reduced Turnover Cost", value: "$500K", formula: "25 fewer exits x $20K replacement", type: "lever", expanded: false, source: "h1", aiGenerated: true, children: [] },
      ],
    },
    {
      id: "d2", label: "Quality Improvement", value: "$3.80M", formula: "Scrap_avoided + Warranty + Recall_prevention",
      type: "driver", expanded: true, source: "Hypothesis h2", aiGenerated: true,
      children: [
        { id: "l4", label: "Scrap & Rework Reduction", value: "$1.60M", formula: "72% defect drop x $2.2M scrap/yr", type: "lever", expanded: false, source: "h2", aiGenerated: true, children: [] },
        { id: "l5", label: "Warranty Exposure Avoided", value: "$1.50M", formula: "Estimated warranty claims prevented", type: "lever", expanded: false, source: "h2", aiGenerated: true, children: [] },
        { id: "l6", label: "Recall Prevention", value: "$700K", formula: "Risk-weighted cost of single recall", type: "lever", expanded: false, source: "h2", aiGenerated: true, children: [] },
      ],
    },
    {
      id: "d3", label: "Throughput Gain", value: "$2.90M", formula: "Cycle_time_value + Uptime_gain",
      type: "driver", expanded: true, source: "Hypothesis h3", aiGenerated: true,
      children: [
        { id: "l7", label: "Cycle Time Reduction (23%)", value: "$2.10M", formula: "Additional units x margin", type: "lever", expanded: false, source: "h3", aiGenerated: true, children: [] },
        { id: "l8", label: "Uptime Improvement (91% to 96%)", value: "$800K", formula: "5% uptime x annual line output", type: "lever", expanded: false, source: "h3", aiGenerated: true, children: [] },
      ],
    },
    {
      id: "d4", label: "Safety / Ergonomics", value: "$1.40M", formula: "WC_savings + Medical + Lost_time",
      type: "driver", expanded: true, source: "Hypothesis h4", aiGenerated: true,
      children: [
        { id: "l9", label: "Workers Comp Reduction", value: "$850K", formula: "65% fewer recordables x avg claim", type: "lever", expanded: false, source: "h4", aiGenerated: true, children: [] },
        { id: "l10", label: "Lost Productivity Avoided", value: "$550K", formula: "1,200 fewer lost days x $457/day", type: "lever", expanded: false, source: "h4", aiGenerated: true, children: [] },
      ],
    },
    {
      id: "d5", label: "Mixed-Model Flexibility", value: "$580K", formula: "Changeover_labor + WIP_reduction",
      type: "driver", expanded: true, source: "Hypothesis h5", aiGenerated: true,
      children: [
        { id: "l11", label: "Changeover Time (45 to 8 min)", value: "$380K", formula: "37 min saved x 4/day x labor rate", type: "lever", expanded: false, source: "h5", aiGenerated: true, children: [] },
        { id: "l12", label: "WIP Inventory Reduction", value: "$200K", formula: "Smaller changeover buffers", type: "lever", expanded: false, source: "h5", aiGenerated: true, children: [] },
      ],
    },
  ],
};

function NodeRow({ node, depth, onToggle }: { node: TreeNode; depth: number; onToggle: (id: string) => void }) {
  const hasChildren = node.children.length > 0;
  const indent = depth * 20;
  const typeColors = {
    goal: "bg-primary text-primary-foreground",
    driver: "bg-primary/40 text-primary-foreground",
    lever: "bg-muted text-muted-foreground"
  };

  return (
    <div>
      <div className={`flex items-center gap-2 py-2 px-3 rounded-lg hover:bg-muted/50 transition-colors group ${depth === 0 ? "bg-primary/5 border border-primary/20" : ""}`} style={{ marginLeft: indent }}>
        <GripVertical className="w-4 h-4 text-muted-foreground/30 shrink-0 cursor-grab opacity-0 group-hover:opacity-100" />
        {hasChildren ? <button onClick={() => onToggle(node.id)} className="shrink-0">{node.expanded ? <ChevronDown className="w-4 h-4 text-muted-foreground/60" /> : <ChevronRight className="w-4 h-4 text-muted-foreground/60" />}</button> : <div className="w-4 shrink-0" />}
        <div className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold shrink-0 ${typeColors[node.type]}`}>{node.type === "goal" ? "G" : node.type === "driver" ? "D" : "L"}</div>
        <span className="text-sm font-medium text-foreground flex-1 min-w-0 truncate">{node.label}</span>
        {node.aiGenerated && <Sparkles className="w-3 h-3 text-primary shrink-0" />}
        <span className="text-xs font-mono text-primary font-semibold w-20 text-right shrink-0">{node.value}</span>
        <span className="text-[10px] text-muted-foreground/60 hidden lg:block w-36 truncate shrink-0">{node.source}</span>
        <Trash2 className="w-3.5 h-3.5 text-muted-foreground/30 hover:text-destructive shrink-0 opacity-0 group-hover:opacity-100 cursor-pointer" />
      </div>
      {hasChildren && node.expanded && (
        <div className="border-l-2 border-dashed border-border ml-5">
          {node.children.map((c) => <NodeRow key={c.id} node={c} depth={depth + 1} onToggle={onToggle} />)}
          <button className="flex items-center gap-1.5 py-1.5 px-3 ml-4 text-xs text-primary"><Plus className="w-3 h-3" /> Add Lever</button>
        </div>
      )}
    </div>
  );
}

export default function ValueDriverTree() {
  const navigate = useNavigate();
  const [tree, setTree] = useState<TreeNode>(initialTree);
  const [rightPanel, setRightPanel] = useState<"formula" | "validation">("formula");

  const toggle = (id: string) => {
    const f = (n: TreeNode): TreeNode => n.id === id ? { ...n, expanded: !n.expanded } : { ...n, children: n.children.map(f) };
    setTree(f(tree));
  };

  return (
    <main className="max-w-7xl mx-auto space-y-4" aria-label="Value Driver Tree">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">Value Driver Tree</h1>
          <p className="text-sm text-muted-foreground mt-0.5">AI-generated from approved hypotheses. Review formulas, edit, or approve.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 rounded-lg border border-primary/20">
            <Sparkles className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs text-primary font-medium">12 of 12 nodes AI-generated</span>
          </div>
          <button onClick={() => navigate("/evidence")} className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:bg-primary/90 shadow-lg shadow-primary/25">
            <ArrowRight className="w-4 h-4" /> Match Evidence
          </button>
        </div>
      </header>

      <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
        <p className="text-sm font-medium text-emerald-500">Tree validated — 5 drivers, 12 platform-controllable levers mapped</p>
      </div>

      <div className="flex gap-4">
        <SectionCard title="Value Driver Tree — 5 Drivers, 12 Levers" className="flex-1"
          action={<div className="flex items-center gap-2 text-xs text-muted-foreground"><span className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-primary" /> Goal</span><span className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-primary/40" /> Driver</span><span className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-muted" /> Lever</span></div>}
        >
          <div className="p-4">
            <NodeRow node={tree} depth={0} onToggle={toggle} />
            <button className="flex items-center gap-2 py-2.5 px-3 mt-2 text-sm text-primary font-medium hover:bg-primary/5 rounded-lg w-full"><Plus className="w-4 h-4" /> Add Driver</button>
          </div>
        </SectionCard>

        <aside className="w-80 shrink-0 space-y-4">
          <div className="flex bg-muted rounded-lg p-0.5">
            {(["formula", "validation"] as const).map((tab) => (
              <button key={tab} onClick={() => setRightPanel(tab)} className={`flex-1 py-1.5 text-xs font-medium rounded-md ${rightPanel === tab ? "bg-card text-foreground shadow-sm" : "text-muted-foreground"}`}>{tab === "formula" ? "Formula" : "Validate"}</button>
            ))}
          </div>

          {rightPanel === "formula" && (
            <SectionCard title="Formula Inspector">
              <div className="p-4 space-y-3">
                <div className="p-3 bg-muted rounded-lg border border-border">
                  <p className="text-[10px] text-muted-foreground uppercase mb-1">Selected</p>
                  <p className="text-sm font-semibold text-foreground">Avoided New Hires (85 positions)</p>
                  <p className="text-xs text-muted-foreground mt-1">AI-generated from h1 — Forge X1 Cobot Workcell</p>
                </div>
                <div className="p-3 bg-primary/5 rounded-lg border border-primary/20">
                  <p className="text-[10px] text-primary uppercase mb-1">Formula</p>
                  <p className="text-sm font-mono text-foreground">Positions x Loaded_Annual_Cost</p>
                  <p className="text-[10px] text-muted-foreground mt-1">= 85 x $50,000 = $4.25M</p>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {["85 positions", "$50K/yr", "$4.25M"].map((v) => (
                    <div key={v} className="p-2 bg-card rounded border border-border text-center">
                      <p className="text-xs font-mono font-semibold text-foreground">{v.split(" ")[0]}</p>
                      <p className="text-[10px] text-muted-foreground">{v.split(" ").slice(1).join(" ")}</p>
                    </div>
                  ))}
                </div>
              </div>
            </SectionCard>
          )}

          {rightPanel === "validation" && (
            <SectionCard title="Driver Validation">
              <div className="p-4 space-y-3">
                {[
                  { label: "Platform-controllable", desc: "All 12 levers map to Forge X1 modules" },
                  { label: "Formula completeness", desc: "All drivers have quantified formulas" },
                  { label: "Evidence coverage", desc: "11/12 levers have evidence anchors" },
                  { label: "Math consistency", desc: "Roll-ups match leaf sums ($14.87M)" },
                ].map((c) => (
                  <div key={c.label} className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                    <div><p className="text-sm font-medium text-foreground">{c.label}</p><p className="text-xs text-muted-foreground">{c.desc}</p></div>
                  </div>
                ))}
              </div>
            </SectionCard>
          )}

          <SectionCard title="Value Distribution">
            <div className="p-4 space-y-2">
              {[
                { label: "Labor Reduction", value: 0.42, color: "bg-primary" },
                { label: "Quality", value: 0.26, color: "bg-primary/70" },
                { label: "Throughput", value: 0.20, color: "bg-primary/50" },
                { label: "Safety", value: 0.09, color: "bg-primary/30" },
                { label: "Flexibility", value: 0.04, color: "bg-muted" },
              ].map((w) => (
                <div key={w.label}>
                  <div className="flex justify-between mb-1"><span className="text-xs text-muted-foreground">{w.label}</span><span className="text-xs font-semibold">{(w.value * 100).toFixed(0)}%</span></div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden"><div className={`h-full ${w.color} rounded-full`} style={{ width: `${w.value * 100}%` }} /></div>
                </div>
              ))}
            </div>
          </SectionCard>
        </aside>
      </div>
    </main>
  );
}
