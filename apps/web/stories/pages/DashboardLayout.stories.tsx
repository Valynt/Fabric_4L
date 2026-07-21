/**
 * DashboardLayout Stories — Page Composition
 * ============================================
 *
 * Full page layout story showing the authenticated app shell:
 *   - Sidebar navigation with tenant selector
 *   - Top bar with search, notifications, user menu
 *   - Main content area with page header and data cards
 *   - Responsive breakpoints (sidebar collapse on mobile)
 *
 * DESIGN.md § Component Architecture: "Page or route fetches data through hooks"
 * DESIGN.md § Typography: Display M (24px) for card titles
 */

import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  LayoutDashboard,
  Workflow,
  Share2,
  Settings,
  Users,
  Search,
  Bell,
  Menu,
  ChevronLeft,
  ChevronRight,
  Activity,
  TrendingUp,
  BarChart3,
  Clock,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Mock DashboardLayout
// ---------------------------------------------------------------------------

interface NavItem {
  icon: React.ReactNode;
  label: string;
  badge?: string;
  active?: boolean;
}

function DashboardLayout({
  sidebarCollapsed = false,
  loading = false,
}: {
  sidebarCollapsed?: boolean;
  loading?: boolean;
}) {
  const [collapsed, setCollapsed] = useState(sidebarCollapsed);

  const navItems: NavItem[] = [
    { icon: <LayoutDashboard className="h-4 w-4" />, label: "Dashboard", active: true },
    { icon: <Workflow className="h-4 w-4" />, label: "Workflows", badge: "3" },
    { icon: <Share2 className="h-4 w-4" />, label: "Knowledge Graph" },
    { icon: <Users className="h-4 w-4" />, label: "Team" },
    { icon: <BarChart3 className="h-4 w-4" />, label: "Analytics" },
    { icon: <Settings className="h-4 w-4" />, label: "Settings" },
  ];

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      {/* Sidebar */}
      <aside
        className={`flex flex-col border-r bg-card transition-all duration-200 ${
          collapsed ? "w-16" : "w-64"
        }`}
      >
        {/* Logo */}
        <div className="flex h-14 items-center border-b px-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Activity className="h-4 w-4 text-primary-foreground" />
          </div>
          {!collapsed && (
            <span className="ml-3 font-semibold text-sm tracking-tight">Value Fabric</span>
          )}
        </div>

        {/* Nav items */}
        <nav className="flex-1 space-y-1 p-2">
          {navItems.map((item) => (
            <button
              key={item.label}
              className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                item.active
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              } ${collapsed ? "justify-center" : ""}`}
            >
              {item.icon}
              {!collapsed && (
                <>
                  <span className="flex-1 text-left">{item.label}</span>
                  {item.badge && (
                    <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
                      {item.badge}
                    </Badge>
                  )}
                </>
              )}
            </button>
          ))}
        </nav>

        {/* Collapse toggle */}
        <div className="border-t p-2">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-center"
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <>
                <ChevronLeft className="mr-2 h-4 w-4" />
                Collapse
              </>
            )}
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 items-center justify-between border-b bg-card px-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="h-5 w-5" />
            </Button>
            <div className="relative hidden sm:block">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search..."
                className="h-9 w-64 rounded-md border bg-transparent px-9 text-sm outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-4 w-4" />
              <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500" />
            </Button>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground">
              JD
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          {/* Page header */}
          <div className="mb-6">
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Overview of your workflows, knowledge graph, and team activity.
            </p>
          </div>

          {/* KPI cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
            {loading
              ? Array.from({ length: 4 }).map((_, i) => (
                  <Card key={i}>
                    <CardHeader className="pb-2">
                      <Skeleton className="h-4 w-[100px]" />
                    </CardHeader>
                    <CardContent>
                      <Skeleton className="h-8 w-[60px] mb-2" />
                      <Skeleton className="h-3 w-[80px]" />
                    </CardContent>
                  </Card>
                ))
              : [
                  { label: "Active Workflows", value: "12", change: "+2 this week", icon: <Workflow className="h-4 w-4 text-blue-600" /> },
                  { label: "Knowledge Graph", value: "3.2k", change: "+148 nodes", icon: <Share2 className="h-4 w-4 text-green-600" /> },
                  { label: "Team Members", value: "8", change: "No change", icon: <Users className="h-4 w-4 text-purple-600" /> },
                  { label: "Avg. Processing", value: "4.2m", change: "-12% vs last week", icon: <Clock className="h-4 w-4 text-orange-600" /> },
                ].map((kpi) => (
                  <Card key={kpi.label}>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <CardDescription>{kpi.label}</CardDescription>
                      {kpi.icon}
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{kpi.value}</div>
                      <p className="text-xs text-muted-foreground mt-1">{kpi.change}</p>
                    </CardContent>
                  </Card>
                ))}
          </div>

          {/* Main grid */}
          <div className="grid gap-6 lg:grid-cols-7">
            {/* Workflow status */}
            <Card className="lg:col-span-4">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base">Recent Workflows</CardTitle>
                    <CardDescription>Latest workflow runs across your workspaces</CardDescription>
                  </div>
                  <Button variant="outline" size="sm">View all</Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {loading
                  ? Array.from({ length: 3 }).map((_, i) => (
                      <div key={i} className="flex items-center gap-4">
                        <Skeleton className="h-8 w-8 rounded-full" />
                        <div className="flex-1 space-y-1">
                          <Skeleton className="h-4 w-[200px]" />
                          <Skeleton className="h-3 w-[120px]" />
                        </div>
                        <Skeleton className="h-4 w-[60px]" />
                      </div>
                    ))
                  : [
                      { name: "CRM Data Pipeline", stage: "Entity Extraction", progress: 67, status: "Running" },
                      { name: "Quarterly Report", stage: "Completed", progress: 100, status: "Done" },
                      { name: "Graph Sync", stage: "Failed at Merge", progress: 45, status: "Failed" },
                    ].map((wf) => (
                      <div key={wf.name} className="flex items-center gap-4">
                        <div className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-medium ${
                          wf.status === "Running" ? "bg-blue-100 text-blue-700" :
                          wf.status === "Done" ? "bg-green-100 text-green-700" :
                          "bg-red-100 text-red-700"
                        }`}>
                          {wf.status === "Running" ? <Activity className="h-4 w-4" /> :
                           wf.status === "Done" ? <TrendingUp className="h-4 w-4" /> :
                           <Bell className="h-4 w-4" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{wf.name}</p>
                          <p className="text-xs text-muted-foreground">{wf.stage}</p>
                        </div>
                        <div className="w-24">
                          <Progress value={wf.progress} className="h-1.5" />
                        </div>
                      </div>
                    ))}
              </CardContent>
            </Card>

            {/* Activity feed */}
            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle className="text-base">Activity</CardTitle>
                <CardDescription>Recent events in your workspace</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {loading
                  ? Array.from({ length: 4 }).map((_, i) => (
                      <div key={i} className="flex gap-3">
                        <Skeleton className="h-6 w-6 rounded-full" />
                        <div className="flex-1 space-y-1">
                          <Skeleton className="h-3 w-full" />
                          <Skeleton className="h-3 w-[60%]" />
                        </div>
                      </div>
                    ))
                  : [
                      { user: "Alice", action: "started workflow", target: "CRM Pipeline", time: "2m ago" },
                      { user: "Bob", action: "completed", target: "Quarterly Report", time: "15m ago" },
                      { user: "Carol", action: "invited", target: "new team member", time: "1h ago" },
                      { user: "System", action: "graph sync", target: "completed", time: "2h ago" },
                    ].map((event) => (
                      <div key={event.user + event.action} className="flex gap-3">
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium">
                          {event.user[0]}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm">
                            <span className="font-medium">{event.user}</span>{" "}
                            {event.action}{" "}
                            <span className="text-muted-foreground">{event.target}</span>
                          </p>
                          <p className="text-xs text-muted-foreground">{event.time}</p>
                        </div>
                      </div>
                    ))}
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const meta: Meta<typeof DashboardLayout> = {
  title: "Pages/DashboardLayout",
  component: DashboardLayout,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    viewport: {
      defaultViewport: "desktop",
    },
  },
  argTypes: {
    sidebarCollapsed: { control: "boolean" },
    loading: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// ---------------------------------------------------------------------------
// Stories
// ---------------------------------------------------------------------------

export const Default: Story = {
  args: {
    sidebarCollapsed: false,
    loading: false,
  },
};

export const SidebarCollapsed: Story = {
  args: {
    sidebarCollapsed: true,
    loading: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Sidebar in collapsed state showing icon-only navigation.",
      },
    },
  },
};

export const Loading: Story = {
  args: {
    sidebarCollapsed: false,
    loading: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Skeleton loading state for the entire dashboard layout.",
      },
    },
  },
};

// ---------------------------------------------------------------------------
// Responsive breakpoint stories
// ---------------------------------------------------------------------------

export const Tablet: Story = {
  args: {
    sidebarCollapsed: true,
    loading: false,
  },
  parameters: {
    viewport: {
      defaultViewport: "tablet",
    },
    docs: {
      description: {
        story: "Tablet viewport: sidebar auto-collapses, grid adjusts to 2 columns.",
      },
    },
  },
};

export const Mobile: Story = {
  args: {
    sidebarCollapsed: true,
    loading: false,
  },
  parameters: {
    viewport: {
      defaultViewport: "mobile",
    },
    docs: {
      description: {
        story: "Mobile viewport: sidebar hidden behind hamburger menu, single column layout.",
      },
    },
  },
};
