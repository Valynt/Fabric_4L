# Dead Code Cleanup Plan - Fabric_4L

**Scope:** High-confidence dead symbols (confidence >= 0.8, safe_to_delete=true)
**Total findings:** 718
**Deletable lines:** 10,692
**Symbols listed in this plan:** 100

## Recommended deletion order

1. **Large UI pages first** - immediate visual reduction in bundle/codebase size.
2. **Shared / utility modules** - removes cross-cutting dead code early.
3. **Service-layer dead exports** - clean API surfaces before refactoring hotspots.
4. **Tests / archive / specs** - lowest risk, can be batched.

## Cleanup batches

### Batch 1: `apps/web` - 22 symbols, ~2904 lines

| File | Symbol | Kind | Lines | Confidence | Reason |
|---|---|---|---|---|---|
| `apps/web/src/pages/studio/NarrativeTab.tsx` | `NarrativeTab` | unused_export | 371 | 1.0 | Public symbol 'NarrativeTab' has no importers |
| `apps/web/src/pages/InteractiveBusinessCase.tsx` | `InteractiveBusinessCase` | unused_export | 332 | 1.0 | Public symbol 'InteractiveBusinessCase' has no importers |
| `apps/web/src/pages/intelligence/ROITab.tsx` | `ROITab` | unused_export | 314 | 1.0 | Public symbol 'ROITab' has no importers |
| `apps/web/src/pages/value-case/ValueCasePage.tsx` | `ValueCasePage` | unused_export | 276 | 1.0 | Public symbol 'ValueCasePage' has no importers |
| `apps/web/src/pages/realization/RealizationPage.tsx` | `RealizationPage` | unused_export | 235 | 1.0 | Public symbol 'RealizationPage' has no importers |
| `apps/web/src/pages/intelligence/EnrichmentTab.tsx` | `EnrichmentTab` | unused_export | 210 | 1.0 | Public symbol 'EnrichmentTab' has no importers |
| `apps/web/src/pages/calculator/ROITab.tsx` | `CalcROITab` | unused_export | 180 | 1.0 | Public symbol 'CalcROITab' has no importers |
| `apps/web/src/pages/studio/ActionPlanTab.tsx` | `ActionPlanTab` | unused_export | 180 | 1.0 | Public symbol 'ActionPlanTab' has no importers |
| `apps/web/src/components/ValueNarrativeHero.tsx` | `ValueNarrativeHero` | unused_export | 172 | 1.0 | Public symbol 'ValueNarrativeHero' has no importers |
| `apps/web/src/hooks/useAgentStream.ts` | `useAgentStream` | unused_export | 107 | 1.0 | Public symbol 'useAgentStream' has no importers |
| `apps/web/src/pages/intelligence/OntologyMatchTab.tsx` | `OntologyMatchTab` | unused_export | 76 | 1.0 | Public symbol 'OntologyMatchTab' has no importers |
| `apps/web/src/pages/calculator/ValueModelTab.tsx` | `CalcValueModelTab` | unused_export | 72 | 1.0 | Public symbol 'CalcValueModelTab' has no importers |
| `apps/web/src/pages/hypothesis/DiscoveryQuestionsTab.tsx` | `DiscoveryQuestionsTab` | unused_export | 71 | 1.0 | Public symbol 'DiscoveryQuestionsTab' has no importers |
| `apps/web/src/pages/hypothesis/PersonaFitTab.tsx` | `PersonaFitTab` | unused_export | 71 | 1.0 | Public symbol 'PersonaFitTab' has no importers |
| `apps/web/src/hooks/useOntology.ts` | `useUpdateOntologyProperty` | unused_export | 43 | 1.0 | Public symbol 'useUpdateOntologyProperty' has no importers |
| `apps/web/src/components/workspace/DriverTreeShell.tsx` | `DriverTreeShell` | unused_export | 40 | 1.0 | Public symbol 'DriverTreeShell' has no importers |
| `apps/web/src/types/valueSignal.ts` | `toSignalCard` | unused_export | 36 | 1.0 | Public symbol 'toSignalCard' has no importers |
| `apps/web/src/hooks/useOntology.ts` | `useOntologyType` | unused_export | 34 | 1.0 | Public symbol 'useOntologyType' has no importers |
| `apps/web/src/hooks/useWorkspaceCase.ts` | `useAttachEvidenceToDriverMutation` | unused_export | 23 | 1.0 | Public symbol 'useAttachEvidenceToDriverMutation' has no importers |
| `apps/web/src/navigation/navigationService.ts` | `pathToState` | unused_export | 23 | 1.0 | Public symbol 'pathToState' has no importers |
| `apps/web/src/test-utils.tsx` | `TestAuthComponent` | unused_export | 19 | 1.0 | Public symbol 'TestAuthComponent' has no importers |
| `apps/web/src/hooks/useEvidence.ts` | `useUnlinkEvidence` | unused_export | 19 | 1.0 | Public symbol 'useUnlinkEvidence' has no importers |

### Batch 2: `services/layer1-ingestion` - 25 symbols, ~1584 lines

| File | Symbol | Kind | Lines | Confidence | Reason |
|---|---|---|---|---|---|
| `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py` | `create_source` | unused_export | 250 | 1.0 | Public symbol 'create_source' has no importers |
| `services/layer1-ingestion/src/crawler/telemetry.py` | `ExecutionMetrics` | unused_export | 169 | 1.0 | Public symbol 'ExecutionMetrics' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/crawler/telemetry.py` | `ExecutionMetrics` | unused_export | 169 | 1.0 | Public symbol 'ExecutionMetrics' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` | `storage_stage` | unused_export | 154 | 1.0 | Public symbol 'storage_stage' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` | `post_processing_stage` | unused_export | 100 | 1.0 | Public symbol 'post_processing_stage' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` | `validation_stage` | unused_export | 99 | 1.0 | Public symbol 'validation_stage' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/crawler/quality_gate.py` | `AdaptiveQualityGate` | unused_export | 49 | 1.0 | Public symbol 'AdaptiveQualityGate' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/shared/circuit_breaker.py` | `with_circuit_breaker` | unused_export | 45 | 1.0 | Public symbol 'with_circuit_breaker' has no importers |
| `services/layer1-ingestion/src/shared/circuit_breaker.py` | `with_circuit_breaker` | unused_export | 45 | 1.0 | Public symbol 'with_circuit_breaker' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/api/consent_routes.py` | `create_consent` | unused_export | 39 | 1.0 | Public symbol 'create_consent' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/shared/models.py` | `CrawlQueueItem` | unused_export | 39 | 1.0 | Public symbol 'CrawlQueueItem' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/shared/models.py` | `EvidenceChunk` | unused_export | 38 | 1.0 | Public symbol 'EvidenceChunk' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` | `run_pipeline_stage` | unused_export | 37 | 1.0 | Public symbol 'run_pipeline_stage' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/api/consent_routes.py` | `list_active_consent` | unused_export | 36 | 1.0 | Public symbol 'list_active_consent' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py` | `IngestionRunResponse` | unused_export | 36 | 1.0 | Public symbol 'IngestionRunResponse' has no importers |
| `services/layer1-ingestion/src/crawler/telemetry.py` | `trace_method` | unused_export | 35 | 1.0 | Public symbol 'trace_method' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/api/consent_routes.py` | `grant_consent` | unused_export | 35 | 1.0 | Public symbol 'grant_consent' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/crawler/telemetry.py` | `trace_method` | unused_export | 35 | 1.0 | Public symbol 'trace_method' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/api/consent_routes.py` | `revoke_consent` | unused_export | 34 | 1.0 | Public symbol 'revoke_consent' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py` | `retry_ingestion_run` | unused_export | 32 | 1.0 | Public symbol 'retry_ingestion_run' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py` | `SourceIntakeRequest` | unused_export | 27 | 1.0 | Public symbol 'SourceIntakeRequest' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/api/app_monolith.py` | `ScheduleInput` | unused_export | 23 | 1.0 | Public symbol 'ScheduleInput' has no importers |
| `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py` | `cancel_ingestion_run` | unused_export | 20 | 1.0 | Public symbol 'cancel_ingestion_run' has no importers |
| `services/layer1-ingestion/src/compliance/pii_scanner.py` | `PIIEntityType` | unused_export | 19 | 1.0 | Public symbol 'PIIEntityType' has no importers |
| `services/layer1-ingestion/src/compliance/url_safety.py` | `log_url_compliance_event` | unused_export | 19 | 1.0 | Public symbol 'log_url_compliance_event' has no importers |

### Batch 3: `services/layer4-agents` - 32 symbols, ~1458 lines

| File | Symbol | Kind | Lines | Confidence | Reason |
|---|---|---|---|---|---|
| `services/layer4-agents/src/layer4_agents/api/routes/state_inspector.py` | `get_performance_metrics` | unused_export | 96 | 1.0 | Public symbol 'get_performance_metrics' has no importers |
| `services/layer4-agents/src/layer4_agents/services/stripe_client.py` | `sync_usage_to_stripe` | unused_export | 80 | 1.0 | Public symbol 'sync_usage_to_stripe' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/checkpoints.py` | `compare_checkpoints` | unused_export | 79 | 1.0 | Public symbol 'compare_checkpoints' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/checkpoints.py` | `resume_from_checkpoint` | unused_export | 78 | 1.0 | Public symbol 'resume_from_checkpoint' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/health_badges.py` | `get_detailed_health` | unused_export | 76 | 1.0 | Public symbol 'get_detailed_health' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/checkpoints.py` | `list_checkpoints` | unused_export | 70 | 1.0 | Public symbol 'list_checkpoints' has no importers |
| `services/layer4-agents/src/layer4_agents/tenants/service.py` | `update_tenant_isolation_tier` | unused_export | 68 | 1.0 | Public symbol 'update_tenant_isolation_tier' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/state_inspector.py` | `get_state_schema` | unused_export | 64 | 1.0 | Public symbol 'get_state_schema' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/state_inspector.py` | `inspect_output_data` | unused_export | 57 | 1.0 | Public symbol 'inspect_output_data' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/health_badges.py` | `report_connection_quality` | unused_export | 56 | 1.0 | Public symbol 'report_connection_quality' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/state_inspector.py` | `analyze_errors` | unused_export | 50 | 1.0 | Public symbol 'analyze_errors' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/signals.py` | `stream_signals_to_websocket` | unused_export | 46 | 1.0 | Public symbol 'stream_signals_to_websocket' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/state_inspector.py` | `get_state_values` | unused_export | 46 | 1.0 | Public symbol 'get_state_values' has no importers |
| `services/layer4-agents/src/layer4_agents/services/stripe_client.py` | `get_billing_meter` | unused_export | 46 | 1.0 | Public symbol 'get_billing_meter' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/checkpoints.py` | `get_checkpoint_state` | unused_export | 43 | 1.0 | Public symbol 'get_checkpoint_state' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/state_inspector.py` | `get_state_history` | unused_export | 43 | 1.0 | Public symbol 'get_state_history' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/health_badges.py` | `get_websocket_status` | unused_export | 40 | 1.0 | Public symbol 'get_websocket_status' has no importers |
| `services/layer4-agents/src/layer4_agents/tools/competitive_tools.py` | `AnalyzeCompetitionInput` | unused_export | 39 | 1.0 | Public symbol 'AnalyzeCompetitionInput' has no importers |
| `services/layer4-agents/src/layer4_agents/tools/files.py` | `delete_file` | unused_export | 37 | 1.0 | Public symbol 'delete_file' has no importers |
| `services/layer4-agents/src/layer4_agents/tools/files.py` | `write_file` | unused_export | 34 | 1.0 | Public symbol 'write_file' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/health_badges.py` | `get_active_badges` | unused_export | 32 | 1.0 | Public symbol 'get_active_badges' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/narratives.py` | `NarrativeGenerateRequest` | unused_export | 32 | 1.0 | Public symbol 'NarrativeGenerateRequest' has no importers |
| `services/layer4-agents/src/layer4_agents/models/agent_state.py` | `WorkflowNodeType` | unused_export | 30 | 1.0 | Public symbol 'WorkflowNodeType' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/integrations.py` | `IntegrationCreateRequest` | unused_export | 28 | 1.0 | Public symbol 'IntegrationCreateRequest' has no importers |
| `services/layer4-agents/src/layer4_agents/messaging/types.py` | `ProvenanceEvent` | unused_export | 27 | 1.0 | Public symbol 'ProvenanceEvent' has no importers |
| `services/layer4-agents/src/layer4_agents/tenant/context.py` | `TenantContextManager` | unused_export | 26 | 1.0 | Public symbol 'TenantContextManager' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/health_badges.py` | `get_component_health` | unused_export | 24 | 1.0 | Public symbol 'get_component_health' has no importers |
| `services/layer4-agents/src/layer4_agents/api/routes/health_badges.py` | `dismiss_badge` | unused_export | 23 | 1.0 | Public symbol 'dismiss_badge' has no importers |
| `services/layer4-agents/src/layer4_agents/provenance/models.py` | `PROVType` | unused_export | 23 | 1.0 | Public symbol 'PROVType' has no importers |
| `services/layer4-agents/src/layer4_agents/services/narrative_builder_service.py` | `NarrativeBuilderService__build_contextResult` | unused_export | 23 | 1.0 | Public symbol 'NarrativeBuilderService__build_contextResult' has no importers |
| `services/layer4-agents/src/layer4_agents/contracts/artifacts.py` | `VariableRegistry` | unused_export | 22 | 1.0 | Public symbol 'VariableRegistry' has no importers |
| `services/layer4-agents/src/layer4_agents/tenants/api/routes/registration.py` | `RegisterTenantRequest` | unused_export | 20 | 1.0 | Public symbol 'RegisterTenantRequest' has no importers |

### Batch 4: `services/layer3-knowledge` - 14 symbols, ~487 lines

| File | Symbol | Kind | Lines | Confidence | Reason |
|---|---|---|---|---|---|
| `services/layer3-knowledge/src/cache/shadow.py` | `ShadowCacheComparator` | unused_export | 91 | 1.0 | Public symbol 'ShadowCacheComparator' has no importers |
| `services/layer3-knowledge/src/api/versioning.py` | `VersionedAPIRoute` | unused_export | 51 | 1.0 | Public symbol 'VersionedAPIRoute' has no importers |
| `services/layer3-knowledge/src/cache/redis_cache.py` | `CacheKey` | unused_export | 43 | 1.0 | Public symbol 'CacheKey' has no importers |
| `services/layer3-knowledge/src/cache/redis_cache.py` | `cache_result` | unused_export | 40 | 1.0 | Public symbol 'cache_result' has no importers |
| `services/layer3-knowledge/src/api/models.py` | `EntityType` | unused_export | 32 | 1.0 | Public symbol 'EntityType' has no importers |
| `services/layer3-knowledge/src/utils/logging_context.py` | `log_with_context` | unused_export | 32 | 1.0 | Public symbol 'log_with_context' has no importers |
| `services/layer3-knowledge/src/api/cache.py` | `get_cached_entities` | unused_export | 29 | 1.0 | Public symbol 'get_cached_entities' has no importers |
| `services/layer3-knowledge/src/auth/middleware.py` | `require_all_permissions` | unused_export | 29 | 1.0 | Public symbol 'require_all_permissions' has no importers |
| `services/layer3-knowledge/src/security/account_authorization.py` | `verify_entity_account_access` | unused_export | 27 | 1.0 | Public symbol 'verify_entity_account_access' has no importers |
| `services/layer3-knowledge/src/auth/middleware.py` | `require_any_permission` | unused_export | 24 | 1.0 | Public symbol 'require_any_permission' has no importers |
| `services/layer3-knowledge/src/api/services/tenant_resolution.py` | `resolve_ingest_tenant_id` | unused_export | 23 | 1.0 | Public symbol 'resolve_ingest_tenant_id' has no importers |
| `services/layer3-knowledge/src/auth/middleware.py` | `create_authorization_error_detail` | unused_export | 23 | 1.0 | Public symbol 'create_authorization_error_detail' has no importers |
| `services/layer3-knowledge/src/auth/middleware.py` | `log_api_usage` | unused_export | 23 | 1.0 | Public symbol 'log_api_usage' has no importers |
| `services/layer3-knowledge/src/cache/redis_cache.py` | `initialize_cache` | unused_export | 20 | 1.0 | Public symbol 'initialize_cache' has no importers |

### Batch 5: `archive` - 1 symbols, ~258 lines

| File | Symbol | Kind | Lines | Confidence | Reason |
|---|---|---|---|---|---|
| `archive/specs/specs/value_fabric_extraction_pipeline.py` | `ExtractionPipeline` | unused_export | 258 | 1.0 | Public symbol 'ExtractionPipeline' has no importers |

### Batch 6: `services/layer5-ground-truth` - 3 symbols, ~106 lines

| File | Symbol | Kind | Lines | Confidence | Reason |
|---|---|---|---|---|---|
| `services/layer5-ground-truth/src/layer5_ground_truth/services/truth_service.py` | `mark_expired_objects` | unused_export | 46 | 1.0 | Public symbol 'mark_expired_objects' has no importers |
| `services/layer5-ground-truth/src/layer5_ground_truth/api/tenant_context.py` | `enforce_authenticated_tenant_precedence` | unused_export | 38 | 1.0 | Public symbol 'enforce_authenticated_tenant_precedence' has no importers |
| `services/layer5-ground-truth/src/layer5_ground_truth/models/formula_governance.py` | `ParameterType` | unused_export | 22 | 1.0 | Public symbol 'ParameterType' has no importers |

### Batch 7: `packages/shared` - 3 symbols, ~87 lines

| File | Symbol | Kind | Lines | Confidence | Reason |
|---|---|---|---|---|---|
| `packages/shared/src/value_fabric/shared/secrets/reload.py` | `SecretReloadContext` | unused_export | 45 | 1.0 | Public symbol 'SecretReloadContext' has no importers |
| `packages/shared/src/value_fabric/shared/error_handling/helpers.py` | `raise_not_found_error` | unused_export | 22 | 1.0 | Public symbol 'raise_not_found_error' has no importers |
| `packages/shared/src/value_fabric/shared/fastapi_framework/health.py` | `Neo4jHealthProbe` | unused_export | 20 | 1.0 | Public symbol 'Neo4jHealthProbe' has no importers |

## Top 20 largest dead symbols (delete first)

| Rank | File | Symbol | Lines | Confidence |
|---|---|---|---|---|
| 1 | `apps/web/src/pages/studio/NarrativeTab.tsx` | `NarrativeTab` | 371 | 1.0 |
| 2 | `apps/web/src/pages/InteractiveBusinessCase.tsx` | `InteractiveBusinessCase` | 332 | 1.0 |
| 3 | `apps/web/src/pages/intelligence/ROITab.tsx` | `ROITab` | 314 | 1.0 |
| 4 | `apps/web/src/pages/value-case/ValueCasePage.tsx` | `ValueCasePage` | 276 | 1.0 |
| 5 | `archive/specs/specs/value_fabric_extraction_pipeline.py` | `ExtractionPipeline` | 258 | 1.0 |
| 6 | `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py` | `create_source` | 250 | 1.0 |
| 7 | `apps/web/src/pages/realization/RealizationPage.tsx` | `RealizationPage` | 235 | 1.0 |
| 8 | `apps/web/src/pages/intelligence/EnrichmentTab.tsx` | `EnrichmentTab` | 210 | 1.0 |
| 9 | `apps/web/src/pages/calculator/ROITab.tsx` | `CalcROITab` | 180 | 1.0 |
| 10 | `apps/web/src/pages/studio/ActionPlanTab.tsx` | `ActionPlanTab` | 180 | 1.0 |
| 11 | `apps/web/src/components/ValueNarrativeHero.tsx` | `ValueNarrativeHero` | 172 | 1.0 |
| 12 | `services/layer1-ingestion/src/crawler/telemetry.py` | `ExecutionMetrics` | 169 | 1.0 |
| 13 | `services/layer1-ingestion/src/layer1_ingestion/crawler/telemetry.py` | `ExecutionMetrics` | 169 | 1.0 |
| 14 | `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` | `storage_stage` | 154 | 1.0 |
| 15 | `apps/web/src/hooks/useAgentStream.ts` | `useAgentStream` | 107 | 1.0 |
| 16 | `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` | `post_processing_stage` | 100 | 1.0 |
| 17 | `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py` | `validation_stage` | 99 | 1.0 |
| 18 | `services/layer4-agents/src/layer4_agents/api/routes/state_inspector.py` | `get_performance_metrics` | 96 | 1.0 |
| 19 | `services/layer3-knowledge/src/cache/shadow.py` | `ShadowCacheComparator` | 91 | 1.0 |
| 20 | `services/layer4-agents/src/layer4_agents/services/stripe_client.py` | `sync_usage_to_stripe` | 80 | 1.0 |

## Safety notes

- All symbols above are flagged `safe_to_delete` by Repowise (zero importers).
- Before bulk deletion, run the existing test suite / `make contract-tests` as a baseline.
- Prefer one batch per commit so rollbacks are easy.
- Re-run `get_dead_code` after each batch; removal may cascade and reveal more dead code.
