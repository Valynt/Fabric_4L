import type { ComponentProps } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { CheckCircle, Clock, XCircle } from 'lucide-react';

type ChargeStatus = 'succeeded' | 'pending' | 'failed';
type BadgeVariant = ComponentProps<typeof Badge>['variant'];

interface ChargeStatusBadgeProps extends Omit<ComponentProps<typeof Badge>, 'children'> {
  status: ChargeStatus | string;
  showIcon?: boolean;
}

const statusConfig: Record<
  ChargeStatus,
  { label: string; variant: BadgeVariant; className: string; icon: typeof CheckCircle }
> = {
  succeeded: {
    label: 'Succeeded',
    variant: 'default',
    className: 'bg-success/10 text-success hover:bg-success/10 border-success/20',
    icon: CheckCircle,
  },
  pending: {
    label: 'Pending',
    variant: 'default',
    className: 'bg-warning/10 text-warning hover:bg-warning/10 border-warning/20',
    icon: Clock,
  },
  failed: {
    label: 'Failed',
    variant: 'destructive',
    className: 'bg-destructive/10 text-destructive hover:bg-destructive/10 border-destructive/20',
    icon: XCircle,
  },
};

export function ChargeStatusBadge({ status, showIcon = true, className, ...props }: ChargeStatusBadgeProps) {
  const config = statusConfig[status as ChargeStatus] || {
    label: status,
    variant: 'secondary',
    className: '',
    icon: Clock,
  };

  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn(config.className, className)} {...props}>
      {showIcon && <Icon className="mr-1 h-3 w-3" />}
      {config.label}
    </Badge>
  );
}
