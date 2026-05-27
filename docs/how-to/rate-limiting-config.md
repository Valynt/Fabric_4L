# Shared rate-limiting middleware configuration

The shared HTTP rate-limiting middleware is configured through environment variables
so policy changes can be rolled out without code changes.

## Exempt routes (policy)

By default, the middleware bypasses rate-limiting for:

- `/health`
- `/metrics`
- `/internal/health`
- `/internal/metrics`

Override with:

- `RATE_LIMIT_EXEMPT_PATH_PREFIXES` (comma-separated list of path prefixes).

## Key strategy

The middleware keying strategy supports tenant + caller + route dimensions:

- `RATE_LIMIT_KEY_INCLUDE_TENANT=true|false`
- `RATE_LIMIT_KEY_INCLUDE_CALLER=true|false`
- `RATE_LIMIT_KEY_INCLUDE_ROUTE=true|false`

Recommended default is all `true` to preserve tenant isolation and avoid caller cross-talk.
