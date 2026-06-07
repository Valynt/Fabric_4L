import type { ComponentProps } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { CheckCircle, Clock, FileText, XCircle, AlertCircle } from 'lucide-react';

type InvoiceStatus = 'draft' | 'open' | 'paid' | 'void' | 'uncollectible';
type BadgeVariant = ComponentProps<typeof Badge>['variant'];

interface InvoiceStatusBadgeProps extends Omit<ComponentProps<typeof Badge>, 'children'> {
  status: InvoiceStatus | string;
  showIcon?: boolean;
}

const statusConfig: Record<
  InvoiceStatus,
  { label: string; variant: BadgeVariant; className: string; icon: typeof CheckCircle }
> = {
  paid: {
    label: 'Paid',
    variant: 'default',
    className: 'bg-success/10 text-success hover:bg-success/10 border-success/20',
    icon: CheckCircle,
  },
  open: {
    label: 'Open',
    variant: 'default',
    className: 'bg-primary/10 text-primary hover:bg-primary/10 border-primary/20',
    icon: Clock,
  },
  draft: {
    label: 'Draft',
    variant: 'secondary',
    className: 'bg-muted text-foreground hover:bg-muted border-border',
    icon: FileText,
  },
  void: {
    label: 'Void',
    variant: 'outline',
    className: 'bg-muted text-muted-foreground hover:bg-muted border-border',
    icon: XCircle,
  },
  uncollectible: {
    label: 'Uncollectible',
    variant: 'destructive',
    className: 'bg-destructive/10 text-destructive hover:bg-destructive/10 border-destructive/20',
    icon: AlertCircle,
  },
};

export function InvoiceStatusBadge({ status, showIcon = true, className, ...props }: InvoiceStatusBadgeProps) {
  const config = statusConfig[status as InvoiceStatus] || {
    label: status,
    variant: 'secondary',
    className: '',
    icon: FileText,
  };

  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn(config.className, className)} {...props}>
      {showIcon && <Icon className="mr-1 h-3 w-3" />}
      {config.label}
    </Badge>
  );
}
