# E2E fixture import boundaries

To prevent test sentinel leakage into runtime code:

- **Allowed to import E2E fixtures:**
  - `tests/**`
  - `apps/web/e2e/**`
- **Disallowed to import E2E fixtures:**
  - `apps/web/src/**`
  - `services/**/src/**` (except dedicated `src/test_support/**` runtime config adapters)
  - `value_fabric/**`

Rules:

1. Keep Playwright/backend-integrated seed constants in fixture modules only:
   - `tests/fixtures/**`
   - `apps/web/e2e/fixtures/**`
2. Production code must use neutral runtime config names and defaults.
3. CI/static checks must fail on known E2E sentinel constants in production trees.
