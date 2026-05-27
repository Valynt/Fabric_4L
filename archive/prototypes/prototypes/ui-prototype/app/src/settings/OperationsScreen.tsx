import { useState } from "react";
import {
  CheckCircle2, AlertTriangle, XCircle, RefreshCw, Clock,
  Layers, Zap, Database, Cloud, ChevronRight,
  Download, Activity, TrendingUp, HardDrive,
  Globe, Server, Brain, Calculator, FileText, Lock,
  Settings, BarChart3
} from "lucide-react";
import { StatusBadge, ProgressBar, TabNav, TopTabNav } from "@/components/blocks";
import type { TabItem, TopTabItem } from "@/components/blocks";

/* ─── Outer vertical tabs ─── */
const outerTabs: TabItem[] = [
  { id: "sync", label: "Sync Health", icon: RefreshCw },
  { id: "jobs", label: "Jobs & Queues", icon: Layers },
  { id: "events", label: "System Events", icon: Activity },
  { id: "tenant", label: "Observability", icon: TrendingUp },
];

/* ─── Data ─── */
const integrations = [
  { name: "Salesforce CRM", type: "CRM", status: "connected" as const, lastSync: "2 min ago", records: 12450, icon: Cloud },
  { name: "HubSpot", type: "CRM", status: "connected" as const, lastSync: "5 min ago", records: 8320, icon: Cloud },
  { name: "SAP ERP", type: "ERP", status: "warning" as const, lastSync: "2 hours ago", records: 45600, icon: Database },
  { name: "NetSuite", type: "ERP", status: "connected" as const, lastSync: "12 min ago", records: 32100, icon: Database },
  { name: "Microsoft Entra ID", type: "Identity", status: "connected" as const, lastSync: "1 min ago", records: 350, icon: Globe },
  { name: "Okta", type: "Identity", status: "error" as const, lastSync: "1 day ago", records: 0, icon: Globe },
  { name: "Snowflake", type: "Data Warehouse", status: "connected" as const, lastSync: "8 min ago", records: 892000, icon: Server },
  { name: "AWS S3", type: "Storage", status: "connected" as const, lastSync: "15 min ago", records: 14500, icon: HardDrive },
];

const agentConnectors = [
  { name: "LinkedIn Sales Navigator", category: "Prospecting", status: "active" as const, queries: 2450, success: "98.2%", icon: Globe },
  { name: "Crunchbase", category: "Firmographics", status: "active" as const, queries: 1200, success: "96.5%", icon: Database },
  { name: "D&B Hoovers", category: "Firmographics", status: "active" as const, queries: 890, success: "99.1%", icon: Database },
  { name: "G2 Reviews", category: "Social Signals", status: "paused" as const, queries: 0, success: "—", icon: Cloud },
  { name: "BuiltWith", category: "Technographics", status: "active" as const, queries: 560, success: "94.8%", icon: Zap },
  { name: "SEMrush", category: "Digital Presence", status: "warning" as const, queries: 320, success: "87.3%", icon: Activity },
];

const jobQueueData = [
  { id: "JOB-2025-0892", type: "AI Model Generation", entity: "Meridian Automotive", status: "running" as const, progress: 65 },
  { id: "JOB-2025-0891", type: "Evidence Enrichment", entity: "Stellar Manufacturing", status: "running" as const, progress: 42 },
  { id: "JOB-2025-0890", type: "Value Calculation", entity: "Apex Logistics", status: "completed" as const, progress: 100 },
  { id: "JOB-2025-0889", type: "Data Sync — Salesforce", entity: "All accounts", status: "completed" as const, progress: 100 },
  { id: "JOB-2025-0888", type: "Ontology Update", entity: "Manufacturing pack", status: "queued" as const, progress: 0 },
  { id: "JOB-2025-0887", type: "Report Generation", entity: "Meridian Automotive", status: "queued" as const, progress: 0 },
  { id: "JOB-2025-0886", type: "Driver Tree Rebuild", entity: "Titan Industries", status: "failed" as const, progress: 30 },
];

const eventFilters = ["All", "Info", "Warning", "Error"] as const;
type EventFilter = (typeof eventFilters)[number];

const systemEvents = [
  { id: "EVT-4521", level: "Info" as EventFilter, message: "AI model generated for Meridian Automotive", source: "AI Engine", user: "Sarah Chen", time: "10:23 AM" },
  { id: "EVT-4520", level: "Warning" as EventFilter, message: "Salesforce sync delayed — rate limit exceeded", source: "Sync Service", user: "System", time: "10:15 AM" },
  { id: "EVT-4519", level: "Info" as EventFilter, message: "Value case PDF generated — Meridian Automotive v2.1", source: "Report Engine", user: "Sarah Chen", time: "10:08 AM" },
  { id: "EVT-4518", level: "Error" as EventFilter, message: "Driver tree rebuild failed for Titan Industries", source: "AI Engine", user: "System", time: "09:47 AM" },
  { id: "EVT-4517", level: "Info" as EventFilter, message: "User Alex Kim approved value model changes", source: "Collaboration", user: "Alex Kim", time: "09:30 AM" },
  { id: "EVT-4516", level: "Info" as EventFilter, message: "Evidence library updated — 23 new entries", source: "Ontology Service", user: "System", time: "09:15 AM" },
  { id: "EVT-4515", level: "Warning" as EventFilter, message: "HubSpot API deprecated field detected", source: "Integration", user: "System", time: "08:52 AM" },
  { id: "EVT-4514", level: "Info" as EventFilter, message: "New member invited — james@axiomrobotics.com", source: "Organization", user: "Sarah Chen", time: "08:30 AM" },
  { id: "EVT-4513", level: "Error" as EventFilter, message: "Okta identity sync failed — invalid credentials", source: "Identity", user: "System", time: "08:15 AM" },
  { id: "EVT-4512", level: "Info" as EventFilter, message: "Daily backup completed — 2.4GB, 14s duration", source: "Infrastructure", user: "System", time: "08:00 AM" },
];

const componentHealth = [
  { name: "AI Model Engine", status: "healthy" as const, uptime: "99.97%", latency: "124ms", icon: Brain },
  { name: "Value Calculator", status: "healthy" as const, uptime: "99.99%", latency: "89ms", icon: Calculator },
  { name: "Evidence Matcher", status: "healthy" as const, uptime: "99.95%", latency: "156ms", icon: Database },
  { name: "Report Generator", status: "degraded" as const, uptime: "98.20%", latency: "2.4s", icon: FileText },
  { name: "Sync Service", status: "healthy" as const, uptime: "99.90%", latency: "210ms", icon: RefreshCw },
  { name: "Auth Service", status: "healthy" as const, uptime: "99.99%", latency: "45ms", icon: Lock },
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
      <StatusBadge status={item.status} size="sm" />
    </div>
  );
}

function JobRow({ job }: { job: typeof jobQueueData[0] }) {
  const barColor = job.status === "completed" ? "bg-emerald-500" : job.status === "failed" ? "bg-destructive" : "bg-primary";
  return (
    <div className="px-5 py-3 hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-6 flex justify-center shrink-0">
          {job.status === "running" && <RefreshCw className="w-4 h-4 text-primary animate-spin" />}
          {job.status === "queued" && <Clock className="w-4 h-4 text-muted-foreground" />}
          {job.status === "completed" && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
          {job.status === "failed" && <XCircle className="w-4 h-4 text-destructive" />}
        </div>
        <div className="w-24 shrink-0 hidden sm:block">
          <p className="text-xs font-medium text-muted-foreground font-mono">{job.id}</p>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground">{job.type}</p>
          <p className="text-xs text-muted-foreground">{job.entity}</p>
        </div>
        <div className="w-28 shrink-0">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground">{job.progress}%</span>
            <StatusBadge status={job.status} size="sm" />
          </div>
          <ProgressBar value={job.progress} barClassName={barColor} size="sm" />
        </div>
      </div>
    </div>
  );
}

function EventRow({ evt }: { evt: typeof systemEvents[0] }) {
  return (
    <div className="px-5 py-3 flex items-start gap-4 hover:bg-muted/50 transition-colors">
      <div className="mt-0.5 shrink-0">
        {evt.level === "Info" && <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5" />}
        {evt.level === "Warning" && <AlertTriangle className="w-4 h-4 text-amber-500" />}
        {evt.level === "Error" && <XCircle className="w-4 h-4 text-destructive" />}
      </div>
      <div className="w-20 shrink-0 hidden sm:block">
        <p className="text-xs font-mono text-muted-foreground">{evt.id}</p>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-foreground">{evt.message}</p>
        <p className="text-xs text-muted-foreground mt-1">{evt.source} · by {evt.user}</p>
      </div>
      <span className="text-xs text-muted-foreground/60 shrink-0">{evt.time}</span>
    </div>
  );
}

/* ═══════════════════════════════════════════
   SYNC HEALTH — inner horizontal tabs
   ═══════════════════════════════════════════ */
const syncSubTabs: TopTabItem[] = [
  { id: "systems", label: "System Integrations", icon: Cloud },
  { id: "connectors", label: "AI Connectors", icon: Zap },
  { id: "config", label: "Sync Settings", icon: Settings },
];

function SyncHealthPanel() {
  const [subTab, setSubTab] = useState("systems");
  return (
    <div>
      <TopTabNav tabs={syncSubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] overflow-hidden">
        {subTab === "systems" && (
          <div>
            <div className="px-6 py-4 border-b border-border/60 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">Connected data sources and their sync status</p>
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
              <p className="text-xs text-muted-foreground">External services used by AI agents for enrichment</p>
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
                  <StatusBadge status={item.status} size="sm" />
                </div>
              ))}
            </div>
          </div>
        )}
        {subTab === "config" && (
          <div className="p-6">
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Auto-sync frequency", value: "Every 15 min", desc: "Incremental sync" },
                { label: "Conflict resolution", value: "System wins", desc: "VP overrides external" },
                { label: "Retry policy", value: "3 attempts", desc: "Exponential backoff" },
              ].map((s) => (
                <button key={s.label} className="p-4 rounded-lg border border-border hover:border-border/80 transition-colors text-left">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-muted-foreground">{s.label}</span>
                    <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
                  </div>
                  <p className="text-lg font-semibold text-foreground">{s.value}</p>
                  <p className="text-[10px] text-muted-foreground/60">{s.desc}</p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   JOBS & QUEUES — inner horizontal tabs
   ═══════════════════════════════════════════ */
const jobsSubTabs: TopTabItem[] = [
  { id: "queue", label: "Job Queue", icon: Layers },
  { id: "history", label: "History", icon: Database },
];

function JobsQueuesPanel() {
  const [subTab, setSubTab] = useState("queue");
  const [filter, setFilter] = useState("All");
  const filters = ["All", "Running", "Queued", "Completed", "Failed"];
  const filtered = filter === "All" ? jobQueueData : jobQueueData.filter((j) => j.status === filter.toLowerCase());

  return (
    <div>
      <TopTabNav tabs={jobsSubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] overflow-hidden">
        {subTab === "queue" && (
          <div>
            <div className="px-6 py-4 border-b border-border/60">
              <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5 w-fit">
                {filters.map((f) => (
                  <button key={f} onClick={() => setFilter(f)} className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${filter === f ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>{f}</button>
                ))}
              </div>
            </div>
            <div className="divide-y divide-border/60">
              {filtered.map((job) => <JobRow key={job.id} job={job} />)}
            </div>
          </div>
        )}
        {subTab === "history" && (
          <div className="p-6">
            <p className="text-sm text-muted-foreground">Recent job history will appear here.</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   SYSTEM EVENTS — inner horizontal tabs
   ═══════════════════════════════════════════ */
const eventsSubTabs: TopTabItem[] = [
  { id: "log", label: "Event Log", icon: FileText },
  { id: "stats", label: "Stats", icon: BarChart3 },
];

function SystemEventsPanel() {
  const [subTab, setSubTab] = useState("log");
  const [filter, setFilter] = useState<EventFilter>("All");
  const filtered = filter === "All" ? systemEvents : systemEvents.filter((e) => e.level === filter);

  return (
    <div>
      <TopTabNav tabs={eventsSubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] overflow-hidden">
        {subTab === "log" && (
          <div>
            <div className="px-6 py-4 border-b border-border/60">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5">
                  {eventFilters.map((f) => (
                    <button key={f} onClick={() => setFilter(f)} className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${filter === f ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>{f}</button>
                  ))}
                </div>
                <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground border border-border rounded-lg hover:bg-muted">
                  <Download className="w-3.5 h-3.5" /> Export
                </button>
              </div>
            </div>
            <div className="divide-y divide-border/60">
              {filtered.map((evt) => <EventRow key={evt.id} evt={evt} />)}
            </div>
          </div>
        )}
        {subTab === "stats" && (
          <div className="p-6">
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: "Total Events (24h)", value: "1,247", icon: Activity, color: "text-emerald-500" },
                { label: "Errors", value: "3", icon: XCircle, color: "text-destructive" },
                { label: "Warnings", value: "8", icon: AlertTriangle, color: "text-amber-500" },
                { label: "Avg Response", value: "142ms", icon: Zap, color: "text-emerald-500" },
              ].map((s) => (
                <div key={s.label} className="p-4 border border-border rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-muted-foreground">{s.label}</span>
                    <s.icon className={`w-4 h-4 ${s.color}`} />
                  </div>
                  <p className="text-2xl font-bold text-foreground">{s.value}</p>
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
   OBSERVABILITY — inner horizontal tabs
   ═══════════════════════════════════════════ */
const tenantSubTabs: TopTabItem[] = [
  { id: "overview", label: "Overview", icon: TrendingUp },
  { id: "health", label: "Component Health", icon: Activity },
  { id: "quotas", label: "Plan Quotas", icon: Database },
];

function TenantObservabilityPanel() {
  const [subTab, setSubTab] = useState("overview");
  return (
    <div>
      <TopTabNav tabs={tenantSubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] overflow-hidden">
        {subTab === "overview" && (
          <div className="p-6">
            <div className="grid grid-cols-4 gap-4 mb-6">
              {[
                { label: "AI Requests (24h)", value: "8,432", trend: "+18%" },
                { label: "Avg Model Gen Time", value: "6.2m", trend: "-12%" },
                { label: "Storage Used", value: "47.2 GB", trend: "+3%" },
                { label: "Active Sessions", value: "12", trend: "+2" },
              ].map((m) => (
                <div key={m.label} className="p-4 border border-border rounded-xl">
                  <p className="text-xs text-muted-foreground">{m.label}</p>
                  <div className="flex items-baseline gap-2 mt-1">
                    <p className="text-2xl font-bold text-foreground">{m.value}</p>
                    <span className="text-xs font-medium text-emerald-500">{m.trend}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {subTab === "health" && (
          <div className="divide-y divide-border/60">
            {componentHealth.map((comp) => (
              <div key={comp.name} className="flex items-center gap-4 px-5 py-3 hover:bg-muted/50 transition-colors">
                <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center border border-border">
                  <comp.icon className="w-4 h-4 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">{comp.name}</p>
                </div>
                <div className="w-24 text-right hidden sm:block">
                  <p className="text-xs text-muted-foreground">Uptime</p>
                  <p className="text-xs font-medium text-foreground">{comp.uptime}</p>
                </div>
                <div className="w-24 text-right hidden sm:block">
                  <p className="text-xs text-muted-foreground">Latency</p>
                  <p className="text-xs font-medium text-foreground">{comp.latency}</p>
                </div>
                <StatusBadge status={comp.status} size="sm" />
              </div>
            ))}
          </div>
        )}
        {subTab === "quotas" && (
          <div className="p-6">
            <h4 className="text-sm font-semibold text-foreground mb-4">Plan Quotas — Professional</h4>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: "AI Generations", used: "847", total: "2,000", pct: 42 },
                { label: "Storage", used: "47", total: "100 GB", pct: 47 },
                { label: "Team Members", used: "8", total: "15", pct: 53 },
                { label: "API Calls", used: "34K", total: "100K", pct: 34 },
              ].map((q) => (
                <div key={q.label}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs text-muted-foreground">{q.label}</span>
                    <span className="text-xs font-medium text-foreground">{q.used} / {q.total}</span>
                  </div>
                  <ProgressBar value={q.pct} max={100} barClassName={q.pct > 80 ? "bg-amber-500" : "bg-primary"} size="sm" />
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
   MAIN
   ═══════════════════════════════════════════ */
export default function OperationsScreen() {
  const [activeTab, setActiveTab] = useState("sync");

  return (
    <main className="max-w-6xl mx-auto" aria-label="Operations">
      <header className="mb-6">
        <h1 className="text-xl font-bold text-foreground">Operations</h1>
        <p className="text-sm text-muted-foreground mt-0.5">System health, job queues, and tenant observability</p>
      </header>

      <div className="flex gap-6">
        <TabNav tabs={outerTabs} activeTab={activeTab} onChange={setActiveTab} />
        <section className="flex-1 min-w-0">
          {activeTab === "sync" && <SyncHealthPanel />}
          {activeTab === "jobs" && <JobsQueuesPanel />}
          {activeTab === "events" && <SystemEventsPanel />}
          {activeTab === "tenant" && <TenantObservabilityPanel />}
        </section>
      </div>
    </main>
  );
}
