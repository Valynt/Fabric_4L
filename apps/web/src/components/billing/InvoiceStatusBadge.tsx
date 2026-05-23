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
    className: 'bg-green-100 text-green-800 hover:bg-green-100 border-green-200',
    icon: CheckCircle,
  },
  open: {
    label: 'Open',
    variant: 'default',
    className: 'bg-blue-100 text-blue-800 hover:bg-blue-100 border-blue-200',
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
    className: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200',
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
