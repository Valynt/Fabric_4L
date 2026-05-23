export function PersonalProfile() {
  return (
    <div className="space-y-6">
      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Profile Information</h3>
        <p className="text-xs text-muted-foreground">Name, avatar, email, and account identity.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="full-name" className="text-xs font-medium">Full name</label>
            <input id="full-name" className="mt-1 h-9 w-full rounded-md border bg-background px-3 text-sm" placeholder="Your name" />
          </div>
          <div>
            <label htmlFor="email" className="text-xs font-medium">Email</label>
            <input id="email" className="mt-1 h-9 w-full rounded-md border bg-background px-3 text-sm" placeholder="you@company.com" />
          </div>
          <div>
            <label htmlFor="title" className="text-xs font-medium">Title</label>
            <input id="title" className="mt-1 h-9 w-full rounded-md border bg-background px-3 text-sm" placeholder="Job title" />
          </div>
          <div>
            <label htmlFor="default-workspace" className="text-xs font-medium">Default workspace</label>
            <input id="default-workspace" className="mt-1 h-9 w-full rounded-md border bg-background px-3 text-sm" placeholder="Primary workspace" />
          </div>
        </div>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Security & Authentication</h3>
        <p className="text-xs text-muted-foreground">SSO, password, MFA, and linked accounts.</p>
        <div className="mt-4 space-y-3">
          {["Multi-factor authentication", "Google SSO", "Password", "Authenticator app"].map((item) => (
            <div key={item} className="flex items-center justify-between rounded-md border p-3">
              <span className="text-sm">{item}</span>
              <button type="button" className="text-xs font-medium text-primary hover:underline" aria-label={`Configure ${item}`}>Configure</button>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Preferences</h3>
        <p className="text-xs text-muted-foreground">Theme, localization, and notifications.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="theme" className="text-xs font-medium">Theme</label>
            <select id="theme" className="mt-1 h-9 w-full rounded-md border bg-background px-3 text-sm">
              <option>System</option>
              <option>Light</option>
              <option>Dark</option>
            </select>
          </div>
          <div>
            <label htmlFor="language" className="text-xs font-medium">Language</label>
            <select id="language" className="mt-1 h-9 w-full rounded-md border bg-background px-3 text-sm">
              <option>English</option>
              <option>Spanish</option>
              <option>German</option>
            </select>
          </div>
        </div>
      </section>
    </div>
  );
}
