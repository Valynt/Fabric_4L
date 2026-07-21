/**
 * WorkflowDetail — Drill-down view for individual workflow instances
 * 
 * Provides rich visibility into workflow execution:
 * - Step-by-step progress visualization
 * - Tool execution log with latency
 * - Human-in-the-loop approval points
 * - Error details and retry actions
 */

import { useState } from "react";
import { 
  X, Bot, Clock, AlertTriangle, CheckCircle2, 
  Play, Pause, RotateCcw, Terminal, ChevronRight,
  Loader2
} from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { Workflow } from "@/hooks/useWorkflows";

// ── Types ────────────────────────────────────────────────────────────────────

interface WorkflowStep {
  id: string;
  label: string;
  status: "pending" | "running" | "completed" | "error" | "waiting";
  detail?: string;
  elapsedMs?: number;
  toolCalls?: ToolCall[];
}

interface ToolCall {
  id: string;
  tool: string;
  input: Record<string, unknown>;
  output?: unknown;
  status: "pending" | "running" | "success" | "error";
  latencyMs?: number;
}

interface WorkflowDetailProps {
  workflow: Workflow | null;
  isOpen: boolean;
  onClose: () => void;
  onCancel?: (id: string) => void;
  onRetry?: (id: string) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function WorkflowDetail({ 
  workflow, 
  isOpen, 
  onClose,
  onCancel,
  onRetry 
}: WorkflowDetailProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "logs" | "tools">("overview");

  if (!workflow) return null;

  const isActive = workflow.status === "running" || workflow.status === "pending";
  const isFailed = workflow.status === "failed";

  // Mock steps - in production, these come from the workflow state API
  const steps: WorkflowStep[] = [
    { id: "1", label: "Initialize", status: "completed", elapsedMs: 120 },
    { id: "2", label: "Data Ingestion", status: "completed", detail: "3 documents processed", elapsedMs: 2500 },
    { id: "3", label: "Entity Extraction", status: workflow.progress > 30 ? "completed" : "running", elapsedMs: 4500 },
    { id: "4", label: "Knowledge Graph Update", status: workflow.progress > 60 ? "completed" : workflow.progress > 30 ? "running" : "pending" },
    { id: "5", label: "Validation", status: workflow.progress >= 100 ? "completed" : "pending" },
  ];

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent className="w-[500px] sm:max-w-[500px] p-0 flex flex-col">
        {/* Header */}
        <SheetHeader className="px-6 py-4 border-b">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <SheetTitle className="text-base font-semibold flex items-center gap-2">
                <Bot size={18} className="text-primary" />
                <span className="truncate">{workflow.name}</span>
              </SheetTitle>
              <div className="flex items-center gap-2 mt-1">
                <code className="text-xs text-muted-foreground font-mono">
                  {workflow.id}
                </code>
                <StatusBadge status={workflow.status} />
              </div>
            </div>
            <div className="flex items-center gap-1">
              {isActive && onCancel && (
                <Button type="button" 
                  variant="ghost" 
                  size="sm" 
                  className="h-8 text-destructive hover:text-destructive"
                  onClick={() => onCancel(workflow.id)}
                >
                  <Pause size={14} className="mr-1" />
                  Cancel
                </Button>
              )}
              {isFailed && onRetry && (
                <Button type="button" 
                  variant="ghost" 
                  size="sm" 
                  className="h-8"
                  onClick={() => onRetry(workflow.id)}
                >
                  <RotateCcw size={14} className="mr-1" />
                  Retry
                </Button>
              )}
            </div>
          </div>
        </SheetHeader>

        {/* Progress Section */}
        <div className="px-6 py-4 bg-muted/30 border-b">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Progress</span>
            <span className="text-sm text-muted-foreground">{workflow.progress}%</span>
          </div>
          <Progress value={workflow.progress} className="h-2" />
          <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Clock size={12} />
              <span>Started {workflow.createdAt ? new Date(workflow.createdAt).toLocaleString() : "—"}</span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b px-6">
          {(["overview", "logs", "tools"] as const).map((tab) => (
            <button type="button"
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-3 text-sm font-medium capitalize border-b-2 -mb-px transition-colors",
                activeTab === tab 
                  ? "border-primary text-primary" 
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <ScrollArea className="flex-1 px-6 py-4">
          {activeTab === "overview" && (
            <div className="space-y-4">
              <h4 className="text-sm font-medium">Execution Steps</h4>
              <div className="space-y-2">
                {steps.map((step, idx) => (
                  <StepRow 
                    key={step.id} 
                    step={step} 
                    isLast={idx === steps.length - 1}
                  />
                ))}
              </div>
            </div>
          )}

          {activeTab === "logs" && (
            <div className="space-y-3">
              <LogEntry level="info" message="Workflow initialized" timestamp="10:23:45" />
              <LogEntry level="info" message="Connected to data source" timestamp="10:23:46" />
              <LogEntry level="success" message="Ingested 3 documents (2.4MB)" timestamp="10:23:48" />
              <LogEntry level="info" message="Starting entity extraction" timestamp="10:23:50" />
              <LogEntry level="info" message="Extracted 47 entities from document_1.pdf" timestamp="10:24:02" />
              <LogEntry level="info" message="Extracted 23 entities from document_2.pdf" timestamp="10:24:15" />
              {workflow.progress < 100 && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 size={14} className="animate-spin" />
                  <span className="text-sm">Processing...</span>
                </div>
              )}
            </div>
          )}

          {activeTab === "tools" && (
            <div className="space-y-3">
              <ToolCallRow 
                call={{
                  id: "1",
                  tool: "document_parser",
                  input: { source: "s3://bucket/doc.pdf" },
                  output: { pages: 12, text_length: 4500 },
                  status: "success",
                  latencyMs: 450
                }} 
              />
              <ToolCallRow 
                call={{
                  id: "2",
                  tool: "entity_extractor",
                  input: { text: "...", model: "gpt-4" },
                  output: { entities: 47 },
                  status: "success",
                  latencyMs: 3200
                }} 
              />
              {workflow.progress < 60 && (
                <ToolCallRow 
                  call={{
                    id: "3",
                    tool: "knowledge_graph_update",
                    input: { entities: 47 },
                    status: "running",
                  }} 
                />
              )}
            </div>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StepRow({ step, isLast }: { step: WorkflowStep; isLast: boolean }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex flex-col items-center">
        <StepIcon status={step.status} />
        {!isLast && <div className="w-px h-6 bg-border mt-1" />}
      </div>
      <div className="flex-1 pb-4">
        <div className="flex items-center gap-2">
          <span className={cn(
            "text-sm font-medium",
            step.status === "completed" && "text-muted-foreground line-through",
            step.status === "running" && "text-primary"
          )}>
            {step.label}
          </span>
          {step.status === "running" && (
            <Loader2 size={14} className="animate-spin text-primary" />
          )}
        </div>
        {step.detail && (
          <p className="text-xs text-muted-foreground mt-0.5">{step.detail}</p>
        )}
        {step.elapsedMs && step.status === "completed" && (
          <span className="vf-text-micro text-muted-foreground">
            {(step.elapsedMs / 1000).toFixed(1)}s
          </span>
        )}
      </div>
    </div>
  );
}

function StepIcon({ status }: { status: WorkflowStep["status"] }) {
  const icons = {
    pending: <CircleIcon className="text-muted-foreground/50" />,
    running: <Loader2 size={16} className="animate-spin text-primary" />,
    completed: <CheckCircle2 size={16} className="text-success" />,
    error: <AlertTriangle size={16} className="text-destructive" />,
    waiting: <Pause size={16} className="text-warning" />,
  };
  return <div className="w-5 h-5 flex items-center justify-center">{icons[status]}</div>;
}

function CircleIcon({ className }: { className?: string }) {
  return (
    <div className={cn("w-3 h-3 rounded-full border-2 border-current", className)} />
  );
}

function LogEntry({ 
  level, 
  message, 
  timestamp 
}: { 
  level: "info" | "success" | "warning" | "error";
  message: string;
  timestamp: string;
}) {
  const colors = {
    info: "text-primary bg-primary/10",
    success: "text-success bg-success/10",
    warning: "text-warning bg-warning/10",
    error: "text-destructive bg-destructive/10",
  };

  return (
    <div className="flex items-start gap-2 text-sm">
      <span className="text-xs text-muted-foreground font-mono w-16 shrink-0">
        {timestamp}
      </span>
      <Badge variant="secondary" className={cn("vf-text-micro px-1.5 py-0 h-5", colors[level])}>
        {level}
      </Badge>
      <span className="text-muted-foreground">{message}</span>
    </div>
  );
}

function ToolCallRow({ call }: { call: ToolCall }) {
  const [expanded, setExpanded] = useState(false);

  const statusIcons = {
    pending: <CircleIcon className="text-muted-foreground/50" />,
    running: <Loader2 size={14} className="animate-spin text-primary" />,
    success: <CheckCircle2 size={14} className="text-success" />,
    error: <AlertTriangle size={14} className="text-destructive" />,
  };

  return (
    <div className="border rounded-lg overflow-hidden">
      <button type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 p-3 hover:bg-muted/50 transition-colors"
      >
        {statusIcons[call.status]}
        <code className="text-sm font-mono">{call.tool}</code>
        {call.latencyMs && (
          <span className="text-xs text-muted-foreground ml-auto">
            {call.latencyMs}ms
          </span>
        )}
        <ChevronRight 
          size={14} 
          className={cn("ml-2 transition-transform", expanded && "rotate-90")}
        />
      </button>
      {expanded && (
        <div className="px-3 pb-3 border-t bg-muted/30">
          <div className="pt-2 space-y-2">
            <div>
              <span className="text-xs font-medium text-muted-foreground">Input:</span>
              <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-auto">
                {`${JSON.stringify(call.input, null, 2)}`}
              </pre>
            </div>
            {call.output !== undefined && (
              <div>
                <span className="text-xs font-medium text-muted-foreground">Output:</span>
                <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-auto">
                  {`${JSON.stringify(call.output, null, 2)}`}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, { color: string; label: string }> = {
    running: { color: "bg-primary/10 text-primary", label: "Running" },
    pending: { color: "bg-warning/10 text-warning", label: "Pending" },
    completed: { color: "bg-success/10 text-success", label: "Completed" },
    failed: { color: "bg-destructive/10 text-destructive", label: "Failed" },
    cancelled: { color: "bg-muted text-muted-foreground", label: "Cancelled" },
  };

  const { color, label } = variants[status] || { color: "bg-muted", label: status };

  return (
    <span className={cn("px-2 py-0.5 rounded text-xs font-medium", color)}>
      {label}
    </span>
  );
}

export default WorkflowDetail;
