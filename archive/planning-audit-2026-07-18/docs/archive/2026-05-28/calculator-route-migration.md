# Calculator Route Migration

- Legacy workflow calculator route remains available at `/workflow/calculator` for guided flow continuity.
- Canonical calculator now lives under account-scoped workspace routes:
  - `/calculator/:accountId/roi`
  - `/calculator/:accountId/value-model`
- Redirect recommendation: route old deep links to the account-scoped ROI route when account context is known.
