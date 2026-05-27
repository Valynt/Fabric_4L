import { useState } from "react";
import {
  User, Building2, Shield, Sun, Moon, Monitor,
  Pencil, Bell, Users, CreditCard, Lock, Globe, Eye
} from "lucide-react";
import { TabNav, TopTabNav } from "@/components/blocks";
import type { TabItem, TopTabItem } from "@/components/blocks";

/* ─── Outer vertical tabs ─── */
const outerTabs: TabItem[] = [
  { id: "personal", label: "Personal", icon: User },
  { id: "organization", label: "Organization", icon: Building2 },
  { id: "security", label: "Security", icon: Shield },
];

/* ─── Toggle component ─── */
function Toggle({ checked, onChange }: { checked: boolean; onChange?: () => void }) {
  return (
    <button
      onClick={onChange}
      role="switch"
      aria-checked={checked}
      className={`relative w-9 h-5 rounded-full transition-colors ${checked ? "bg-primary" : "bg-muted"}`}
    >
      <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-card rounded-full shadow-sm transition-transform ${checked ? "translate-x-4" : "translate-x-0"}`} />
    </button>
  );
}

/* ═══════════════════════════════════════════
   PERSONAL — inner horizontal tabs
   ═══════════════════════════════════════════ */
const personalSubTabs: TopTabItem[] = [
  { id: "profile", label: "Profile", icon: Pencil },
  { id: "appearance", label: "Appearance", icon: Eye },
  { id: "notifications", label: "Notifications", icon: Bell },
];

function PersonalPanel() {
  const [subTab, setSubTab] = useState("profile");

  return (
    <div>
      <TopTabNav tabs={personalSubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] p-7">
        {subTab === "profile" && <ProfileContent />}
        {subTab === "appearance" && <AppearanceContent />}
        {subTab === "notifications" && <NotificationsContent />}
      </div>
    </div>
  );
}

function ProfileContent() {
  return (
    <div>
      <h2 className="text-base font-semibold text-foreground mb-4">Profile Details</h2>
      <div className="flex items-center gap-4 mb-6">
        <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center text-lg font-bold text-primary">SC</div>
        <button className="text-xs text-primary font-medium hover:underline">Change photo</button>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: "First Name", value: "Sarah" },
          { label: "Last Name", value: "Chen" },
          { label: "Email", value: "sarah.chen@axiomrobotics.com" },
          { label: "Role", value: "Value Engineer" },
          { label: "Team", value: "Sales Engineering" },
          { label: "Time Zone", value: "America/Los Angeles" },
        ].map((f) => (
          <div key={f.label}>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">{f.label}</label>
            <input
              defaultValue={f.value}
              className="w-full px-3 py-2.5 bg-muted rounded-xl border border-input text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        ))}
      </div>
      <div className="flex justify-end gap-3 mt-6">
        <button className="px-5 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground rounded-xl">Cancel</button>
        <button className="px-5 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-semibold hover:bg-primary/90">Save Changes</button>
      </div>
    </div>
  );
}

function AppearanceContent() {
  return (
    <div>
      <h2 className="text-base font-semibold text-foreground mb-4">Appearance</h2>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-foreground">Theme</p>
          <p className="text-xs text-muted-foreground">Choose your preferred color scheme</p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-primary/10 text-primary rounded-xl text-xs font-medium flex items-center gap-1.5">
            <Sun className="w-3.5 h-3.5" /> Light
          </button>
          <button className="px-4 py-2 bg-muted text-muted-foreground rounded-xl text-xs font-medium flex items-center gap-1.5">
            <Moon className="w-3.5 h-3.5" /> Dark
          </button>
        </div>
      </div>
    </div>
  );
}

function NotificationsContent() {
  const notifications = [
    { label: "Value model shared with me", on: true },
    { label: "Approval requested", on: true },
    { label: "AI generation complete", on: true },
    { label: "Evidence mapping suggestions", on: false },
    { label: "Weekly digest", on: true },
  ];
  return (
    <div>
      <h2 className="text-base font-semibold text-foreground mb-4">Notifications</h2>
      <div className="space-y-4">
        {notifications.map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="text-sm text-foreground">{item.label}</span>
            <Toggle checked={item.on} />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   ORGANIZATION — inner horizontal tabs
   ═══════════════════════════════════════════ */
const orgSubTabs: TopTabItem[] = [
  { id: "workspace", label: "Workspace", icon: Globe },
  { id: "members", label: "Members", icon: Users },
  { id: "billing", label: "Billing", icon: CreditCard },
];

function OrganizationPanel() {
  const [subTab, setSubTab] = useState("workspace");

  return (
    <div>
      <TopTabNav tabs={orgSubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] p-7">
        {subTab === "workspace" && <WorkspaceContent />}
        {subTab === "members" && <MembersContent />}
        {subTab === "billing" && <BillingContent />}
      </div>
    </div>
  );
}

function WorkspaceContent() {
  return (
    <div>
      <h2 className="text-base font-semibold text-foreground mb-4">Workspace</h2>
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: "Workspace Name", value: "Axiom Robotics" },
          { label: "Domain", value: "axiomrobotics.com" },
          { label: "Business Unit", value: "Commercial — North America" },
          { label: "Region", value: "US West" },
          { label: "Default Ontology", value: "Manufacturing v3.2" },
          { label: "Default Currency", value: "USD ($)" },
        ].map((f) => (
          <div key={f.label}>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">{f.label}</label>
            <input
              defaultValue={f.value}
              className="w-full px-3 py-2.5 bg-muted rounded-xl border border-input text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        ))}
      </div>
      <div className="flex justify-end gap-3 mt-6">
        <button className="px-5 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground rounded-xl">Cancel</button>
        <button className="px-5 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-semibold hover:bg-primary/90">Save Changes</button>
      </div>
    </div>
  );
}

function MembersContent() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-foreground">Members</h2>
        <button className="text-xs text-primary font-medium">Invite</button>
      </div>
      <div className="space-y-3">
        {[
          { name: "Sarah Chen", role: "Admin", team: "Sales Engineering" },
          { name: "James Torres", role: "Value Engineer", team: "Sales Engineering" },
          { name: "Lisa Park", role: "Viewer", team: "Marketing" },
          { name: "David Kim", role: "Value Engineer", team: "Customer Success" },
        ].map((m) => (
          <div key={m.name} className="flex items-center justify-between py-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground">{m.name}</span>
              <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded-full text-muted-foreground">{m.team}</span>
            </div>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
              m.role === "Admin" ? "bg-purple-400/10 text-purple-400" : m.role === "Value Engineer" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
            }`}>{m.role}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BillingContent() {
  return (
    <div>
      <h2 className="text-base font-semibold text-foreground mb-4">Plan & Usage</h2>
      <div className="flex items-center gap-3 mb-5">
        <span className="text-xs px-2.5 py-1 bg-primary/10 text-primary rounded-full font-medium">Enterprise</span>
        <span className="text-xs text-muted-foreground">12 of 25 seats · 48 of 200 models · 2.4 of 50 GB</span>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Seats Used", used: "12", total: "25", pct: 48 },
          { label: "Models Created", used: "48", total: "200", pct: 24 },
          { label: "Storage", used: "2.4", total: "50 GB", pct: 5 },
        ].map((q) => (
          <div key={q.label} className="p-4 border border-border rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted-foreground">{q.label}</span>
              <span className="text-xs font-medium text-foreground">{q.used} / {q.total}</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full bg-primary rounded-full" style={{ width: `${q.pct}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   SECURITY — inner horizontal tabs
   ═══════════════════════════════════════════ */
const securitySubTabs: TopTabItem[] = [
  { id: "authentication", label: "Authentication", icon: Lock },
  { id: "data", label: "Data Protection", icon: Shield },
  { id: "sessions", label: "Sessions", icon: Monitor },
];

function SecurityPanel() {
  const [subTab, setSubTab] = useState("authentication");

  return (
    <div>
      <TopTabNav tabs={securitySubTabs} activeTab={subTab} onChange={setSubTab} className="mb-5" />
      <div className="bg-card border border-border rounded-[20px] p-7">
        {subTab === "authentication" && <AuthenticationContent />}
        {subTab === "data" && <DataProtectionContent />}
        {subTab === "sessions" && <SessionsContent />}
      </div>
    </div>
  );
}

function AuthenticationContent() {
  return (
    <div>
      <h2 className="text-base font-semibold text-foreground mb-4">Authentication</h2>
      <div className="space-y-4">
        {[
          { label: "Single Sign-On (SSO)", value: "SAML 2.0 — Okta" },
          { label: "Multi-Factor Authentication", value: "Required for all users" },
          { label: "Session Timeout", value: "8 hours idle" },
        ].map((s) => (
          <div key={s.label} className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm font-medium text-foreground">{s.label}</p>
              <p className="text-xs text-muted-foreground">{s.value}</p>
            </div>
            <span className="text-xs px-2 py-0.5 bg-emerald-500/10 text-emerald-500 rounded-full font-medium">Active</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DataProtectionContent() {
  return (
    <div>
      <h2 className="text-base font-semibold text-foreground mb-4">Data Protection</h2>
      <div className="space-y-4">
        {[
          { label: "Default Classification", value: "Internal" },
          { label: "Retention", value: "Models 7 years · Evidence 3 years" },
          { label: "Encryption", value: "AES-256 at rest · TLS 1.3 in transit" },
          { label: "Backups", value: "Daily automated · 30-day recovery" },
        ].map((s) => (
          <div key={s.label} className="flex items-center justify-between py-2">
            <span className="text-sm font-medium text-foreground">{s.label}</span>
            <span className="text-xs text-muted-foreground">{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SessionsContent() {
  return (
    <div>
      <h2 className="text-base font-semibold text-foreground mb-4">Sessions</h2>
      <div className="space-y-3">
        {[
          { device: "Chrome on macOS", location: "San Francisco, CA", time: "Active now", current: true },
          { device: "Safari on iPhone", location: "San Francisco, CA", time: "2 hours ago", current: false },
        ].map((s) => (
          <div key={s.device} className="flex items-center justify-between py-2">
            <div className="flex items-center gap-2">
              <Monitor className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm text-foreground">{s.device}</span>
              {s.current && <span className="text-[10px] px-1.5 py-0.5 bg-emerald-500/10 text-emerald-500 rounded-full font-medium">Current</span>}
            </div>
            {!s.current && <button className="text-xs text-destructive font-medium">Revoke</button>}
          </div>
        ))}
      </div>
      <button className="mt-4 text-xs text-destructive font-medium">Sign out all other sessions</button>
    </div>
  );
}

/* ═══════════════════════════════════════════
   MAIN
   ═══════════════════════════════════════════ */
export default function SettingsScreen() {
  const [activeTab, setActiveTab] = useState("personal");

  return (
    <main className="max-w-5xl mx-auto" aria-label="Settings">
      <header className="mb-6">
        <h1 className="text-xl font-bold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Your profile, workspace, and security preferences.</p>
      </header>

      <div className="flex gap-6">
        <TabNav tabs={outerTabs} activeTab={activeTab} onChange={setActiveTab} />
        <section className="flex-1 min-w-0">
          {activeTab === "personal" && <PersonalPanel />}
          {activeTab === "organization" && <OrganizationPanel />}
          {activeTab === "security" && <SecurityPanel />}
        </section>
      </div>
    </main>
  );
}
