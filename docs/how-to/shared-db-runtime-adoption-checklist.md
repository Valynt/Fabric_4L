# Shared DB Runtime Adoption Checklist

Adopt `value_fabric.shared.database.postgresql` for each maintained service entrypoint.

## Per-service checklist (`services/*`)

1. Resolve the **async runtime** DSN via `resolve_runtime_dsn(...)` using service-priority env vars (must be `postgresql+asyncpg://...` or `postgresql+psycopg://...`).
2. Validate DSN with `validate_postgresql_dsn` before engine creation.
3. Build engine with `create_postgresql_engine` and explicit `PostgresPoolConfig`.
4. Build session maker with `create_session_maker`.
5. Wire FastAPI dependency injection to `get_db_session` through app state/session maker.
6. Use `transactional(...)` or `session_scope(...)` for unit-of-work behavior.
7. Add startup health probe via `health_probe` and fail closed on unhealthy DB.
8. Add shutdown hook calling `shutdown_engine`.
9. Confirm migration env uses matching runtime URL precedence.
10. Confirm one Alembic head and `.env.example` variable presence via CI script.

## Services to apply

- `services/layer1-ingestion`
- `services/layer2-extraction`
- `services/layer3-knowledge`
- `services/layer4-agents`
- `services/layer5-ground-truth`
- `services/layer6-benchmarks`
- `services/api`
