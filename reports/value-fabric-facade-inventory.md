# Value Fabric Facade Import Inventory

<<<<<<< HEAD
Generated: 2026-05-29T13:14:59.798136
=======
Generated: 2026-05-29T03:42:48.876810
>>>>>>> f43ab27b (```)

## Facade Status

**Status:** ACTIVE PATH-RESOLUTION FACADE

The `value_fabric/` directory is **not merely a legacy compatibility shim**. It provides critical Python path resolution by appending service source paths to package `__path__`. Direct canonical imports (e.g., `layer6_benchmarks.database`) fail without this path bootstrapping.

**Removal Blocked:** Canonical package import resolution must be solved before facade removal. See `.jr/tickets/IMPORT-ARCH-FACADE-RESOLUTION.md` for details.

## Phase 0 Finding: L6 Canonical Import Failure

**Attempted:** Migrate L6 test imports from `value_fabric.layer6.*` to `layer6_benchmarks.*`

**Result:** FAILED with `ModuleNotFoundError: No module named 'layer6_benchmarks.database'`

**Root Cause:** The facade appends `services/layer6-benchmarks/src` to `__path__`, but the canonical package structure requires additional path configuration that the facade currently provides.

**Resolution:** Reverted all changes. L6 tests pass with facade imports, fail with canonical imports.

## Summary

<<<<<<< HEAD
- **Total files with facade imports**: 108
- **Total facade import statements**: 253
=======
- **Total files with facade imports**: 232
- **Total facade import statements**: 750
>>>>>>> f43ab27b (```)

## Imports by Layer

| Layer | Count |
|-------|-------|
<<<<<<< HEAD
| 1 | 7 |
=======
| 1 | 6 |
>>>>>>> f43ab27b (```)
| 3 | 223 |
| 4 | 17 |
| 5 | 1 |
| 6 | 5 |

## Imports by File Type

| File Type | Count |
|-----------|-------|
| ci_script | 10 |
| other | 9 |
| package | 1 |
| service | 17 |
<<<<<<< HEAD
| test | 71 |
=======
| test | 197 |
>>>>>>> f43ab27b (```)

## Files with Facade Imports

### `archive\legacy-shims\layer4_agents\main.py` (other)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 21 | `from value_fabric.layer4.api.main import app` |

### `packages\shared\src\value_fabric\shared\rate_limiting\admin_api.py` (package)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 154 | `from value_fabric.layer3.db.driver import get_driver as _get_driver` |

### `scripts\ci\check_layer1_imports.py` (ci_script)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 192 | `"\nSome files import value_fabric.layer1 outside the allowlist, "` |

### `scripts\ci\check_layer3_imports.py` (ci_script)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 221 | `"\nSome files import value_fabric.layer3 outside the allowlist, "` |

### `scripts\ci\check_layer3_settings_shim_drift.py` (ci_script)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 73 | `"Shim must re-export via wildcard from value_fabric.layer3.config (or submodu...` |

### `scripts\ci\check_layer6_imports.py` (ci_script)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 157 | `"\nSome files import value_fabric.layer6 outside the allowlist, "` |

### `scripts\migrate_l1_test_imports_canonical.py` (ci_script)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 2 | `"""Migrate L1 test imports from value_fabric.layer1.* to layer1_ingestion.*."""` |

<<<<<<< HEAD
### `scripts\migrate_l4_test_imports_canonical.py` (ci_script)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 2 | `"""Migrate L4 test imports from value_fabric.layer4.* to layer4_agents.*."""` |

=======
>>>>>>> f43ab27b (```)
### `scripts\migrate_l6_test_imports_canonical.py` (ci_script)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 2 | `"""Migrate L6 test imports from value_fabric.layer6.* to layer6_benchmarks.*"""` |

### `scripts\validation\generate_live_llm_provider_evidence.py` (ci_script)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 31 | `from value_fabric.layer4.metrics.llm_cost_calculator import LLMCostCalculator` |

### `scripts\verify_layer4_imports.py` (ci_script)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `import value_fabric.layer4` |
| 4 | 17 | `from value_fabric.layer4.observability import Layer4EventContext as LEC2` |

### `scripts\verify_layer4_shim.py` (ci_script)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 6 | `from value_fabric.layer4.observability import Layer4EventContext` |
| 4 | 12 | `from value_fabric.layer4.database_facade import validate_tenant_id` |
| 4 | 18 | `from value_fabric.layer4.database import get_db_from_context` |

### `services\layer3-knowledge\scripts\check_backup_shim_drift.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 15 | `'from value_fabric.layer3.backup.backup_manager import *  # noqa: F401,F403\n'` |
| 3 | 21 | `'from value_fabric.layer3.backup import *  # noqa: F401,F403\n'` |

### `services\layer3-knowledge\src\analytics\centrality.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 7 | `from value_fabric.layer3.config import Settings, get_settings` |

### `services\layer3-knowledge\src\analytics\communities.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 7 | `from value_fabric.layer3.config import Settings, get_settings` |

### `services\layer3-knowledge\src\analytics\similarity.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 7 | `from value_fabric.layer3.config import Settings, get_settings` |

### `services\layer3-knowledge\src\api\dependencies.py` (service)

**Total imports**: 7

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 19 | `from value_fabric.layer3.agents import (` |
| 3 | 26 | `from value_fabric.layer3.analytics import (` |
| 3 | 31 | `from value_fabric.layer3.config import Settings, get_settings` |
| 3 | 32 | `from value_fabric.layer3.db.driver import get_driver, reset_driver` |
| 3 | 33 | `from value_fabric.layer3.ingestion import Neo4jLoader, SyncManager` |
| 3 | 34 | `from value_fabric.layer3.retrieval import GraphRAGEngine, HybridSearch, Vecto...` |
| 3 | 35 | `from value_fabric.layer3.schema import SchemaInitializer` |

### `services\layer3-knowledge\src\api\main.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 25 | `from value_fabric.layer3.config import get_settings` |
| 3 | 26 | `from value_fabric.layer3.logging_config import get_logger, setup_logging` |

### `services\layer3-knowledge\src\api\routes\entity_compat.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 10 | `from value_fabric.layer3.api.routes.entities import router` |

### `services\layer3-knowledge\src\api\routes\models.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 7 | `from value_fabric.layer3.api.auth_context import _get_tenant_context  # noqa:...` |
| 3 | 8 | `from value_fabric.layer3.api.routes.models_router import *  # noqa: F401,F403` |

### `services\layer3-knowledge\src\api\routes\system.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 40 | `from value_fabric.layer3.config import get_settings` |
| 3 | 81 | `from value_fabric.layer3.schema.initializer import SchemaInitializer` |

### `services\layer3-knowledge\src\api\routes\value_packs.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 19 | `from value_fabric.layer3.models.valuepack import (` |

### `services\layer3-knowledge\src\config.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 9 | `from value_fabric.layer3.config import *  # noqa: F401,F403` |

### `services\layer3-knowledge\src\db\audited_mutation.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 21 | `from value_fabric.layer3.db.query_execution import run_tenant_query` |
| 3 | 22 | `from value_fabric.layer3.utils.cypher_security import (` |

### `services\layer3-knowledge\src\db\query_execution.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 32 | `from value_fabric.layer3.utils.cypher_security import TENANT_OWNED_LABELS` |

### `services\layer3-knowledge\src\security\query_validator.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 42 | `from value_fabric.layer3.utils.cypher_security import (` |
| 3 | 410 | `from value_fabric.layer3.db.query_execution import (` |

### `services\layer3-knowledge\src\services\competitive_intel_service.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 40 | `from value_fabric.layer3.security.query_validator import ValidatedNeo4jSession` |
| 3 | 41 | `from value_fabric.layer3.services.cypher_scope_guard import (` |

### `services\layer3-knowledge\src\services\cypher_scope_guard.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 15 | `from value_fabric.layer3.utils.cypher_security import (  # noqa: F401` |

### `services\layer3-knowledge\src\services\product_service.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 21 | `from value_fabric.layer3.security.query_validator import ValidatedNeo4jSession` |
| 3 | 22 | `from value_fabric.layer3.services.cypher_scope_guard import (` |

### `services\layer3-knowledge\tests\conftest.py` (test)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 53 | `from value_fabric.layer3.api.dependencies import AppState` |
| 3 | 54 | `from value_fabric.layer3.config import Settings, get_settings` |
| 3 | 178 | `from value_fabric.layer3.api.main import app` |
| 3 | 184 | `from value_fabric.layer3.api.dependencies import (` |
| 3 | 214 | `from value_fabric.layer3.api.main import app` |
| 3 | 220 | `from value_fabric.layer3.api.dependencies import (` |

### `services\layer3-knowledge\tests\test_account_authorization.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 13 | `from value_fabric.layer3.schema.entity_scope import (` |
| 3 | 22 | `from value_fabric.layer3.security.account_authorization import (` |

### `services\layer3-knowledge\tests\test_api_wrapper_startup_regression.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.api.main import app` |

### `services\layer3-knowledge\tests\test_audited_graph_mutation.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 9 | `from value_fabric.layer3.db.audited_mutation import AuditedGraphMutation` |
| 3 | 10 | `from value_fabric.layer3.utils.cypher_security import ALLOWED_REL_TYPES` |

### `services\layer3-knowledge\tests\test_backup_runtime_bindings.py` (test)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.backup.backup_manager import BackupConfig as Service...` |
| 3 | 2 | `from value_fabric.layer3.backup.backup_manager import BackupManager as Servic...` |
| 3 | 3 | `from value_fabric.layer3.backup.backup_manager import LocalStorage as Service...` |
| 3 | 4 | `from value_fabric.layer3.backup.backup_manager import BackupConfig, BackupMan...` |

### `services\layer3-knowledge\tests\test_backup_tenant_scoping.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.backup.backup_manager import (` |

### `services\layer3-knowledge\tests\test_benchmark_policies_route.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 6 | `from value_fabric.layer3.api.routes.benchmarks import list_benchmark_policies` |

### `services\layer3-knowledge\tests\test_cache_characterization.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 15 | `from value_fabric.layer3.cache.redis_cache import CacheManager, RequestDedupl...` |

### `services\layer3-knowledge\tests\test_cache_oss1_parity.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 14 | `from value_fabric.layer3.cache import (` |

### `services\layer3-knowledge\tests\test_cache_ports.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 10 | `from value_fabric.layer3.cache.ports import CachePort, LegacyCacheAdapter, as...` |

### `services\layer3-knowledge\tests\test_canonical_endpoint_surface.py` (test)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 11 | `from value_fabric.layer3.api.routes.entities import router as entities_router` |
| 3 | 12 | `from value_fabric.layer3.api.routes.calculators import router as calculators_...` |
| 3 | 13 | `from value_fabric.layer3.api.routes.graph_viz import router as graph_viz_router` |

### `services\layer3-knowledge\tests\test_config.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 9 | `from value_fabric.layer3.config import Settings, get_settings` |

### `services\layer3-knowledge\tests\test_config_import_surface.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.config import Settings, get_settings` |

### `services\layer3-knowledge\tests\test_cross_tenant_hostile_behavioral.py` (test)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 41 | `from value_fabric.layer3.api.dependencies_tenant import Neo4jTenantSession` |
| 3 | 57 | `from value_fabric.layer3.api.dependencies_tenant import Neo4jTenantSession` |
| 3 | 85 | `from value_fabric.layer3.api.dependencies_tenant import Neo4jTenantSession` |

### `services\layer3-knowledge\tests\test_cypher_scope_remediation.py` (test)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 8 | `from value_fabric.layer3.db.tenant_queries import get_entity_context` |
| 3 | 9 | `from value_fabric.layer3.retrieval.graph_rag import GraphRAGEngine` |
| 3 | 51 | `from value_fabric.layer3.retrieval.graph_rag import _validate_relationship_types` |
| 3 | 58 | `from value_fabric.layer3.retrieval.graph_rag import _validate_entity_type` |
| 3 | 65 | `from value_fabric.layer3.retrieval.graph_rag import _validate_hops` |

### `services\layer3-knowledge\tests\test_dil_phase1.py` (test)

**Total imports**: 29

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 108 | `from value_fabric.layer3.services.product_service import ProductCreate, Produ...` |
| 3 | 129 | `from value_fabric.layer3.services.product_service import ProductService` |
| 3 | 141 | `from value_fabric.layer3.services.product_service import ProductService` |
| 3 | 163 | `from value_fabric.layer3.services.product_service import ProductService` |
| 3 | 184 | `from value_fabric.layer3.services.product_service import ProductService` |
| 3 | 196 | `from value_fabric.layer3.services.product_service import ProductService` |
| 3 | 208 | `from value_fabric.layer3.services.product_service import FeatureCreate, Produ...` |
| 3 | 224 | `from value_fabric.layer3.services.product_service import ProductService` |
| 3 | 247 | `from value_fabric.layer3.services.product_service import ProductService` |
| 3 | 269 | `from value_fabric.layer3.services.product_service import ProductService` |
| 3 | 305 | `from value_fabric.layer3.services.case_study_service import CaseStudy, CaseSt...` |
| 3 | 333 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 357 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 373 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 389 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 401 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 428 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 440 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 452 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 479 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 495 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 509 | `from value_fabric.layer3.services.case_study_service import CaseStudyService` |
| 3 | 546 | `from value_fabric.layer3.services.case_study_service import CaseStudy` |
| 3 | 563 | `from value_fabric.layer3.services.case_study_service import CaseStudy` |
| 3 | 585 | `from value_fabric.layer3.services.case_study_service import CaseStudyOutcome` |
| 3 | 602 | `from value_fabric.layer3.services.case_study_service import CaseStudy, CaseSt...` |
| 3 | 628 | `from value_fabric.layer3.services.product_service import ProductCreate` |
| 3 | 639 | `from value_fabric.layer3.services.product_service import ProductCreate` |
| 3 | 658 | `from value_fabric.layer3.services.product_service import FeatureCreate` |

### `services\layer3-knowledge\tests\test_dil_phase2.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 28 | `from value_fabric.layer3.services.competitive_intel_service import (` |
| 3 | 34 | `from value_fabric.layer3.services.roi_calculator_service import (` |

### `services\layer3-knowledge\tests\test_e2e_pipeline.py` (test)

**Total imports**: 11

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 40 | `from value_fabric.layer3.api.dependencies import (` |
| 3 | 46 | `from value_fabric.layer3.api.main import app` |
| 3 | 47 | `from value_fabric.layer3.config import Settings` |
| 3 | 48 | `from value_fabric.layer3.ingestion.neo4j_loader import Neo4jLoader` |
| 3 | 49 | `from value_fabric.layer3.ingestion.sync_manager import SyncManager` |
| 3 | 50 | `from value_fabric.layer3.retrieval.graph_rag import GraphRAGEngine` |
| 3 | 51 | `from value_fabric.layer3.retrieval.hybrid_search import HybridSearch` |
| 3 | 52 | `from value_fabric.layer3.retrieval.vector_store import VectorStore` |
| 3 | 53 | `from value_fabric.layer3.schema.initializer import SchemaInitializer` |
| 3 | 256 | `from value_fabric.layer3.schema.constraints import CONSTRAINTS, TENANT_CONSTR...` |
| 3 | 260 | `from value_fabric.layer3.schema.constraints import CONSTRAINTS, TENANT_CONSTR...` |

### `services\layer3-knowledge\tests\test_entities_route_tenant_scoped_regression.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.api.routes.entities import list_entities, query_enti...` |
| 3 | 6 | `from value_fabric.layer3.api.models import EntityFilterRequest` |

### `services\layer3-knowledge\tests\test_entity_resolution.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 12 | `from value_fabric.layer3.schema.entity_resolution import (` |
| 3 | 21 | `from value_fabric.layer3.services.entity_resolution import EntityResolutionSe...` |

### `services\layer3-knowledge\tests\test_entrypoint_route_resolution_regression.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.api.main import app` |

### `services\layer3-knowledge\tests\test_evidence_embedding_failure.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.services.embedding_errors import EmbeddingProviderUn...` |

### `services\layer3-knowledge\tests\test_evidence_links_tenant_isolation.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 8 | `from value_fabric.layer3.api.dependencies import get_neo4j_driver` |
| 3 | 9 | `from value_fabric.layer3.api.main import app` |

### `services\layer3-knowledge\tests\test_exception_handlers.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 8 | `from value_fabric.layer3.api.exceptions import ValueFabricException` |
| 3 | 9 | `from value_fabric.layer3.api.main import (` |

### `services\layer3-knowledge\tests\test_exception_mapping.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.api.exception_mapping import map_exception_to_http_e...` |
| 3 | 2 | `from value_fabric.layer3.api.exceptions import (` |

### `services\layer3-knowledge\tests\test_exceptions.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 3 | `from value_fabric.layer3.api.exceptions import (` |

### `services\layer3-knowledge\tests\test_formula_governance_tenant_extraction.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 11 | `from value_fabric.layer3.api.routes.formula_governance import list_pending_ap...` |

### `services\layer3-knowledge\tests\test_graph_alias_deprecation_policy.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.api.models import (` |

### `services\layer3-knowledge\tests\test_graph_viz_security_boundaries.py` (test)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 21 | `from value_fabric.layer3.api.dependencies_tenant_secured import require_reque...` |
| 3 | 22 | `from value_fabric.layer3.api.routes.graph_viz import (` |
| 3 | 28 | `from value_fabric.layer3.db.query_execution import MAX_QUERY_DEPTH` |

### `services\layer3-knowledge\tests\test_hybrid_search_api_compat.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.config import Settings` |
| 3 | 6 | `from value_fabric.layer3.retrieval.hybrid_search import HybridSearch` |

### `services\layer3-knowledge\tests\test_i03_variables_production_fail_closed.py` (test)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 29 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |
| 3 | 38 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |
| 3 | 47 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |
| 3 | 56 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |
| 3 | 65 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |
| 3 | 73 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |

### `services\layer3-knowledge\tests\test_ingestion.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 8 | `from value_fabric.layer3.ingestion import Neo4jLoader, RDFLoadError` |
| 3 | 9 | `from value_fabric.layer3.ingestion.neo4j_loader import (` |

### `services\layer3-knowledge\tests\test_ingestion_route_docstring_policy.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 3 | `from value_fabric.layer3.api.routes import ingestion` |

### `services\layer3-knowledge\tests\test_knowledge_subgraph_routes.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 22 | `from value_fabric.layer3.api.routes.knowledge import (` |

### `services\layer3-knowledge\tests\test_layer3_compat_deprecation_phases.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 3 | `from value_fabric.layer3.api.models import GraphEdge, GraphNode, get_deprecat...` |
| 3 | 4 | `from value_fabric.layer3.api.main import app` |

### `services\layer3-knowledge\tests\test_layer3_compat_metrics_thresholds.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.services.compat_metrics import deprecation_ready_for...` |

### `services\layer3-knowledge\tests\test_monolith_route_delegation_guardrail.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 29 | `from value_fabric.layer3.api.routes import (  # noqa: F401` |
| 3 | 40 | `from value_fabric.layer3.api.main import app  # noqa: F401` |

### `services\layer3-knowledge\tests\test_neo4j_integration.py` (test)

**Total imports**: 18

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 80 | `from value_fabric.layer3.config import Settings` |
| 3 | 101 | `from value_fabric.layer3.db.driver import get_driver, reset_driver` |
| 3 | 131 | `from value_fabric.layer3.db.driver import get_driver, reset_driver` |
| 3 | 144 | `from value_fabric.layer3.schema import SchemaInitializer` |
| 3 | 160 | `from value_fabric.layer3.schema import SchemaInitializer` |
| 3 | 177 | `from value_fabric.layer3.ingestion.neo4j_loader import Neo4jLoader` |
| 3 | 205 | `from value_fabric.layer3.ingestion.neo4j_loader import Neo4jLoader` |
| 3 | 245 | `from value_fabric.layer3.retrieval.vector_store import VectorStore` |
| 3 | 246 | `from value_fabric.layer3.schema import SchemaInitializer` |
| 3 | 259 | `from value_fabric.layer3.retrieval.vector_store import VectorStore` |
| 3 | 260 | `from value_fabric.layer3.schema import SchemaInitializer` |
| 3 | 279 | `from value_fabric.layer3.retrieval.hybrid_search import HybridSearch` |
| 3 | 280 | `from value_fabric.layer3.retrieval.vector_store import VectorStore` |
| 3 | 281 | `from value_fabric.layer3.schema import SchemaInitializer` |
| 3 | 301 | `from value_fabric.layer3.retrieval.graph_rag import GraphRAGEngine` |
| 3 | 302 | `from value_fabric.layer3.retrieval.vector_store import VectorStore` |
| 3 | 303 | `from value_fabric.layer3.schema import SchemaInitializer` |
| 3 | 321 | `from value_fabric.layer3.retrieval.graph_rag import GraphRAGEngine` |

### `services\layer3-knowledge\tests\test_neo4j_schema_integration.py` (test)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 29 | `from value_fabric.layer3.config import Settings` |
| 3 | 30 | `from value_fabric.layer3.schema.initializer import SchemaInitializer` |
| 3 | 283 | `from value_fabric.layer3.schema.constraints import get_tenant_constraints` |
| 3 | 291 | `from value_fabric.layer3.schema.constraints import TENANT_CONSTRAINTS, get_te...` |

### `services\layer3-knowledge\tests\test_observability_contract_integration.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 4 | `from value_fabric.layer3.api.main import app` |
| 3 | 25 | `from value_fabric.layer3.metrics.prometheus_metrics import PrometheusMetrics,...` |

### `services\layer3-knowledge\tests\test_pack_loader.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 18 | `from value_fabric.layer3.api.routes import pack_loader` |
| 3 | 19 | `from value_fabric.layer3.api.routes.pack_loader import (` |

### `services\layer3-knowledge\tests\test_packaged_system_routes.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 11 | `from value_fabric.layer3.api.routes import system as system_routes` |
| 3 | 12 | `from value_fabric.layer3.api.models import ServiceMetrics` |

### `services\layer3-knowledge\tests\test_query_search_error_context.py` (test)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 6 | `from value_fabric.layer3.api.exceptions import SearchError` |
| 3 | 7 | `from value_fabric.layer3.api.models import GraphRAGQuery, SearchRequest` |
| 3 | 8 | `from value_fabric.layer3.api.routes import query_search` |

### `services\layer3-knowledge\tests\test_query_validator.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 11 | `from value_fabric.layer3.security.query_validator import (` |

### `services\layer3-knowledge\tests\test_required_field_validator.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 9 | `from value_fabric.layer3.ingestion.validators import RequiredFieldValidator, ...` |
| 3 | 99 | `from value_fabric.layer3.api.exceptions import IngestionError` |

### `services\layer3-knowledge\tests\test_retrieval.py` (test)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 9 | `from value_fabric.layer3.retrieval.graph_rag import GraphRAGResult` |
| 3 | 29 | `from value_fabric.layer3.retrieval.hybrid_search import HybridSearchResult` |
| 3 | 49 | `from value_fabric.layer3.retrieval.vector_store import VectorStoreError` |

### `services\layer3-knowledge\tests\test_roi_formula_security.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 14 | `from value_fabric.layer3.agents.roi_calculation import ROICalculationAgent` |

### `services\layer3-knowledge\tests\test_scenario_engine.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.agents.scenario_engine import (` |
| 3 | 122 | `from value_fabric.layer3.agents.scenario_engine import SavedScenario` |

### `services\layer3-knowledge\tests\test_strict_builder_enforcement.py` (test)

**Total imports**: 7

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 18 | `from value_fabric.layer3.analytics.centrality import CentralityAnalyzer` |
| 3 | 19 | `from value_fabric.layer3.analytics.communities import CommunityDetector` |
| 3 | 20 | `from value_fabric.layer3.analytics.similarity import SimilarityAnalyzer` |
| 3 | 21 | `from value_fabric.layer3.retrieval.graph_rag import GraphRAGEngine` |
| 3 | 22 | `from value_fabric.layer3.retrieval.hybrid_search import HybridSearch` |
| 3 | 23 | `from value_fabric.layer3.retrieval.vector_store import Neo4jVectorStore` |
| 3 | 37 | `from value_fabric.layer3.api.dependencies_tenant import Neo4jTenantSession` |

### `services\layer3-knowledge\tests\test_sync_manager_tenant_isolation.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 6 | `from value_fabric.layer3.ingestion.sync_manager import SyncManager` |

### `services\layer3-knowledge\tests\test_system_routes.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 12 | `from value_fabric.layer3.api.dependencies import get_schema_initializer` |
| 3 | 13 | `from value_fabric.layer3.api.routes import system as system_routes` |

### `services\layer3-knowledge\tests\test_tenant_context_extraction.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 17 | `from value_fabric.layer3.api.dependencies import _extract_tenant_id` |

### `services\layer3-knowledge\tests\test_tenant_id_migration_expansion_labels.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.migrations.migrate_tenant_ids import TenantIdMigration` |

### `services\layer3-knowledge\tests\test_tenant_isolation.py` (test)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 14 | `from value_fabric.layer3.api.dependencies_tenant_secured import require_reque...` |
| 3 | 15 | `from value_fabric.layer3.api.routes.graph_viz import get_entity_subgraph, get...` |
| 3 | 16 | `from value_fabric.layer3.api.routes.query_search import graph_rag_query_impl,...` |
| 3 | 17 | `from value_fabric.layer3.api.models import GraphRAGQuery, SearchRequest, Sear...` |
| 3 | 18 | `from value_fabric.layer3.api.routes.entities import list_entities` |

### `services\layer3-knowledge\tests\test_tenant_read_isolation.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 10 | `from value_fabric.layer3.db.tenant_queries import (` |

### `services\layer3-knowledge\tests\test_trace_context_propagation_integration.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 8 | `from value_fabric.layer3.tracing.middleware import TracingMiddleware` |

### `services\layer3-knowledge\tests\test_value_packs.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 16 | `from value_fabric.layer3.api.routes.value_packs import (` |

### `services\layer3-knowledge\tests\test_value_packs_tenant_extraction.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 16 | `from value_fabric.layer3.api.routes.value_packs import _tenant_id_from_api_key` |

### `services\layer3-knowledge\tests\test_valuepack_model_forwarder_guard.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 10 | `assert "from value_fabric.layer3.models.valuepack import *" in content` |

### `services\layer3-knowledge\tests\test_vault_config_source.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 16 | `from value_fabric.layer3.config.manager import (` |

### `services\layer3-knowledge\tests\test_vector_e2e.py` (test)

**Total imports**: 8

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 37 | `from value_fabric.layer3.api.dependencies import (` |
| 3 | 41 | `from value_fabric.layer3.api.main import app` |
| 3 | 42 | `from value_fabric.layer3.config import Settings` |
| 3 | 43 | `from value_fabric.layer3.ingestion.neo4j_loader import Neo4jLoader` |
| 3 | 44 | `from value_fabric.layer3.ingestion.sync_manager import SyncManager` |
| 3 | 45 | `from value_fabric.layer3.retrieval.hybrid_search import HybridSearch` |
| 3 | 46 | `from value_fabric.layer3.retrieval.vector_store import VectorStore` |
| 3 | 47 | `from value_fabric.layer3.schema.initializer import SchemaInitializer` |

### `services\layer3-knowledge\tests\test_vector_store_tenant_write_isolation.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 7 | `from value_fabric.layer3.retrieval.vector_store import Neo4jVectorStore` |

### `services\layer3-knowledge\tests\test_versioning_registration.py` (test)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 7 | `from value_fabric.layer3.api import main as main_module` |
| 3 | 8 | `from value_fabric.layer3.api import versioning as versioning_module` |
| 3 | 9 | `from value_fabric.layer3.api.versioning import VersionCompatibility` |

### `services\layer4-agents\tests\test_c1_proxy.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `from value_fabric.layer4.api.routes.c1 import C1Message, C1StreamRequest, router` |

### `services\layer4-agents\tests\test_code_quality.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 78 | `This allows 'from value_fabric.layer4.interfaces' to work when running from l...` |

### `services\layer4-agents\tests\test_trace_header_propagation_integration.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 13 | `from value_fabric.layer3.tracing.middleware import TracingMiddleware` |

### `tests\arch\test_canonical_module_sentinels.py` (test)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 5 | 173 | `"""Regression: no production code should import value_fabric.layer5.*.` |
| 6 | 227 | `import value_fabric.layer6` |

### `tests\ci\test_deprecated_namespace_imports.py` (test)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 23 | `sample.write_text("from value_fabric.layer1_ingestion.src import api\n", enco...` |
| 1 | 30 | `statement = "from value_fabric.layer1_ingestion.src import api"` |
| 1 | 37 | `'"statement":"from value_fabric.layer1_ingestion.src import api",'` |
| 3 | 48 | `(tmp_path / "services/demo/sample.py").write_text("import value_fabric.layer3...` |
| 1 | 49 | `(tmp_path / "tests/demo/sample_test.py").write_text("import value_fabric.laye...` |
| 3 | 60 | `(tmp_path / "services/demo/sample.py").write_text("import value_fabric.layer3...` |

### `tests\ci\test_layer4_canonical_service_imports.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 30 | `import value_fabric.layer4` |

### `tests\security\test_audit_event_emission.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 12 | `from value_fabric.layer4 import database_facade as database` |

### `tests\security\test_tenant_validation_metrics.py` (test)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 11 | `from value_fabric.layer4 import database_facade as database` |

### `value_fabric\layer1\__init__.py` (other)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 5 | ```import value_fabric.layer1.api.main`` resolves to the canonical tree.` |

### `value_fabric\layer3\__init__.py` (other)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | ```import value_fabric.layer3.api.main`` resolves to the canonical tree.` |

### `value_fabric\layer4\__init__.py` (other)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 5 | ```import value_fabric.layer4.engine`` resolves to the canonical tree.` |

### `value_fabric\layer4\billing\models.py` (other)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.models.billing import (` |

### `value_fabric\layer4\billing\schemas.py` (other)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 8 | `from value_fabric.layer4.api.schemas.billing import (` |

### `value_fabric\layer4\billing\services\__init__.py` (other)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 8 | `from value_fabric.layer4.services.billing_service import BillingService` |

### `value_fabric\layer6\__init__.py` (other)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 5 | ```import value_fabric.layer6.api.main`` resolves to the canonical tree.` |

### `value_fabric\layer6\test_structured_logging_smoke.py` (other)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 5 | `from value_fabric.layer6 import configure_structured_logging` |

## Runtime vs Test Classification

- **Runtime/Service imports**: 17
<<<<<<< HEAD
- **Test imports**: 71
- **CI Script imports**: 10
=======
- **Test imports**: 197
- **CI Script imports**: 9
>>>>>>> f43ab27b (```)

## Migration Priority

Based on file type classification:

1. **HIGH PRIORITY - Runtime/Service code**
   - 17 files
   - Must migrate first to ensure services work without facades

2. **MEDIUM PRIORITY - CI Scripts**
   - 10 files
   - Migrate in batches by category

3. **LOWER PRIORITY - Test code**
<<<<<<< HEAD
   - 71 files
=======
   - 197 files
>>>>>>> f43ab27b (```)
   - Migrate layer by layer after runtime is clean
