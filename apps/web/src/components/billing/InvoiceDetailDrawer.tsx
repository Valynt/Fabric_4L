import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { InvoiceStatusBadge } from './InvoiceStatusBadge';
import { Download, Loader2 } from 'lucide-react';
import { useState } from 'react';
import type { Invoice, InvoiceItem, Charge } from '@/hooks/useInvoices';

interface InvoiceDetailDrawerProps {
  invoice: (Invoice & { items?: InvoiceItem[]; charges?: Charge[] }) | null;
  onClose: () => void;
}

// Format currency helper
const formatCurrency = (dollars: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(dollars);
};

// Format date helper
const formatDate = (dateString: string | null): string => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

export function InvoiceDetailDrawer({ invoice, onClose }: InvoiceDetailDrawerProps) {
  const [downloading, setDownloading] = useState(false);

  if (!invoice) return null;

  const items = invoice.items || [];
  const charges = invoice.charges || [];

  const handleDownloadPDF = async () => {
    if (!invoice.invoice_pdf_url) return;
    setDownloading(true);
    try {
      window.open(invoice.invoice_pdf_url, '_blank');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Sheet open={!!invoice} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-[500px] sm:max-w-[600px] overflow-y-auto">
        <SheetHeader className="space-y-1">
          <SheetTitle className="text-xl">Invoice {invoice.invoice_number}</SheetTitle>
          <SheetDescription className="flex items-center gap-2 pt-2">
            <InvoiceStatusBadge status={invoice.status} />
            <span className="text-muted-foreground">
              {formatDate(invoice.period_start)} - {formatDate(invoice.period_end)}
            </span>
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Invoice Summary */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="space-y-1">
              <Label className="text-muted-foreground text-xs">Due Date</Label>
              <p className="font-medium">{formatDate(invoice.due_date)}</p>
            </div>
            <div className="space-y-1">
              <Label className="text-muted-foreground text-xs">Created</Label>
              <p className="font-medium">{formatDate(invoice.created_at)}</p>
            </div>
            {invoice.paid_at && (
              <div className="space-y-1">
                <Label className="text-muted-foreground text-xs">Paid On</Label>
                <p className="font-medium text-success">{formatDate(invoice.paid_at)}</p>
              </div>
            )}
            {invoice.voided_at && (
              <div className="space-y-1">
                <Label className="text-muted-foreground text-xs">Voided</Label>
                <p className="font-medium text-muted-foreground">{formatDate(invoice.voided_at)}</p>
              </div>
            )}
          </div>

          {invoice.description && (
            <div className="text-sm">
              <Label className="text-muted-foreground text-xs">Description</Label>
              <p className="mt-1">{invoice.description}</p>
            </div>
          )}

          {/* Line Items */}
          {items.length > 0 && (
            <div>
              <h4 className="font-medium mb-3 text-sm">Line Items</h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[50%]">Description</TableHead>
                    <TableHead className="text-right">Qty</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="py-3">
                        <div className="space-y-0.5">
                          <p className="font-medium">{item.description}</p>
                          {item.usage_metric && (
                            <p className="text-xs text-muted-foreground">
                              {item.usage_quantity?.toLocaleString()} {item.usage_metric}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        {item.quantity.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(item.amount_dollars)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Payment History */}
          {charges.length > 0 && (
            <div>
              <h4 className="font-medium mb-3 text-sm">Payments</h4>
              <div className="space-y-2">
                {charges.map((charge) => (
                  <div
                    key={charge.id}
                    className="flex items-center justify-between p-3 bg-muted/50 rounded-lg text-sm"
                  >
                    <div className="space-y-0.5">
                      <p className="font-medium capitalize">
                        {charge.payment_method_type || 'Payment'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(charge.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <span className="font-medium text-success">
                      {formatCurrency(charge.amount_dollars)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Totals */}
          <div className="border-t pt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Subtotal</span>
              <span>{formatCurrency(invoice.total_dollars - (invoice.tax_cents / 100))}</span>
            </div>
            {invoice.tax_cents > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Tax</span>
                <span>{formatCurrency(invoice.tax_cents / 100)}</span>
              </div>
            )}
            <div className="flex justify-between text-lg font-bold pt-2 border-t">
              <span>Total</span>
              <span>{formatCurrency(invoice.total_dollars)}</span>
            </div>
            {invoice.amount_due_cents > 0 && (
              <div className="flex justify-between text-sm text-destructive">
                <span>Amount Due</span>
                <span className="font-medium">{formatCurrency(invoice.amount_due_dollars)}</span>
              </div>
            )}
          </div>

          {/* Actions */}
          {invoice.invoice_pdf_url && (
            <div className="pt-4">
              <Button
                onClick={handleDownloadPDF}
                disabled={downloading}
                className="w-full"
              >
                {downloading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Opening...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    Download PDF
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
