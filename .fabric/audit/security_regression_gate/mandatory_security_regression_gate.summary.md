# Mandatory Security Regression Gate Evidence

- **Timestamp**: 2026-06-25T16:43:21Z
- **Git SHA**: 0c6da8a4
- **Branch**: chore/production-readiness
- **OS**: Linux
- **Test Mode**: 1
- **Artifact Directory**: artifacts/mandatory_security

## Check Results

| Check | Command | Required | Result | Evidence |
|-------|---------|----------|--------|----------|
| I-02/I-03 API Production Safety | `pytest app/tests/test_auth_enforcement.py test_health.py test_production_safety.py test_i03_durable_persistence_and_llm.py` | Yes | PASS | artifacts/mandatory_security/standalone_api_security.xml |
| Tenant/Auth Security Regression | `pytest tests/security/*` | Yes | PASS | artifacts/mandatory_security/tenant_security.xml |
| Cross-Layer Tenant Isolation Matrix | `pytest tests/security/test_cross_layer_tenant_isolation_matrix.py` | Yes | PARTIAL | artifacts/mandatory_security/cross_layer_tenant_isolation_matrix.json |
| Layer 4 C-06 Security Regression | `pytest services/layer4-agents/tests/test_tenant_rate_limits.py services/layer4-agents/tests/test_security_fixes.py` | Yes | PASS | artifacts/mandatory_security/layer4_c06_security.xml |
| Tenant Context Contract | `pytest tests/context/test_tenant_context_contract.py tests/contract/test_shared_import_boundary.py tests/contract/test_retention_deletion_contract.py` | Yes | PASS | artifacts/mandatory_security/shared_contracts.xml |
| OpenAPI Contract Drift | `make contract-drift` | Yes | SKIPPED_TEST_MODE | ⊘ |
| Deprecation Marker Standardization | `standardize_deprecation_markers.py --check` | Yes | SKIPPED_TEST_MODE | ⊘ |
| Frontend Contract Tests | `vitest + placeholder guard` | Yes | SKIPPED_TEST_MODE | ⊘ |
| Critical E2E Skip-Valve | `assert-no-skipped-critical-e2e.mjs` | Yes | SKIPPED_TEST_MODE | ⊘ |
| Kubernetes Hardening | `pytest tests/k8s/*` | Yes | PASS | artifacts/mandatory_security/k8s_security.xml |
| I-02 Layer 2 Production Fail-Closed | `pytest tests/test_production_fail_closed_i02.py` | Yes | PASS | artifacts/mandatory_security/layer2_fail_closed.xml |
| I-02 Layer 5 Production Fail-Closed | `pytest tests/test_production_fail_closed_i02.py` | Yes | PASS | artifacts/mandatory_security/layer5_fail_closed.xml |

## Final Result

**Status**: PASS
**Exit Code**: 0
**Recommendation**: PASS
