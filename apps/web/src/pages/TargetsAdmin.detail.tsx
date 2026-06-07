/**
 * TargetDetailPanel — Right-rail detail view for a scraping target.
 * Shows identity, config sections, job history, and live run status.
 */
import { useEffect, useRef } from 'react';
import { Edit3, Play, ExternalLink, Clock, CheckCircle2, XCircle, Loader2, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { useTarget, useTargetJobs, useExecuteTarget } from '@/hooks/useTargets';
import { toast } from 'sonner';

interface Props {
  targetId: string;
  onEdit: () => void;
  onClose: () => void;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <p className="vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider mb-2">{title}</p>
      {children}
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5 vf-text-body-m">
      <span className="text-muted-foreground shrink-0 w-36">{label}</span>
      <span className="text-foreground text-right break-all">{value ?? '—'}</span>
    </div>
  );
}

function JobStatusIcon({ status }: { status: string }) {
  if (status === 'COMPLETED') return <CheckCircle2 size={13} className="text-success" />;
  if (status === 'FAILED') return <XCircle size={13} className="text-destructive" />;
  if (['PENDING', 'QUEUED', 'RUNNING', 'NAVIGATING', 'EXTRACTING'].includes(status))
    return <Loader2 size={13} className="text-primary animate-spin" />;
  return <Clock size={13} className="text-muted-foreground" />;
}

export function TargetDetailPanel({ targetId, onEdit, onClose }: Props) {
  const { data: target, isLoading } = useTarget(targetId);
  const { data: jobsData, isLoading: jobsLoading, refetch: refetchJobs } = useTargetJobs(targetId);
  const executeTarget = useExecuteTarget();

  // Poll for live status if any job is running
  const jobs = (jobsData?.jobs ?? []) as Array<Record<string, unknown>>;
  const hasRunning = jobs.some(j => ['PENDING', 'QUEUED', 'RUNNING', 'NAVIGATING', 'EXTRACTING', 'TRANSFORMING', 'STORING'].includes(String(j.status)));
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (hasRunning) {
      pollRef.current = setInterval(() => refetchJobs(), 5000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [hasRunning, refetchJobs]);

  const handleRun = async () => {
    try {
      await executeTarget.mutateAsync({ id: targetId });
      toast.success('Crawl job queued');
      setTimeout(() => refetchJobs(), 1000);
    } catch {
      toast.error('Failed to queue job');
    }
  };

  if (isLoading) {
    return <div className="space-y-3">{[...Array(6)].map((_, i) => <Skeleton key={i} className="h-8 rounded" />)}</div>;
  }

  if (!target) {
    return <p className="vf-text-body-m text-muted-foreground">Target not found.</p>;
  }

  const schedule = target.schedule as Record<string, unknown> | null;
  const scheduleEnabled = Boolean(schedule?.enabled);
  const rateLimit = target.rateLimit as Record<string, unknown>;
  const compliance = target.compliance as Record<string, unknown>;
  const auth = target.authentication;

  return (
    <div className="space-y-1">
      {/* Actions */}
      <div className="flex items-center gap-2 mb-4">
        <Button size="sm" variant="outline" onClick={onEdit} className="h-7 vf-text-body-s">
          <Edit3 size={12} className="mr-1.5" />Edit
        </Button>
        {target.status === 'ACTIVE' && (
          <Button size="sm" variant="outline" onClick={handleRun} disabled={executeTarget.isPending} className="h-7 vf-text-body-s">
            {executeTarget.isPending ? <Loader2 size={12} className="mr-1.5 animate-spin" /> : <Play size={12} className="mr-1.5" />}
            Run now
          </Button>
        )}
        <a href={target.url} target="_blank" rel="noopener noreferrer" className="ml-auto">
          <Button size="sm" variant="ghost" className="h-7 vf-text-body-s">
            <ExternalLink size={12} className="mr-1.5" />Open URL
          </Button>
        </a>
      </div>

      <Separator className="mb-4" />

      {/* Identity */}
      <Section title="Identity">
        <Field label="Name" value={target.name} />
        <Field label="Description" value={target.description} />
        <Field label="URL" value={<span className="font-mono vf-text-caption break-all">{target.url}</span>} />
        {target.urlPattern && <Field label="URL Pattern" value={<span className="font-mono vf-text-caption">{target.urlPattern}</span>} />}
        <Field label="Type" value={<Badge variant="outline" className="vf-text-caption">{target.targetType}</Badge>} />
        <Field label="Category" value={target.sourceCategory} />
        <Field label="Crawl Path" value={target.crawlPath} />
        <Field label="Status" value={target.status} />
        <Field label="Tags" value={
          target.tags.length > 0
            ? <div className="flex flex-wrap gap-1 justify-end">{target.tags.map(t => <Badge key={t} variant="secondary" className="vf-text-micro">{t}</Badge>)}</div>
            : '—'
        } />
        <Field label="Created" value={new Date(target.createdAt).toLocaleDateString()} />
        <Field label="Last success" value={target.lastSuccessAt ? new Date(target.lastSuccessAt).toLocaleString() : '—'} />
      </Section>

      <Separator className="my-3" />

      {/* Schedule */}
      <Section title="Schedule">
        <Field label="Enabled" value={scheduleEnabled ? 'Yes' : 'No'} />
        {scheduleEnabled && (
          <>
            <Field label="Cron" value={<span className="font-mono vf-text-caption">{String(schedule?.cron_expression ?? '—')}</span>} />
            <Field label="Timezone" value={String(schedule?.timezone ?? 'UTC')} />
          </>
        )}
      </Section>

      <Separator className="my-3" />

      {/* Rate Limits */}
      <Section title="Rate Limits">
        <Field label="Req / second" value={String(rateLimit?.requests_per_second ?? '—')} />
        <Field label="Req / minute" value={String(rateLimit?.requests_per_minute ?? '—')} />
        <Field label="Retry attempts" value={String(rateLimit?.retry_attempts ?? '—')} />
        <Field label="Backoff" value={String(rateLimit?.retry_backoff ?? '—')} />
      </Section>

      <Separator className="my-3" />

      {/* Compliance */}
      <Section title="Compliance">
        <Field label="Respect robots.txt" value={compliance?.respect_robots_txt ? 'Yes' : 'No'} />
        <Field label="PII redaction" value={compliance?.pii_redaction_enabled ? 'Enabled' : 'Disabled'} />
        <Field label="Crawl delay (s)" value={String(compliance?.crawl_delay_seconds ?? '—')} />
      </Section>

      <Separator className="my-3" />

      {/* Authentication */}
      <Section title="Authentication">
        <Field label="Type" value={auth?.type ?? 'NONE'} />
        {auth?.credentials_ref && <Field label="Credentials ref" value="••••••••" />}
      </Section>

      <Separator className="my-3" />

      {/* Job History */}
      <Section title="Recent Jobs">
        <div className="flex items-center justify-between mb-2">
          <span />
          <Button size="sm" variant="ghost" onClick={() => refetchJobs()} className="h-6 vf-text-caption px-2">
            <RefreshCw size={11} className={cn('mr-1', jobsLoading && 'animate-spin')} />Refresh
          </Button>
        </div>
        {jobsLoading ? (
          <div className="space-y-1.5">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 rounded" />)}</div>
        ) : jobs.length === 0 ? (
          <p className="vf-text-body-s text-muted-foreground py-2">No jobs yet.</p>
        ) : (
          <div className="space-y-1">
            {jobs.map((job, i) => (
              <div key={String(job.id ?? i)} className="flex items-center gap-2 py-1.5 vf-text-body-s">
                <JobStatusIcon status={String(job.status)} />
                <span className="text-muted-foreground capitalize">{String(job.status).toLowerCase().replace(/_/g, ' ')}</span>
                <span className="ml-auto text-muted-foreground">
                  {job.created_at ? new Date(String(job.created_at)).toLocaleDateString() : ''}
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Live run status */}
      {hasRunning && (
        <>
          <Separator className="my-3" />
          <Section title="Live Run Status">
            <div className="flex items-center gap-2 vf-text-body-m text-primary">
              <Loader2 size={14} className="animate-spin" />
              <span>Crawl in progress — polling every 5s</span>
            </div>
          </Section>
        </>
      )}
    </div>
  );
}
