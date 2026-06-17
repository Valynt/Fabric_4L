/**
 * Semantic badges shared across the core workspace views.
 */
import { cn } from "@/lib/utils";
import { Tag } from "./primitives";

function titleCase(value: string): string {
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const SIGNAL_TYPE_STYLES: Record<string, string> = {
  pain: "bg-destructive/10 text-destructive",
  buying: "bg-success/10 text-success",
  risk: "bg-warning/10 text-warning",
  budget: "bg-primary/10 text-primary",
  stakeholder: "bg-info/10 text-info",
  timeline: "bg-warning/10 text-warning",
  competitive: "bg-muted text-muted-foreground",
  metric: "bg-info/10 text-info",
};

export function SignalTypeBadge({ type }: { type?: string }) {
  if (!type) return null;
  const key = type.toLowerCase();
  return (
    <Tag className={cn(SIGNAL_TYPE_STYLES[key])}>{titleCase(type)}</Tag>
  );
}

const SIGNAL_STATUS_STYLES: Record<string, string> = {
  detected: "bg-muted text-muted-foreground",
  accepted: "bg-success/10 text-success",
  rejected: "bg-destructive/10 text-destructive",
  promoted: "bg-primary/10 text-primary",
  assumption: "bg-warning/10 text-warning",
};

export function SignalStatusBadge({ status }: { status?: string }) {
  if (!status) return null;
  const key = status.toLowerCase();
  return (
    <Tag className={cn(SIGNAL_STATUS_STYLES[key])}>{titleCase(status)}</Tag>
  );
}

const VERIFICATION_STYLES: Record<string, string> = {
  verified: "bg-success/10 text-success",
  partial: "bg-warning/10 text-warning",
  unverified: "bg-muted text-muted-foreground",
};

export function VerificationBadge({ state }: { state?: string }) {
  if (!state) return <Tag>Unverified</Tag>;
  const key = state.toLowerCase();
  return (
    <Tag className={cn(VERIFICATION_STYLES[key])}>{titleCase(state)}</Tag>
  );
}

const INFLUENCE_STYLES: Record<string, string> = {
  high: "bg-destructive/10 text-destructive",
  medium: "bg-warning/10 text-warning",
  low: "bg-muted text-muted-foreground",
};

export function InfluenceBadge({ level }: { level?: string }) {
  if (!level) return null;
  const key = level.toLowerCase();
  return (
    <Tag className={cn(INFLUENCE_STYLES[key])}>Influence: {titleCase(level)}</Tag>
  );
}

export function RoleBadge({ role }: { role?: string }) {
  if (!role) return null;
  return <Tag className="bg-primary/10 text-primary">{titleCase(role)}</Tag>;
}
