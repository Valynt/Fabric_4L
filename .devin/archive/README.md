# Archive

Old execution plans, deduplicated artifacts, and superseded documents.

## Structure

```
archive/
  plans/              # Timestamped execution plans older than 30 days
  testing-dedup/      # Deduplicated test artifact variants (2026-04-28)
```

## Retention

| Content | Retention | Action After |
|---------|-----------|--------------|
| Execution plans | 1 year | Delete or move to cold storage |
| Deduplicated artifacts | 1 year | Delete after reconciliation verified |
| Old agent configs | 6 months | Delete |

## Do Not Edit

Files in this directory are immutable historical records.
