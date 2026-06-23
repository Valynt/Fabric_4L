# HTTPException Inventory

Generated for PR 1: Database and HTTPException Inventory

## Summary

Total sites identified: ~200+ (including test files)

**Note**: This inventory includes both production code and test files. Test files are marked separately.

## Categorization

### 1. Router/API Boundary (High Priority for Migration)

#### 401 Authentication Errors
- `layer6-benchmarks/src/api/main.py:302` - "Tenant context required"
- `layer3-knowledge/src/api/auth_context.py:54` - "Missing or invalid authorization header"
- `layer3-knowledge/src/api/auth_context.py:59` - "Malformed JWT token"
- `layer3-knowledge/src/api/auth_context.py:65` - "Could not decode JWT payload"
- `layer3-knowledge/src/api/auth_context.py:69` - "JWT token missing tenant_id claim"
- `layer3-knowledge/src/api/auth_context.py:75` - (missing detail in grep)
- `layer3-knowledge/src/api/app_monolith.py:30` - "Authentication context is required"
- `layer3-knowledge/src/api/provenance_audit.py:37` - "Authentication context is required"
- `layer3-knowledge/src/api/provenance_audit.py:41` - "Authentication context is required"
- `layer4-agents/src/tenants/api/routes/oidc.py:574` - "No active session"
- `layer4-agents/src/tenants/api/routes/oidc.py:578` - "Invalid or expired session"
- `layer4-agents/src/tenants/api/routes/oidc.py:589` - "Invalid session claims"
- `layer4-agents/src/tenants/api/routes/oidc.py:596` - "User not found or inactive"

#### 403 Authorization Errors
- `layer7-billing/src/layer7_billing/api/main.py:27` - "Missing RBAC role: {role}"
- `layer6-benchmarks/src/api/main.py:276` - "Metrics endpoint requires internal access"
- `layer6-benchmarks/src/api/main.py:308` - "Global benchmark baselines require privileged admin role"
- `layer4-agents/src/tenants/api/routes/admin.py:102` - "Access denied"
- `layer4-agents/src/tenants/api/routes/admin_dashboard.py:119` - (missing detail in grep)
- `layer4-agents/src/tenants/api/routes/oidc.py:129` - (missing detail in grep)
- `layer4-agents/src/tenants/api/routes/oidc.py:252` - (missing detail in grep)
- `layer4-agents/src/tenants/api/routes/oidc.py:462` - (missing detail in grep)
- `layer4-agents/src/api/routes/analysis.py:439` - "Validation seeding is disabled in production"
- `layer4-agents/src/api/routes/analysis.py:441` - "Validation seeding requires tenant context"
- `layer4-agents/src/api/routes/analysis.py:444` - "Validation seeding requires privileged reason"
- `layer4-agents/src/api/routes/analysis.py:598` - "Validation seed tenant mismatch"
- `layer4-agents/src/api/routes/models_router.py:410` - "Not authorized to delete this model"

#### 404 Not Found Errors
- `layer6-benchmarks/src/api/main.py:416` - "Dataset not found"
- `layer6-benchmarks/src/api/main.py:447` - "Dataset not found"
- `layer6-benchmarks/src/api/main.py:452` - "Metric '{payload.metric}' not found"
- `layer6-benchmarks/src/api/main.py:510` - "Dataset not found"
- `layer6-benchmarks/src/api/main.py:514` - "Metric '{payload.metric}' not found"
- `layer5-ground-truth/src/layer5_ground_truth/api/assumption_governance_routes.py:64` - "AssumptionRecord not found"
- `layer4-agents/src/tenants/api/routes/admin.py:221` - "Tenant not found"
- `layer4-agents/src/tenants/api/routes/admin.py:253` - "Tenant not found"
- `layer4-agents/src/tenants/api/routes/admin_dashboard.py:228` - "Tenant not found"
- `layer4-agents/src/tenants/api/routes/admin_dashboard.py:372` - "Tenant not found"
- `layer4-agents/src/tenants/api/routes/admin_dashboard.py:407` - "Tenant not found"
- `layer4-agents/src/tenants/api/routes/api_keys.py:121` - "API key {key_id!r} not found"
- `layer4-agents/src/tenants/api/routes/oidc.py:238` - "Tenant not found"
- `layer4-agents/src/tenants/api/routes/oidc.py:359` - "Tenant not found"
- `layer4-agents/src/tenants/api/routes/oidc.py:529` - "Tenant not found"
- `layer4-agents/src/tenants/api/routes/tenants.py:81` - "Tenant not found"
- `layer4-agents/src/tenants/api/routes/tenants.py:105` - "Tenant not found"
- `layer4-agents/src/tenants/api/routes/tenants.py:176` - "Tenant {tenant_id} not found"
- `layer4-agents/src/tenants/api/routes/tenants.py:190` - "Tenant {tenant_id} not found"
- `layer4-agents/src/tenants/api/routes/tenants.py:203` - "Tenant {tenant_id} not found"
- `layer4-agents/src/tenants/api/routes/tenants.py:229` - "Tenant {tenant_id} not found"
- `layer4-agents/src/tenants/api/routes/tenants.py:252` - "Tenant {tenant_id} not found"
- `layer4-agents/src/tenants/api/routes/tenants.py:276` - "Tenant {tenant_id} not found"
- `layer4-agents/src/tenants/api/routes/users.py:67` - "User {user_id} not found"
- `layer4-agents/src/tenants/api/routes/users.py:81` - "User {user_id} not found"
- `layer4-agents/src/tenants/api/routes/users.py:94` - "User {user_id} not found"
- `layer4-agents/src/registry/api/routes.py:131` - "Model version not found"
- `layer4-agents/src/registry/api/routes.py:158` - "Model version not found"
- `layer4-agents/src/registry/api/routes.py:175` - "Model version not found"
- `layer4-agents/src/registry/api/routes.py:193` - "No active production model found"
- `layer4-agents/src/feature_flags/api/routes.py:100` - "Feature flag '{flag_key}' not found"
- `layer4-agents/src/feature_flags/api/routes.py:167` - "Feature flag '{flag_key}' not found"
- `layer4-agents/src/api/routes/analysis.py:1075` - "Business case {case_id} not found"
- `layer4-agents/src/api/routes/analysis.py:1267` - "Business case {case_id} not found"
- `layer4-agents/src/api/routes/analysis.py:1519` - "Account not found: {request.account_id}"
- `layer4-agents/src/api/routes/analysis.py:1716` - "Saved scenario not found"
- `layer4-agents/src/api/routes/analysis.py:1742` - "Saved scenario not found"
- `layer3-knowledge/src/api/routes/benchmarks.py:216` - "Benchmark not found"
- `layer3-knowledge/src/api/routes/benchmarks.py:286` - "Policy not found"
- `layer3-knowledge/src/api/routes/calculators.py:206` - "Value case {case_id} not found"
- `layer3-knowledge/src/api/routes/calculators.py:258` - "Value case {case_id} not found"
- `layer3-knowledge/src/api/routes/models_router.py:410` - "Model {model_id} not found"
- `layer3-knowledge/src/api/routes/models_router.py:530` - "Model {model_id} not found"
- `layer3-knowledge/src/api/routes/graph_viz.py:242` - "Entity {entity_id} not found"
- `layer3-knowledge/src/api/routes/products.py:189` - "Product not found"
- `layer3-knowledge/src/api/routes/products.py:206` - "Product not found"
- `layer3-knowledge/src/api/routes/products.py:219` - "Product not found"
- `layer3-knowledge/src/api/routes/products.py:245` - "Product not found"
- `layer3-knowledge/src/api/routes/products.py:259` - "Feature or product not found"
- `layer3-knowledge/src/api/routes/products.py:295` - "Link not found"
- `layer3-knowledge/src/api/routes/provenance_audit.py:90` - "Entity {entity_id} not found"
- `layer3-knowledge/src/api/routes/formula_governance.py:292` - "Formula not found"
- `layer3-knowledge/src/api/routes/formula_governance.py:347` - "Formula not found"
- `layer3-knowledge/src/api/routes/formula_governance.py:435` - "Formula not found"

#### 400/422 Validation Errors
- `layer6-benchmarks/src/api/main.py:458` - "Invalid company_value format"
- `layer6-benchmarks/src/api/main.py:519` - "Invalid value format"
- `layer6-benchmarks/src/api/main.py:569` - "ownership_mode must be one of: tenant, global_system"
- `layer5-ground-truth/src/layer5_ground_truth/api/assumption_governance_routes.py:71` - "Approval required for high-impact assumption..."
- `layer5-ground-truth/src/layer5_ground_truth/api/assumption_governance_routes.py:74` - "Assumption is not in an approved lifecycle state"
- `layer4-agents/src/tenants/api/routes/oidc.py:242` - "OIDC is not enabled for this tenant"
- `layer4-agents/src/tenants/api/routes/oidc.py:335` - "Invalid or expired state parameter"
- `layer4-agents/src/tenants/api/routes/oidc.py:346` - "OIDC session expired"
- `layer4-agents/src/tenants/api/routes/oidc.py:363` - "OIDC is not enabled for this tenant"
- `layer4-agents/src/tenants/api/routes/oidc.py:419` - "OIDC nonce mismatch"
- `layer4-agents/src/tenants/api/routes/oidc.py:533` - "OIDC is not configured for this tenant"
- `layer4-agents/src/api/routes/analysis.py:536` - "Seeded API key hash must be HMAC-SHA256 hex"
- `layer4-agents/src/api/routes/analysis.py:830` - "prospect_id or account_id is required"
- `layer4-agents/src/api/routes/analysis.py:838` - "account_id is required for smoke-mode ROI validation"
- `layer4-agents/src/api/routes/analysis.py:842` - "account_id must be a UUID for smoke-mode ROI validation"
- `layer4-agents/src/api/routes/analysis.py:1041` - "previous_case_id must match route case_id"
- `layer4-agents/src/api/routes/analysis.py:1491` - "account_id must be a UUID"
- `layer3-knowledge/src/api/routes/benchmarks.py:266` - "No fields to update"
- `layer3-knowledge/src/api/routes/knowledge.py:166` - "driver_ids must not be empty"
- `layer3-knowledge/src/api/routes/knowledge.py:177` - "driver_ids must contain non-empty strings"
- `layer3-knowledge/src/api/routes/models_router.py:226` - "Invalid folder: {folder}"
- `layer3-knowledge/src/api/routes/models_router.py:228` - "Invalid sort_by: {sort_by}"
- `layer3-knowledge/src/api/routes/models_router.py:230` - "Invalid sort_dir: {sort_dir}"
- `layer3-knowledge/src/api/routes/products.py:203` - "No fields to update"
- `layer3-knowledge/src/api/routes/provenance_audit.py:45` - "entity_id is required"
- `layer3-knowledge/src/api/routes/provenance_audit.py:63` - "entity_id is required"
- `layer3-knowledge/src/api/routes/provenance_audit.py:72` - "entity_id too long (max 255 chars)"

#### 409 Conflict Errors
- `layer5-ground-truth/src/layer5_ground_truth/api/assumption_governance_routes.py:71` - "Approval required for high-impact assumption..."
- `layer5-ground-truth/src/layer5_ground_truth/api/assumption_governance_routes.py:74` - "Assumption is not in an approved lifecycle state"
- `layer4-agents/src/tenants/api/routes/tenants.py:151` - "Tenant slug already exists"
- `layer4-agents/src/tenants/api/routes/tenants.py:227` - "Invalid tenant status transition"
- `layer4-agents/src/tenants/api/routes/tenants.py:250` - "Invalid tenant status transition"
- `layer4-agents/src/tenants/api/routes/tenants.py:274` - "Invalid tenant status transition"
- `layer4-agents/src/api/routes/analysis.py:511` - "Seeded user tenant mismatch: {user_id}"
- `layer4-agents/src/api/routes/analysis.py:562` - "Seeded API key tenant mismatch: {key.key_id}"
- `layer4-agents/src/api/routes/analysis.py:1335` - "Business case document bytes unavailable"

#### 503 Service Unavailable Errors
- `layer6-benchmarks/src/api/main.py:385` - "Benchmark store not initialized"
- `layer6-benchmarks/src/api/main.py:412` - "Benchmark store not initialized"
- `layer6-benchmarks/src/api/main.py:442` - "Benchmark store not initialized"
- `layer6-benchmarks/src/api/main.py:506` - "Benchmark store not initialized"
- `layer6-benchmarks/src/api/main.py:557` - "Benchmark store not initialized"
- `layer6-benchmarks/src/api/main.py:566` - "Benchmark store not initialized"
- `layer4-agents/src/api/routes/analysis.py:304` - "Workflow executor not initialized"
- `layer4-agents/src/api/routes/analysis.py:1341` - "Export storage endpoint is not configured"
- `layer3-knowledge/src/api/routes/dependencies.py:479` - "Vector store not available"
- `layer3-knowledge/src/api/routes/graph_viz.py:90` - "Neo4j not available"
- `layer3-knowledge/src/api/routes/graph_viz.py:226` - "Neo4j not available"
- `layer3-knowledge/src/api/routes/graph_viz.py:385` - "Neo4j not available"
- `layer3-knowledge/src/api/routes/provenance_audit.py:77` - "Neo4j not available"

#### 500 Internal Server Errors
- `layer3-knowledge/src/api/routes/calculators.py:127` - "Database error"
- `layer3-knowledge/src/api/routes/calculators.py:182` - "Database error"
- `layer3-knowledge/src/api/routes/calculators.py:223` - "Database error"
- `layer3-knowledge/src/api/routes/calculators.py:275` - "Database error"
- `layer3-knowledge/src/api/routes/models_router.py:320` - "Database error"
- `layer3-knowledge/src/api/routes/models_router.py:371` - "Database error"
- `layer3-knowledge/src/api/routes/models_router.py:425` - "Database error"
- `layer3-knowledge/src/api/routes/models_router.py:492` - "Failed to create model"
- `layer3-knowledge/src/api/routes/models_router.py:495` - "Database error"
- `layer3-knowledge/src/api/routes/models_router.py:551` - "Database error"
- `layer3-knowledge/src/api/routes/provenance_audit.py:145` - "Provenance query failed. Please try again later."
- `layer3-knowledge/src/api/routes/provenance_audit.py:242` - "Failed to query audit logs"
- `layer3-knowledge/src/api/routes/formula_governance.py:400` - "Failed to create version"

#### 502/504 Gateway/Timeout Errors
- `layer3-knowledge/src/api/routes/documents.py:55` - "Export service error"
- `layer3-knowledge/src/api/routes/documents.py:111` - "Document generation timed out"
- `layer4-agents/src/tenants/api/routes/oidc.py:384` - "No id_token in token response"

### 2. Database Module HTTPException (Internal Infrastructure)

These are in database.py files and handle tenant context, database errors, and privileged access:

- `layer5-ground-truth/src/layer5_ground_truth/database.py:476` - (tenant context error)
- `layer5-ground-truth/src/layer5_ground_truth/database.py:485` - (tenant context error)
- `layer5-ground-truth/src/layer5_ground_truth/database.py:538` - (privileged access)
- `layer5-ground-truth/src/layer5_ground_truth/database.py:557` - (privileged access)
- `layer5-ground-truth/src/layer5_ground_truth/database.py:609` - (tenant context error)
- `layer5-ground-truth/src/layer5_ground_truth/database.py:617` - (tenant context error)
- `layer4-agents/src/database.py:541` - (tenant context error)
- `layer4-agents/src/database.py:549` - (tenant context error)
- `layer4-agents/src/database.py:654` - (tenant context error)
- `layer4-agents/src/database.py:664` - (tenant context error)
- `layer4-agents/src/database.py:682` - (isolation tier error)
- `layer4-agents/src/database.py:750` - (tenant context error)
- `layer4-agents/src/database.py:766` - (privileged access)
- `layer4-agents/src/database.py:855` - (isolation tier error)
- `layer4-agents/src/database.py:865` - (isolation tier error)
- `layer4-agents/src/database.py:962` - (isolation tier error)

### 3. Service/Internal Logic (Lower Priority for Migration)

These are in service layer code, tools, and internal utilities:

- `layer4-agents/src/tools/knowledge.py:41` - (internal tool error)
- `layer4-agents/src/tools/signal_tools.py:54` - (internal tool error)
- `layer4-agents/src/tools/signal_tools.py:97` - (internal tool error)
- `layer4-agents/src/tools/signal_tools.py:195` - (internal tool error)
- `layer4-agents/src/tenants/tier_enforcement.py:285` - (tier enforcement error)
- `layer3-knowledge/src/security/account_authorization.py:232` - (authorization error)
- `layer3-knowledge/src/security/account_authorization.py:278` - (authorization error)
- `layer3-knowledge/src/auth/middleware.py:133` - (auth middleware error)
- `layer3-knowledge/src/auth/middleware.py:149` - (auth middleware error)
- `layer3-knowledge/src/auth/middleware.py:195` - (auth middleware error)
- `layer3-knowledge/src/auth/middleware.py:225` - (auth middleware error)
- `layer3-knowledge/src/auth/middleware.py:255` - (auth middleware error)
- `layer3-knowledge/src/auth/middleware.py:289` - (auth middleware error)

### 4. Test Files (Excluded from Migration)

Test files that use HTTPException for testing purposes:

- `layer6-benchmarks/tests/test_benchmark_route_matrix_and_contracts.py:235`
- `layer5-ground-truth/tests/test_layer3_failure_modes.py:265`
- `layer3-knowledge/tests/test_error_handling_integration.py:60`
- `layer3-knowledge/tests/test_graph_viz_security_boundaries.py:159`
- `layer3-knowledge/tests/test_value_packs.py:49`
- `layer3-knowledge/tests/test_value_packs.py:56`
- `layer4-agents/tests/test_frontend_compat_routes.py:83`
- `layer4-agents/tests/test_frontend_compat_routes.py:109`
- `layer4-agents/tests/test_frontend_compat_routes.py:128`
- `layer4-agents/tests/test_frontend_compat_routes.py:137`
- `layer4-agents/tests/test_tenant_isolation.py:139`
- `layer4-agents/tests/test_tenant_isolation.py:320`
- `layer4-agents/tests/test_workflow_archive_and_list.py:145`
- `layer4-agents/tests/test_workflow_archive_and_list.py:148`
- `layer4-agents/tests/test_workflow_archive_and_list.py:155`
- `layer4-agents/tests/test_workflow_archive_and_list.py:157`
- `layer4-agents/tests/test_workflow_controls.py:211`
- `layer4-agents/tests/test_workflow_controls.py:215`
- `layer4-agents/tests/test_workflow_controls.py:221`
- `layer4-agents/tests/test_workflow_controls.py:233`
- `layer4-agents/tests/test_workflow_controls.py:248`
- `layer4-agents/tests/test_workflow_controls.py:252`
- `layer4-agents/tests/test_workflow_controls.py:281`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:115`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:118`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:131`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:134`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:136`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:149`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:152`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:155`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:169`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:172`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:174`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:189`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:192`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:194`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:196`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:210`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:213`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:216`
- `layer4-agents/tests/test_workflow_tenant_isolation.py:228`
- `layer4-agents/tests/test_security_fixes.py:301`
- `layer4-agents/tests/test_crm_webhook_auth_unit.py:62`
- `layer4-agents/tests/test_crm_webhook_auth_unit.py:73`
- `layer4-agents/tests/test_workflow_tenant_isolation_evidence.md:76`
- `layer4-agents/collect_out.txt:2602`

### 5. Additional Router Files (Truncated in Grep)

The grep output was truncated. Additional router files with HTTPException:
- `layer4-agents/src/api/routes/*.py` (many routes)
- `layer5-ground-truth/src/layer5_ground_truth/api/*.py` (many routes)
- `layer3-knowledge/src/api/routes/*.py` (many routes)

These need to be inventoried separately with a more targeted grep.

## Migration Priority

### Phase 1 (High Priority - Router/API Boundary)
1. 401 Authentication errors (~15 sites)
2. 403 Authorization errors (~15 sites)
3. 404 Not found errors (~60 sites)
4. 400/422 Validation errors (~30 sites)
5. 409 Conflict errors (~10 sites)
6. 503 Service unavailable errors (~15 sites)

### Phase 2 (Medium Priority - Database Module)
- Database.py HTTPException sites (~20 sites)
- These are infrastructure-level and may need different approach

### Phase 3 (Low Priority - Internal Logic)
- Service/internal logic HTTPException sites (~15 sites)
- Tools and utilities

### Excluded
- Test files (~50+ sites) - These are intentional for testing

## Additional Router Files (Layer 1, Layer 2, API Gateway)

### Layer 1 (Ingestion) Routes

#### 401 Authentication Errors
- `layer1-ingestion/src/api/main.py:378` - "Authentication required"
- `layer1-ingestion/src/api/main.py:397` - "Invalid user ID format"
- `layer1-ingestion/src/api/main.py:399` - "Authentication required"
- `layer1-ingestion/src/api/app_monolith.py:479` - "Authentication required"
- `layer1-ingestion/src/api/app_monolith.py:498` - "Invalid user ID format"
- `layer1-ingestion/src/api/app_monolith.py:500` - "Authentication required"
- `layer1-ingestion/src/api/routes/compatibility.py:137` - (cross-tenant access denied)

#### 403 Authorization Errors
- `layer1-ingestion/src/api/main.py:369` - "X-Organization-ID does not match authenticated tenant"
- `layer1-ingestion/src/api/main.py:1801` - "No access to this domain"
- `layer1-ingestion/src/api/app_monolith.py:1818` - "No access to this domain"
- `layer1-ingestion/src/api/routes/compatibility.py:137` - "User cannot access another user's private data"

#### 404 Not Found Errors
- `layer1-ingestion/src/api/main.py:1282` - "Target not found"
- `layer1-ingestion/src/api/main.py:1302` - "Target not found"
- `layer1-ingestion/src/api/main.py:1453` - "Target not found"
- `layer1-ingestion/src/api/main.py:1487` - "Target not found"
- `layer1-ingestion/src/api/main.py:1553` - "Target not found"
- `layer1-ingestion/src/api/main.py:1703` - "Target not found"
- `layer1-ingestion/src/api/main.py:1753` - "Job not found"
- `layer1-ingestion/src/api/main.py:1932` - "Job not found"
- `layer1-ingestion/src/api/main.py:2023` - "Job not found"
- `layer1-ingestion/src/api/main.py:2056` - "Job not found"
- `layer1-ingestion/src/api/main.py:2092` - "Job not found"
- `layer1-ingestion/src/api/main.py:2140` - "Job not found"
- `layer1-ingestion/src/api/main.py:2250` - "Target not found"
- `layer1-ingestion/src/api/main.py:2416` - "Corpus not found"
- `layer1-ingestion/src/api/main.py:2433` - "Intelligence packet not found"
- `layer1-ingestion/src/api/main.py:2450` - "Job not found"
- `layer1-ingestion/src/api/main.py:2453` - "Job has no skill output"
- `layer1-ingestion/src/api/main.py:2462` - "SourceCorpus not yet available"
- `layer1-ingestion/src/api/main.py:2475` - "AccountIntelligencePacket not yet available"
- `layer1-ingestion/src/api/main.py:2590` - "SourceCorpus not found"
- `layer1-ingestion/src/api/main.py:2664` - "AccountIntelligencePacket not found"
- `layer1-ingestion/src/api/main.py:2690` - "Content not found"
- `layer1-ingestion/src/api/main.py:2743` - "Extracted data not found"
- `layer1-ingestion/src/api/app_monolith.py:1355` - "Target not found"
- `layer1-ingestion/src/api/app_monolith.py:1375` - "Target not found"
- `layer1-ingestion/src/api/app_monolith.py:1526` - "Target not found"
- `layer1-ingestion/src/api/app_monolith.py:1560` - "Target not found"
- `layer1-ingestion/src/api/app_monolith.py:1618` - "Target not found"
- `layer1-ingestion/src/api/app_monolith.py:1716` - "Target not found"
- `layer1-ingestion/src/api/app_monolith.py:1768` - "Job not found"
- `layer1-ingestion/src/api/app_monolith.py:1949` - "Job not found"
- `layer1-ingestion/src/api/app_monolith.py:2040` - "Job not found"
- `layer1-ingestion/src/api/app_monolith.py:2073` - "Job not found"
- `layer1-ingestion/src/api/app_monolith.py:2109` - "Job not found"
- `layer1-ingestion/src/api/app_monolith.py:2157` - "Job not found"
- `layer1-ingestion/src/api/app_monolith.py:2453` - "Content not found"
- `layer1-ingestion/src/api/app_monolith.py:2506` - "Extracted data not found"
- `layer1-ingestion/src/api/routes/compatibility.py:96` - "Source not found"
- `layer1-ingestion/src/api/routes/compatibility.py:99` - "Source not found"

#### 400/422 Validation Errors
- `layer1-ingestion/src/api/main.py:376` - "Invalid X-Organization-ID header format"
- `layer1-ingestion/src/api/main.py:1154` - (URL safety error)
- `layer1-ingestion/src/api/main.py:2259` - "Unknown job_type: {job_type.value}"
- `layer1-ingestion/src/api/main.py:2481` - "Unknown output_contract: {job.output_contract}"
- `layer1-ingestion/src/api/main.py:2557` - "Invalid cursor format; expected ISO-8601 datetime"
- `layer1-ingestion/src/api/main.py:2628` - "Invalid cursor format; expected ISO-8601 datetime"
- `layer1-ingestion/src/api/app_monolith.py:476` - "Invalid X-Organization-ID header format"
- `layer1-ingestion/src/api/app_monolith.py:1227` - "URL must use http/https protocol"
- `layer1-ingestion/src/api/app_monolith.py:2226` - "target_ids required for execute operation"
- `layer1-ingestion/src/api/app_monolith.py:2228` - "job_ids not allowed for execute operation"
- `layer1-ingestion/src/api/app_monolith.py:2231` - "job_ids required for cancel/retry operations"
- `layer1-ingestion/src/api/app_monolith.py:2233` - "target_ids not allowed for cancel/retry operations"
- `layer1-ingestion/src/api/app_monolith.py:2239` - "At least one target_id or job_id is required"
- `layer1-ingestion/src/api/routes/compatibility.py:67` - "Invalid source payload"
- `layer1-ingestion/src/api/routes/compatibility.py:69` - "Source payload must be an object"

#### 409 Conflict Errors
- `layer1-ingestion/src/api/main.py:2034` - "Job already in terminal state: {job.status}"
- `layer1-ingestion/src/api/app_monolith.py:2051` - "Job already in terminal state: {job.status}"

### Layer 2 (Extraction) Routes

#### 401 Authentication Errors
- `layer2-extraction/src/layer2_extraction/api/routes/signal_lifecycle.py:33` - "Tenant context required"
- `layer2-extraction/src/layer2_extraction/api/routes/signal_lifecycle.py:39` - "Tenant/account context required"

#### 403 Authorization Errors
- `layer2-extraction/src/layer2_extraction/api/main.py:1339` - "Metrics endpoint requires internal access"

#### 404 Not Found Errors
- `layer2-extraction/src/layer2_extraction/api/main.py:1493` - "Job not found"
- `layer2-extraction/src/layer2_extraction/api/main.py:1504` - "Quarantine record not found"
- `layer2-extraction/src/layer2_extraction/api/main.py:1572` - "Job not found"
- `layer2-extraction/src/layer2_extraction/api/main.py:1594` - "Entity provenance not found"
- `layer2-extraction/src/layer2_extraction/api/main.py:1756` - "Job {job_id} not found"
- `layer2-extraction/src/layer2_extraction/api/routes/signal_lifecycle.py:57` - "Signal not found"
- `layer2-extraction/src/layer2_extraction/api/routes/signal_lifecycle.py:70` - "Signal not found"
- `layer2-extraction/src/layer2_extraction/api/routes/extraction.py:83` - "Job not found"
- `layer2-extraction/src/layer2_extraction/api/routes/extraction.py:90` - "Job not found"
- `layer2-extraction/src/layer2_extraction/api/routes/extraction.py:100` - "No extraction artifacts found"
- `layer2-extraction/src/layer2_extraction/api/routes/extraction.py:102` - "No extraction artifacts found"

#### 400/422 Validation Errors
- `layer2-extraction/src/layer2_extraction/api/main.py:745` - "model_version is required in extraction_config or EXTRACTION_MODEL env var"
- `layer2-extraction/src/layer2_extraction/api/main.py:749` - "schema_version is required in extraction_config"
- `layer2-extraction/src/layer2_extraction/api/main.py:753` - "prompt_version is required in extraction_config"

#### 409 Conflict Errors
- `layer2-extraction/src/layer2_extraction/api/routes/signal_lifecycle.py:60` - "Invalid lifecycle transition"
- `layer2-extraction/src/layer2_extraction/api/routes/signal_lifecycle.py:73` - "Invalid lifecycle transition"

### API Gateway Routes

#### 404 Not Found Errors
- `api/app/routers/evidence.py:49` - "Evidence not found"
- `api/app/routers/evidence.py:63` - "Evidence not found"
- `api/app/routers/context_engine.py:25` - "Value pack not found"
- `api/app/routers/context_engine.py:44` - "Formula not found"
- `api/app/routers/hypotheses.py:49` - "Hypothesis not found"
- `api/app/routers/privacy.py:35` - "DSAR request not found"
- `api/app/routers/privacy.py:43` - "DSAR package not found"
- `api/app/routers/drivers.py:62` - "Driver not found"
- `api/app/routers/versioning.py:49` - "Snapshot not found"
- `api/app/routers/versioning.py:63` - "Base snapshot not found"
- `api/app/routers/versioning.py:65` - "Compare snapshot not found"
- `api/app/routers/versioning.py:95` - "Snapshot not found"
- `api/app/routers/reviews.py:49` - "Review request not found"
- `api/app/routers/reviews.py:62` - "Review request not found"
- `api/app/routers/reviews.py:76` - "Review request not found"
- `api/app/routers/reviews.py:96` - "Review request not found"
- `api/app/routers/value_cases.py:20` - "No value case found for account"
- `api/app/routers/value_cases.py:42` - "Value case not found"
- `api/app/routers/value_cases.py:72` - "Value case not found"
- `api/app/routers/realization.py:63` - "Plan not found"
- `api/app/routers/realization.py:77` - "Plan not found"
- `api/app/routers/realization.py:94` - "Plan not found"
- `api/app/routers/intelligence.py:68` - "Account not found"
- `api/app/routers/intelligence.py:87` - "Account not found"
- `api/app/routers/calculator.py:63` - "ROI calculation not found"
- `api/app/routers/agents.py:81` - "Agent run not found"
- `api/app/routers/agents.py:89` - "Agent run not found"
- `api/app/routers/agents.py:97` - "Agent run not found"
- `api/app/routers/agents.py:124` - "Workflow not found"
- `api/app/routers/agents.py:132` - "Workflow not found"
- `api/app/routers/agents.py:141` - "Workflow not found"
- `api/app/routers/agents.py:152` - "Workflow not found"
- `api/app/routers/agents.py:161` - "Workflow not found"
- `api/app/routers/auth.py:363` - "Target user not found in tenant scope"
- `api/app/routers/accounts.py:92` - "Account not found"
- `api/app/routers/accounts.py:129` - "Account not found"
- `api/app/routers/accounts.py:142` - "Account not found"
- `api/app/routers/accounts.py:173` - "Account not found"
- `api/app/routers/accounts.py:207` - "Account not found"

#### 400/422 Validation Errors
- `api/app/routers/privacy.py:27` - "Invalid DSAR request"
- `api/app/routers/auth.py:112` - "Password does not meet strength requirements"
- `api/app/routers/auth.py:291` - "Password does not meet strength requirements"
- `api/app/routers/accounts.py:125` - "No fields provided for update"

#### 403 Authorization Errors
- `api/app/routers/privacy.py:48` - "Access denied"
- `api/app/routers/auth.py:360` - "Insufficient role for impersonation"
- `api/app/routers/auth.py:365` - "Cross-tenant impersonation is forbidden"

#### 409 Conflict Errors
- `api/app/routers/accounts.py:66` - (conflict error from exc)
- `api/app/routers/accounts.py:117` - (conflict error from exc)

#### 503 Service Unavailable Errors
- `api/app/routers/auth.py:379` - "Impersonation store unavailable"
- `api/app/routers/auth.py:434` - "Impersonation store unavailable"

### Layer 1 Database Module HTTPException
- `layer1-ingestion/src/shared/database.py:201` - (tenant context error)
- `layer1-ingestion/src/shared/database.py:209` - (tenant context error)
- `layer1-ingestion/src/shared/database.py:308` - (tenant context error)
- `layer1-ingestion/src/shared/database.py:316` - (tenant context error)
- `layer1-ingestion/src/shared/database.py:357` - (tenant context error)
- `layer1-ingestion/src/shared/database.py:365` - (tenant context error)
- `layer1-ingestion/src/shared/database.py:453` - (tenant context error)
- `layer1-ingestion/src/shared/database.py:463` - (tenant context error)
- `layer1-ingestion/src/shared/database.py:517` - (privileged access)
- `layer1-ingestion/src/shared/database.py:536` - (privileged access)

## Notes

- The grep output was truncated at 500 lines. A complete inventory requires additional targeted searches.
- Some entries have incomplete details due to grep truncation. Full file review needed for accurate categorization.
- Layer 4, Layer 5, and Layer 3 routes were partially captured in initial grep and may need additional review.
