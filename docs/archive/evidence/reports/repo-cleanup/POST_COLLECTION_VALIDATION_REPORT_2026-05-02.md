# Post-Collection Validation Report
**Date:** 2026-05-02
**Purpose:** Document execution results after pytest collection remediation

## 1. Collection Status

**Repo-root pytest collection is clean.**

**Collection Results:**
- Layer 1: 114 tests collected, 8 skipped (optional dependencies), 0 errors
- Layer 2: 152 tests collected, 0 errors
- Layer 3: 417 tests collected, 0 errors
- Layer 4: 731 tests collected, 0 errors
- Root tests: 145+ tests collected, 0 errors
- Total: 3031 tests collected, 0 errors (default import mode)

**Layer 1–4 are collection-ready and import-topology compliant.**

## 2. Contract/Security/Arch/State/Tools Execution Results

### Contract Tests (tests/contract)
**Result:** 119 failed, 207 passed, 7 skipped, 1 xfailed

**Failure Analysis:**
- Primary failure cause: httpx.ConnectError - All connection attempts failed
- Tests require running services (integration tests)
- Some FileNotFoundError for stale value-fabric paths in test_l2_l3_contract.py

**Status:** Expected failure - services not running. Tests are integration tests that require deployed infrastructure.

### Security Tests (tests/security)
**Result:** 99 failed, 209 passed, 7 skipped, 1 xfailed (interrupted)

**Failure Analysis:**
- Primary failure cause: httpx.ConnectError - All connection attempts failed
- Tests require running services (integration tests)

**Status:** Expected failure - services not running. Tests are integration tests that require deployed infrastructure.

### Architecture Tests (tests/arch)
**Result:** Passed (exit code 0)

**Status:** Clean - no failures detected.

### State Tests (tests/state)
**Result:** 1 failed, 5 errors

**Failure Analysis:**
- FileNotFoundError for stale value-fabric paths:
  - `C:\\Users\\BBB\\Fabric_4L\\value-fabric\\layer4-agents\\src\\models\\agent_state.py`
  - Should be: `services/layer4-agents/src/models/agent_state.py`

**Status:** Requires path fixes in test files.

### Tools Tests (tests/tools)
**Result:** 29 failed, 12 passed

**Failure Analysis:**
- ModuleNotFoundError: No module named 'services.layer4_agents' (stale import)
- AttributeError: missing attributes in value_fabric.layer4.tools modules
- TypeError: unexpected keyword arguments (tenant_id parameter issues)

**Status:** Requires import fixes and attribute additions in tool modules.

## 3. Layer Test Execution Results

### Layer 1 (services/layer1-ingestion/tests)
**Result:** 33 failed, 81 passed, 8 skipped

**Failure Analysis:**
- ModuleNotFoundError: No module named 'celery' (test_celery_tasks.py)
- AssertionError failures in test_smart_router.py (routing logic issues)

**Status:** Requires celery installation and routing test fixes.

### Layer 2 (services/layer2-extraction/tests)
**Result:** Collection successful (152 tests collected)

**Status:** Clean for collection. Execution not run due to terminal command issues.

### Layer 3 (services/layer3-knowledge/tests)
**Result:** Collection successful (417 tests collected)

**Status:** Clean for collection. Execution not run due to terminal command issues.

### Layer 4 (services/layer4-agents/tests)
**Result:** Collection successful (731 tests collected)

**Status:** Clean for collection. Execution not run due to terminal command issues.

## 4. Importlib-Mode Duplicate Test-File Report Status

**Report Created:** `PYTEST_IMPORTLIB_MODE_DUPLICATES_2026-05-02.md`

**Key Findings:**
- 30 additional collection errors with --import-mode=importlib
- Duplicate test files identified:
  - test_tenant_isolation.py (3 copies: layer3-knowledge, layer4-agents, tests/security)
  - test_llm_cost_metrics.py (2 copies: layer2-extraction, layer4-agents)
  - test_api.py (2 copies: layer3-knowledge, layer5-ground-truth)
  - Pack test duplicates (intentional, not problematic)

**CI Configuration:** Needs investigation to determine if --import-mode=importlib is used by CI.

**Recommendation:** If CI does not use importlib mode, these duplicates are not a launch blocker.

## 5. Structural Preflight Status

### Shared Imports Check
**Command:** `python scripts/ci/check_shared_imports.py --strict --scope executable`
**Result:** Passed - 0 legacy shared imports found

### Navigation Patterns Check
**Command:** `python scripts/ci/check_navigation_patterns.py --strict`
**Result:** Passed - 0 hard violations, 24 approved state navigation (not a violation)

### Structural Preflight Check
**Command:** `python scripts/ci/structural_preflight.py --strict`
**Result:** Failed on tracked K8s secret manifests

**Findings:**
- 40+ secret_file_risk findings (tracked K8s secret manifests in git)
- Files include: k8s/secrets.yml, k8s/external-secrets/*.yaml, k8s/base/*.yaml, k8s/envs/dev/secrets.yml
- Type: tracked_k8s secret manifest
- Recommendation: Remove from git, rotate secrets, add to .gitignore, use ExternalSecret

**Status:** Expected failure - secret remediation is a P0 human-only blocker.

## 6. Remaining Blockers

### Human-Only Security Blockers (P0)

1. **Tracked K8s Secret Manifests** - 40+ files
   - Location: k8s/secrets.yml, k8s/external-secrets/*.yaml, k8s/base/*.yaml
   - Action Required:
     - Remove from git
     - Rotate credentials before history purge
     - Add to .gitignore
     - Use ExternalSecret for production
     - git-filter-repo/BFG only after rotation
     - Collaborators must reclone/hard-reset after rewrite
   - **Status:** P0 release blocker - requires human intervention

### Engineering Blockers

1. **State Tests Stale Paths** - 1 failed, 5 errors
   - Files: tests/state/test_state_alignment.py
   - Issue: Stale services/layer4-agents paths
   - Action Required: Fix paths to use services/layer4-agents
   - **Status:** Engineering blocker - requires path fixes

2. **Tools Tests Stale Imports** - 29 failed
   - Files: tests/tools/*.py
   - Issues: Stale services.layer4_agents imports, missing attributes
   - Action Required: Fix imports to use value_fabric.layer4, add missing attributes
   - **Status:** Engineering blocker - requires import/attribute fixes

3. **Layer 1 Celery Dependency** - 20+ failed
   - File: services/layer1-ingestion/tests/unit/test_celery_tasks.py
   - Issue: celery module not installed
   - Action Required: Install celery or add pytest.importorskip
   - **Status:** Engineering blocker - requires dependency handling

4. **Layer 1 Routing Tests** - 4 failed
   - File: services/layer1-ingestion/tests/crawler/test_smart_router.py
   - Issue: Routing logic test failures
   - Action Required: Fix routing logic or test expectations
   - **Status:** Engineering blocker - requires test/fix

### Optional Dependency Skips

1. **Layer 1 Optional Dependencies** - 8 skipped
   - Files: Multiple layer1 test files
   - Issue: trafilatura, respx, defusedxml, playwright not installed
   - Action Required: Install dependencies if needed for coverage
   - **Status:** Optional - not blocking

## 7. E2E Validation Readiness Assessment

**Recommendation:** E2E validation cannot start until the following are resolved:

**Must Fix (Blocking):**
1. P0 Human-Only: Secret remediation (tracked K8s manifests in git)
2. Engineering: State tests stale paths
3. Engineering: Tools tests stale imports
4. Engineering: Layer 1 celery dependency or skip

**Should Fix (Recommended):**
1. Importlib-mode duplicate test files (if CI uses importlib mode)
2. Layer 1 routing test failures

**Optional (Can Defer):**
1. Contract/security tests (require running services - can run in E2E environment)
2. Layer 1 optional dependencies (can install if needed)

**Conclusion:** Repository is collection-ready but not execution-ready. Engineering blockers (state paths, tools imports, celery dependency) must be fixed before E2E validation can proceed. Secret remediation remains a P0 human-only release blocker that requires credential rotation and git history cleanup.
