import { useAuthContext } from "@/contexts/AuthContext";
import { useBilling } from "@/hooks/useBilling";
import { CapabilityGate } from "../components/CapabilityGate";
import { safeAsync } from '@/lib/async';

export function BillingPaymentMethods() {
  const { user } = useAuthContext();
  const customerId = user?.tenantId ?? "";
  const { openCustomerPortal, isOpeningPortal } = useBilling(customerId);

  return (
    <CapabilityGate capability="billing">
      <div className="space-y-6">
        <section className="rounded-lg border bg-card p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold">Payment Methods</h3>
              <p className="text-xs text-muted-foreground">
                Payment instrument management is delegated to the hosted customer portal.
              </p>
            </div>
            <button
              type="button"
              onClick={() => safeAsync(openCustomerPortal(window.location.href), "billing.openPortal")}
              disabled={isOpeningPortal || !customerId}
              className="inline-flex h-8 items-center rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {isOpeningPortal ? "Opening..." : "Manage payment methods"}
            </button>
          </div>
        </section>
      </div>
    </CapabilityGate>
  );
}
