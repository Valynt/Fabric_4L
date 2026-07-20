# Layer 3 service source inventory (`services/layer3-knowledge/src`)

Reviewed: 2026-05-12 (policy reconciliation sweep for shim-only vs service-local exceptions).


Source-of-truth policy references:


- `docs/reference/layer-runtime-path-governance.md`
- `docs/governance/compatibility-debt-registry.md`

## Per-path inventory


### shim-only required

- `services/layer3-knowledge/src/__init__.py`
- `services/layer3-knowledge/src/analytics/__init__.py`
- `services/layer3-knowledge/src/analytics/centrality.py`
- `services/layer3-knowledge/src/analytics/communities.py`
- `services/layer3-knowledge/src/analytics/manager.py`
- `services/layer3-knowledge/src/analytics/similarity.py`
- `services/layer3-knowledge/src/auth/__init__.py`
- `services/layer3-knowledge/src/auth/api_keys.py`
- `services/layer3-knowledge/src/auth/middleware.py`
- `services/layer3-knowledge/src/backup/__init__.py`
- `services/layer3-knowledge/src/backup/backup_manager.py`
- `services/layer3-knowledge/src/backup/interfaces.py`
- `services/layer3-knowledge/src/config/__init__.py`
- `services/layer3-knowledge/src/config/manager.py`
- `services/layer3-knowledge/src/config/settings.py`
- `services/layer3-knowledge/src/db/__init__.py`
- `services/layer3-knowledge/src/db/cypher_execution_helper.py`
- `services/layer3-knowledge/src/db/driver.py`
- `services/layer3-knowledge/src/db/query_execution.py`
- `services/layer3-knowledge/src/db/tenant_queries.py`
- `services/layer3-knowledge/src/gateway/__init__.py`
- `services/layer3-knowledge/src/gateway/api_gateway.py`
- `services/layer3-knowledge/src/ingestion/__init__.py`
- `services/layer3-knowledge/src/ingestion/neo4j_loader.py`
- `services/layer3-knowledge/src/ingestion/sync_manager.py`
- `services/layer3-knowledge/src/ingestion/validators.py`
- `services/layer3-knowledge/src/load_balancing/__init__.py`
- `services/layer3-knowledge/src/load_balancing/manager.py`
- `services/layer3-knowledge/src/logging_config.py`
- `services/layer3-knowledge/src/models/valuepack.py`
- `services/layer3-knowledge/src/performance/__init__.py`
- `services/layer3-knowledge/src/performance/cache.py`
- `services/layer3-knowledge/src/rate_limiting/__init__.py`
- `services/layer3-knowledge/src/rate_limiting/manager.py`
- `services/layer3-knowledge/src/rate_limiting/types.py`
- `services/layer3-knowledge/src/retrieval/__init__.py`
- `services/layer3-knowledge/src/retrieval/graph_rag.py`
- `services/layer3-knowledge/src/retrieval/hybrid_search.py`
- `services/layer3-knowledge/src/retrieval/types.py`
- `services/layer3-knowledge/src/retrieval/vector_store.py`
- `services/layer3-knowledge/src/schema/__init__.py`
- `services/layer3-knowledge/src/schema/constraints.py`
- `services/layer3-knowledge/src/schema/initializer.py`
- `services/layer3-knowledge/src/security/__init__.py`
- `services/layer3-knowledge/src/security/monitor.py`
- `services/layer3-knowledge/src/security/query_validator.py`
- `services/layer3-knowledge/src/services/__init__.py`
- `services/layer3-knowledge/src/services/case_study_service.py`
- `services/layer3-knowledge/src/services/compat_metrics.py`
- `services/layer3-knowledge/src/services/competitive_intel_service.py`
- `services/layer3-knowledge/src/services/cypher_scope_guard.py`
- `services/layer3-knowledge/src/services/evidence_search.py`
- `services/layer3-knowledge/src/services/product_service.py`
- `services/layer3-knowledge/src/services/roi_calculator_service.py`
- `services/layer3-knowledge/src/services/signal_persistence.py`
- `services/layer3-knowledge/src/services/signal_quantification.py`
- `services/layer3-knowledge/src/tracing/__init__.py`
- `services/layer3-knowledge/src/tracing/middleware.py`
- `services/layer3-knowledge/src/tracing/tracer.py`

### allowed service-local exception

- `services/layer3-knowledge/src/agents/__init__.py`
- `services/layer3-knowledge/src/agents/base.py`
- `services/layer3-knowledge/src/agents/narrative_synthesis.py`
- `services/layer3-knowledge/src/agents/provenance_tracking.py`
- `services/layer3-knowledge/src/agents/roi_calculation.py`
- `services/layer3-knowledge/src/agents/scenario_engine.py`
- `services/layer3-knowledge/src/agents/value_tree_projection.py`
- `services/layer3-knowledge/src/agents/whitespace_analysis.py`
- `services/layer3-knowledge/src/api/__init__.py`
- `services/layer3-knowledge/src/api/app_monolith.py`
- `services/layer3-knowledge/src/api/cache.py`
- `services/layer3-knowledge/src/api/dependencies.py`
- `services/layer3-knowledge/src/api/dependencies_tenant.py`
- `services/layer3-knowledge/src/api/dependencies_tenant_secured.py`
- `services/layer3-knowledge/src/api/exception_mapping.py`
- `services/layer3-knowledge/src/api/exceptions.py`
- `services/layer3-knowledge/src/api/main.py`
- `services/layer3-knowledge/src/api/metrics_state.py`
- `services/layer3-knowledge/src/api/models.py`
- `services/layer3-knowledge/src/api/rate_limiter.py`
- `services/layer3-knowledge/src/api/routes/__init__.py`
- `services/layer3-knowledge/src/api/routes/_utils.py`
- `services/layer3-knowledge/src/api/routes/benchmarks.py`
- `services/layer3-knowledge/src/api/routes/calculators.py`
- `services/layer3-knowledge/src/api/routes/compat_aliases.py`
- `services/layer3-knowledge/src/api/routes/competitive_intel.py`
- `services/layer3-knowledge/src/api/routes/entities.py`
- `services/layer3-knowledge/src/api/routes/entity_compat.py`
- `services/layer3-knowledge/src/api/routes/evidence.py`
- `services/layer3-knowledge/src/api/routes/formula_governance.py`
- `services/layer3-knowledge/src/api/routes/formulas.py`
- `services/layer3-knowledge/src/api/routes/models.py`
- `services/layer3-knowledge/src/api/routes/models_router.py`
- `services/layer3-knowledge/src/api/routes/pack_loader.py`
- `services/layer3-knowledge/src/api/routes/products.py`
- `services/layer3-knowledge/src/api/routes/provenance_audit.py`
- `services/layer3-knowledge/src/api/routes/query_search.py`
- `services/layer3-knowledge/src/api/routes/roi_calculator.py`
- `services/layer3-knowledge/src/api/routes/system.py`
- `services/layer3-knowledge/src/api/routes/tenant_resolution.py`
- `services/layer3-knowledge/src/api/routes/value_packs.py`
- `services/layer3-knowledge/src/api/routes/value_trees.py`
- `services/layer3-knowledge/src/api/routes/variables.py`
- `services/layer3-knowledge/src/api/services/tenant_resolution.py`
- `services/layer3-knowledge/src/api/shared_bootstrap.py`
- `services/layer3-knowledge/src/api/telemetry.py`
- `services/layer3-knowledge/src/api/versioning.py`
- `services/layer3-knowledge/src/cache/__init__.py`
- `services/layer3-knowledge/src/cache/aiocache_adapter.py`
- `services/layer3-knowledge/src/cache/factory.py`
- `services/layer3-knowledge/src/cache/ports.py`
- `services/layer3-knowledge/src/cache/redis_cache.py`
- `services/layer3-knowledge/src/cache/shadow.py`
- `services/layer3-knowledge/src/config.py`
- `services/layer3-knowledge/src/docs/__init__.py`
- `services/layer3-knowledge/src/docs/api_documentation.py`
- `services/layer3-knowledge/src/metrics/__init__.py`
- `services/layer3-knowledge/src/metrics/prometheus_metrics.py`
- `services/layer3-knowledge/src/migrations/028_l3_tenant_standardization.py`
- `services/layer3-knowledge/src/migrations/029_backfill_sync_metadata_tenant.py`
- `services/layer3-knowledge/src/migrations/create_composite_tenant_indexes.py`
- `services/layer3-knowledge/src/migrations/migrate_tenant_ids.py`

All allowed service-local exception modules must retain an explicit module docstring with owner (`layer3-knowledge`) and migration target date (`2026-09-30`) while exceptions remain.


### canonical implementation required in `value_fabric/layer3`

- `value_fabric/layer3/config/settings.py` is the canonical runtime settings source.
- `value_fabric/layer3/config.py` is compatibility-only and must stay a thin re-export wrapper.
