export function PersonalSecurity() {
  return (
    <div className="space-y-6">
      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Password</h3>
        <p className="text-xs text-muted-foreground">Update your password and manage recovery options.</p>
        <div className="mt-4 space-y-3 max-w-md">
          <input type="password" aria-label="Current password" className="h-9 w-full rounded-md border bg-background px-3 text-sm" placeholder="Current password" />
          <input type="password" aria-label="New password" className="h-9 w-full rounded-md border bg-background px-3 text-sm" placeholder="New password" />
          <input type="password" aria-label="Confirm new password" className="h-9 w-full rounded-md border bg-background px-3 text-sm" placeholder="Confirm new password" />
          <button type="button" className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:opacity-90">Update password</button>
        </div>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Two-Factor Authentication</h3>
        <p className="text-xs text-muted-foreground">Add an extra layer of security to your account.</p>
        <div className="mt-4 flex items-center justify-between rounded-md border p-3">
          <div>
            <p className="text-sm font-medium">Authenticator app</p>
            <p className="text-xs text-muted-foreground">Not configured</p>
          </div>
          <button type="button" className="inline-flex h-8 items-center rounded-md border px-3 text-xs font-medium hover:bg-accent" aria-label="Enable authenticator app">Enable</button>
        </div>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Linked Accounts</h3>
        <p className="text-xs text-muted-foreground">Manage SSO providers and linked identities.</p>
        <div className="mt-4 space-y-2">
          {["Google", "Microsoft", "SAML"].map((provider) => (
            <div key={provider} className="flex items-center justify-between rounded-md border p-3">
              <span className="text-sm">{provider}</span>
              <button type="button" className="text-xs font-medium text-primary hover:underline" aria-label={`Connect ${provider}`}>Connect</button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
