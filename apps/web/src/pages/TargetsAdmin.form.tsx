/**
 * TargetFormPanel — Create / Edit form for a scraping target.
 * Uses React Hook Form with Zod validation.
 */
import { useEffect } from 'react';
import { useForm, Controller, type UseFormProps } from 'react-hook-form';
import { z } from 'zod';
import { standardSchemaResolver } from '@hookform/resolvers/standard-schema';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { useTarget, useCreateTarget, useUpdateTarget, type Target, type CreateTargetRequest } from '@/hooks/useTargets';

// ── Schema ────────────────────────────────────────────────────────────────────

const schema = z.object({
  name: z.string().min(1, 'Name is required').max(255),
  url: z.string().url('Must be a valid URL'),
  urlPattern: z.string().optional(),
  targetType: z.enum(['SINGLE_PAGE', 'PAGINATED', 'SPIDER', 'API_ENDPOINT']),
  sourceCategory: z.string().optional(),
  description: z.string().optional(),
  crawlPath: z.enum(['fast', 'browser', 'fast_fallback']),
  tags: z.string().optional(), // comma-separated
  scheduleEnabled: z.boolean(),
  cronExpression: z.string().optional(),
  timezone: z.string().optional(),
  requestsPerSecond: z.coerce.number().min(0).optional(),
  requestsPerMinute: z.coerce.number().min(0).optional(),
  retryAttempts: z.coerce.number().min(0).max(10).optional(),
  respectRobotsTxt: z.boolean(),
  piiRedaction: z.boolean(),
  crawlDelaySeconds: z.coerce.number().min(0).optional(),
  authType: z.enum(['NONE', 'BEARER', 'API_KEY', 'BASIC', 'OAUTH2']),
  credentialsRef: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

// ── Helpers ───────────────────────────────────────────────────────────────────

function targetToForm(t: Target): FormValues {
  const schedule = t.schedule as Record<string, unknown> | null;
  const rateLimit = t.rateLimit as Record<string, unknown>;
  const compliance = t.compliance as Record<string, unknown>;
  return {
    name: t.name,
    url: t.url,
    urlPattern: t.urlPattern ?? '',
    targetType: t.targetType,
    sourceCategory: t.sourceCategory ?? '',
    description: t.description ?? '',
    crawlPath: t.crawlPath,
    tags: t.tags.join(', '),
    scheduleEnabled: Boolean(schedule?.enabled),
    cronExpression: String(schedule?.cron_expression ?? ''),
    timezone: String(schedule?.timezone ?? 'UTC'),
    requestsPerSecond: Number(rateLimit?.requests_per_second ?? 1),
    requestsPerMinute: Number(rateLimit?.requests_per_minute ?? 30),
    retryAttempts: Number(rateLimit?.retry_attempts ?? 3),
    respectRobotsTxt: Boolean(compliance?.respect_robots_txt ?? true),
    piiRedaction: Boolean(compliance?.pii_redaction_enabled ?? true),
    crawlDelaySeconds: Number(compliance?.crawl_delay_seconds ?? 1),
    authType: (t.authentication?.type ?? 'NONE') as FormValues['authType'],
    credentialsRef: t.authentication?.credentials_ref ?? '',
  };
}

function formToRequest(v: FormValues): CreateTargetRequest {
  return {
    name: v.name,
    url: v.url,
    urlPattern: v.urlPattern || undefined,
    targetType: v.targetType,
    sourceCategory: v.sourceCategory as CreateTargetRequest['sourceCategory'] || undefined,
    description: v.description || undefined,
    crawlPath: v.crawlPath,
    tags: v.tags ? v.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
    schedule: {
      enabled: v.scheduleEnabled,
      cron_expression: v.cronExpression || undefined,
      timezone: v.timezone || 'UTC',
    },
    rateLimit: {
      requests_per_second: v.requestsPerSecond,
      requests_per_minute: v.requestsPerMinute,
      retry_attempts: v.retryAttempts,
    },
    compliance: {
      respect_robots_txt: v.respectRobotsTxt,
      pii_redaction_enabled: v.piiRedaction,
      crawl_delay_seconds: v.crawlDelaySeconds,
    },
    authentication: v.authType !== 'NONE'
      ? { type: v.authType, credentials_ref: v.credentialsRef || undefined }
      : null,
  };
}

// ── Field helpers ─────────────────────────────────────────────────────────────

function FieldRow({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="vf-text-body-m">{label}</Label>
      {children}
      {error && <p className="vf-text-body-s text-destructive">{error}</p>}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider mt-5 mb-3">{children}</p>;
}

// ── Component ─────────────────────────────────────────────────────────────────

const BASE_DEFAULTS: Partial<FormValues> = {
  targetType: 'SINGLE_PAGE',
  crawlPath: 'browser',
  scheduleEnabled: false,
  respectRobotsTxt: true,
  piiRedaction: true,
  authType: 'NONE',
  crawlDelaySeconds: 1,
  retryAttempts: 3,
  requestsPerSecond: 1,
  requestsPerMinute: 30,
};

interface Props {
  targetId: string | null;
  onSuccess: (target: Target) => void;
  onCancel: () => void;
}

export function TargetFormPanel({ targetId, onSuccess, onCancel }: Props) {
  const { data: existing, isLoading: loadingExisting } = useTarget(targetId);
  const createTarget = useCreateTarget();
  const updateTarget = useUpdateTarget();

  const { register, handleSubmit, control, reset, watch, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: standardSchemaResolver(schema),
    defaultValues: existing ? targetToForm(existing) : BASE_DEFAULTS,
  } as UseFormProps<FormValues>);

  useEffect(() => {
    if (existing) reset(targetToForm(existing));
  }, [existing, reset]);

  const scheduleEnabled = watch('scheduleEnabled');
  const authType = watch('authType');
  const isMutating = createTarget.isPending || updateTarget.isPending;

  const onSubmit = async (values: FormValues) => {
    const request = formToRequest(values);
    try {
      let result: Target;
      if (targetId && existing) {
        result = await updateTarget.mutateAsync({ id: targetId, ...request });
      } else {
        result = await createTarget.mutateAsync(request);
      }
      onSuccess(result);
    } catch (err) {
      // Error toast handled by hook; form stays open for correction
    }
  };

  if (targetId && loadingExisting) {
    return <div className="space-y-3">{[...Array(5)].map((_, i) => <div key={i} className="h-10 bg-muted rounded animate-pulse" />)}</div>;
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pb-6">
      {/* Identity */}
      <SectionTitle>Identity</SectionTitle>
      <FieldRow label="Name *" error={errors.name?.message}>
        <Input {...register('name')} placeholder="e.g. Acme Corp Careers" className="h-8 vf-text-body-m" />
      </FieldRow>
      <FieldRow label="URL *" error={errors.url?.message}>
        <Input {...register('url')} placeholder="https://example.com" className="h-8 vf-text-body-m" />
      </FieldRow>
      <FieldRow label="URL Pattern" error={errors.urlPattern?.message}>
        <Input {...register('urlPattern')} placeholder="Regex (optional)" className="h-8 vf-text-body-m font-mono" />
      </FieldRow>
      <div className="grid grid-cols-2 gap-3">
        <FieldRow label="Target Type *" error={errors.targetType?.message}>
          <Controller name="targetType" control={control} render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger className="h-8 vf-text-body-m"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="SINGLE_PAGE">Single Page</SelectItem>
                <SelectItem value="PAGINATED">Paginated</SelectItem>
                <SelectItem value="SPIDER">Spider</SelectItem>
                <SelectItem value="API_ENDPOINT">API Endpoint</SelectItem>
              </SelectContent>
            </Select>
          )} />
        </FieldRow>
        <FieldRow label="Crawl Path" error={errors.crawlPath?.message}>
          <Controller name="crawlPath" control={control} render={({ field }) => (
            <Select value={field.value} onValueChange={field.onChange}>
              <SelectTrigger className="h-8 vf-text-body-m"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="fast">Fast (HTTPX)</SelectItem>
                <SelectItem value="browser">Browser (Playwright)</SelectItem>
                <SelectItem value="fast_fallback">Fast with fallback</SelectItem>
              </SelectContent>
            </Select>
          )} />
        </FieldRow>
      </div>
      <FieldRow label="Source Category">
        <Controller name="sourceCategory" control={control} render={({ field }) => (
          <Select value={field.value ?? ''} onValueChange={field.onChange}>
            <SelectTrigger className="h-8 vf-text-body-m"><SelectValue placeholder="Select category" /></SelectTrigger>
            <SelectContent>
              {['API','CRM','ERP','HRIS','MARKETING','FINANCE','PRODUCT','SUPPORT','GENERAL'].map(c => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
      </FieldRow>
      <FieldRow label="Description">
        <Textarea {...register('description')} placeholder="Optional description" className="vf-text-body-m min-h-[60px] resize-none" />
      </FieldRow>
      <FieldRow label="Tags (comma-separated)">
        <Input {...register('tags')} placeholder="prospect, competitor, licensing" className="h-8 vf-text-body-m" />
      </FieldRow>

      <Separator />

      {/* Schedule */}
      <SectionTitle>Schedule</SectionTitle>
      <div className="flex items-center justify-between">
        <Label className="vf-text-body-m">Enable schedule</Label>
        <Controller name="scheduleEnabled" control={control} render={({ field }) => (
          <Switch checked={field.value} onCheckedChange={field.onChange} aria-label="Enable schedule" />
        )} />
      </div>
      {scheduleEnabled && (
        <>
          <FieldRow label="Cron expression" error={errors.cronExpression?.message}>
            <Input {...register('cronExpression')} placeholder="0 0 * * *" className="h-8 vf-text-body-m font-mono" />
          </FieldRow>
          <FieldRow label="Timezone">
            <Input {...register('timezone')} placeholder="UTC" className="h-8 vf-text-body-m" />
          </FieldRow>
        </>
      )}

      <Separator />

      {/* Rate Limits */}
      <SectionTitle>Rate Limits</SectionTitle>
      <div className="grid grid-cols-3 gap-3">
        <FieldRow label="Req/sec">
          <Input {...register('requestsPerSecond')} type="number" min={0} className="h-8 vf-text-body-m" />
        </FieldRow>
        <FieldRow label="Req/min">
          <Input {...register('requestsPerMinute')} type="number" min={0} className="h-8 vf-text-body-m" />
        </FieldRow>
        <FieldRow label="Retries">
          <Input {...register('retryAttempts')} type="number" min={0} max={10} className="h-8 vf-text-body-m" />
        </FieldRow>
      </div>

      <Separator />

      {/* Compliance */}
      <SectionTitle>Compliance</SectionTitle>
      <div className="flex items-center justify-between">
        <Label className="vf-text-body-m">Respect robots.txt</Label>
        <Controller name="respectRobotsTxt" control={control} render={({ field }) => (
          <Switch checked={field.value} onCheckedChange={field.onChange} />
        )} />
      </div>
      <div className="flex items-center justify-between">
        <Label className="vf-text-body-m">PII redaction</Label>
        <Controller name="piiRedaction" control={control} render={({ field }) => (
          <Switch checked={field.value} onCheckedChange={field.onChange} />
        )} />
      </div>
      <FieldRow label="Crawl delay (seconds)">
        <Input {...register('crawlDelaySeconds')} type="number" min={0} className="h-8 vf-text-body-m" />
      </FieldRow>

      <Separator />

      {/* Authentication */}
      <SectionTitle>Authentication</SectionTitle>
      <FieldRow label="Auth type">
        <Controller name="authType" control={control} render={({ field }) => (
          <Select value={field.value} onValueChange={field.onChange}>
            <SelectTrigger className="h-8 vf-text-body-m"><SelectValue /></SelectTrigger>
            <SelectContent>
              {['NONE','BEARER','API_KEY','BASIC','OAUTH2'].map(t => (
                <SelectItem key={t} value={t}>{t}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )} />
      </FieldRow>
      {authType !== 'NONE' && (
        <FieldRow label="Credentials reference">
          <Input {...register('credentialsRef')} placeholder="secret_manager_key" className="h-8 vf-text-body-m font-mono" />
        </FieldRow>
      )}

      {/* Footer actions */}
      <div className="flex items-center gap-3 pt-4 border-t border-border">
        <Button type="button" variant="outline" onClick={onCancel} className="flex-1 h-8 vf-text-body-m">Cancel</Button>
        <Button type="submit" disabled={isSubmitting || isMutating} className="flex-1 h-8 vf-text-body-m">
          {(isSubmitting || isMutating) && <Loader2 size={13} className="mr-1.5 animate-spin" />}
          {targetId ? 'Save changes' : 'Create target'}
        </Button>
      </div>
    </form>
  );
}
