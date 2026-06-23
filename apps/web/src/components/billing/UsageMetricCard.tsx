import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { Activity, AlertCircle, AlertTriangle, CheckCircle } from 'lucide-react';

interface UsageMetricCardProps {
  metric: string;
  current: number;
  limit: number;
  unit: string;
  warningThreshold?: number;
}

export function UsageMetricCard({
  metric,
  current,
  limit,
  unit,
  warningThreshold = 75,
}: UsageMetricCardProps) {
  const percentage = limit > 0 ? Math.min((current / limit) * 100, 100) : 0;
  const isWarning = percentage >= warningThreshold && percentage < 90;
  const isDanger = percentage >= 90;
  const isSafe = percentage < warningThreshold;

  const StatusIcon = isDanger ? AlertTriangle : isWarning ? AlertCircle : CheckCircle;
  const statusColor = isDanger ? 'text-destructive' : isWarning ? 'text-warning' : 'text-success';
  const progressColor = isDanger
    ? 'bg-destructive/100'
    : isWarning
      ? 'bg-warning/100'
      : 'bg-success/100';

  // Format metric name for display (e.g., "api_calls" -> "API Calls")
  const formatMetricName = (name: string): string => {
    return name
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <Card className={cn('transition-all', isDanger && 'border-destructive/20 bg-destructive/10/50')}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Activity className="h-4 w-4 text-muted-foreground" />
            {formatMetricName(metric)}
          </CardTitle>
          <StatusIcon className={cn('h-4 w-4', statusColor)} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold">
              {current.toLocaleString()}
              <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>
            </span>
            <span className="text-sm text-muted-foreground">
              of {limit.toLocaleString()} {unit}
            </span>
          </div>

          <div className="relative">
            <Progress value={percentage} className="h-2" />
            <div
              className={cn('absolute top-0 h-2 rounded-full transition-all', progressColor)}
              style={{ width: `${percentage}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className={cn('font-medium', statusColor)}>{percentage.toFixed(1)}% used</span>
            {isDanger && <span className="text-destructive font-medium">Overage imminent</span>}
            {isWarning && <span className="text-warning">Approaching limit</span>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
