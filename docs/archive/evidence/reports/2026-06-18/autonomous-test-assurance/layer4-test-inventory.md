# Layer 4 Test Inventory

Generated: 2026-05-28

## Backend Tests
| Layer | Unit Tests | Integration Tests | Security Tests | E2E Tests |
|-------|-----------|-------------------|----------------|-----------|
| Layer 4 Agents | 19 unit tests | 146 integration tests | 25 security tests | 0 E2E tests |

## Test Categories

### Unit Tests (19 files)
- test_api_common_helpers.py
- test_executor_checkpoint_conflict.py
- test_executor_controller_invariants.py
- test_layer4_correctness_patch.py
- test_layer4_observability_schema.py
- test_observability_schema_legacy.py
- test_oss0_ports.py
- test_overage_service.py
- test_production_readiness_fixes.py
- test_scheduler_execution.py
- test_services_unit.py
- test_state_manager.py
- test_task_scheduler.py
- test_value_flow_facade.py
- test_variable_registry_service.py
- test_workflow_routes.py
- test_workflow_state_machine.py

### Integration Tests (146 files)
- test_accounts_api.py
- test_action_level_approval.py
- test_admin_tool_h01.py
- test_agent_grounding_and_refusal.py
- test_agent_mutation_approval_audit.py
- test_agent_output_traceability.py
- test_agent_tenant_isolation.py
- test_agent_tool_result_contracts.py
- test_agent_workflow_traceability.py
- test_analysis_routes.py
- test_analysis_smoke_mode_service_routes.py
- test_api_tenant_propagation.py
- test_app_title_contract.py
- test_audit_route_h01.py
- test_authorization_adversarial.py
- test_billing_security_exceptions.py
- test_billing_service.py
- test_billing_tenant_scoped_customer_keys.py
- test_billing_webhook_security_consistency.py
- test_business_case_claim_promotion.py
- test_c1_proxy.py
- test_case_permissions_and_audit.py
- test_checkpoint_boundary.py
- test_checkpoint_resume.py
- test_checkpoint_resume_failure_paths.py
- test_checkpoint_resume_restart.py
- test_checkpoint_tenant_isolation.py
- test_checkpoints_route_errors.py
- test_checkpoints_route_identity.py
- test_code_quality.py
- test_comments_route.py
- test_company_knowledge.py
- test_compat_app_surface_contract.py
- test_context_gatherer.py
- test_crm_sync_service.py
- test_crm_tools_pagination.py
- test_crm_webhook_auth_unit.py
- test_crm_webhook_tenant_isolation.py
- test_cross_tenant_hostile.py
- test_database_optional_tenant_security.py
- test_database_session_tenant_enforcement.py
- test_db_pool_metrics.py
- test_dil_phase3.py
- test_encryption_service.py
- test_enrichment.py
- test_error_contract_adapter.py
- test_error_handling_paths.py
- test_error_response_shape_canonical.py
- test_executor_lifecycle_facade.py
- test_export_provenance.py
- test_fail_closed_authz_guards.py
- test_feature_flags.py
- test_frontend_compat_routes.py
- test_frontend_endpoint_contracts.py
- test_governance_workflow_contracts.py
- test_harness_routes.py
- test_health_tracker.py
- test_input_validation_adversarial.py
- test_integration_service.py
- test_interfaces_exports.py
- test_isolation_tier_provisioning.py
- test_knowledge_tool_persistence.py
- test_langgraph_execution.py
- test_layer3_client_knowledge_methods.py
- test_llm_budget_guardrails.py
- test_llm_cost_metrics.py
- test_llm_cost_tracking.py
- test_messaging.py
- test_model_registry.py
- test_narratives_tenant_hardening.py
- test_notification.py
- test_notifications_route.py
- test_observability_contract_integration.py
- test_observability_gaps.py
- test_oidc.py
- test_oidc_cleanup.py
- test_oidc_id_token_validation.py
- test_oidc_state_store.py
- test_output_envelope_contract.py
- test_pack_variable_loader.py
- test_phase3_control_plane.py
- test_plan_version_billing.py
- test_prospects_start_analysis.py
- test_provenance.py
- test_rate_limiting_edge_cases.py
- test_reasoning_trace_schema.py
- test_replay_conflict_policy.py
- test_resilience.py
- test_roi_calculator_workflow.py
- test_run_envelope_contract.py
- test_runtime_hardening.py
- test_salesforce_oauth.py
- test_salesforce_oauth_routes.py
- test_security_fixes.py
- test_signal_review_route.py
- test_startup_contract.py
- test_startup_dependencies.py
- test_startup_dependency_verifier.py
- test_tasks_route.py
- test_tenant_api.py
- test_tenant_context_route.py
- test_tenant_guardrails_clients.py
- test_tenant_isolation.py
- test_tenant_lifecycle.py
- test_tenant_provisioning.py
- test_tenant_rate_limits.py
- test_tiers.py
- test_tool_execution_contract.py
- test_tool_output_structure_validation.py
- test_tool_result_contract.py
- test_tools_authorization.py
- test_tools_route_response_models.py
- test_tools_routes_contract.py
- test_trace_header_propagation_integration.py
- test_usage_idempotency.py
- test_usage_service.py
- test_validation_auth_seed.py
- test_value_flow_facade.py
- test_value_hypothesis.py
- test_variable_registry_helpers.py
- test_webhook_security.py
- test_webhook_security_matrix.py
- test_websocket_auth_routes.py
- test_websocket_manager.py
- test_websocket_multitenant_hostile.py
- test_workflow_archive_and_list.py
- test_workflow_canonical_contract.py
- test_workflow_controls.py
- test_workflow_replay_determinism.py
- test_workflow_replay_harness.py
- test_workflow_resume_checkpoint_conflict_route.py
- test_workflow_start_tenant_invariant.py
- test_workflow_tenant_isolation.py
- test_workflows_real_execution.py

### Security Tests (25 files)
- test_authorization_adversarial.py
- test_billing_security_exceptions.py
- test_billing_tenant_scoped_customer_keys.py
- test_billing_webhook_security_consistency.py
- test_checkpoint_tenant_isolation.py
- test_cross_tenant_hostile.py
- test_database_optional_tenant_security.py
- test_database_session_tenant_enforcement.py
- test_fail_closed_authz_guards.py
- test_input_validation_adversarial.py
- test_narratives_tenant_hardening.py
- test_oidc_id_token_validation.py
- test_security_fixes.py
- test_tenant_guardrails_clients.py
- test_tenant_isolation.py
- test_tools_authorization.py
- test_webhook_security.py
- test_webhook_security_matrix.py
- test_websocket_auth_routes.py
- test_websocket_multitenant_hostile.py
- test_workflow_start_tenant_invariant.py
- test_workflow_tenant_isolation.py

## Key Invariants Discovered

### Tenant Isolation
- **Rule**: No cross-tenant reads or writes in workflows, checkpoints, or billing
- **Enforcement**: Tenant-scoped database sessions, RLS policies
- **Code Path**: `src/database.py`, `src/tenants/`

### Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: OIDC, API key authentication, Fabric auth envelope
- **Code Path**: `src/api/main.py`, `src/tenants/api/`

### Authorization
- **Rule**: No authorization bypass via headers, params, body fields
- **Enforcement**: Role-based access, tenant admin checks
- **Code Path**: `src/tenants/tier_enforcement.py`

### Input Validation
- **Rule**: No unvalidated input reaching LLM calls or tool execution
- **Enforcement**: Pydantic schemas, adversarial validation tests
- **Code Path**: `src/contracts/`, validation modules

### Tool Execution Security
- **Rule**: Tool execution must enforce tenant isolation and authorization
- **Enforcement**: Tool result contracts, authorization checks
- **Code Path**: `src/tools/`, `src/contracts/`

### Webhook Security
- **Rule**: Webhook endpoints must validate signatures and tenant context
- **Enforcement**: Webhook security matrix, signature validation
- **Code Path**: `src/integration/`, webhook handlers

## Test Markers
- `@pytest.mark.asyncio` - Async test functions

## Discovery Notes
- Layer 4 has the most comprehensive test coverage (165 total tests)
- Strong security test coverage (25 security tests)
- Extensive adversarial validation tests
- Good coverage of tenant isolation in workflows and checkpoints
- Webhook security tests present
- OIDC authentication tests
- Tool execution contract tests
- WebSocket multitenant hostile tests
