# Safe Exception Handling Patterns

Use stable error codes and sanitized user-facing messages for API responses.

## Rules

- Never return raw exception text (`str(e)`, `f"{e}"`) to clients.
- Return contract-stable payloads like:
  - `{"code": "auth.webhook_invalid_body", "message": "Bad request."}`
- Keep internal diagnostics in structured logs only.
- Use `logger.exception(...)` in catch-all handlers so stack traces remain internal.
- Prefer explicit exception branches (`ValueError`, `KeyError`, domain errors) before broad fallback handlers.

## API pattern

```python
try:
    risky_operation()
except ValueError as exc:
    logger.info("input validation failed", extra={"error": str(exc)})
    raise HTTPException(status_code=400, detail={"code": "domain.invalid_input", "message": "Bad request."}) from exc
except Exception as exc:
    logger.exception("unexpected failure", extra={"error_code": "domain.unexpected"})
    raise HTTPException(status_code=500, detail={"code": "domain.unexpected", "message": "Internal error."}) from exc
```

## Logging hygiene

- Do not include secrets, access tokens, API keys, or customer PII in exception logs.
- Sanitize any externally sourced strings before attaching them to logs.
- Include stable `error_code` fields for observability correlation.
