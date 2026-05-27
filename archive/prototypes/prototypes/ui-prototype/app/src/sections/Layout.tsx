import * as React from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Search, Bell, ChevronRight,
  Radar, Building2, BrainCircuit, GitFork, Database, Calculator,
  FileText, Sparkles, Command,
  Sun, Moon, ChevronDown, Frame, LifeBuoy, Send,
  PanelLeft, SlidersHorizontal, Cog, Activity
} from "lucide-react";

/* ─── Nav Data ─── */
const workflowSteps = [
  { path: "/", label: "Prospect" },
  { path: "/intelligence", label: "Intelligence" },
  { path: "/ai-model", label: "AI Model" },
  { path: "/driver-tree", label: "Driver Tree" },
  { path: "/evidence", label: "Evidence" },
  { path: "/calculator", label: "Calculator" },
  { path: "/value-case", label: "Value Case" },
];

const workflowItems = [
  { icon: Radar, label: "Prospect Setup", path: "/" },
  { icon: Building2, label: "Intelligence", path: "/intelligence" },
  { icon: BrainCircuit, label: "AI Model", path: "/ai-model" },
  { icon: GitFork, label: "Driver Tree", path: "/driver-tree" },
  { icon: Database, label: "Evidence", path: "/evidence" },
  { icon: Calculator, label: "Calculator", path: "/calculator" },
  { icon: FileText, label: "Value Case", path: "/value-case" },
];

const supportItems = [
  { icon: SlidersHorizontal, label: "Setup", path: "/setup" },
  { icon: Cog, label: "Settings", path: "/settings" },
  { icon: Activity, label: "Operations", path: "/operations" },
];

const bottomItems = [
  { icon: LifeBuoy, label: "Support", path: "#" },
  { icon: Send, label: "Feedback", path: "#" },
];

const isWorkflowPath = (path: string) => workflowItems.some((i) => i.path === path);

/* ─── Tooltip ─── */
function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <div className="group/tooltip relative flex items-center justify-center">
      {children}
      <div className="absolute left-full ml-2 px-2.5 py-1.5 bg-popover text-popover-foreground text-xs font-medium rounded-lg border border-border shadow-lg opacity-0 invisible group-hover/tooltip:opacity-100 group-hover/tooltip:visible transition-all duration-150 whitespace-nowrap z-50">
        {text}
      </div>
    </div>
  );
}

/* ─── Component ─── */
export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentPath = location.pathname;
  const inWorkflow = isWorkflowPath(currentPath);
  const currentStep = workflowSteps.findIndex((s) => s.path === currentPath);

  const [isDark, setIsDark] = React.useState(() => document.documentElement.classList.contains("dark"));
  const [collapsed, setCollapsed] = React.useState(false);
  const [userOpen, setUserOpen] = React.useState(false);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("vp-theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("vp-theme", "light");
    }
  };

  const NavButton = ({ item, isCollapsed }: { item: typeof workflowItems[0]; isCollapsed: boolean }) => {
    const isActive = currentPath === item.path;
    if (isCollapsed) {
      return (
        <Tooltip text={item.label}>
          <button
            onClick={() => navigate(item.path)}
            className={`w-8 h-8 mx-auto rounded-lg flex items-center justify-center transition-colors ${
              isActive ? "bg-sidebar-primary/15 text-sidebar-primary" : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent"
            }`}
          >
            <item.icon className="w-4 h-4" />
          </button>
        </Tooltip>
      );
    }
    return (
      <button
        onClick={() => navigate(item.path)}
        className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
          isActive ? "bg-sidebar-primary/15 text-sidebar-primary font-semibold" : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent"
        }`}
      >
        <item.icon className="w-4 h-4 shrink-0" />
        <span className="text-left flex-1">{item.label}</span>
        {isActive && <div className="w-1.5 h-1.5 rounded-full bg-sidebar-primary shrink-0" />}
      </button>
    );
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* ─── SIDEBAR ─── */}
      <aside
        className="shrink-0 h-full bg-sidebar border-r border-sidebar-border flex flex-col overflow-hidden transition-[width] duration-300 ease-in-out"
        style={{ width: collapsed ? 56 : 260 }}
      >
        {/* Company Header */}
        <div className="px-3 py-3 flex items-center" style={{ justifyContent: collapsed ? "center" : "stretch" }}>
          {collapsed ? (
            <Tooltip text="Axiom Robotics">
              <div className="w-8 h-8 rounded-lg bg-sidebar-primary flex items-center justify-center shrink-0 cursor-pointer">
                <Frame className="w-4 h-4 text-sidebar-primary-foreground" />
              </div>
            </Tooltip>
          ) : (
            <button className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-sidebar-accent transition-colors text-left">
              <div className="w-8 h-8 rounded-lg bg-sidebar-primary flex items-center justify-center shrink-0">
                <Frame className="w-4 h-4 text-sidebar-primary-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-sidebar-foreground truncate leading-tight">Axiom Robotics</p>
                <p className="text-[10px] text-sidebar-foreground/50 leading-tight">Enterprise</p>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-sidebar-foreground/40 shrink-0" />
            </button>
          )}
        </div>

        {/* Search */}
        <div className="px-3 pb-2">
          {collapsed ? (
            <Tooltip text="Search">
              <div className="w-8 h-8 mx-auto rounded-lg hover:bg-sidebar-accent flex items-center justify-center cursor-pointer transition-colors">
                <Search className="w-4 h-4 text-sidebar-foreground/50" />
              </div>
            </Tooltip>
          ) : (
            <div className="flex items-center gap-2 px-3 py-2 bg-sidebar-accent rounded-lg border border-sidebar-border">
              <Search className="w-3.5 h-3.5 text-sidebar-foreground/40" />
              <span className="text-xs text-sidebar-foreground/40 flex-1">Search</span>
              <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-sidebar-border bg-sidebar px-1.5 text-[10px] font-medium text-sidebar-foreground/50">
                <Command className="w-2.5 h-2.5" />K
              </kbd>
            </div>
          )}
        </div>

        {/* Scrollable nav */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 space-y-5 min-h-0">
          {/* Workflow Section */}
          <div>
            {!collapsed && (
              <p className="px-3 pb-1.5 text-[10px] font-semibold text-sidebar-foreground/40 uppercase tracking-wider">Workflow</p>
            )}
            <div className="space-y-0.5">
              {workflowItems.map((item) => (
                <NavButton key={item.path} item={item} isCollapsed={collapsed} />
              ))}
            </div>
          </div>

          {/* Co-Pilot Card */}
          {!collapsed && (
            <div className="bg-sidebar-accent/60 rounded-lg p-3 border border-sidebar-border">
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-4 h-4 rounded-full bg-sidebar-primary/20 flex items-center justify-center">
                  <Sparkles className="w-2.5 h-2.5 text-sidebar-primary" />
                </div>
                <span className="text-[10px] font-semibold text-sidebar-foreground/40 uppercase tracking-wider">Co-Pilot</span>
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              </div>
              <p className="text-[11px] text-sidebar-foreground/50 leading-relaxed">
                {inWorkflow ? "Enter a prospect to generate an AI value model" : "Configure integrations and ontology for better models"}
              </p>
            </div>
          )}

          {/* Support Section */}
          <div>
            {!collapsed && (
              <p className="px-3 pb-1.5 text-[10px] font-semibold text-sidebar-foreground/40 uppercase tracking-wider">Setup</p>
            )}
            <div className="space-y-0.5">
              {supportItems.map((item) => {
                const isActive = currentPath === item.path;
                if (collapsed) {
                  return (
                    <Tooltip key={item.path} text={item.label}>
                      <button
                        onClick={() => navigate(item.path)}
                        className={`w-8 h-8 mx-auto rounded-lg flex items-center justify-center transition-colors ${
                          isActive ? "bg-sidebar-primary/15 text-sidebar-primary" : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent"
                        }`}
                      >
                        <item.icon className="w-4 h-4" />
                      </button>
                    </Tooltip>
                  );
                }
                return (
                  <button
                    key={item.path}
                    onClick={() => navigate(item.path)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                      isActive ? "bg-sidebar-primary/15 text-sidebar-primary font-semibold" : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent"
                    }`}
                  >
                    <item.icon className="w-4 h-4 shrink-0" />
                    <span className="text-left flex-1">{item.label}</span>
                    {isActive && <div className="w-1.5 h-1.5 rounded-full bg-sidebar-primary shrink-0" />}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Bottom nav items */}
        <div className="px-3 pb-2 space-y-0.5">
          {bottomItems.map((item) =>
            collapsed ? (
              <Tooltip key={item.label} text={item.label}>
                <div className="w-8 h-8 mx-auto rounded-lg flex items-center justify-center text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors cursor-pointer">
                  <item.icon className="w-4 h-4" />
                </div>
              </Tooltip>
            ) : (
              <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors">
                <item.icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </button>
            )
          )}
        </div>

        {/* User Profile */}
        <div className="border-t border-sidebar-border pt-2 pb-3">
          {collapsed ? (
            <Tooltip text="Sarah Chen">
              <button
                onClick={() => setUserOpen(!userOpen)}
                className="w-8 h-8 mx-auto rounded-full bg-sidebar-primary/20 flex items-center justify-center hover:bg-sidebar-accent transition-colors"
              >
                <span className="text-xs font-bold text-sidebar-primary">SC</span>
              </button>
            </Tooltip>
          ) : (
            <div className="px-3">
              <button
                onClick={() => setUserOpen(!userOpen)}
                className="w-full flex items-center gap-2.5 px-2 py-2 rounded-lg hover:bg-sidebar-accent transition-colors text-left"
              >
                <div className="w-8 h-8 rounded-full bg-sidebar-primary/20 flex items-center justify-center shrink-0">
                  <span className="text-xs font-bold text-sidebar-primary">SC</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-sidebar-foreground truncate leading-tight">Sarah Chen</p>
                  <p className="text-[10px] text-sidebar-foreground/50 truncate leading-tight">sarah.chen@axiomrobotics.com</p>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-sidebar-foreground/40 shrink-0 transition-transform ${userOpen ? "rotate-180" : ""}`} />
              </button>
              {userOpen && (
                <div className="mt-1 ml-2 space-y-0.5">
                  <button className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-sidebar-foreground/70 hover:text-sidebar-foreground rounded-md hover:bg-sidebar-accent">Profile</button>
                  <button className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-sidebar-foreground/70 hover:text-sidebar-foreground rounded-md hover:bg-sidebar-accent">Settings</button>
                  <button className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-sidebar-foreground/70 hover:text-sidebar-foreground rounded-md hover:bg-sidebar-accent">Sign Out</button>
                </div>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* ─── MAIN CONTENT ─── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Bar — Full Length */}
        <header className="h-14 bg-card border-b border-border flex items-center justify-between px-4 shrink-0">
          {/* Left: Collapse toggle + Breadcrumb */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <PanelLeft className={`w-4 h-4 text-muted-foreground transition-transform duration-300 ${collapsed ? "rotate-180" : ""}`} />
            </button>
            <div className="w-px h-5 bg-border" />
            <div className="flex items-center gap-2 text-sm">
              {inWorkflow ? (
                <>
                  <span className="text-muted-foreground">Value Models</span>
                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40" />
                  <span className="text-foreground font-medium">Meridian Automotive</span>
                  {currentStep >= 0 && (
                    <>
                      <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40" />
                      <span className="text-muted-foreground">{workflowSteps[currentStep]?.label}</span>
                    </>
                  )}
                </>
              ) : currentPath === "/setup" ? (
                <>
                  <span className="text-muted-foreground">Setup</span>
                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40" />
                  <span className="text-foreground font-medium">Intelligence Setup</span>
                </>
              ) : currentPath === "/settings" ? (
                <>
                  <span className="text-muted-foreground">Settings</span>
                </>
              ) : currentPath === "/operations" ? (
                <>
                  <span className="text-muted-foreground">Operations</span>
                </>
              ) : (
                <span className="text-foreground font-medium">ValuePilot</span>
              )}
            </div>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
              title={isDark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDark ? <Sun className="w-4 h-4 text-muted-foreground" /> : <Moon className="w-4 h-4 text-muted-foreground" />}
            </button>
            <button className="p-2 rounded-lg hover:bg-muted transition-colors relative">
              <Bell className="w-4 h-4 text-muted-foreground" />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-primary" />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
