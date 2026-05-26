/**
 * Extraction Engine — Configuration-driven extraction pipeline
 * 
 * Design: Refined Enterprise SaaS
 * Layout: Configuration Panel | Control Bar + Live Stream + Results Table
 */
import { useEffect, useState, useMemo } from "react";
import { Pause, Play, Settings2, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useExtractionConfig } from "@/hooks/useExtractionConfig";
import { useRunExtraction } from "@/hooks/useRunExtraction";
import { useExtractionResults, useExtractedEntities } from "@/hooks/useExtractionResults";
import { useJobStream } from "@/hooks/useJobStream";
import { createFeatureLogger } from "@/lib/telemetry";
import { usePauseAllExtractions } from "@/hooks/usePauseAllExtractions";
import { toast } from "sonner";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, DataTable, Btn, StatusBadge } from "@/components/ui/fabric";

const log = createFeatureLogger('ExtractionEngine');

// Types for log entries
type LogType = 'sys' | 'info' | 'warn' | 'extract' | 'map' | 'plain';
interface StreamLog {
  timestamp: string;
  level: string;
  message: string;
}

// Constants for log level mapping
const LOG_LEVEL_MAP: Record<string, LogType> = {
  'error': 'warn',
  'warning': 'warn',
  'warn': 'warn',
  'info': 'info',
  'debug': 'sys',
  'extract': 'extract',
  'map': 'map',
};

const TYPE_COLORS: Record<string, string> = {
  sys: 'text-neutral-400',
  info: 'text-cyan-400',
  warn: 'text-amber-400',
  extract: 'text-neutral-300',
  map: 'text-neutral-300',
  plain: 'text-neutral-400',
};

const TYPE_LABELS: Record<string, string> = {
  sys: '[SYS]', info: '[INFO]', warn: '[WARN]', extract: '[EXTRACT]', map: '[MAP]', plain: '',
};

/** Map log level string to display type */
function mapLogType(level: string): LogType {
  return LOG_LEVEL_MAP[level?.toLowerCase()] || 'plain';
}

export default function ExtractionEngine() {
  // Local state for active job
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [visibleLogLines, setVisibleLogLines] = useState(50);

  // Config store
  const config = useExtractionConfig();

  // Mutations
  const runExtraction = useRunExtraction();
  const pauseAllExtractions = usePauseAllExtractions();

  // Queries for active job
  const { data: jobResults, isLoading: resultsLoading } = useExtractionResults(activeJobId);
  const { 
    progress: streamProgress, 
    status: streamStatus, 
    logs: streamLogs, 
    isConnected, 
    error: streamError 
  } = useJobStream(activeJobId);
  const { data: extractedEntities } = useExtractedEntities(
    activeJobId, 
    jobResults?.entitiesExtracted ?? 0
  );

  // Memoize log transformation
  const liveLogs = useMemo(() => {
    if (streamLogs && streamLogs.length > 0) {
      return streamLogs.map((log) => ({
        t: new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        type: mapLogType(log.level),
        text: log.message,
      }));
    }
    return [];
  }, [streamLogs]);

  const isRunning = streamStatus === 'running' || streamStatus === 'pending';

  // Auto-scroll logs
  useEffect(() => {
    if (liveLogs.length > 0) {
      setVisibleLogLines(liveLogs.length);
    }
  }, [liveLogs.length]);

  // Handle run extraction
  const handleRunExtraction = async () => {
    if (!config.sourceUrl) return;
    
    const request = config.getExtractionRequest();
    try {
      const result = await runExtraction.mutateAsync({
        sourceUrl: request.source_url,
        extractionConfig: request.extraction_config,
        batchSize: config.batchSize,
        priority: config.priority,
      });
      setActiveJobId(result.jobId);
    } catch (err) {
      // Error handled by mutation onError
    }
  };

  const pauseAllEnabled = import.meta.env.VITE_ENABLE_EXTRACTION_PAUSE_ALL === 'true';

  const handlePauseAll = async () => {
    try {
      const response = await pauseAllExtractions.mutateAsync();
      toast.success(response.message || 'Running extraction jobs paused');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to pause extraction jobs');
    }
  };

  // Loading state
  if (runExtraction.isPending || resultsLoading) {
    return <ExtractionEngineSkeleton />;
  }

  // Error state from stream
  if (streamError) {
    return (
      <div className="flex flex-col h-full items-center justify-center">
        <AlertCircle className="w-8 h-8 text-red-500 mb-3" />
        <span className="text-sm text-red-600">{streamError.message || 'Failed to load job'}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <PageHeader
        title="Extraction Engine"
        subtitle="Configure and monitor document extraction pipelines"
        actions={
          <div className="flex items-center gap-2">
            {pauseAllEnabled && (
              <Btn variant="ghost" onClick={handlePauseAll} disabled={!isRunning || pauseAllExtractions.isPending}>
                {pauseAllExtractions.isPending ? <><Loader2 size={14} className="animate-spin" /> Pausing...</> : <><Pause size={14} /> Pause All</>}
              </Btn>
            )}
            <Btn 
              variant="primary" 
              onClick={handleRunExtraction}
              disabled={!config.sourceUrl || runExtraction.isPending || isRunning}
            >
              {runExtraction.isPending ? (
                <><Loader2 size={14} className="animate-spin" /> Starting...</>
              ) : isRunning ? (
                <><Loader2 size={14} className="animate-spin" /> Running...</>
              ) : (
                <><Play size={14} /> Run Extraction</>
              )}
            </Btn>
          </div>
        }
      />

      <div className="flex flex-1 overflow-hidden gap-4 p-4">
        {/* Configuration Panel */}
        <div className="w-[280px] shrink-0 flex flex-col gap-4">
          <SectionCard title="Configuration Panel" className="flex-1">
            <div className="space-y-5">
              {/* Source URL */}
              <div className="space-y-2">
                <Label htmlFor="sourceUrl" className="text-xs font-medium">Source URL</Label>
                <Input
                  id="sourceUrl"
                  type="url"
                  placeholder="https://example.com/docs"
                  value={config.sourceUrl}
                  onChange={(e) => config.setSourceUrl(e.target.value)}
                  className="text-xs h-8"
                />
              </div>

              {/* Entity Types */}
              <div className="space-y-2">
                <Label className="text-xs font-medium">Entity Types</Label>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="capability"
                      checked={config.entityTypes.capability}
                      onCheckedChange={(v) => config.setEntityType('capability', !!v)}
                    />
                    <Label htmlFor="capability" className="text-xs cursor-pointer">Capabilities</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="useCase"
                      checked={config.entityTypes.useCase}
                      onCheckedChange={(v) => config.setEntityType('useCase', !!v)}
                    />
                    <Label htmlFor="useCase" className="text-xs cursor-pointer">Use Cases</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="persona"
                      checked={config.entityTypes.persona}
                      onCheckedChange={(v) => config.setEntityType('persona', !!v)}
                    />
                    <Label htmlFor="persona" className="text-xs cursor-pointer">Personas</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="valueDriver"
                      checked={config.entityTypes.valueDriver}
                      onCheckedChange={(v) => config.setEntityType('valueDriver', !!v)}
                    />
                    <Label htmlFor="valueDriver" className="text-xs cursor-pointer">Value Drivers</Label>
                  </div>
                </div>
              </div>

              {/* Confidence Threshold */}
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs font-medium">Confidence Threshold</Label>
                  <span className="text-xs text-muted-foreground">{config.confidenceThreshold.toFixed(2)}</span>
                </div>
                <Slider
                  value={[config.confidenceThreshold]}
                  onValueChange={([v]) => config.setConfidenceThreshold(v)}
                  min={0.5}
                  max={0.95}
                  step={0.05}
                />
              </div>

              {/* Chunk Size */}
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs font-medium">Chunk Size</Label>
                  <span className="text-xs text-muted-foreground">{config.chunkSize}</span>
                </div>
                <Slider
                  value={[config.chunkSize]}
                  onValueChange={([v]) => config.setChunkSize(v)}
                  min={500}
                  max={4000}
                  step={100}
                />
              </div>

              {/* Chunk Overlap */}
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label className="text-xs font-medium">Chunk Overlap</Label>
                  <span className="text-xs text-muted-foreground">{config.chunkOverlap}</span>
                </div>
                <Slider
                  value={[config.chunkOverlap]}
                  onValueChange={([v]) => config.setChunkOverlap(v)}
                  min={0}
                  max={500}
                  step={50}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 pt-2">
                <Btn variant="primary" onClick={() => {}} className="flex-1">
                  <Settings2 size={14} /> Apply Config
                </Btn>
                <Btn variant="ghost" onClick={config.resetToDefaults}>
                  Reset
                </Btn>
              </div>
            </div>
          </SectionCard>
        </div>

        {/* Main Area */}
        <div className="flex-1 flex flex-col gap-4 min-w-0">
          {/* Control Bar */}
          <SectionCard noPad className="px-4 py-3">
            <div className="flex items-center gap-6">
              {/* Model Selector */}
              <div className="flex items-center gap-2">
                <Label className="text-xs font-medium whitespace-nowrap">Model</Label>
                <Select value={config.model} onValueChange={(v) => config.setModel(v as typeof config.model)}>
                  <SelectTrigger className="w-[140px] h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                    <SelectItem value="gpt-4o-mini">GPT-4o Mini</SelectItem>
                    <SelectItem value="claude-3-sonnet">Claude 3 Sonnet</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Batch Size */}
              <div className="flex items-center gap-2">
                <Label className="text-xs font-medium whitespace-nowrap">Batch Size</Label>
                <Select 
                  value={String(config.batchSize)} 
                  onValueChange={(v) => config.setBatchSize(Number(v))}
                >
                  <SelectTrigger className="w-[80px] h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="5">5</SelectItem>
                    <SelectItem value="10">10</SelectItem>
                    <SelectItem value="25">25</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Priority */}
              <div className="flex items-center gap-2">
                <Label className="text-xs font-medium whitespace-nowrap">Priority</Label>
                <Select 
                  value={config.priority} 
                  onValueChange={(v) => config.setPriority(v as typeof config.priority)}
                >
                  <SelectTrigger className="w-[100px] h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Job Status Indicator */}
              {activeJobId && (
                <div className="ml-auto flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Job:</span>
                  <span className="text-xs font-mono">{activeJobId.slice(0, 8)}...</span>
                  {isConnected && (
                    <span className="flex items-center gap-1 text-xs text-emerald-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      LIVE
                    </span>
                  )}
                  {streamStatus && <StatusBadge status={isRunning ? 'running' : streamStatus} />}
                </div>
              )}
            </div>
          </SectionCard>

          {/* Live Stream / Log Output */}
          <SectionCard title="Live Stream / Log Output" className="flex-1 min-h-[200px]">
            <div className="h-full overflow-y-auto font-mono text-[11px] leading-relaxed space-y-1 pr-2">
              {liveLogs.length === 0 && !activeJobId && (
                <div className="text-muted-foreground py-8 text-center">
                  Configure extraction settings and click "Run Extraction" to begin
                </div>
              )}
              {liveLogs.length === 0 && activeJobId && !isRunning && (
                <div className="text-muted-foreground py-8 text-center">
                  No logs available yet...
                </div>
              )}
              {liveLogs.slice(0, visibleLogLines).map((line, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-muted-foreground shrink-0 w-[60px]">
                    {line.t}
                  </span>
                  <span className={`shrink-0 font-semibold ${TYPE_COLORS[line.type]}`}>
                    {TYPE_LABELS[line.type]}
                  </span>
                  <span className="text-foreground">
                    {line.text}
                  </span>
                </div>
              ))}
              {isRunning && (
                <div className="flex gap-2 text-muted-foreground">
                  <span className="w-[60px]">
                    {new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                  <span>Processing...</span>
                </div>
              )}
            </div>
          </SectionCard>

          {/* Results Table */}
          <SectionCard title="Results Table" className="flex-1 min-h-[200px]">
            <DataTable
              columns={['Name', 'Type', 'Confidence', 'Source', 'Status']}
              rows={extractedEntities?.map(entity => [
                entity.name,
                <span key={`type-${entity.name}`} className="text-xs">{entity.type}</span>,
                <span key={`conf-${entity.name}`} className="text-xs">
                  {(entity.confidence * 100).toFixed(0)}%
                </span>,
                <span key={`src-${entity.name}`} className="text-xs text-muted-foreground">{entity.provenance?.source_url ?? entity.source_span?.document_id ?? "N/A"}</span>,
                entity.confidence >= 0.5 
                  ? <CheckCircle2 key={`status-${entity.name}`} size={14} className="text-emerald-500" />
                  : <Loader2 key={`status-${entity.name}`} size={14} className="animate-spin text-muted-foreground" />,
              ]) || []}
              emptyMessage={activeJobId ? "No entities extracted yet..." : "Run an extraction to see results"}
            />
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

/** Skeleton loader for the extraction engine loading state */
function ExtractionEngineSkeleton() {
  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header skeleton */}
      <div className="px-6 py-4 border-b">
        <div className="flex items-start justify-between">
          <div>
            <Skeleton className="h-7 w-48 mb-2" />
            <Skeleton className="h-4 w-64" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-9 w-28" />
            <Skeleton className="h-9 w-32" />
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden gap-4 p-4">
        {/* Config panel skeleton */}
        <div className="w-[280px] shrink-0">
          <div className="bg-card border rounded-lg p-4 space-y-5">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-full" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-4 w-32" />
              ))}
            </div>
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-6 w-full" />
            <div className="flex gap-2 pt-2">
              <Skeleton className="h-9 flex-1" />
              <Skeleton className="h-9 w-20" />
            </div>
          </div>
        </div>

        {/* Main area skeleton */}
        <div className="flex-1 flex flex-col gap-4">
          {/* Control bar skeleton */}
          <div className="bg-card border rounded-lg px-4 py-3">
            <div className="flex gap-6">
              <Skeleton className="h-8 w-40" />
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-8 w-28" />
            </div>
          </div>

          {/* Log output skeleton */}
          <div className="bg-card border rounded-lg flex-1 p-4">
            <Skeleton className="h-4 w-32 mb-4" />
            <div className="space-y-2">
              {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                <Skeleton key={i} className="h-3 w-full" />
              ))}
            </div>
          </div>

          {/* Results table skeleton */}
          <div className="bg-card border rounded-lg flex-1">
            <Skeleton className="h-4 w-24 m-4" />
            <div className="px-4 pb-4">
              <Skeleton className="h-8 w-full mb-2" />
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-10 w-full mb-2" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
