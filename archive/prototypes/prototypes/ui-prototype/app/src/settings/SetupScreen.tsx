import { useState } from "react";
import {
  Plug, Bot, GitFork, FunctionSquare, RefreshCw,
  Cloud, Database, Globe, Server, Sparkles, Zap,
  ChevronRight, BrainCircuit, Cpu
} from "lucide-react";
import { StatusBadge, TabNav, TopTabNav } from "@/components/blocks";
import type { TabItem, TopTabItem } from "@/components/blocks";

/* ─── Outer vertical tabs ─── */
const outerTabs: TabItem[] = [
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "ontology", label: "Ontology & Packs", icon: GitFork },
  { id: "formulas", label: "Formulas & Models", icon: FunctionSquare },
  { id: "agents", label: "Agents & AI", icon: Bot },
];

/* ─── Data ─── */
const integrations = [
  { name: "Salesforce CRM", type: "CRM", status: "connected" as const, lastSync: "2 min ago", records: 12450, icon: Cloud },
  { name: "HubSpot", type: "CRM", status: "connected" as const, lastSync: "5 min ago", records: 8320, icon: Cloud },
  { name: "SAP ERP", type: "ERP", status: "warning" as const, lastSync: "2 hours ago", records: 45600, icon: Database },
  { name: "NetSuite", type: "ERP", status: "connected" as const, lastSync: "12 min ago", records: 32100, icon: Database },
  { name: "Workday", type: "HR", status: "connected" as const, lastSync: "18 min ago", records: 12800, icon: Globe },
  { name: "Snowflake", type: "Data Warehouse", status: "connected" as const, lastSync: "8 min ago", records: 892000, icon: Server },
];

const agentConnectors = [
  { name: "LinkedIn Sales Navigator", category: "Prospecting", status: "active" as const, queries: 2450, success: "98.2%", icon: Globe },
  { name: "Crunchbase", category: "Firmographics", status: "active" as const, queries: 1200, success: "96.5%", icon: Database },
  { name: "D&B Hoovers", category: "Firmographics", status: "active" as const, queries: 890, success: "99.1%", icon: Database },
  { name: "G2 Reviews", category: "Social Signals", status: "paused" as const, queries: 0, success: "—", icon: Cloud },
  { name: "BuiltWith", category: "Technographics", status: "active" as const, queries: 560, success: "94.8%", icon: Zap },
];

const packs = [
  { name: "Manufacturing", installed: true, drivers: 48, formulas: 32, updated: "Mar 15, 2026", version: "3.2" },
  { name: "Automotive", installed: true, drivers: 36, formulas: 28, updated: "Feb 28, 2026", version: "2.8" },
  { name: "Logistics", installed: true, drivers: 24, formulas: 18, updated: "Jan 10, 2026", version: "2.1" },
];

const availablePacks = [
  { name: "Aerospace & Defense", drivers: 41, formulas: 30 },
  { name: "Medical Devices", drivers: 33, formulas: 22 },
  { name: "Electronics Assembly", drivers: 28, formulas: 19 },
  { name: "Energy & Utilities", drivers: 22, formulas: 15 },
  { name: "Food & Beverage", drivers: 18, formulas: 12 },
];

const formulaCategories = [
  { name: "Labor Cost", formulas: 12, default: true },
  { name: "Throughput", formulas: 8, default: true },
  { name: "Quality", formulas: 7, default: true },
  { name: "Safety", formulas: 5, default: false },
  { name: "Energy", formulas: 4, default: false },
  { name: "Sustainability", formulas: 3, default: false },
];

const agents = [
  { name: "Prospect Intelligence Agent", status: "active" as const, description: "Researches prospects from CRM and public data", icon: Globe },
  { name: "Value Model Generator", status: "active" as const, description: "Generates IF-THEN hypotheses from ontology match", icon: Sparkles },
  { name: "Evidence Matcher", status: "active" as const, description: "Maps evidence to driver tree levers", icon: Zap },
  { name: "Stakeholder Mapper", status: "active" as const, description: "Identifies and scores stakeholder influence", icon: Bot },
  { name: "Report Composer", status: "active" as const, description: "Assembles value cases from validated models", icon: FunctionSquare },
];

/* ─── Sub-components ─── */
function IntegrationRow({ item }: { item: typeof integrations[0] }) {
  return (
    <div className="flex items-center gap-4 px-5 py-3 hover:bg-muted/50 transition-colors">
      <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center border border-border">
        <item.icon className="w-4 h-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground">{item.name}</p>
        <p className="text-xs text-muted-foreground">{item.type} · {item.records.toLocaleString()} records</p>
      </div>
      <div className="text-right mr-3 hidden sm:block">
        <p className="text-xs text-muted-foreground">Last sync</p>
        <p className="text-xs font-medium text-foreground">{item.lastSync}</p>
      </div>
      <StatusBadge status={item.status} />
    </div>
  );
}

/* ═══════════════════════════════════════════
   INTEGRATIONS — inner horizontal tabs
   ═══════════════════════════════════════════ */
const integrationsSubTabs: TopTabItem[] = [
  { id: "systems", label: "System Integrations", icon: Cloud },
  { id: "connectors", label: "AI Connectors", icon: Zap },
];

function IntegrationsPanel() {
  const [subTab, setSubTab] = useState("systems");
  return (
    <div>
      <TopTabNav tabs={integrationsSubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] p-0 overflow-hidden">
        {subTab === "systems" && (
          <div>
            <div className="px-6 py-4 border-b border-border/60 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">Connected data sources that feed intelligence</p>
              <button className="text-xs flex items-center gap-1.5 text-primary font-medium"><RefreshCw className="w-3.5 h-3.5" /> Refresh All</button>
            </div>
            <div className="divide-y divide-border/60">
              {integrations.map((item) => <IntegrationRow key={item.name} item={item} />)}
            </div>
          </div>
        )}
        {subTab === "connectors" && (
          <div>
            <div className="px-6 py-4 border-b border-border/60">
              <p className="text-xs text-muted-foreground">External enrichment services used by AI agents</p>
            </div>
            <div className="divide-y divide-border/60">
              {agentConnectors.map((item) => (
                <div key={item.name} className="flex items-center gap-4 px-5 py-3 hover:bg-muted/50 transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center border border-border">
                    <item.icon className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground">{item.name}</p>
                    <p className="text-xs text-muted-foreground">{item.category} · {item.queries.toLocaleString()} queries</p>
                  </div>
                  <div className="text-right mr-3 hidden sm:block">
                    <p className="text-xs text-muted-foreground">Success rate</p>
                    <p className="text-xs font-medium text-foreground">{item.success}</p>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   ONTOLOGY — inner horizontal tabs
   ═══════════════════════════════════════════ */
const ontologySubTabs: TopTabItem[] = [
  { id: "installed", label: "Installed Packs", icon: GitFork },
  { id: "available", label: "Available Packs", icon: Sparkles },
];

function OntologyPanel() {
  const [subTab, setSubTab] = useState("installed");
  return (
    <div>
      <TopTabNav tabs={ontologySubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] p-6">
        {subTab === "installed" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs text-muted-foreground">{packs.length} active · {packs.reduce((s, p) => s + p.drivers, 0)} drivers · {packs.reduce((s, p) => s + p.formulas, 0)} formulas</p>
              <button className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-xs font-medium hover:bg-primary/90">
                <Sparkles className="w-3.5 h-3.5" /> Browse Packs
              </button>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {packs.map((p) => (
                <div key={p.name} className="p-4 rounded-lg border border-border hover:border-primary/50 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-foreground">{p.name}</span>
                    <StatusBadge status="active" size="sm" />
                  </div>
                  <p className="text-xs text-muted-foreground">{p.drivers} drivers · {p.formulas} formulas</p>
                  <p className="text-[10px] text-muted-foreground/60 mt-1">v{p.version} · Updated {p.updated}</p>
                </div>
              ))}
            </div>
          </div>
        )}
        {subTab === "available" && (
          <div className="space-y-2">
            {availablePacks.map((p) => (
              <div key={p.name} className="flex items-center justify-between py-2 px-3 hover:bg-muted/50 rounded-lg transition-colors">
                <div className="flex items-center gap-3">
                  <GitFork className="w-4 h-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-foreground">{p.name}</p>
                    <p className="text-xs text-muted-foreground">{p.drivers} drivers · {p.formulas} formulas</p>
                  </div>
                </div>
                <button className="text-xs px-3 py-1.5 bg-primary/10 text-primary rounded-lg font-medium hover:bg-primary/20">Install</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   FORMULAS — inner horizontal tabs
   ═══════════════════════════════════════════ */
const formulasSubTabs: TopTabItem[] = [
  { id: "library", label: "Formula Library", icon: FunctionSquare },
  { id: "defaults", label: "Active Defaults", icon: Database },
];

function FormulasPanel() {
  const [subTab, setSubTab] = useState("library");
  return (
    <div>
      <TopTabNav tabs={formulasSubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] p-6">
        {subTab === "library" && (
          <div className="space-y-2">
            {formulaCategories.map((c) => (
              <div key={c.name} className="flex items-center justify-between py-2.5 px-3 hover:bg-muted/50 rounded-lg transition-colors">
                <div className="flex items-center gap-3">
                  <FunctionSquare className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium text-foreground">{c.name}</span>
                  {c.default && <StatusBadge status="active" label="Default" size="sm" />}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">{c.formulas} formulas</span>
                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40" />
                </div>
              </div>
            ))}
          </div>
        )}
        {subTab === "defaults" && (
          <div className="grid grid-cols-3 gap-3">
            {[
              { name: "Labor Value", source: "Positions x Loaded Annual Cost", output: "$/year" },
              { name: "Throughput Gain", source: "Cycle reduction x Line capacity", output: "$/year" },
              { name: "Defect Cost", source: "Defect rate x Unit cost x Volume", output: "$/year" },
            ].map((m) => (
              <div key={m.name} className="p-3 rounded-lg border border-border hover:border-primary/50 transition-colors cursor-pointer">
                <p className="text-sm font-medium text-foreground">{m.name}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{m.source}</p>
                <p className="text-[10px] text-muted-foreground/60 mt-1">&rarr; {m.output}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   AGENTS — inner horizontal tabs
   ═══════════════════════════════════════════ */
const agentsSubTabs: TopTabItem[] = [
  { id: "agents", label: "AI Agents", icon: BrainCircuit },
  { id: "config", label: "Model Configuration", icon: Cpu },
];

function AgentsPanel() {
  const [subTab, setSubTab] = useState("agents");
  return (
    <div>
      <TopTabNav tabs={agentsSubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] p-6">
        {subTab === "agents" && (
          <div className="space-y-2">
            {agents.map((a) => (
              <div key={a.name} className="flex items-center gap-4 py-3 px-3 hover:bg-muted/50 rounded-lg transition-colors">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <a.icon className="w-4 h-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">{a.name}</p>
                  <p className="text-xs text-muted-foreground">{a.description}</p>
                </div>
                <StatusBadge status={a.status} />
              </div>
            ))}
          </div>
        )}
        {subTab === "config" && (
          <div className="grid grid-cols-3 gap-4">
            {[{ label: "AI Model", value: "GPT-4o" }, { label: "Temperature", value: "0.3" }, { label: "Max Tokens", value: "8,192" }].map((c) => (
              <button key={c.label} className="p-3 rounded-lg border border-border hover:border-border/80 transition-colors text-left">
                <p className="text-xs text-muted-foreground">{c.label}</p>
                <p className="text-lg font-semibold text-foreground">{c.value}</p>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   MAIN
   ═══════════════════════════════════════════ */
export default function SetupScreen() {
  const [activeTab, setActiveTab] = useState("integrations");

  return (
    <main className="max-w-5xl mx-auto" aria-label="Intelligence Setup">
      <header className="mb-6">
        <h1 className="text-xl font-bold text-foreground">Intelligence Setup</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Configure what shapes value model quality — integrations, ontology, formulas, and AI agents.</p>
      </header>

      <div className="flex gap-6">
        <TabNav tabs={outerTabs} activeTab={activeTab} onChange={setActiveTab} />
        <section className="flex-1 min-w-0">
          {activeTab === "integrations" && <IntegrationsPanel />}
          {activeTab === "ontology" && <OntologyPanel />}
          {activeTab === "formulas" && <FormulasPanel />}
          {activeTab === "agents" && <AgentsPanel />}
        </section>
      </div>
    </main>
  );
}
