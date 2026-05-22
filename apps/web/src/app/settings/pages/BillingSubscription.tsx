import { useAuthContext } from "@/contexts/AuthContext";
import { useBilling, useEntitlements } from "@/hooks/useBilling";
import { CapabilityGate } from "../components/CapabilityGate";
import { safeAsync } from '@/lib/async';

export function BillingSubscription() {
  const { user } = useAuthContext();
  const customerId = user?.tenantId ?? "";
  const { subscription, isLoading, error, openCustomerPortal, isOpeningPortal } = useBilling(customerId);
  const { data: entitlements } = useEntitlements(customerId);

  return (
    <CapabilityGate capability="billing">
      <div className="space-y-6">
        <section className="rounded-lg border bg-card p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold">Current Plan</h3>
              <p className="text-xs text-muted-foreground">Live subscription state from the billing control plane.</p>
            </div>
            <button
              type="button"
              onClick={() => safeAsync(openCustomerPortal(window.location.href), "billing.openPortal")}
              disabled={isOpeningPortal || !customerId}
              className="inline-flex h-8 items-center rounded-md border px-3 text-xs font-medium hover:bg-accent disabled:opacity-50"
            >
              {isOpeningPortal ? "Opening..." : "Open billing portal"}
            </button>
          </div>
          {isLoading ? (
            <div className="mt-4 rounded-md border p-4 text-sm text-muted-foreground">Loading subscription...</div>
          ) : error ? (
            <div className="mt-4 rounded-md border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
              {error.message}
            </div>
          ) : subscription ? (
            <div className="mt-4 flex items-center justify-between rounded-md border p-4">
              <div>
                <p className="text-base font-semibold capitalize">{subscription.plan_id}</p>
                <p className="text-xs text-muted-foreground">
                  Status: {subscription.status}
                  {subscription.current_period_end ? ` • Renews ${new Date(subscription.current_period_end).toLocaleDateString()}` : ""}
                </p>
              </div>
              <span className="rounded-full border px-2 py-1 text-[11px] font-medium uppercase tracking-wide">
                {subscription.status}
              </span>
            </div>
          ) : null}
        </section>

        <section className="rounded-lg border bg-card p-5">
          <h3 className="text-sm font-semibold">Entitlements</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {entitlements?.features ? Object.entries(entitlements.features).map(([key, feature]) => (
              <div key={key} className="rounded-md border p-3">
                <p className="text-xs text-muted-foreground">{feature.name}</p>
                <p className="text-sm font-medium">{feature.enabled ? "Enabled" : "Disabled"}</p>
                <p className="mt-1 text-xs text-muted-foreground">{feature.description}</p>
              </div>
            )) : (
              <div className="rounded-md border p-4 text-sm text-muted-foreground">
                No entitlement metadata returned for this tenant.
              </div>
            )}
          </div>
        </section>
      </div>
    </CapabilityGate>
  );
}
