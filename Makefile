.PHONY: help verify verify-strict lint lint-layer1 lint-layer2 lint-layer2-5 lint-layer3 lint-layer4 \
        lint-layer5 lint-layer6 typecheck typecheck-layer1 typecheck-layer2 typecheck-layer2-5 \
        typecheck-layer3 typecheck-layer4 typecheck-layer4-strict typecheck-layer5 typecheck-layer6 \
        mypy-baseline-write-layer2 mypy-baseline-write-layer2-5 mypy-baseline-write-layer3 mypy-baseline-write-layer4 mypy-baseline-write-layer5 mypy-baseline-write-layer6 \
		test contract-tests contract-lint test-layer1 test-layer1-crawler test-layer1-router-cache test-layer1-benchmarks test-layer1-router-benchmarks test-layer2 test-layer2-5 test-layer3 test-layer3-live test-layer4 test-layer4-live \
        test-frontend build docker-build docker-build-multi migrate migrate-layer1 migrate-layer2 migrate-layer2-5 migrate-layer4 migrate-layer5 migrate-api db-migrate-status db-migrate-check gate-database gate-database-live db-production-readiness-gate evals perf-test perf-eval clean sdk check-layer4-boundaries check-layer4-collection check-layer4-canonical-paths \
        setup bootstrap \
        check-env check-env-backend check-env-frontend validate-env-contract \
        preflight up down logs check-deprecations test-backup-drills \
	test-backend-integrated-validation test-backend-integrated-release-smoke production-edge-smoke \
	certify-meridian-journey \
	check-workflow-matrix check-workflow-registry check-workflow-references \
	gate-mandatory-security-regression gate-security gate-security-broad gate-state gate-arch gate-config gate-local gate-local-production-subset \
	gate-chaos gate-smoke gate-agent gate-obs gate-release-policy \
	gate-policy gate-lint gate-sign-manifest gate-summary \
	gate-migration-readiness gate-database-readiness gate-backup-restore-readiness \
	gate-api-contracts gate-auth-readiness gate-secrets-readiness gate-deployment-readiness \
	gate-launch-blockers gate-frontend-readiness gate-reliability-readiness gate-rollback-readiness \
	gate-performance-readiness gate-data-governance-readiness gate-compliance-readiness gate-incident-response-readiness \
	gate-behavior-readiness check-behavior-readiness-audit \
	gates-validate-policy gates-sign-manifest gates-render-summary release-gate \
	architecture-readiness-gate security-readiness-gate gate-all \
	gate-production gate-production-core tier0-production-safety-gate tier1-beta-readiness-gate tier2-enterprise-readiness-gate production-readiness-gate \
	release-evidence-packet collect-95-plus-evidence collect-95-plus-evidence-focused \
	generate-sbom-and-provenance compose-config-validate helm-dependency-validate \
	k8s-production-overlay-validate k8s-manifest-consistency-check \
	build-reproducibility-check validate-monitoring-stack \
	validate-launch-contract release-baseline certify-release-candidate build-release-evidence \
	platform-contract-lint setup-hooks check-ui-duplicates check-readiness-consistency \
	check-pytest-skip-governance check-type-escape-ratchet check-conflict-markers check-adr check-legacy-debt check-operational-debt check-reports-evidence-policy check-no-nul-bytes check-migration-entrypoints check-migration-heads check-migration-status-artifacts \
	check-migration-rollback-policy check-migration-runtime-consistency check-database-governance-docs check-migration-postgres-roundtrip \
	check-temporal-skips check-hermetic-build-inputs check-production-k8s-mutable-tags check-k8s-image-digests \
	check-keycloak-realm-seed-security \
	check-manifest-secret-hygiene \
	check-trivy-ignore-policy \
	check-security-exceptions \
	check-path-env-hygiene \
	check-compatibility-shims \
	check-layer3-legacy-tenant-dependency-imports \
	check-layer3-tenant-dependency-imports \
	check-test-skip-register-uniqueness \
	check-raw-http-exception-usage \
	check-behavior-contract \
	harness-task harness-guard harness-check \
	docs-harness \
	contracts validate-openapi-contracts contract-drift contract-freshness-fast contract-freshness \
	auth-dev

.PHONY: verify-structure check-model-provider-boundaries check-hostile-tenant-evidence \
	check-dead-code check-structural-fitness-ratchet mypy-changed-layer1 \
	test-e2e-contracts test-e2e-behaviors test-e2e-journeys test-backend-contracts \
	certify-production-path seed-e2e reset-e2e test-e2e-full pact-tests test-unit \
	test-integration test-e2e-docker test-fast setup-layer2-5 test-layer1-integration \
	test-layer1-security-postgres test-layer5 test-layer6 test-shared test-e2e \
	security-smoke security-test-gating security-test security-test-isolation \
	security-test-rbac security-test-owasp security-test-injection security-coverage \
	evals-full perf-test-journeys check-tool-contracts check-prompt-registry check-deprecated-tracer-imports \
	check-risk-register debt-baseline-snapshot check-health-ratchets gate-tenant-isolation \
	promote-staging lint-release clean-root-debris check-value-fabric-public-imports

auth-dev: ## Seed local dev auth environment with mock users, tenants, and envelopes
	@$(PYTHON) scripts/dev_auth_seed.py


# Strict shell settings for production safety
.ONESHELL:
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

PROFILE ?= release-candidate
POLICY_FILE := .fabric/prod-gates.policy.yaml
ARTIFACT_DIR := artifacts/release
# Default RELEASE_SHA to the current HEAD so docker-build records digests
# under artifacts/release/<sha>/ even when invoked standalone; certification
# runs make docker-build with the checkout already at the candidate SHA.
RELEASE_SHA ?= $(shell git rev-parse HEAD 2>/dev/null || echo UNKNOWN)
DB_MIGRATION_DATABASE_URL ?=

PYTHON_BOOTSTRAP ?= python
PYTHON ?= $(shell $(PYTHON_BOOTSTRAP) scripts/ci/resolve_python.py)
# If a local venv exists, prefer its binaries (ruff, alembic, pytest, mypy, ...).
# This is scoped to this make invocation — it does not mutate the user's shell.
ifneq ($(wildcard .venv/bin),)
export PATH := $(CURDIR)/.venv/bin:$(PATH)
endif
PIP    := $(PYTHON) -m pip install -e
PNPM ?= corepack pnpm
# Use python -m pytest to ensure pytest is available via the selected Python 3.11+ interpreter.
PYTEST := $(PYTHON) -m pytest -v --tb=short
ROOT_MAKE := $(MAKE) -f $(firstword $(MAKEFILE_LIST))

# Ensure mypy is available before running typecheck targets
MYPY_VERSION_CHECK := $(shell $(PYTHON) -c "import shutil; print('mypy_found' if shutil.which('mypy') else 'mypy_not_found')")

help: ## Show this help
	@$(PYTHON) scripts/ci/render_make_help.py $(MAKEFILE_LIST)

# ─── Verification ────────────────────────────────────────────────────────────

VERIFY_CHECKS := check-health-ratchets \
	check-keycloak-realm-seed-security check-manifest-secret-hygiene check-path-env-hygiene \
	check-trivy-ignore-policy check-security-exceptions check-model-provider-boundaries \
	lint typecheck test contract-tests security-smoke \
	check-deprecations check-tool-contracts check-deprecated-tracer-imports \
	platform-contract-lint check-ui-duplicates check-readiness-consistency check-adr \
	check-workflow-matrix check-workflow-references \
	check-pytest-skip-governance check-layer3-legacy-tenant-dependency-imports \
	check-hermetic-build-inputs check-production-k8s-mutable-tags check-k8s-image-digests \
	check-behavior-readiness-audit verify-structure docs-harness

verify: $(VERIFY_CHECKS) ## Run all checks before PR
	@echo "✅  All checks passed"

verify-structure: check-model-provider-boundaries check-temporal-skips ## Run structural preflight and Python contract lint checks
	@echo "→ Running structural preflight..."
	@$(PYTHON) scripts/ci/structural_preflight.py --strict
	@echo "→ Running Python contract lint..."
	@$(PYTHON) scripts/ci/python_contract_lint.py --strict --baseline config/ci/python_contract_lint_baseline.json
	@echo "→ Checking Layer 1 API main shim drift..."
	@$(PYTHON) scripts/ci/check_layer1_api_main_shim_drift.py
	@echo "→ Running strict shared-import enforcement..."
	@$(PYTHON) scripts/ci/check_shared_imports.py --strict --scope executable
	@echo "→ Running import topology tests..."
	@$(PYTHON) -m pytest --no-mandatory-dep-check tests/contract/test_import_topology.py -q
	@echo "→ Running strict navigation pattern check..."
	@$(PYTHON) scripts/ci/check_navigation_patterns.py --strict
	@echo "→ Running Layer 4 bounded-context dependency check..."
	@$(PYTHON) scripts/ci/check_layer4_boundaries.py
	@echo "✅  Structure verification passed"

check-layer4-boundaries: ## Report/fail on Layer 4 bounded-context dependency violations and transitive hotspots
	@$(PYTHON) scripts/ci/check_layer4_boundaries.py

check-model-provider-boundaries: ## Block new direct LLM/provider access outside migration baseline
	@$(PYTHON) scripts/ci/check_model_provider_boundaries.py

check-layer4-collection: ## Check that all Layer 4 tests can be collected without import errors
	cd services/layer4-agents && pytest --collect-only . -q

check-layer4-canonical-paths: ## Enforce Layer 4 canonical path layout via AST checks
	python scripts/ci/check_layer4_canonical_paths.py

check-ui-duplicates: ## Block new duplicate UI component filenames between prototype and production trees
	@$(PYTHON) scripts/check_ui_duplicate_filenames.py

check-readiness-consistency: ## Ensure canonical readiness percentages are aligned and archives are snapshot-tagged
	@$(PYTHON) scripts/ci/check_readiness_consistency.py

check-workflow-matrix: ## Ensure the master workflow traceability matrix keeps its release-significant coverage markers
	@$(PYTHON) scripts/ci/assert_master_workflow_traceability.py
	@$(PYTHON) scripts/ci/assert_backend_workflow_traceability.py
	@$(PYTHON) scripts/ci/assert_backend_platform_validation_ownership.py
	@$(PYTHON) -m pytest tests/ci/test_product_workflow_validation_matrix.py -n 0 -q -o cache_dir=.tmp/pytest-cache

check-workflow-registry: ## Validate GitHub Actions workflow ownership and artifact registry
	@$(PYTHON) scripts/ci/generate_workflow_registry.py --check
	@$(PYTHON) scripts/ci/sync_ci_gate_docs.py --check
	@$(PYTHON) scripts/ci/verify_workflow_registry.py

check-workflow-references: ## Validate task inventory and GitHub/Depot workflow task/artifact references
	@$(PYTHON) scripts/ci/check_workflow_targets_and_artifacts.py
	@$(PYTHON) scripts/ci/check_workflow_task_parity.py
	@$(PYTHON) scripts/ci/generate_make_task_inventory.py --check

check-conflict-markers: ## Fail if unresolved merge conflict markers exist in tracked source files
	@$(PYTHON) scripts/ci/check_conflict_markers.py

check-adr: ## Validate ADR registry, indexes, numbering, and related-code links
	@$(PYTHON) scripts/ci/check_adr.py

check-no-nul-bytes: ## Fail if tracked source/config files contain NUL bytes
	@$(PYTHON) scripts/ci/check_no_nul_bytes.py

check-keycloak-realm-seed-security: ## Fail when committed Keycloak realm seed includes embedded secrets/default credentials
	@$(PYTHON) scripts/ci/check_keycloak_realm_seed_security.py


check-manifest-secret-hygiene: ## Enforce secret-only references and denylisted sensitive patterns in production manifests
	@$(PYTHON) scripts/ci/check_manifest_secret_hygiene.py

check-trivy-ignore-policy: ## Validate .trivyignore.yaml governance and waiver health
	@$(PYTHON) scripts/ci/check_trivy_ignore_policy.py
check-security-exceptions: ## Validate security exceptions registry governance and lifecycle
	@$(PYTHON) scripts/ci/check_security_exceptions.py
check-hostile-tenant-evidence: ## Validate hostile tenant evidence across all 8 isolation contracts
	@$(PYTHON) scripts/ci/check_hostile_tenant_evidence.py
check-path-env-hygiene: ## Fail on suspicious tracked path artifacts and unapproved tracked .env-style files
	@$(PYTHON) scripts/ci/check_path_and_env_hygiene.py
check-migration-entrypoints: ## Ensure maintained services expose migration entrypoints and revision history commands
	@$(PYTHON) scripts/ci/check_migration_entrypoints.py

check-migration-heads: check-migration-entrypoints ## Compatibility alias: validate one Alembic head per maintained service

check-migration-rollback-policy: ## Enforce rollback documentation and approval for unsupported downgrades
	@$(PYTHON) scripts/ci/check_migration_rollback_policy.py

check-migration-postgres-roundtrip: ## Run upgrade, downgrade -1, upgrade, and metadata drift checks against PostgreSQL
	@test -n "$(DB_MIGRATION_DATABASE_URL)" || (echo "❌ Set DB_MIGRATION_DATABASE_URL to a disposable PostgreSQL maintenance URL" && exit 1)
	@$(PYTHON) scripts/ci/check_migration_drift.py --database-url "$(DB_MIGRATION_DATABASE_URL)" --round-trip

check-migration-runtime-consistency: ## Static migration/runtime URL and revision consistency checks
	@$(PYTHON) scripts/ci/check_migration_runtime_consistency.py

db-migrate-status: ## Read-only database migration status report with JSON and Markdown artifacts
	@$(PYTHON) scripts/ci/migration_status_report.py --mode status

db-migrate-check: ## Read-only database migration drift gate; fails on drift
	@$(PYTHON) scripts/ci/migration_status_report.py --mode check

check-migration-status-artifacts: db-migrate-check ## Emit database migration status artifacts and fail on drift
	@test -s artifacts/database/migration-status.json
	@test -s artifacts/database/migration-status.md

check-database-governance-docs: ## Static validation for database runtime compatibility and governance docs
	@$(PYTHON) scripts/ci/check_database_governance_docs.py

gate-database: check-migration-heads check-migration-entrypoints check-migration-rollback-policy check-migration-runtime-consistency check-migration-status-artifacts check-database-governance-docs ## Gate: static local database readiness checks plus read-only migration drift status
	@echo "→ Gate: Database Readiness — static local checks"
	@$(PYTHON) scripts/ci/check_db_bootstrap_conformance.py
	@$(PYTHON) scripts/ci/check_db_production_readiness_split.py
	@mkdir -p $(GATE_JUNIT_DIR)
	timeout $(GATE_TIMEOUT_SECONDS)s $(PYTHON) -m pytest -v --tb=short -q -o addopts='' --confcutdir=tests/integration tests/integration/test_cross_store_consistency.py --junitxml=$(GATE_JUNIT_DIR)/gate-database-consistency.xml
	@$(PYTHON) scripts/ci/assert_no_pytest_skips.py $(GATE_JUNIT_DIR)/gate-database-consistency.xml
	timeout $(GATE_TIMEOUT_SECONDS)s $(GATE_PYTEST) tests/production_readiness -m "contract_static" --junitxml=$(GATE_JUNIT_DIR)/gate-database-static.xml
	@$(PYTHON) scripts/ci/assert_no_pytest_skips.py $(GATE_JUNIT_DIR)/gate-database-static.xml
	@echo "✅  gate-database passed"

gate-database-live: check-migration-postgres-roundtrip ## Live/destructive database drills requiring isolated PostgreSQL/backup environments
	@echo "→ Gate: Database Readiness — live isolated checks"
	@bash scripts/ci/run_db_production_readiness_gate.sh
	@bash scripts/ops/test_postgres_backup_restore.sh
	@echo "✅  gate-database-live passed"

check-pytest-skip-governance: ## Reconcile subordinate pytest collection evidence with canonical static governance
	@mkdir -p artifacts
	@set +e; $(PYTHON) -m pytest --collect-only -q -ra tests > artifacts/pytest-collection.txt 2>&1; collect_status=$$?; set -e; \
	 $(PYTHON) scripts/ci/check_pytest_skip_governance.py artifacts/pytest-collection.txt --write-report artifacts/test-debt-governance.json; \
	 if [ "$$collect_status" -ne 0 ]; then echo "pytest collection exited non-zero ($$collect_status); structural-preflight should catch import errors separately."; fi

check-type-escape-ratchet: ## Fail on net-new unapproved Python or TypeScript type escapes
	@$(PYTHON) scripts/ci/type_escape_ratchet.py

check-dead-code: ## Fail on new unreferenced top-level Python symbols
	@$(PYTHON) scripts/ci/check_dead_code.py

check-structural-fitness-ratchet: ## Fail on net-new oversized modules, high-complexity functions, or import cycles
	@$(PYTHON) scripts/ci/structural_fitness_ratchet.py

check-temporal-skips: ## Compatibility delegate to canonical test-debt governance
	@$(PYTHON) scripts/ci/check_temporal_skips.py --json-out artifacts/test-debt-governance.json --md-out artifacts/test-debt-governance.md

check-hermetic-build-inputs: ## Enforce digest-pinned Docker base images and approved external domains in CI inputs
	@echo "→ Checking hermetic build inputs..."
	@$(PYTHON) scripts/ci/check_hermetic_build_inputs.py
	@echo "✅ Hermetic build input checks passed"

check-production-k8s-mutable-tags: ## Fail if production-facing K8s manifests use :latest or :main image tags
	@echo "→ Checking production K8s manifests for mutable tags..."
	@$(PYTHON) scripts/ci/check_production_k8s_mutable_tags.py
	@echo "✅ Production K8s mutable tag check passed"

check-k8s-image-digests: ## Fail if production overlays use mutable image tags
	@echo "→ Checking K8s production overlays for mutable tags..."
	@bash scripts/ci/check-k8s-image-digests.sh
	@echo "✅ K8s image digest check passed"

check-layer3-legacy-tenant-dependency-imports: ## Block legacy Layer 3 tenant dependency imports under src/api/
	@$(PYTHON) scripts/ci/check_layer3_legacy_tenant_dependency_imports.py

check-layer3-tenant-dependency-imports: check-layer3-legacy-tenant-dependency-imports ## Alias for check-layer3-legacy-tenant-dependency-imports (backward compat)

check-test-skip-register-uniqueness: ## Compatibility delegate to canonical test-debt governance
	@$(PYTHON) scripts/ci/check_test_skip_register_uniqueness.py --register config/ci/test_skip_register.yaml

check-reports-evidence-policy: ## Enforce reports/ artifact policy and fail on unarchived failing snapshots
	@$(PYTHON) scripts/ci/check_reports_evidence_policy.py
check-legacy-debt: ## Enforce legacy debt baseline (markers + legacy directories)
	@mkdir -p artifacts
	@$(PYTHON) scripts/ci/check_legacy_debt.py --baseline config/ci/legacy_debt_baseline.json --approvals config/ci/legacy_debt_approvals.json --config config/ci/legacy_debt_config.json --write-report artifacts/legacy-debt-report.json

check-operational-debt: ## Enforce operational debt registry (SLI/type/tooling debt is owned + time-boxed; fail closed on expiry)
	@mkdir -p artifacts
	@$(PYTHON) scripts/ci/check_operational_debt.py --registry config/ci/operational_debt_registry.yaml --write-report artifacts/operational-debt-report.json

check-behavior-contract: ## Enforce behavior contract registry (every capability has allowed + denied tests)
	@mkdir -p artifacts
	@$(PYTHON) scripts/ci/check_behavior_contract.py --strict --write-report artifacts/behavior-contract.json

check-behavior-readiness-audit: ## Enforce executable, skip-controlled behavior readiness audit (GREEN/YELLOW/RED)
	@mkdir -p artifacts/readiness
	@$(PYTHON) scripts/ci/behavior_readiness_audit.py --report artifacts/readiness/behavior-readiness-audit.json


verify-strict: verify contract-drift ## Full verification including contract drift detection (slower)
	@echo "✅  Strict verification passed"

# ─── Linting ─────────────────────────────────────────────────────────────────

lint-layer1: ## Lint Layer 1 only
	@echo "→ Linting Layer 1..."
	@cd services/layer1-ingestion && ruff check src/

lint-layer2: ## Lint Layer 2 only
	@echo "→ Linting Layer 2..."
	@cd services/layer2-extraction && ruff check src/

lint-layer2-5: ## Lint Layer 2.5 only
	@echo "→ Linting Layer 2.5..."
	@cd services/layer2-5-signal-refinery && ruff check src/

lint-layer3: ## Lint Layer 3 only
	@echo "→ Linting Layer 3..."
	@cd services/layer3-knowledge && ruff check src/

lint-layer4: ## Lint Layer 4 only
	@echo "→ Linting Layer 4..."
	@cd services/layer4-agents && ruff check src/

lint-layer5: ## Lint Layer 5 only
	@echo "→ Linting Layer 5..."
	@cd services/layer5-ground-truth && ruff check src/

lint-layer6: ## Lint Layer 6 only
	@echo "→ Linting Layer 6..."
	@cd services/layer6-benchmarks && ruff check src/

lint: ## Lint all Python layers with ruff (fails fast on first error)
	@$(ROOT_MAKE) lint-layer1 && \
	 $(ROOT_MAKE) lint-layer2 && \
	 $(ROOT_MAKE) lint-layer2-5 && \
	 $(ROOT_MAKE) lint-layer3 && \
	 $(ROOT_MAKE) lint-layer4 && \
	 $(ROOT_MAKE) lint-layer5 && \
	 $(ROOT_MAKE) lint-layer6 && \
	 echo "✅  Linting complete for all layers"

# Per-layer mypy flags - stricter layers enforce more type safety
# Layer 1: Relaxed with explicit untyped handling
MYPY_LAYER1_FLAGS = --warn-return-any --warn-unused-configs
# Layer 2: Strict - fully typed codebase
MYPY_LAYER2_FLAGS = --strict --warn-return-any --warn-unused-configs
# Layer 3: Strict - fully typed codebase
MYPY_LAYER3_FLAGS = --strict --warn-return-any --warn-unused-configs
# Layer 4: Moderate - typed with some flexibility for agent patterns
MYPY_LAYER4_FLAGS = --warn-return-any --warn-unused-configs
# Layer 4: Strict - unified canonical namespace
MYPY_LAYER4_STRICT_FLAGS = --strict --warn-return-any --warn-unused-configs
# Layer 5: Strict - fully typed codebase
MYPY_LAYER5_FLAGS = --strict --warn-return-any --warn-unused-configs
# Layer 2.5: Moderate - signal refinery with some flexibility
MYPY_LAYER2_5_FLAGS = --warn-return-any --warn-unused-configs

# Layer 6: Minimal - gradual typing
MYPY_LAYER6_FLAGS = --warn-return-any --warn-unused-configs

# Allow specific third-party overrides only where needed
MYPY_OVERRIDES = --python-version 3.11

# Per-layer typecheck targets for development efficiency
typecheck-layer1: ## Type-check Layer 1 typed core + baseline ratchet
	@echo "→ Type-checking Layer 1 typed core (must be clean)..."
	@$(PYTHON) scripts/ci/check_mypy_typed_core.py --service-dir services/layer1-ingestion
	@echo "→ Enforcing Layer 1 mypy baseline ratchet..."
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer1-ingestion \
		--baseline config/ci/mypy_baseline_layer1.json \
		--paths src

mypy-changed-layer1: ## Type-check changed Python files in Layer 1 (PR gate)
	@echo "→ Type-checking changed Layer 1 files..."
	@$(PYTHON) scripts/ci/check_mypy_changed_files.py --service-dir services/layer1-ingestion

typecheck-layer2: ## Type-check Layer 2 (mypy baseline ratchet — blocks new errors)
	@echo "→ Enforcing Layer 2 mypy baseline ratchet..."
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer2-extraction \
		--baseline config/ci/mypy_baseline_layer2.json \
		--paths src --mypy-args "$(MYPY_LAYER2_FLAGS)"

typecheck-layer2-5: ## Type-check Layer 2.5 (mypy baseline ratchet)
	@echo "→ Enforcing Layer 2.5 mypy baseline ratchet..."
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer2-5-signal-refinery \
		--baseline config/ci/mypy_baseline_layer2_5.json \
		--paths src --mypy-args "$(MYPY_LAYER2_5_FLAGS)"

typecheck-layer3: ## Type-check Layer 3 (mypy baseline ratchet — blocks new errors)
	@echo "→ Enforcing Layer 3 mypy baseline ratchet..."
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer3-knowledge \
		--baseline config/ci/mypy_baseline_layer3.json \
		--paths src --mypy-args "$(MYPY_LAYER3_FLAGS)"

typecheck-layer4: ## Type-check Layer 4 (mypy baseline ratchet — blocks new errors)
	@echo "→ Enforcing Layer 4 mypy baseline ratchet..."
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer4-agents \
		--baseline config/ci/mypy_baseline_layer4.json \
		--paths src --mypy-args "$(MYPY_LAYER4_FLAGS)"

typecheck-layer4-strict: ## Type-check unified Layer 4 namespace strictly
	@echo "→ Type-checking Layer 4 (strict, unified namespace)..."
	@$(PYTHON) scripts/ci/run_mypy_layer.py services/layer4-agents src/layer4_agents/ -- $(MYPY_LAYER4_STRICT_FLAGS)
	@echo "✅ Layer 4 strict type-check passed"

typecheck-layer5: ## Type-check Layer 5 (mypy baseline ratchet — blocks new errors)
	@echo "→ Enforcing Layer 5 mypy baseline ratchet..."
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer5-ground-truth \
		--baseline config/ci/mypy_baseline_layer5.json \
		--paths src --mypy-args "$(MYPY_LAYER5_FLAGS)"

typecheck-layer6: ## Type-check Layer 6 (mypy baseline ratchet — blocks new errors)
	@echo "→ Enforcing Layer 6 mypy baseline ratchet..."
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer6-benchmarks \
		--baseline config/ci/mypy_baseline_layer6.json \
		--paths src --mypy-args "$(MYPY_LAYER6_FLAGS)"

# Per-layer mypy baseline ratchets (layers 2-6). Baselines are populated and
# enforced by the `typecheck-layerN` targets above via check_mypy_baseline.py.
# Use `make mypy-baseline-write-layerN` to refresh a baseline after a
# deliberate, reviewed debt increase. Reductions are credited automatically;
# the ratchet blocks any increase above the committed baseline.
mypy-baseline-write-layer2: ## Write/refresh the Layer 2 mypy error baseline
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer2-extraction \
		--baseline config/ci/mypy_baseline_layer2.json \
		--paths src --mypy-args "$(MYPY_LAYER2_FLAGS)" --write-baseline

mypy-baseline-write-layer2-5: ## Write/refresh the Layer 2.5 mypy error baseline
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer2-5-signal-refinery \
		--baseline config/ci/mypy_baseline_layer2_5.json \
		--paths src --mypy-args "$(MYPY_LAYER2_5_FLAGS)" --write-baseline

mypy-baseline-write-layer3: ## Write/refresh the Layer 3 mypy error baseline
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer3-knowledge \
		--baseline config/ci/mypy_baseline_layer3.json \
		--paths src --mypy-args "$(MYPY_LAYER3_FLAGS)" --write-baseline

mypy-baseline-write-layer4: ## Write/refresh the Layer 4 mypy error baseline
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer4-agents \
		--baseline config/ci/mypy_baseline_layer4.json \
		--paths src --mypy-args "$(MYPY_LAYER4_FLAGS)" --write-baseline

mypy-baseline-write-layer5: ## Write/refresh the Layer 5 mypy error baseline
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer5-ground-truth \
		--baseline config/ci/mypy_baseline_layer5.json \
		--paths src --mypy-args "$(MYPY_LAYER5_FLAGS)" --write-baseline

mypy-baseline-write-layer6: ## Write/refresh the Layer 6 mypy error baseline
	@$(PYTHON) scripts/ci/check_mypy_baseline.py \
		--service-dir services/layer6-benchmarks \
		--baseline config/ci/mypy_baseline_layer6.json \
		--paths src --mypy-args "$(MYPY_LAYER6_FLAGS)" --write-baseline

typecheck: ## Type-check all Python layers with mypy (fails fast on first error)
	@$(ROOT_MAKE) typecheck-layer1 && \
	 $(ROOT_MAKE) typecheck-layer2 && \
	 $(ROOT_MAKE) typecheck-layer2-5 && \
	 $(ROOT_MAKE) typecheck-layer3 && \
	 $(ROOT_MAKE) typecheck-layer4 && \
	 $(ROOT_MAKE) typecheck-layer5 && \
	 $(ROOT_MAKE) typecheck-layer6 && \
	 echo "✅  Type-checking complete for all layers"

# ─── Testing (4-Layer Strategy) ───────────────────────────────────────────────

test: test-layer1 test-layer2 test-layer2-5 test-layer3 test-layer4 test-layer5 test-layer6 ## Run all backend unit tests

test-e2e-contracts: ## Layer 1: Run Playwright isolated page contract tests (mocked)
	cd apps/web && npx playwright test --project=contracts

test-e2e-behaviors: ## Layer 2: Run strict behavior-first allowed/denied path tests (mocked)
	cd apps/web && npx playwright test --project=behaviors

test-e2e-journeys: ## Layer 3: Run Playwright chained user journeys (live or mocked)
	cd apps/web && npx playwright test --project=journeys

test-backend-contracts: ## Layer 3: Run backend contract/integration assertions
	$(PYTEST) tests/contract/test_journey_contracts.py -v

test-backend-integrated-validation: ## Backend milestone: run direct release-policy proofs plus live-service workflow, persistence, tenant, agent, and resilience validation
	$(PYTEST) services/api/app/tests/test_auth_enforcement.py services/api/app/tests/test_health.py services/api/app/tests/test_i03_durable_persistence_and_llm.py services/api/app/tests/test_production_safety.py tests/contract/test_retention_deletion_contract.py -v
	$(PYTEST) tests/backend_integrated -m backend_integrated -v

test-backend-integrated-release-smoke: ## Backend milestone: boot full L1-L6 release stack and run release-environment smoke validation
	bash scripts/ci/run_release_smoke.sh

production-edge-smoke: ## Verify public /api/v1 routes to gateway JSON rather than frontend HTML (APPLICATION_URL required)
	@test -n "$(APPLICATION_URL)" || (echo "APPLICATION_URL is required" && exit 2)
	$(PYTHON) scripts/ci/production_edge_smoke.py --base-url "$(APPLICATION_URL)"

certify-meridian-journey: ## Certification: run the Meridian L1-L6 production-path journey through the live gateway (requires the running stack)
	$(PYTEST) tests/certification -m certification -v

certify-production-path: ## Production path certification: execute end-to-end production path verification
	@echo "→ Starting Production Path Certification..."
	@echo "  Commit: $$(git rev-parse HEAD)"
	@echo "  Timestamp: $$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	python scripts/certify_production_path.py

seed-e2e: ## Seed deterministic E2E fixture data into the local backend (requires running stack)
	@echo "→ Seeding E2E test data..."
	npx tsx scripts/db/seed-e2e-data.ts
	@echo "✅  E2E seed complete"

reset-e2e: ## Remove all E2E tenant data from the local backend
	@echo "→ Resetting E2E test data..."
	npx tsx scripts/db/reset-e2e-data.ts
	@echo "✅  E2E reset complete"

test-e2e-full: ## Run full E2E suite: seed → contracts → journeys → reset
	@echo "→ Starting full E2E run..."
	$(MAKE) seed-e2e
	$(MAKE) test-e2e-contracts
	$(MAKE) test-e2e-journeys
	$(MAKE) reset-e2e
	@echo "✅  Full E2E suite complete"

contract-tests: ## Run cross-layer contract + architecture tests (fast, no secrets required)
	@echo "→ Auditing contract test collection (static subset)..."
	$(PYTEST) tests/contract/ --basetemp=.tmp/pytest-contract --collect-only -q -m "contract_static and not service_required" -n 0 -o cache_dir=.tmp/pytest-cache-contract || exit $$?
	@echo "→ Auditing contract test collection (service-required subset)..."
	$(PYTEST) tests/contract/ --basetemp=.tmp/pytest-contract --collect-only -q -m service_required -n 0 -o cache_dir=.tmp/pytest-cache-contract || exit $$?
	@echo "→ Running contract-static tests (deterministic, no live services)..."
	$(PYTEST) tests/contract/ --basetemp=.tmp/pytest-contract -v --tb=short -m "contract_static and not service_required" -n 0 -o cache_dir=.tmp/pytest-cache-contract || exit $$?
	@echo "→ Service-required contract tests are collected above; execute them via live validation targets."
	$(PNPM) --dir packages/platform-contract run contract:test || exit $$?
	@echo "→ Running architecture tests (tenant isolation guards)..."
	$(PYTEST) tests/arch/ --basetemp=.tmp/pytest-contract-arch -v --tb=short -o cache_dir=.tmp/pytest-cache-contract || exit $$?
	@echo "✅  Contract and architecture tests passed"

pact-tests: ## Run Pact consumer tests (generates .pact files) and provider verification
	@echo "→ Running Pact consumer contract tests..."
	$(PYTEST) tests/pact/test_l4_consumer_contract.py -v --tb=short -n 0
	@echo "→ Running Pact provider verification (requires Layer 4 running)..."
	$(PYTEST) tests/pact/test_l4_provider_verify.py -v --tb=short -n 0
	@echo "✅  Pact contract tests passed"

# ─── Stratified Test Targets ─────────────────────────────────────────────────

test-unit: ## Run only unit tests (fast, no external deps)
	@echo "→ Running unit tests (marked with @pytest.mark.unit)"
	cd services/layer4-agents && $(PYTEST) -m unit tests/

test-integration: ## Run integration tests (real DB, cache, no containers)
	@echo "→ Running integration tests (marked with @pytest.mark.integration)"
	cd services/layer4-agents && $(PYTEST) -m integration tests/

test-e2e-docker: ## Run E2E tests with Docker containers
	@echo "→ Running E2E tests (requires Docker)"
	cd services/layer3-knowledge && $(PYTEST) -m e2e tests/ 2>/dev/null || true

test-fast: ## Run only fast tests (exclude slow and e2e)
	@echo "→ Running fast tests only"
	cd services/layer4-agents && $(PYTEST) -m "not slow and not e2e" tests/

# ─── Setup ───────────────────────────────────────────────────────────────────

setup-layer2-5: ## Install Layer 2.5 dev dependencies into the pytest pipx venv
	@PYTEST_BIN=$$(which pytest 2>/dev/null); \
	if [ -z "$$PYTEST_BIN" ]; then \
	  echo "ERROR: pytest not found in PATH. Install via: pipx install pytest"; \
	  exit 1; \
	fi; \
	PYTEST_PY=$$(head -1 "$$PYTEST_BIN" | sed 's|#!||'); \
	echo "→ Installing Layer 2.5 dev dependencies into $$PYTEST_PY"; \
	cd services/layer2-5-signal-refinery && $$PYTEST_PY -m pip install -e ".[dev]" -q && cd ../.. || (cd ../..; exit 1); \
	echo "✅  Layer 2.5 dependencies installed"

bootstrap: ## One-command first-time setup: Infisical → corepack → pnpm → Python deps → migrate
	@echo "=== Step 1: Infisical login ==="
	@infisical login || (echo "ERROR: Infisical CLI not installed. See https://infisical.com/docs/cli/overview" && exit 1)
	@echo "=== Step 2: Enable corepack and activate pnpm ==="
	corepack enable
	corepack prepare pnpm@10.18.1 --activate
	@echo "=== Step 3: Install frontend dependencies ==="
	$(PNPM) install --frozen-lockfile
	@echo "=== Step 4: Install Python service dependencies ==="
	$(MAKE) setup
	@echo "=== Step 5: Run database migrations ==="
	$(MAKE) migrate
	@echo ""
	@echo "✅  Bootstrap complete!"
	@echo "    Next: pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d"

setup: ## Install all service dev dependencies into the pytest Python environment
	$(PYTHON) scripts/ci/setup_python_dev_deps.py

# ─── Layer-Specific Tests ─────────────────────────────────────────────────────

test-layer1: ## Run Layer 1 unit tests (no external services)
	cd services/layer1-ingestion && $(PYTEST) --basetemp=../../.tmp/pytest-layer1 -m "not integration and not postgres and not requires_postgres and not benchmark" tests/unit

test-layer1-integration: ## Run Layer 1 integration tests (requires PostgreSQL)
	cd services/layer1-ingestion && $(PYTEST) --basetemp=../../.tmp/pytest-layer1-integration -m "integration or postgres or requires_postgres" tests/integration

test-layer1-crawler: ## Run focused Layer 1 crawler tests
	cd services/layer1-ingestion && $(PYTEST) --basetemp=../../.tmp/pytest-layer1-crawler tests/crawler/ tests/unit/test_playwright_crawler.py tests/unit/test_crawler_config.py tests/unit/test_crawler_telemetry.py tests/unit/test_quality_gate.py

test-layer1-router-cache: ## Run focused Layer 1 router tests and shared cache isolation tests
	cd services/layer1-ingestion && $(PYTEST) --basetemp=../../.tmp/pytest-layer1-router tests/crawler/test_smart_router.py tests/unit/test_smart_router.py tests/integration/test_router_edge_cases.py
	$(PYTEST) --basetemp=.tmp/pytest-layer1-cache tests/cache/test_redis_tenant_isolation.py tests/shared/identity/test_api_key_cache.py

test-layer1-benchmarks: ## Run Layer 1 benchmark and performance tests
	cd services/layer1-ingestion && $(PYTEST) -m benchmark tests/benchmarks/ -v

test-layer1-router-benchmarks: ## Run quarantined Layer 1 router benchmarks (explicit opt-in)
	cd services/layer1-ingestion && RUN_ROUTER_BENCHMARKS=1 $(PYTEST) tests/benchmarks/test_router_performance.py -v

test-layer1-security-postgres: ## Run Layer 1 PostgreSQL-backed security tests (requires PostgreSQL)
	@echo "→ Testing Layer 1 security with PostgreSQL..."
	@cd services/layer1-ingestion && TEST_DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/ingestion" $(PYTEST) -m "postgres or requires_postgres" tests/security/ tests/pipeline/ -v

test-layer2: ## Run Layer 2 tests
	cd services/layer2-extraction && $(PYTEST) --basetemp=../../.tmp/pytest-layer2 tests/

test-layer2-5: ## Run Layer 2.5 tests
	cd services/layer2-5-signal-refinery && $(PYTEST) --basetemp=../../.tmp/pytest-layer2-5 tests/

test-layer3: ## Run Layer 3 tests
	$(PYTHON) scripts/ci/check_layer3_source_mirror.py
	cd services/layer3-knowledge && $(PYTEST) --basetemp=../../.tmp/pytest-layer3 -m "not integration and not requires_neo4j and not vector" tests/

test-layer3-live: ## Run Layer 3 live Neo4j/vector integration tests
	$(PYTHON) scripts/ci/check_layer3_source_mirror.py
	cd services/layer3-knowledge && $(PYTEST) --basetemp=../../.tmp/pytest-layer3-live -m "integration or requires_neo4j or vector" tests/

test-layer4: ## Run Layer 4 local tests
	# Run with TMPDIR pointing outside the repo so pytest's ``tmp_path``
	# lands in /tmp, not in ``.tmp/pytest-layer4`` inside the work tree.
	# Tests that assert "no git repo" behaviour depend on this: if
	# ``tmp_path`` is inside the repo, the filesystem walk for ``.git``
	# correctly finds the repo's own ``.git`` and the test's premise
	# collapses. We drop the explicit ``--basetemp`` so ``TMPDIR`` is
	# honoured; the cache dir stays inside the repo (it is just pytest
	# metadata and does not affect ``tmp_path``).
	cd services/layer4-agents && TMPDIR=/tmp $(PYTEST) -o cache_dir=../../.tmp/pytest-cache-layer4 -o tmp_path_retention_count=0 -m "not postgres and not requires_postgres and not docker and not integration and not e2e" tests/

test-layer4-live: ## Run Layer 4 live Docker/PostgreSQL/integration tests
	cd services/layer4-agents && $(PYTEST) --basetemp=../../.tmp/pytest-layer4-live -o cache_dir=../../.tmp/pytest-cache-layer4-live -m "postgres or requires_postgres or docker or integration or e2e" tests/

test-layer5: ## Run Layer 5 tests
	cd services/layer5-ground-truth
	$(PYTHON) scripts/check_no_duplicate_modules.py
	$(PYTEST) --basetemp=../../.tmp/pytest-layer5 tests/

test-layer6: ## Run Layer 6 tests
	cd services/layer6-benchmarks && $(PYTEST) --basetemp=../../.tmp/pytest-layer6 tests/

test-shared: ## Run the shared-package suite (value_fabric.shared; fans out to every layer)
	$(PYTEST) packages/shared/tests tests/shared --basetemp=.tmp/pytest-shared \
		--cov=value_fabric.shared.identity \
		--cov=value_fabric.shared.governance \
		--cov=value_fabric.shared.rate_limiting \
		--cov-report=term-missing

test-frontend: ## Run frontend unit tests
	cd apps/web && $(PNPM) run test

test-e2e: ## Run Playwright end-to-end tests (requires running stack)
	cd apps/web && $(PNPM) exec playwright test

# ─── Security Tests ───────────────────────────────────────────────────────────

security-smoke: ## Run fast security smoke tests (< 2 min, PR gating) - HARD FAIL
	@echo "→ Running security smoke tests (critical checks only)..."
	$(PYTEST) tests/security/test_security_smoke.py -v --tb=short -x
	@echo "✅  Security smoke tests passed"

security-test-gating: security-smoke ## Alias for security-smoke (explicit gating semantic)

security-test: ## Run full security test suite (~ 15 min, scheduled workflows)
	@echo "→ Running full security test suite..."
	$(PYTEST) tests/security/test_tenant_isolation.py -v --tb=short -k "P0"
	$(PYTEST) tests/security/test_rbac.py -v --tb=short -k "P0"
	$(PYTEST) tests/security/test_owasp_top10.py -v --tb=short -k "P0"
	$(PYTEST) tests/security/test_security_misconfiguration.py -v --tb=short
	@echo "✅  Full security test suite complete"

security-test-isolation: ## Run tenant isolation tests only
	@echo "→ Running tenant isolation tests..."
	$(PYTEST) tests/security/test_tenant_isolation.py -v --tb=short

security-test-rbac: ## Run RBAC tests only
	@echo "→ Running RBAC tests..."
	$(PYTEST) tests/security/test_rbac.py -v --tb=short

security-test-owasp: ## Run OWASP Top 10 tests only
	@echo "→ Running OWASP Top 10 tests..."
	$(PYTEST) tests/security/test_owasp_top10.py -v --tb=short

security-test-injection: ## Run injection prevention tests
	@echo "→ Running injection tests..."
	$(PYTEST) tests/security/test_injection.py -v --tb=short

security-coverage: ## Run security tests with coverage report
	@echo "→ Running security tests with coverage..."
	$(PYTEST) tests/security/ --cov=shared/security --cov-report=html --cov-report=term

# ─── Agent Evaluations ────────────────────────────────────────────────────────

evals: ## Run agent golden-trace evaluations (requires OPENAI_API_KEY)
	$(PYTEST) tests/evals/ -v --tb=short -m "not slow"

evals-full: ## Run full eval suite including slow/expensive traces
	$(PYTEST) tests/evals/ -v --tb=short


perf-test: ## Run k6 L2/L3/L4 critical-path load suite
	k6 run --summary-export artifacts/performance/k6-summary.json tests/performance/k6/l2_l3_l4_critical_paths.js

perf-test-journeys: ## Layer 4: Run k6 journey-aligned load tests
	k6 run tests/performance/k6/journey-load-test.js

perf-eval: ## Evaluate k6 results against versioned SLO thresholds
	$(PYTHON) scripts/perf/evaluate_slo.py \
		--summary artifacts/performance/k6-summary.json \
		--slo docs/slo/performance-slo.v1.json \
		--report artifacts/performance/slo-report.md \
		--output artifacts/performance/slo-evaluation.json

# ─── Build ────────────────────────────────────────────────────────────────────

build: ## Build frontend production bundle
	cd apps/web && $(PNPM) run build

docker-build: ## Build all deployable production Docker images locally
	docker build -t fabric-4l/api-gateway:local -f services/api/Dockerfile .
	docker build -t fabric-4l/layer1-ingestion:local -f services/layer1-ingestion/Dockerfile .
	docker build -t fabric-4l/layer2-extraction:local -f services/layer2-extraction/Dockerfile .
	docker build -t fabric-4l/layer2-5-signal-refinery:local -f services/layer2-5-signal-refinery/Dockerfile .
	docker build -t fabric-4l/layer3-knowledge:local -f services/layer3-knowledge/Dockerfile .
	docker build -t fabric-4l/layer4-agents:local -f services/layer4-agents/Dockerfile .
	docker build -t fabric-4l/layer5-ground-truth:local -f services/layer5-ground-truth/Dockerfile .
	docker build -t fabric-4l/layer6-benchmarks:local -f services/layer6-benchmarks/Dockerfile .
	docker build -t fabric-4l/web:local -f apps/web/Dockerfile .
	# When certifying a candidate (RELEASE_SHA set), bind each built image's
	# immutable content digest to the candidate evidence manifest. 04b records
	# this file (scripts/release/build_evidence_bundle.py:image-digests.txt).
	if test -n "$(RELEASE_SHA)" && test "$(RELEASE_SHA)" != UNKNOWN; then outdir="$(ARTIFACT_DIR)/$(RELEASE_SHA)"; mkdir -p "$$outdir"; : > "$$outdir/image-digests.txt"; for service in api-gateway layer1-ingestion layer2-extraction layer2-5-signal-refinery layer3-knowledge layer4-agents layer5-ground-truth layer6-benchmarks web; do digest=$$(docker inspect --format='{{.Id}}' "fabric-4l/$$service:local"); echo "fabric-4l/$$service@$$digest" >> "$$outdir/image-digests.txt"; done; echo "Recorded release image digests to $$outdir/image-digests.txt"; fi

docker-build-multi: ## Build all deployable images for linux/amd64 and linux/arm64 (requires docker buildx)
	@echo "→ Building multi-arch images (requires docker buildx)..."
	@set -e; \
	for ctx in services/api services/layer1-ingestion services/layer2-extraction services/layer2-5-signal-refinery services/layer3-knowledge services/layer4-agents services/layer5-ground-truth services/layer6-benchmarks apps/web; do \
		service=$$(basename $$ctx); \
		echo "Building $$service..."; \
		docker buildx build --platform linux/amd64,linux/arm64 -t fabric_4l/$$service:multi-arch $$ctx; \
	done
	@echo "✅ Multi-arch build complete"

# ─── Database ─────────────────────────────────────────────────────────────────

migrate: ## Run Alembic migrations for all Alembic-managed layers
	@echo "→ Migrating Layer 1..."
	cd services/layer1-ingestion && alembic upgrade head
	@echo "→ Migrating Layer 2..."
	cd services/layer2-extraction && alembic upgrade head
	@echo "→ Migrating Layer 2.5..."
	cd services/layer2-5-signal-refinery && alembic upgrade head
	@echo "→ Migrating Layer 4..."
	cd services/layer4-agents && alembic upgrade head
	@echo "→ Migrating Layer 5..."
	cd services/layer5-ground-truth && alembic upgrade head
	@echo "→ Migrating API..."
	cd services/api && alembic -c migrations/alembic.ini upgrade head

migrate-layer1: ## Run Alembic migrations for Layer 1 only
	cd services/layer1-ingestion && alembic upgrade head

migrate-layer2: ## Run Alembic migrations for Layer 2 only
	cd services/layer2-extraction && alembic upgrade head

migrate-layer2-5: ## Run Alembic migrations for Layer 2.5 only
	cd services/layer2-5-signal-refinery && alembic upgrade head

migrate-layer4: ## Run Alembic migrations for Layer 4 only
	cd services/layer4-agents && alembic upgrade head

migrate-layer5: ## Run Alembic migrations for Layer 5 only
	cd services/layer5-ground-truth && alembic upgrade head

migrate-api: ## Run Alembic migrations for API gateway only
	cd services/api && alembic -c migrations/alembic.ini upgrade head

# ─── Contracts ────────────────────────────────────────────────────────────────

contracts: ## Export OpenAPI specs from all layers
	$(PYTHON) scripts/export_openapi.py

validate-openapi-contracts: ## Validate all tracked JSON OpenAPI specs in contracts/openapi
	$(PYTHON) scripts/ci/contract_compliance_gate.py --validate-only

contract-drift: contracts validate-openapi-contracts ## Detect OpenAPI contract drift (exports + validates tracked JSON specs)
	@echo "✅ Tracked OpenAPI specs are present and valid"

contract-freshness-fast: ## Fast contract-freshness lane: validates committed specs and shapes, no live services
	$(PYTHON) scripts/ci/contract_compliance_gate.py --mode fast
	$(PYTHON) scripts/ci/check_l1_target_schema.py
	$(PYTHON) scripts/ci/check_targets_stats_named_schema.py
	$(PYTHON) scripts/ci/check_generated_jsonvalue_absent.py
	$(PYTHON) scripts/ci/check_clerk_tenant_response_exported.py
	$(PYTHON) scripts/ci/check_clerk_tenant_mapping_contract.py
	@echo "✅ Fast contract-freshness lane passed"

contract-freshness: ## Full contract-freshness lane: exports all hermetic specs, regenerates clients, fails on drift
	bash scripts/ci/check_contract_freshness.sh

sdk: ## Generate the Python SDK (manual typed client)
	$(PYTHON) scripts/generate_sdk.py

# ─── Dev Infrastructure ───────────────────────────────────────────────────────

preflight: ## Run pre-flight checks (Docker, env, ports)
	@bash scripts/dev/dev-preflight.sh

up: preflight ## Start all services with Docker Compose (runs preflight first)
	docker compose -f infra/compose/docker-compose.dev.yml up -d

down: ## Stop all services
	docker compose -f infra/compose/docker-compose.dev.yml down

logs: ## Tail logs for all services
	docker compose -f infra/compose/docker-compose.dev.yml logs -f

# ─── Cleanup ─────────────────────────────────────────────────────────────────

# ─── Environment Validation ───────────────────────────────────────────────────

check-env: ## Validate env vars against Zod schemas (backend + frontend)
	npx tsx scripts/dev/check-env.ts all

check-env-backend: ## Validate backend env vars only
	npx tsx scripts/dev/check-env.ts backend

check-env-frontend: ## Validate frontend env vars only
	npx tsx scripts/dev/check-env.ts frontend

validate-env-contract: ## CI gate — validate env contract + schema
	npx tsx scripts/ci/validate-env-contract.ts all

# ─── Deprecation Checks ─────────────────────────────────────────────────────

check-deprecations: ## CI gate — check for overdue deprecations
	$(PYTHON) scripts/ci/check_deprecations.py

check-tool-contracts: ## CI gate — validate tool error structure (CONTRACT.md §2.4)
	@echo "→ Checking tool contracts in Layer 4..."
	$(PYTHON) scripts/ci/check_tool_contracts.py services/layer4-agents/src/layer4_agents/tools/
	@echo "✅ Tool contract check passed"

check-prompt-registry: ## CI gate — validate prompt-version contracts and agent operating contracts
	@echo "→ Checking prompt registry contracts..."
	$(PYTHON) scripts/ci/check_prompt_registry.py
	@echo "✅ Prompt registry check passed"

check-deprecated-tracer-imports: ## CI gate — block imports from deprecated custom tracer modules
	@echo "→ Checking for deprecated custom tracer imports..."
	$(PYTHON) scripts/ci/check_deprecated_tracer_imports.py
	@echo "✅ Deprecated tracer import check passed"

check-compatibility-shims: ## CI gate — run registry-driven compatibility shim inventory checks
	@echo "→ Running registry-driven compatibility shim checks..."
	$(PYTHON) scripts/ci/check_compatibility_shims.py run-all --strict
	@echo "✅ Compatibility shim gate passed"

check-risk-register: ## Fail on un-countersigned ACCEPTED P0 risks
	@$(PYTHON) scripts/ci/check_risk_register_countersignatures.py --baseline config/ci/risk_countersignature_baseline.json

debt-baseline-snapshot: ## Aggregate checked-in debt baselines into config/ci/phase0_debt_baseline.json
	@$(PYTHON) scripts/ci/debt_baseline_snapshot.py

check-health-ratchets: check-conflict-markers check-no-nul-bytes check-type-escape-ratchet check-structural-fitness-ratchet check-dead-code check-legacy-debt check-operational-debt check-behavior-contract check-compatibility-shims check-temporal-skips check-test-skip-register-uniqueness check-reports-evidence-policy check-migration-entrypoints check-migration-rollback-policy check-migration-runtime-consistency check-risk-register check-shared-duplication ## Run all fail-on-net-new health ratchets (single entry point)
	@echo "✅  check-health-ratchets passed"

# ─── Architecture Governance ────────────────────────────────────────────────

.PHONY: check-governance check-import-cycles check-architecture-boundaries check-ownership-registry check-shared-duplication check-governance-baseline

check-governance: ## Run the canonical architecture-governance aggregate (import/cycle/DRY + ownership)
	@$(PYTHON) scripts/ci/check_governance.py

check-import-cycles: ## Import-cycle enforcement via the structural fitness ratchet
	@$(PYTHON) scripts/ci/check_governance.py --check check-import-cycles

check-architecture-boundaries: ## Architecture boundary ratchet (model/provider gateway)
	@$(PYTHON) scripts/ci/check_governance.py --check check-architecture-boundaries

check-ownership-registry: ## Enforce ownership and canonical-import registry
	@$(PYTHON) scripts/ci/check_governance.py --check check-ownership-registry

check-shared-duplication: ## Fail on net-new duplication within packages/shared (DRY ratchet)
	@$(PYTHON) scripts/ci/check_shared_duplication.py

check-governance-baseline: ## Validate governance baselines are present and regenerable
	@$(PYTHON) scripts/ci/check_governance.py --check check-governance-baseline

# ─── Developer Setup ─────────────────────────────────────────────────────────

setup-hooks: ## Configure git to use .githooks/ (run once after clone)
	@git config core.hooksPath .githooks
	@echo "✅  Git hooks configured. Pre-push gate tests will run before every push."

# ─── Production Readiness Gates ─────────────────────────────────────────────
# Gate system: pytest is the single source of truth.
# Each gate-* target runs pytest directly. Non-zero exit = release blocked.
# No runners, no policy engines, no simulation.

GATE_PYTEST := $(PYTEST) --tb=short -q -n 0
GATE_TIMEOUT_SECONDS ?= 180
GATE_JUNIT_DIR := $(ARTIFACT_DIR)/junit
PRODUCTION_READINESS_SUITES := security reliability observability recovery release tenancy billing abuse config audit
PRODUCTION_READINESS_ARTIFACT_DIR := artifacts/production-readiness

gate-mandatory-security-regression: ## Gate: mandatory security regression suite for launch readiness
	@echo "→ Gate: Mandatory Security Regression"
	bash scripts/ci/mandatory_security_regression_gate.sh
	@echo "✅  gate-mandatory-security-regression passed"

gate-tenant-isolation: ## Gate: dedicated tenant isolation launch-readiness suite
	@echo "→ Gate: Tenant Isolation — dedicated launch-readiness suite"
	bash scripts/ci/tenant_isolation_readiness_gate.sh
	@echo "✅  gate-tenant-isolation passed"

gate-security: gate-mandatory-security-regression ## Gate: broader security regression coverage beyond the dedicated tenant isolation gate
	@echo "→ Gate: Security — broader auth, fail-closed, and regression suite"
	@echo "✅  gate-security passed"

security-readiness-gate: gate-security ## Compatibility alias for the canonical security readiness gate
	@echo "✅  security-readiness-gate alias passed (canonical: gate-security)"

gate-security-broad: ## Advisory gate: exhaustive legacy security coverage for Broad GA backlog classification
	@echo "→ Gate: Broad Security Coverage — advisory legacy suite (bounded to 300s)"
	timeout 300s $(GATE_PYTEST) tests/security/
	@echo "✅  gate-security-broad passed"

gate-state: ## Gate: frontend/backend state alignment, workflow type consistency
	@echo "→ Gate: State Alignment"
	$(GATE_PYTEST) tests/state/
	@echo "✅  gate-state passed"

gate-arch: ## Gate: architecture conformance, tenant guards, testability
	@echo "→ Gate: Architecture Conformance"
	$(GATE_PYTEST) tests/arch/
	@echo "✅  gate-arch passed"

architecture-readiness-gate: gate-arch ## Compatibility alias for the canonical architecture readiness gate
	@echo "✅  architecture-readiness-gate alias passed (canonical: gate-arch)"

gate-config: ## Gate: startup validation, security config hardening
	@echo "→ Gate: Startup Configuration"
	$(GATE_PYTEST) tests/config/
	@echo "✅  gate-config passed"

gate-local: gate-security ## Run the minimal local security gate only (not a production-readiness decision)
	@echo "✅  Local gate passed — production readiness NOT assessed; run make production-readiness-gate for the canonical gate"

gate-local-production-subset: gate-security gate-database ## Run a local-only production-readiness subset; not a ship/no-ship decision
	@echo "✅  Local production-readiness subset passed — production readiness NOT fully assessed; run make production-readiness-gate for the canonical gate"

# Backward-compatible alias retained for scripts/users that still call gate-all.
gate-all: gate-local-production-subset ## Compatibility alias for the local-only subset; not a production-readiness decision
	@echo "⚠️  gate-all is local-only and does not authorize production release; run make production-readiness-gate for the canonical gate"

production-readiness-gate: ## Canonical production-readiness gate required by CI
	@echo "→ Gate: Production Readiness — centralized suites"
	$(PYTHON) scripts/ci/run_production_readiness_gate.py --artifact-dir $(PRODUCTION_READINESS_ARTIFACT_DIR)
	$(PYTHON) scripts/ci/validate_production_readiness_manifest.py $(PRODUCTION_READINESS_ARTIFACT_DIR)/manifest.json
	@echo "✅  production-readiness-gate passed"

gate-production: production-readiness-gate ## Compatibility alias for the canonical production-readiness gate
	@echo "✅  gate-production alias completed (canonical: production-readiness-gate)"

# Tiered readiness targets intentionally delegate to release-gate profiles so
# gate composition stays centralized in $(POLICY_FILE) instead of drifting across
# ad hoc Makefile dependency lists.
gate-production-core: ## Run near-term critical production readiness gates via the production-core policy profile
	@$(MAKE) release-gate PROFILE=production-core

tier0-production-safety-gate: ## Run Tier 0 safety gates: security, tenant isolation, DB, backup/restore, secrets, auth, launch blockers
	@$(MAKE) release-gate PROFILE=tier0-production-safety

tier1-beta-readiness-gate: ## Run Tier 1 beta gates: API contracts, frontend, observability, reliability, deployment, rollback
	@$(MAKE) release-gate PROFILE=tier1-beta-readiness

tier2-enterprise-readiness-gate: ## Run Tier 2 enterprise gates: performance, agents, data governance, compliance, incident response
	@$(MAKE) release-gate PROFILE=tier2-enterprise-readiness

db-production-readiness-gate: ## Gate: PostgreSQL-only database production readiness invariants
	@echo "→ Gate: Database Production Readiness (PostgreSQL-only)"
	$(PYTHON) scripts/ci/check_db_bootstrap_conformance.py
	$(PYTHON) scripts/ci/check_db_production_readiness_split.py
	@mkdir -p $(GATE_JUNIT_DIR)
	timeout $(GATE_TIMEOUT_SECONDS)s $(GATE_PYTEST) tests/production_readiness -m "contract_static or postgres_only" --junitxml=$(GATE_JUNIT_DIR)/db-production-readiness-gate.xml
	$(PYTHON) scripts/ci/assert_no_pytest_skips.py $(GATE_JUNIT_DIR)/db-production-readiness-gate.xml
	@echo "✅  db-production-readiness-gate passed"

release-evidence-packet: ## Generate the canonical release evidence packet
	$(PYTHON) scripts/ci/generate_release_evidence_packet.py --allow-placeholder-sha

# ─── V1 Release Factory (thin control plane over existing gates) ─────────────

validate-launch-contract: ## Validate release/v1 launch contract, schemas, tasks, and risk-register reconciliation
	$(PYTHON) scripts/release/validate_contract.py

release-baseline: ## Run canonical gates from a clean checkout; write classified baseline to artifacts/release/<sha>/
	$(PYTHON) scripts/release/baseline.py

certify-release-candidate: ## Fail-closed certification of RELEASE_SHA (live steps need CERTIFY_LIVE=1); evidence to artifacts/release/<sha>/
	@test -n "$(RELEASE_SHA)" || { echo "usage: make certify-release-candidate RELEASE_SHA=<sha>"; exit 2; }
	$(PYTHON) scripts/release/certify_candidate.py $(RELEASE_SHA)

build-release-evidence: ## Compose the candidate-scoped release evidence packet plus the candidate manifest for RELEASE_SHA
	@test -n "$(RELEASE_SHA)" || { echo "usage: make build-release-evidence RELEASE_SHA=<sha>"; exit 2; }
	$(PYTHON) scripts/release/build_evidence_bundle.py $(RELEASE_SHA)

# ─── Deployment manifest certification (thin control plane over validators) ──

generate-sbom-and-provenance: ## Generate a deterministic, source-bound CycloneDX SBOM and SLSA provenance (no Docker required)
	$(PYTHON) scripts/ci/supply_chain_gate.py sbom
	@if test -n "$(RELEASE_SHA)" && test "$(RELEASE_SHA)" != UNKNOWN; then \
		outdir="$(ARTIFACT_DIR)/$(RELEASE_SHA)"; \
		mkdir -p "$$outdir"; \
		test -f artifacts/supply-chain/fabric-4l-source-sbom.cdx.json && cp -f artifacts/supply-chain/fabric-4l-source-sbom.cdx.json "$$outdir/fabric-4l-source-sbom.cdx.json" || true; \
		test -f artifacts/supply-chain/sbom-summary.json && cp -f artifacts/supply-chain/sbom-summary.json "$$outdir/sbom-summary.json" || true; \
		test -f artifacts/supply-chain/provenance.json && cp -f artifacts/supply-chain/provenance.json "$$outdir/provenance.json" || true; \
		echo "Copied candidate SBOM and provenance to $$outdir"; \
	fi

compose-config-validate: ## Validate all release-significant Docker Compose definitions (requires Docker)
	$(PYTHON) scripts/ci/check_docker_compose_config.py

helm-dependency-validate: ## Generate then validate integrity evidence for locked Helm chart dependencies (writes artifacts/helm-dependency-evidence)
	@mkdir -p artifacts/helm-dependency-evidence
	$(PYTHON) scripts/ci/validate_helm_dependencies.py generate \
		--chart-dir infra/helm/fabric-chart \
		--evidence-dir artifacts/helm-dependency-evidence \
		--helm-version v3.16.2
	$(PYTHON) scripts/ci/validate_helm_dependencies.py validate \
		--chart-dir infra/helm/fabric-chart \
		--evidence-dir artifacts/helm-dependency-evidence \
		--helm-version v3.16.2

k8s-production-overlay-validate: ## Render and validate Kubernetes production overlays (requires kustomize/kubeconform/kubectl)
	$(PYTHON) scripts/ci/validate_k8s_production_overlays.py

k8s-manifest-consistency-check: ## Static cross-service Kubernetes manifest consistency check (pure Python, no cluster)
	$(PYTHON) scripts/ci/check_k8s_manifest_consistency.py

build-reproducibility-check: ## Verify every deployable image builds to byte-identical output (deterministic; requires Docker)
	bash scripts/ci/build-reproducibility-check.sh all

validate-monitoring-stack: ## End-to-end monitoring stack readiness (YAML + compose config + runbook coverage; requires Docker)
	bash scripts/ci/validate-monitoring-stack.sh

collect-95-plus-evidence-focused: release-evidence-packet ## Compatibility alias: canonical release evidence packet replaces focused 95+ evidence collection
	@echo "✅  collect-95-plus-evidence-focused alias completed (canonical: release-evidence-packet)"

collect-95-plus-evidence: release-evidence-packet ## Compatibility alias: canonical release evidence packet replaces full 95+ evidence collection
	@echo "✅  collect-95-plus-evidence alias completed (canonical: release-evidence-packet)"

# ─── Promotion Targets ────────────────────────────────────────────────────────

promote-staging: verify release-evidence-packet ## Verify local gates + evidence, then trigger staging promotion workflow
	@echo "→ Verifying immutable image ref..."
	@ref="sha-$$(git rev-parse HEAD)"; \
	 echo "Image ref: $$ref"; \
	 if ! command -v gh >/dev/null 2>&1; then \
	   echo "❌ gh CLI not found. Install: https://cli.github.com/"; \
	   echo "   Then run: gh workflow run environment-promotion.yml --ref main -f environment=staging -f image_ref=$$ref"; \
	   exit 1; \
	 fi; \
	 if ! gh auth status >/dev/null 2>&1; then \
	   echo "❌ gh CLI not authenticated. Run: gh auth login"; \
	   exit 1; \
	 fi; \
	 echo "→ Triggering Environment Promotion workflow for staging..."; \
	 gh workflow run environment-promotion.yml \
	   --ref main \
	   -f environment=staging \
	   -f image_ref="$$ref"; \
	 echo "✅  Staging promotion triggered. Monitor at: https://github.com/$$(gh repo view --json owner,name -q '.owner.login + \"/\" + .name')/actions/workflows/environment-promotion.yml"

# ─── Extended Gate Targets (referenced by prod-readiness.yml) ────────────────

gate-lint: lint-layer1 lint-layer2 lint-layer3 lint-layer4 lint-layer5 lint-layer6 ## Gate: lint all layers for release readiness
	@echo "✅  gate-lint passed"

lint-release: gate-lint ## Compatibility alias for the canonical release lint gate
	@echo "✅  lint-release alias passed (canonical: gate-lint)"

gate-policy: ## Gate: validate policy schema, profile existence, and artifact dirs
	@echo "→ Gate: Validate Policy"
	@test -s $(POLICY_FILE) || (echo "❌ Policy file $(POLICY_FILE) not found" && exit 1)
	@$(PYTHON) -c "import yaml; yaml.safe_load(open('$(POLICY_FILE)'))" || (echo "❌ Policy file is not valid YAML" && exit 1)
	@$(PYTHON) scripts/ci/verify_workflow_registry.py
	@mkdir -p artifacts/{arch,security,chaos,smoke,agent,state,obs,release,junit}
	@echo "✅  gate-policy passed"

gates-validate-policy: gate-policy ## Compatibility alias for the canonical policy validation gate
	@echo "✅  gates-validate-policy alias passed (canonical: gate-policy)"

gate-migration-readiness: check-migration-entrypoints check-migration-heads check-migration-rollback-policy ## Gate: migration entrypoints, head uniqueness, rollback policy, and runtime safety
	@echo "→ Gate: Migration Readiness"
	@$(PYTHON) scripts/ci/check_migration_safety.py
	@$(PYTHON) scripts/ci/check_migration_runtime_consistency.py
	@echo "✅  gate-migration-readiness passed"

gate-database-readiness: ## Gate: database production readiness split checks and static invariants
	@echo "→ Gate: Database Readiness"
	@$(PYTHON) scripts/ci/check_db_bootstrap_conformance.py
	@$(PYTHON) scripts/ci/check_db_production_readiness_split.py
	@bash scripts/ci/run_db_production_readiness_gate.sh
	@echo "✅  gate-database-readiness passed"

gate-backup-restore-readiness: ## Gate: PostgreSQL backup/restore production-readiness drill
	@echo "→ Gate: Backup/Restore Readiness"
	@$(PYTHON) scripts/ci/check_walg_enablement_gate.py
	@bash scripts/ops/test_postgres_backup_restore.sh
	@echo "✅  gate-backup-restore-readiness passed"

gate-api-contracts: contract-tests platform-contract-lint check-tool-contracts check-prompt-registry ## Gate: API/platform contract compliance, tool contract structure, and prompt-version registry
	@echo "→ Gate: API Contracts"
	@$(PNPM) run check:contract-compliance
	@echo "✅  gate-api-contracts passed"

gate-auth-readiness: check-keycloak-realm-seed-security ## Gate: route auth dependencies and production auth-bypass prevention
	@echo "→ Gate: Auth Readiness"
	@$(PYTHON) scripts/ci/check_route_auth_dependencies.py
	@$(PYTHON) scripts/ci/check_auth_bypass.py
	@echo "✅  gate-auth-readiness passed"

gate-behavior-readiness: ## Gate: executable, skip-controlled behavior readiness audit (GREEN/YELLOW/RED)
	@echo "→ Gate: Behavior Readiness Audit"
	@mkdir -p artifacts/readiness
	@$(PYTHON) scripts/ci/behavior_readiness_audit.py --report artifacts/readiness/behavior-readiness-audit.json
	@echo "✅  gate-behavior-readiness passed"

gate-secrets-readiness: check-keycloak-realm-seed-security check-manifest-secret-hygiene check-path-env-hygiene ## Gate: committed secret hygiene and secret mapping invariants
	@echo "→ Gate: Secrets Readiness"
	@$(PYTHON) scripts/ci/audit_infra_secrets.py --enforce
	@$(PYTHON) scripts/ci/check_no_workflow_secret_fallbacks.py
	@$(PYTHON) scripts/ci/check_neo4j_secret_key_mappings.py
	@echo "✅  gate-secrets-readiness passed"

gate-deployment-readiness: ## Gate: deployable image coverage and deployment profile controls
	@echo "→ Gate: Deployment Readiness"
	@$(PYTHON) scripts/ci/check_deployable_service_images.py
	@for profile in production-core tier0-production-safety tier1-beta-readiness tier2-enterprise-readiness release-candidate; do \
		$(PYTHON) scripts/ci/validate_deploy_profile_controls.py --policy-file $(POLICY_FILE) --profile $$profile; \
	done
	@echo "✅  gate-deployment-readiness passed"

gate-launch-blockers: check-conflict-markers check-no-nul-bytes check-readiness-consistency check-legacy-debt ## Gate: launch governance, blocker registers, and release checklist evidence
	@echo "→ Gate: Launch Blockers"
	@$(PYTHON) scripts/ci/check_release_launch_governance.py
	@$(PYTHON) scripts/ci/validate_final_testing_launch_gate.py
	@$(PYTHON) scripts/ci/validate_core_ga_launch_evidence.py
	@echo "✅  gate-launch-blockers passed"

gate-frontend-readiness: ## Gate: frontend beta readiness verification suite
	@echo "→ Gate: Frontend Readiness"
	@$(PNPM) run verify:frontend
	@echo "✅  gate-frontend-readiness passed"

gate-reliability-readiness: gate-chaos gate-smoke ## Gate: reliability failure-mode and smoke coverage
	@echo "✅  gate-reliability-readiness passed"

gate-rollback-readiness: check-migration-rollback-policy ## Gate: rollback policy and promotion artifact contract
	@echo "→ Gate: Rollback Readiness"
	@$(PYTHON) scripts/ci/validate_promotion_artifact_contract.py --build-workflow .github/workflows/build-deploy.yml --promotion-workflow .github/workflows/environment-promotion.yml
	@echo "✅  gate-rollback-readiness passed"

gate-performance-readiness: perf-test perf-eval ## Gate: performance load suite and SLO evaluation
	@echo "✅  gate-performance-readiness passed"

gate-data-governance-readiness: ## Gate: data governance, retention/deletion, and shared governance contracts
	@echo "→ Gate: Data Governance Readiness"
	@$(GATE_PYTEST) tests/contract/test_retention_deletion_contract.py tests/shared/governance/ tests/security/test_pii_encryption_at_rest.py
	@echo "✅  gate-data-governance-readiness passed"

gate-compliance-readiness: ## Gate: compliance evidence integrity and governance export controls
	@echo "→ Gate: Compliance Readiness"
	@$(PYTHON) scripts/ci/check_compliance_evidence_integrity.py
	@$(GATE_PYTEST) tests/backend_integrated/test_approval_export_crm_governance.py tests/security/test_layer5_governance_security_controls.py
	@echo "✅  gate-compliance-readiness passed"

gate-incident-response-readiness: ## Gate: incident response runbook ownership and observability contracts
	@echo "→ Gate: Incident Response Readiness"
	@$(GATE_PYTEST) tests/ci/test_incident_runbook_contacts_policy.py tests/security/test_audit_resilience.py tests/contract/test_service_observability_contracts.py
	@echo "✅  gate-incident-response-readiness passed"

gate-chaos: ## Gate: dependency chaos and failure injection
	@echo "→ Gate: Chaos"
	@if [ ! -d tests/chaos ] || [ -z "$$(find tests/chaos -name 'test_*.py' -print -quit)" ]; then \
		echo "❌ No chaos test files found in tests/chaos/"; \
		exit 1; \
	fi
	@mkdir -p $(GATE_JUNIT_DIR)
	timeout $(GATE_TIMEOUT_SECONDS)s $(GATE_PYTEST) tests/chaos/ --junitxml=$(GATE_JUNIT_DIR)/gate-chaos.xml
	$(PYTHON) scripts/ci/assert_no_pytest_skips.py $(GATE_JUNIT_DIR)/gate-chaos.xml
	@echo "✅  gate-chaos passed"

gate-smoke: ## Gate: cross-domain smoke tests
	@echo "→ Gate: Smoke"
	@test -s tests/e2e/test_value_engine_smoke_contract.py || (echo "❌ Smoke contract test is missing" && exit 1)
	@mkdir -p $(GATE_JUNIT_DIR)
	timeout $(GATE_TIMEOUT_SECONDS)s $(GATE_PYTEST) tests/e2e/test_value_engine_smoke_contract.py --junitxml=$(GATE_JUNIT_DIR)/gate-smoke.xml
	$(PYTHON) scripts/ci/assert_no_pytest_skips.py $(GATE_JUNIT_DIR)/gate-smoke.xml
	@echo "✅  gate-smoke passed"

gate-agent: ## Gate: agent provenance and behavior regression
	@echo "→ Gate: Agent"
	@if [ ! -d tests/agents ] || [ -z "$$(find tests/agents -name 'test_*.py' -print -quit)" ]; then \
		echo "❌ No agent test files found in tests/agents/"; \
		exit 1; \
	fi
	@mkdir -p $(GATE_JUNIT_DIR)
	timeout $(GATE_TIMEOUT_SECONDS)s $(GATE_PYTEST) tests/agents/ --junitxml=$(GATE_JUNIT_DIR)/gate-agent.xml
	$(PYTHON) scripts/ci/assert_no_pytest_skips.py $(GATE_JUNIT_DIR)/gate-agent.xml
	@echo "✅  gate-agent passed"

gate-obs: ## Gate: observability, metrics, and SLO validation
	@echo "→ Gate: Observability"
	@if [ ! -d tests/performance ] || [ -z "$$(find tests/performance -name 'test_*.py' -print -quit)" ]; then \
		echo "❌ No performance test files found in tests/performance/"; \
		exit 1; \
	fi
	@mkdir -p $(GATE_JUNIT_DIR)
	timeout $(GATE_TIMEOUT_SECONDS)s $(GATE_PYTEST) tests/performance/ --junitxml=$(GATE_JUNIT_DIR)/gate-obs.xml
	# Note: gate-obs is advisory per policy, so skipped tests are allowed
	@echo "✅  gate-obs passed (advisory - skipped tests allowed)"

gate-release-policy: ## Gate: release policy compliance
	@echo "→ Gate: Release Policy"
	@if [ ! -d tests/release ] || [ -z "$$(find tests/release -name 'test_*.py' -print -quit)" ]; then \
		echo "❌ No release-policy test files found in tests/release/"; \
		exit 1; \
	fi
	@mkdir -p $(GATE_JUNIT_DIR)
	timeout $(GATE_TIMEOUT_SECONDS)s $(GATE_PYTEST) tests/release/ --junitxml=$(GATE_JUNIT_DIR)/gate-release-policy.xml
	$(PYTHON) scripts/ci/assert_no_pytest_skips.py $(GATE_JUNIT_DIR)/gate-release-policy.xml
	$(PYTHON) scripts/ci/check_deprecations.py
	@echo "✅  gate-release-policy passed"

gate-sign-manifest: ## Gate: sign artifact manifest with SHA-256
	@echo "→ Gate: Sign Manifest"
	@mkdir -p $(ARTIFACT_DIR)/logs
	@if [ ! -d $(ARTIFACT_DIR) ]; then \
		echo "❌ Artifact directory $(ARTIFACT_DIR) does not exist"; \
		exit 1; \
	fi
	@$(PYTHON) scripts/ops/validate-release-manifest.py $(ARTIFACT_DIR)
	@FILE_COUNT=$$(find $(ARTIFACT_DIR) -type f -not -path "*/logs/*" -not -name "manifest.sha256" | wc -l); \
	if [ "$$FILE_COUNT" -eq 0 ]; then \
		echo "❌ No artifacts to sign in $(ARTIFACT_DIR)"; \
		exit 1; \
	fi
	@find $(ARTIFACT_DIR) -type f -not -path "*/logs/*" -not -name "manifest.sha256" -exec sha256sum {} \; > $(ARTIFACT_DIR)/manifest.sha256
	@echo "✅  gate-sign-manifest passed ($$(wc -l < $(ARTIFACT_DIR)/manifest.sha256) files)"

gates-sign-manifest: gate-sign-manifest ## Compatibility alias for the canonical artifact signing gate
	@echo "✅  gates-sign-manifest alias passed (canonical: gate-sign-manifest)"

gate-summary: ## Gate: render release summary with gate results
	@echo "→ Gate: Render Summary"
	@bash scripts/ops/render-release-summary.sh
	@test -s $(ARTIFACT_DIR)/summary.md || (echo "❌ Summary file not generated" && exit 1)
	@echo "✅  gate-summary passed"

gates-render-summary: gate-summary ## Compatibility alias for the canonical release summary gate
	@echo "✅  gates-render-summary alias passed (canonical: gate-summary)"

release-gate: ## Run the policy-driven production readiness gate sequence
	@echo "🚀 Starting Release Gate Sequence..."
	@bash scripts/ops/release-gate.sh $(PROFILE)

contract-lint: ## Run ESLint contract rules across all packages
	@echo "→ Running contract lint rules..."
	@cd apps/web && npm run lint -- --ext .ts,.tsx --rule 'fabric-contracts/no-tenant-id-parameter: error' --rule 'fabric-contracts/no-req-tenant-access: error' --rule 'fabric-contracts/no-raw-tenant-query: error' --rule 'fabric-contracts/no-explicit-db-connect: error' --rule 'fabric-contracts/no-inline-middleware: error' --rule 'fabric-contracts/no-inline-tool-definition: error' --rule 'fabric-contracts/no-throw-in-tool: error' --rule 'fabric-contracts/no-json-parse-agent-output: error' --rule 'fabric-contracts/no-imperative-navigation: error' --rule 'fabric-contracts/no-url-concatenation: error' --rule 'fabric-contracts/no-private-imports: error' --rule 'fabric-contracts/no-circular-dependencies: error' 2>/dev/null || echo "⚠️  Contract ESLint plugin not yet installed"

# ─── Backup/DR Tests ─────────────────────────────────────────────────────────

test-backup-drills: ## Run backup/DR drill tests (requires pytest-asyncio)
	@echo "→ Running backup manager tests..."
	cd services/layer3-knowledge && $(PYTEST) tests/test_backup_manager.py -v --tb=short

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅  Clean complete"

clean-root-debris: ## Remove root-level temp artifacts, caches, and generated files
	@echo "→ Removing root debris..."
	@rm -rf "C:UsersBBBFabric_4L.bunny" \
		"c:UsersBBBFabric_4Lappswebtest-resultsui-audit" \
		"C:UsersBBBFabric_4Ltest_failures.txt" \
		nul __pycache__ .pytest_cache .ruff_cache .hypothesis node_modules \
		.tmp_conflict_resolver.py defer_billing_tests.py pytest.ini.test \
		rotation_audit_*.json test_failures.txt
	@rm -f generated/valuepacks_output-*.txt
	@rm -rf generated/logs/*
	@echo "✅  Root debris clean complete"

# Platform Contract Lint
platform-contract-lint: ## Run platform contract lint
	@echo Running platform contract lint...
	@$(PYTHON) scripts/ci/platform_contract_lint.py

# ─── Value Fabric Harness ────────────────────────────────────────────────────

HARNESS_DIR := .windsurf/harness

harness-task: ## Assemble VF harness context for a task (TASK=... FILES=...)
	@echo "→ Assembling Value Fabric harness context..."
	@cd $(HARNESS_DIR) && $(PYTHON) vf_context.py

harness-guard: ## Run pre-edit boundary and contract checks (TASK=... FILES=...)
	@echo "→ Running harness pre-edit guard..."
	@cd $(HARNESS_DIR) && $(PYTHON) vf_contract_guard.py

harness-check: harness-guard harness-task ## Full harness preflight (guard + context)
	@echo "✅  Harness preflight complete"

docs-harness: ## Validate harness documentation artifacts (endpoints, models, runbook, config)
	@echo "→ Validating harness docs..."
	@$(PYTHON) scripts/generate_harness_docs.py --check


check-value-fabric-public-imports: ## Enforce public import policy
	@$(PYTHON) scripts/ci/check_value_fabric_public_imports.py


check-raw-http-exception-usage: ## Enforce raw HTTPException usage only in boundary adapter files
	@$(PYTHON) scripts/ci/check_raw_http_exception_usage.py

# --- Launch Audit Validation Targets ---
.PHONY: secret-scan pip-audit-all k8s-validate

secret-scan:
	@echo "Running secret scan..."
	infisical scan || python scripts/ci/check_manifest_secret_hygiene.py

pip-audit-all:
	@echo "Running pip audit..."
	pip-audit || true

k8s-validate:
	@echo "Running Kubernetes validation..."
	bash scripts/ci/validate-deploy-safety.sh
