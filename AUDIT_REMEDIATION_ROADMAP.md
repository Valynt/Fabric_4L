# Remediation Roadmap: Fabric_4L
*Based on Principal Repository Audit (July 12, 2026)*

This roadmap outlines the prioritized remediation plan to address the findings identified in the `REPO_AUDIT.md` report.

## Phase 1: Critical Security & Architecture (Immediate / P0)
**Goal:** Unblock the upcoming release by securing tenant boundaries and resolving architectural drift.

1. **Enforce Security Test Integrity (F-001)**
   - **Action**: Audit `tests/security/` and convert all `@pytest.mark.xfail(strict=False)` markers to `strict=True`.
   - **Action**: For tests requiring a live database (e.g., cross-tenant write, injection), implement an integration test harness or document the accepted risk with owner sign-off.
2. **Secure Tenant Context Boundary (F-002)**
   - **Action**: Refactor `services/layer4-agents/src/layer4_agents/engine/executor.py` (Line 1460).
   - **Action**: Remove `payload.get("tenant_id")`. Inject the `tenant_id` exclusively from the authenticated `RequestContext`.
3. **Resolve Layer 3 Architectural Drift (F-003)**
   - **Action**: Rename `services/layer3-knowledge/src/` contents to use the `layer3_knowledge` package namespace per ADR-027.
   - **Action**: Update all 27 production files and 91 test files using `from src.` to use absolute imports (`from layer3_knowledge.`).
   - **Action**: Update `PYTHONPATH` in `services/layer3-knowledge/pyproject.toml` and `tests/conftest.py`.

## Phase 2: High-Priority Quality & Security (Next Release / P1)
**Goal:** Harden the supply chain, eliminate exception leakage, and ensure consistent documentation.

1. **Eliminate Exception Leakage (F-004)**
   - **Action**: Fix `ban_str_e.py` failures in `agent_permission_service.py`, `billing_usage.py`, and `security/config.py`. Replace `str(exc)` with structured logging (`error_type=type(exc).__name__`).
2. **Expand Dependabot Coverage (F-005)**
   - **Action**: Update `.github/dependabot.yml` to include `directory:` entries for all 10 Python services and the frontend application.
3. **Parameterize SOQL Queries (F-006)**
   - **Action**: Refactor `crm_tools.py` to replace string interpolation (`f"SELECT... '{safe_id}'"`) with parameterized queries supported by the Salesforce API client.
4. **Enable Strict Type Checking (F-007)**
   - **Action**: Update `pyproject.toml` for Layer 1 and Layer 4 to set `disallow_untyped_defs = true`. Resolve resulting mypy errors.
5. **Resolve Documentation Discrepancies (F-008, F-009)**
   - **Action**: Run `scripts/ci/check_adr_numbering.py`. Renumber ADRs 028-031 to resolve duplicates, add missing `# ADR-###:` headers, and document sequence gaps.
   - **Action**: Update `version.txt` to `1.1.0` to match `pyproject.toml` files. Add a CI check to prevent future drift.
6. **Implement Billing Webhook Logic (F-010)**
   - **Action**: Replace the `TODO` at `billing_webhooks.py:137` with actual event processing logic for Stripe webhooks, or formally scope billing out of the GA release.

## Phase 3: Medium-Priority Debt Reduction (30 Days / P2)
**Goal:** Improve maintainability, testing reliability, and infrastructure consistency.

1. **Pin Infrastructure Images (F-011, F-017)**
   - **Action**: Resolve the SHA256 digest for `ghcr.io/zalando/spilo-16:3.2-p1` and pin it in the k8s base manifests.
   - **Action**: Replace `newTag: latest` in `k8s/envs/dev/kustomization.yaml` with explicit tags.
2. **Refactor Bare Exceptions & Large Files (F-012, F-013)**
   - **Action**: Replace the 233 bare `except Exception:` blocks with specific exception types.
   - **Action**: Begin decomposing the 5 files exceeding 1,400 LOC (e.g., `tasks.py`, `executor.py`) into smaller modules.
3. **Stabilize Test Collection (F-014, F-015)**
   - **Action**: Refactor `conftest.py` to allow pytest collection without requiring the full service dependency stack (e.g., mock SQLAlchemy/Pydantic during collection).
   - **Action**: Audit and resolve the 112 `skip`/`xfail` markers, particularly the module-level skips in Layer 3.
4. **Enhance Governance Docs (F-016, F-018)**
   - **Action**: Add `CODE_OF_CONDUCT.md`.
   - **Action**: Add `.github/copilot-instructions.md` mirroring the rules in `AGENTS.md`.
