import { useState } from "react";
import {
  Home, BookOpen, Compass, Box, GitBranch, Truck, ShieldCheck,
  Settings, ChevronDown, ChevronRight, Plus, Search, Bell,
  MousePointer2, ZoomIn, ZoomOut, Maximize2,
  Undo2, Redo2
} from "lucide-react";

/* ─── Sidebar Icons ─── */
const mainNav = [
  { icon: Home, label: "Home", active: false },
  { icon: BookOpen, label: "Library", active: false },
  { icon: Compass, label: "Discover", active: false },
  { icon: Box, label: "Model", active: false, hasSub: true, expanded: true },
  { icon: GitBranch, label: "Value Studio", active: true, hasSub: true, expanded: true },
  { icon: Truck, label: "Deliver", active: false },
  { icon: ShieldCheck, label: "Evidence", active: false },
  { icon: Settings, label: "Govern", active: false, badge: "Admin" },
];

const modelSub = [
  { label: "Explorer", active: false },
  { label: "Normalization", active: false },
  { label: "Formula Builder", active: false },
];

const studioSub = [
  { label: "Explorer", active: true },
  { label: "Normalization", active: false },
  { label: "Formula Builder", active: false },
];

/* ─── Tree Data ─── */
interface TreeNode {
  id: string;
  label: string;
  level: number;
  children?: TreeNode[];
  x?: number;
  y?: number;
}

const treeData: TreeNode = {
  id: "root",
  label: "Revenue Impact",
  level: 0,
  children: [
    {
      id: "l2-1",
      label: "Cost Reduction",
      level: 1,
      children: [
        { id: "l3-1", label: "Labor Efficiency", level: 2 },
        { id: "l3-2", label: "Material Waste", level: 2 },
      ],
    },
    {
      id: "l2-2",
      label: "Throughput Gain",
      level: 1,
      children: [
        { id: "l3-3", label: "Cycle Time", level: 2 },
        { id: "l3-4", label: "OEE Uptime", level: 2 },
      ],
    },
    {
      id: "l2-3",
      label: "Quality Improvement",
      level: 1,
      children: [
        { id: "l3-5", label: "Defect Rate", level: 2 },
        { id: "l3-6", label: "Rework Cost", level: 2 },
      ],
    },
  ],
};

/* ─── Node Colors by Level ─── */
function nodeColor(level: number): string {
  if (level === 0) return "bg-amber-50 border-amber-200 text-amber-900";
  if (level === 1) return "bg-sky-50 border-sky-200 text-sky-900";
  return "bg-emerald-50 border-emerald-200 text-emerald-900";
}

function nodeLabel(level: number): string {
  if (level === 0) return "ROOT";
  if (level === 1) return "L2";
  return "L3";
}

/* ─── Tree Node Component ─── */
function TreeNodeBox({ node, isSelected, onSelect }: { node: TreeNode; isSelected: boolean; onSelect: () => void }) {
  const hasChildren = node.children && node.children.length > 0;
  return (
    <div className="flex flex-col items-center">
      <button
        onClick={onSelect}
        className={`relative px-4 py-2.5 rounded-xl border-2 text-sm font-semibold transition-all min-w-[140px] text-center ${
          isSelected ? "ring-2 ring-primary ring-offset-2 border-primary" : "border-dashed hover:border-solid"
        } ${nodeColor(node.level)}`}
      >
        <span className="text-[10px] font-medium opacity-60 absolute -top-2 left-3 bg-white px-1 rounded">
          {nodeLabel(node.level)} NODE
        </span>
        {node.label}
        {hasChildren && (
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-0.5 h-2 bg-border" />
        )}
      </button>
      {hasChildren && (
        <>
          <div className="w-full h-0.5 bg-border my-2 relative">
            {node.children!.map((_, i) => (
              <div
                key={i}
                className="absolute top-0 w-0.5 h-2 bg-border"
                style={{
                  left: `${((i + 1) / (node.children!.length + 1)) * 100}%`,
                  transform: "translateX(-50%)",
                }}
              />
            ))}
          </div>
          <div className="flex gap-6">
            {node.children!.map((child) => (
              <TreeNodeBox
                key={child.id}
                node={child}
                isSelected={isSelected}
                onSelect={onSelect}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/* ─── Placeholder Bars ─── */
function PlaceholderBars({ count = 6, widths = ["100%", "85%", "92%", "70%", "88%", "60%"] }: { count?: number; widths?: string[] }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-2.5 bg-muted rounded-full"
          style={{ width: widths[i] || "80%" }}
        />
      ))}
    </div>
  );
}

/* ─── Main Page ─── */
export default function ValueStudioExplorer() {
  const [selectedNode, setSelectedNode] = useState<string>("root");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    model: true,
    studio: true,
  });

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      {/* ═══════ TOP HEADER ═══════ */}
      <header className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0 bg-card">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="w-8 h-8 rounded-lg hover:bg-muted flex items-center justify-center transition-colors"
          >
            <MousePointer2 className="w-4 h-4 text-muted-foreground" />
          </button>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-foreground">Value Fabric</span>
            <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">Intelligence Platform</span>
          </div>
          <div className="ml-6 relative">
            <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              placeholder="Search entities, domains, cases..."
              className="pl-8 pr-3 py-1.5 w-72 text-xs bg-muted rounded-lg border border-input focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2 py-1 rounded-full">
            Admin mode
          </span>
          <button className="w-8 h-8 rounded-lg hover:bg-muted flex items-center justify-center">
            <Bell className="w-4 h-4 text-muted-foreground" />
          </button>
          <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center text-[10px] font-bold text-primary-foreground">
            SC
          </div>
        </div>
      </header>

      {/* ═══════ BODY ═══════ */}
      <div className="flex-1 flex overflow-hidden">
        {/* ─── Sidebar ─── */}
        <aside
          className="border-r border-border bg-card flex flex-col shrink-0 transition-all duration-200 overflow-y-auto"
          style={{ width: sidebarCollapsed ? 56 : 200 }}
        >
          <nav className="p-2 space-y-0.5">
            {mainNav.map((item) => (
              <div key={item.label}>
                <button
                  onClick={() => {
                    if (item.hasSub) toggleSection(item.label.toLowerCase().replace(" ", ""));
                  }}
                  className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs transition-colors ${
                    item.active
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                  style={{ justifyContent: sidebarCollapsed ? "center" : "flex-start" }}
                >
                  <item.icon className="w-4 h-4 shrink-0" />
                  {!sidebarCollapsed && (
                    <>
                      <span className="flex-1 text-left">{item.label}</span>
                      {item.hasSub && (
                        expandedSections[item.label.toLowerCase().replace(" ", "")] ? (
                          <ChevronDown className="w-3 h-3" />
                        ) : (
                          <ChevronRight className="w-3 h-3" />
                        )
                      )}
                      {item.badge && (
                        <span className="text-[9px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded-full font-medium">
                          {item.badge}
                        </span>
                      )}
                    </>
                  )}
                </button>
                {/* Sub-items */}
                {!sidebarCollapsed && item.hasSub && expandedSections[item.label.toLowerCase().replace(" ", "")] && (
                  <div className="ml-7 mt-0.5 space-y-0.5">
                    {(item.label === "Model" ? modelSub : studioSub).map((sub) => (
                      <button
                        key={sub.label}
                        className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                          sub.active
                            ? "bg-primary/10 text-primary font-medium"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        }`}
                      >
                        {sub.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </nav>
        </aside>

        {/* ─── Main Content ─── */}
        <main className="flex-1 flex flex-col min-w-0 bg-muted/30">
          {/* Title Bar */}
          <div className="h-14 border-b border-border flex items-center justify-between px-6 bg-card shrink-0">
            <div>
              <h1 className="text-base font-semibold text-foreground">Value Studio — Explorer</h1>
              <p className="text-xs text-muted-foreground">Visualize and edit normalized value hierarchies</p>
            </div>
            <div className="flex items-center gap-2">
              <button className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-muted transition-colors">
                Select Tree
              </button>
              <button className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-muted transition-colors">
                Import
              </button>
              <button className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-muted transition-colors">
                Export
              </button>
              <button className="px-3 py-1.5 text-xs font-semibold bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-1.5">
                <Plus className="w-3.5 h-3.5" /> New Tree
              </button>
            </div>
          </div>

          {/* Three-Panel Workspace */}
          <div className="flex-1 flex overflow-hidden p-4 gap-4">
            {/* Tree Navigator */}
            <div className="w-56 shrink-0 flex flex-col gap-4">
              <div className="bg-card border border-border rounded-xl p-4 flex-1">
                <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">Tree Navigator</h3>
                <PlaceholderBars count={8} widths={["100%", "90%", "85%", "95%", "75%", "88%", "70%", "92%"]} />
              </div>
              <div className="bg-card border border-border rounded-xl p-4 h-32">
                <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">Path Tracer</h3>
                <PlaceholderBars count={3} widths={["100%", "80%", "65%"]} />
              </div>
            </div>

            {/* Tree Canvas */}
            <div className="flex-1 bg-card border border-dashed border-primary/30 rounded-xl relative overflow-auto">
              <div className="absolute inset-0 flex items-center justify-center p-8">
                <TreeNodeBox
                  node={treeData}
                  isSelected={selectedNode === treeData.id}
                  onSelect={() => setSelectedNode(treeData.id)}
                />
              </div>
              {/* Canvas Controls */}
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-card border border-border rounded-lg p-1 shadow-sm">
                <button className="w-7 h-7 flex items-center justify-center rounded hover:bg-muted" title="Undo">
                  <Undo2 className="w-3.5 h-3.5 text-muted-foreground" />
                </button>
                <button className="w-7 h-7 flex items-center justify-center rounded hover:bg-muted" title="Redo">
                  <Redo2 className="w-3.5 h-3.5 text-muted-foreground" />
                </button>
                <div className="w-px h-4 bg-border mx-0.5" />
                <button className="w-7 h-7 flex items-center justify-center rounded hover:bg-muted" title="Zoom Out">
                  <ZoomOut className="w-3.5 h-3.5 text-muted-foreground" />
                </button>
                <span className="text-[10px] text-muted-foreground w-8 text-center">100%</span>
                <button className="w-7 h-7 flex items-center justify-center rounded hover:bg-muted" title="Zoom In">
                  <ZoomIn className="w-3.5 h-3.5 text-muted-foreground" />
                </button>
                <div className="w-px h-4 bg-border mx-0.5" />
                <button className="w-7 h-7 flex items-center justify-center rounded hover:bg-muted" title="Fit">
                  <Maximize2 className="w-3.5 h-3.5 text-muted-foreground" />
                </button>
              </div>
            </div>

            {/* Node Inspector */}
            <div className="w-64 shrink-0 flex flex-col gap-4">
              <div className="bg-card border border-border rounded-xl p-4 flex-1">
                <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">Node Inspector</h3>
                <PlaceholderBars count={10} widths={["100%", "85%", "92%", "78%", "88%", "70%", "95%", "82%", "75%", "90%"]} />
                <div className="flex gap-2 mt-5">
                  <button className="px-3 py-1.5 bg-primary text-primary-foreground text-xs font-medium rounded-lg">
                    Edit Node
                  </button>
                  <button className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-muted">
                    Remove
                  </button>
                </div>
              </div>
              <div className="bg-card border border-border rounded-xl p-4">
                <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">Toolbar</h3>
                <div className="flex gap-2">
                  <button className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-muted">
                    Add Child
                  </button>
                  <button className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-muted">
                    Move
                  </button>
                  <button className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-muted">
                    Link
                  </button>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
