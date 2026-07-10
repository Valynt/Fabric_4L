/**
 * WorkflowCard Stories — Domain Component
 * =========================================
 *
 * Covers workflow status cards used throughout the application:
 *   - Running (with progress indicator)
 *   - Completed (success state)
 *   - Failed (error state with retry action)
 *   - Pending (queued / waiting state)
 *   - Cancelled (user-stopped state)
 *
 * DESIGN.md § Domain: "Encapsulates product behavior for formula workflows"
 * DESIGN.md § State: "Explicit loading, empty, error, and success states"
 */

import type { Meta, StoryObj } from "@storybook/react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  RotateCcw,
  Ban,
  MoreHorizontal,
  ArrowRight,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Mock WorkflowCard component (production version lives in
// src/components/domain/WorkflowCard.tsx)
// ---------------------------------------------------------------------------

interface WorkflowCardProps {
  id: string;
  name: string;
  status: "running" | "completed" | "failed" | "pending" | "cancelled";
  progress?: number;
  stage?: string;
  lastUpdated: string;
  errorMessage?: string;
  onRetry?: () => void;
  onView?: () => void;
  onCancel?: () => void;
}

function WorkflowCard({
  name,
  status,
  progress = 0,
  stage,
  lastUpdated,
  errorMessage,
  onRetry,
  onView,
  onCancel,
}: WorkflowCardProps) {
  const statusConfig = {
    running: {
      badge: <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">Running</Badge>,
      icon: <Play className="h-4 w-4 text-blue-600 animate-pulse" />,
      border: "border-blue-200",
    },
    completed: {
      badge: <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Completed</Badge>,
      icon: <CheckCircle2 className="h-4 w-4 text-green-600" />,
      border: "border-green-200",
    },
    failed: {
      badge: <Badge className="bg-red-100 text-red-800 hover:bg-red-100">Failed</Badge>,
      icon: <XCircle className="h-4 w-4 text-red-600" />,
      border: "border-red-200",
    },
    pending: {
      badge: <Badge variant="outline">Pending</Badge>,
      icon: <Clock className="h-4 w-4 text-muted-foreground" />,
      border: "border-dashed",
    },
    cancelled: {
      badge: <Badge className="bg-gray-100 text-gray-800 hover:bg-gray-100">Cancelled</Badge>,
      icon: <Ban className="h-4 w-4 text-gray-500" />,
      border: "border-gray-200",
    },
  };

  const config = statusConfig[status];

  return (
    <Card className={`w-[400px] ${config.border}`}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            {config.icon}
            <div>
              <CardTitle className="text-base leading-tight">{name}</CardTitle>
              <CardDescription className="text-xs">{lastUpdated}</CardDescription>
            </div>
          </div>
          {config.badge}
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        {status === "running" && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{stage}</span>
              <span className="font-medium">{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}
        {status === "failed" && errorMessage && (
          <div className="flex items-start gap-2 rounded-md bg-red-50 p-3 dark:bg-red-950/20">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
            <p className="text-sm text-red-700 dark:text-red-300">{errorMessage}</p>
          </div>
        )}
        {status === "pending" && (
          <p className="text-sm text-muted-foreground">
            Waiting for available worker. Estimated start: ~2 min.
          </p>
        )}
        {status === "completed" && (
          <p className="text-sm text-muted-foreground">
            All stages completed successfully. Output available in the knowledge graph.
          </p>
        )}
        {status === "cancelled" && (
          <p className="text-sm text-muted-foreground">
            Workflow was stopped by the user. Partial results may be available.
          </p>
        )}
      </CardContent>
      <CardFooter className="flex justify-between pt-0">
        <div className="flex gap-2">
          {status === "failed" && (
            <Button variant="outline" size="sm" onClick={onRetry}>
              <RotateCcw className="mr-2 h-3 w-3" />
              Retry
            </Button>
          )}
          {status === "running" && (
            <Button variant="outline" size="sm" onClick={onCancel}>
              <Ban className="mr-2 h-3 w-3" />
              Cancel
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="secondary" onClick={onView}>
            View <ArrowRight className="ml-2 h-3 w-3" />
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const meta: Meta<typeof WorkflowCard> = {
  title: "Domain/WorkflowCard",
  component: WorkflowCard,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
  },
  argTypes: {
    status: {
      control: "select",
      options: ["running", "completed", "failed", "pending", "cancelled"],
    },
    progress: {
      control: { type: "range", min: 0, max: 100, step: 1 },
    },
    onRetry: { action: "retry" },
    onView: { action: "view" },
    onCancel: { action: "cancel" },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// ---------------------------------------------------------------------------
// Status stories
// ---------------------------------------------------------------------------

export const Running: Story = {
  args: {
    id: "wf-001",
    name: "CRM Data Pipeline",
    status: "running",
    progress: 67,
    stage: "Entity Extraction",
    lastUpdated: "Updated 30s ago",
  },
};

export const Completed: Story = {
  args: {
    id: "wf-002",
    name: "Quarterly Value Report",
    status: "completed",
    progress: 100,
    lastUpdated: "Finished 2h ago",
  },
};

export const Failed: Story = {
  args: {
    id: "wf-003",
    name: "Knowledge Graph Sync",
    status: "failed",
    progress: 45,
    stage: "Graph Merge",
    lastUpdated: "Failed 15m ago",
    errorMessage:
      "Neo4j connection timeout after 30s. Check the database health dashboard.",
  },
};

export const Pending: Story = {
  args: {
    id: "wf-004",
    name: "Benchmark Evaluation",
    status: "pending",
    lastUpdated: "Queued 5m ago",
  },
};

export const Cancelled: Story = {
  args: {
    id: "wf-005",
    name: "Ad-hoc Data Pull",
    status: "cancelled",
    progress: 12,
    stage: "Data Download",
    lastUpdated: "Cancelled 1h ago",
  },
};

// ---------------------------------------------------------------------------
// Interactive: progress animation
// ---------------------------------------------------------------------------

export const ProgressDemo: Story = {
  parameters: {
    controls: { disable: true },
    docs: {
      description: {
        story:
          "Interactive demo showing the running state at various progress levels.",
      },
    },
  },
  render: () => (
    <div className="flex flex-col gap-4">
      <WorkflowCard
        id="wf-p0"
        name="Progress: 0%"
        status="running"
        progress={0}
        stage="Initializing"
        lastUpdated="Just now"
      />
      <WorkflowCard
        id="wf-p25"
        name="Progress: 25%"
        status="running"
        progress={25}
        stage="Data Ingestion"
        lastUpdated="1m ago"
      />
      <WorkflowCard
        id="wf-p50"
        name="Progress: 50%"
        status="running"
        progress={50}
        stage="Signal Extraction"
        lastUpdated="3m ago"
      />
      <WorkflowCard
        id="wf-p75"
        name="Progress: 75%"
        status="running"
        progress={75}
        stage="Graph Construction"
        lastUpdated="5m ago"
      />
      <WorkflowCard
        id="wf-p100"
        name="Progress: 100%"
        status="running"
        progress={100}
        stage="Finalizing"
        lastUpdated="6m ago"
      />
    </div>
  ),
};

// ---------------------------------------------------------------------------
// Composition: workflow list
// ---------------------------------------------------------------------------

export const WorkflowList: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="flex flex-col gap-3 w-[440px]">
      <WorkflowCard
        id="wf-001"
        name="CRM Data Pipeline"
        status="running"
        progress={67}
        stage="Entity Extraction"
        lastUpdated="Updated 30s ago"
      />
      <WorkflowCard
        id="wf-002"
        name="Quarterly Value Report"
        status="completed"
        lastUpdated="Finished 2h ago"
      />
      <WorkflowCard
        id="wf-003"
        name="Knowledge Graph Sync"
        status="failed"
        lastUpdated="Failed 15m ago"
        errorMessage="Neo4j connection timeout"
      />
      <WorkflowCard
        id="wf-004"
        name="Benchmark Evaluation"
        status="pending"
        lastUpdated="Queued 5m ago"
      />
    </div>
  ),
};

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

export const Loading: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <Card className="w-[400px]">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <Skeleton className="h-5 w-[200px]" />
            <Skeleton className="h-3 w-[120px]" />
          </div>
          <Skeleton className="h-5 w-[70px]" />
        </div>
      </CardHeader>
      <CardContent className="pb-3 space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-2 w-full" />
      </CardContent>
      <CardFooter className="pt-0 flex justify-end">
        <Skeleton className="h-8 w-[80px]" />
      </CardFooter>
    </Card>
  ),
};
