# Value Fabric Facade Import Inventory

Generated: 2026-05-28T22:56:23.631436

## Summary

- **Total files with facade imports**: 304
- **Total facade import statements**: 1072

## Imports by Layer

| Layer | Count |
|-------|-------|
| 1 | 289 |
| 2 | 1 |
| 3 | 223 |
| 4 | 516 |
| 5 | 1 |
| 6 | 42 |

## Imports by File Type

| File Type | Count |
|-----------|-------|
| ci_script | 8 |
| other | 8 |
| package | 1 |
| service | 282 |
| test | 5 |

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

### `scripts\ci\check_layer2_imports.py` (ci_script)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 2 | 183 | `"\nSome files import value_fabric.layer2 outside the allowlist, "` |

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

### `services\layer1-ingestion\tests\api\conftest.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 32 | `from value_fabric.layer1.api.app_monolith import app` |
| 1 | 37 | `from value_fabric.layer1.shared.models import Base` |
| 1 | 42 | `from value_fabric.layer1.shared.database import get_db_from_context_sync` |
| 1 | 47 | `from value_fabric.layer1.shared.models import create_scraping_target` |

### `services\layer1-ingestion\tests\api\test_targets_batch.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 182 | `from value_fabric.layer1.shared.models import ScrapingJob` |
| 1 | 255 | `from value_fabric.layer1.shared.models import create_scraping_job` |

### `services\layer1-ingestion\tests\api\test_targets_execute_idempotency.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 49 | `from value_fabric.layer1.shared.models import ScrapingJob` |
| 1 | 85 | `from value_fabric.layer1.shared.models import ScrapingJob` |
| 1 | 108 | `from value_fabric.layer1.shared.models import ScrapingJob` |
| 1 | 177 | `from value_fabric.layer1.shared.models import ScrapingJob, JobStatus` |
| 1 | 210 | `from value_fabric.layer1.shared.models import ScrapingJob, JobStatus` |

### `services\layer1-ingestion\tests\api\test_targets_route_ordering.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 25 | `from value_fabric.layer1.api.app_monolith import app` |

### `services\layer1-ingestion\tests\api\test_targets_status.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 183 | `from value_fabric.layer1.api.app_monolith import app` |
| 1 | 184 | `from value_fabric.layer1.shared.database import get_db_from_context_sync` |
| 1 | 246 | `from value_fabric.layer1.shared.models import create_scraping_job` |

### `services\layer1-ingestion\tests\benchmarks\test_router_performance.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 18 | `from value_fabric.layer1.crawler.smart_router import SmartRouter, RouteType` |
| 1 | 19 | `from value_fabric.layer1.crawler.httpx_crawler import HttpxCrawler, FastPathR...` |
| 1 | 20 | `from value_fabric.layer1.crawler.quality_gate import QualityGate` |
| 1 | 21 | `from value_fabric.layer1.crawler.decision_store import InMemoryCrawlDecisionR...` |

### `services\layer1-ingestion\tests\compliance\test_strict_robots_mode.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 15 | `from value_fabric.layer1.compliance.robots_checker import RobotsChecker` |
| 1 | 16 | `from value_fabric.layer1.compliance.exceptions import RobotsFetchError, Robot...` |

### `services\layer1-ingestion\tests\contract\test_l1_targets_openapi.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 22 | `from value_fabric.layer1.api.app_monolith import app` |

### `services\layer1-ingestion\tests\crawler\test_httpx_crawler.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 15 | `from value_fabric.layer1.crawler.httpx_crawler import (` |

### `services\layer1-ingestion\tests\crawler\test_httpx_crawler_retry.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 23 | `from value_fabric.layer1.crawler.httpx_crawler import (` |

### `services\layer1-ingestion\tests\crawler\test_quality_gate.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 12 | `from value_fabric.layer1.crawler.httpx_crawler import FastPathResult` |
| 1 | 13 | `from value_fabric.layer1.crawler.quality_gate import AdaptiveQualityGate, Qua...` |

### `services\layer1-ingestion\tests\crawler\test_smart_router.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 10 | `from value_fabric.layer1.crawler.smart_router import (` |

### `services\layer1-ingestion\tests\domain\test_target_status_transitions.py` (service)

**Total imports**: 8

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 26 | `from value_fabric.layer1.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS` |
| 1 | 30 | `from value_fabric.layer1.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS` |
| 1 | 35 | `from value_fabric.layer1.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS` |
| 1 | 39 | `from value_fabric.layer1.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS` |
| 1 | 46 | `from value_fabric.layer1.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS` |
| 1 | 53 | `from value_fabric.layer1.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS` |
| 1 | 58 | `from value_fabric.layer1.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS` |
| 1 | 63 | `from value_fabric.layer1.api.app_monolith import _ALLOWED_STATUS_TRANSITIONS` |

### `services\layer1-ingestion\tests\integration\test_fast_path_pipeline.py` (service)

**Total imports**: 7

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 13 | `from value_fabric.layer1.crawler.execution_logger import ExecutionLogger, Exe...` |
| 1 | 14 | `from value_fabric.layer1.crawler.httpx_crawler import HttpxCrawler` |
| 1 | 15 | `from value_fabric.layer1.crawler.quality_gate import QualityGate` |
| 1 | 16 | `from value_fabric.layer1.crawler.smart_router import RouteType, SmartRouter` |
| 1 | 17 | `from value_fabric.layer1.shared.models import CrawlPath` |
| 1 | 504 | `from value_fabric.layer1.crawler.execution_logger import ExecutionLogger` |
| 1 | 536 | `from value_fabric.layer1.crawler.quality_gate import QualityGate, QualityThre...` |

### `services\layer1-ingestion\tests\integration\test_router_edge_cases.py` (service)

**Total imports**: 10

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 16 | `from value_fabric.layer1.crawler.smart_router import SmartRouter, RouteType, ...` |
| 1 | 17 | `from value_fabric.layer1.crawler.httpx_crawler import HttpxCrawler` |
| 1 | 18 | `from value_fabric.layer1.crawler.quality_gate import QualityGate` |
| 1 | 75 | `from value_fabric.layer1.crawler.httpx_crawler import FastPathResult` |
| 1 | 129 | `from value_fabric.layer1.crawler.httpx_crawler import FastPathResult` |
| 1 | 130 | `from value_fabric.layer1.crawler.quality_gate import QualityGate` |
| 1 | 156 | `from value_fabric.layer1.crawler.httpx_crawler import FastPathResult` |
| 1 | 157 | `from value_fabric.layer1.crawler.quality_gate import QualityGate` |
| 1 | 186 | `from value_fabric.layer1.crawler.httpx_crawler import FastPathResult` |
| 1 | 187 | `from value_fabric.layer1.crawler.quality_gate import QualityGate` |

### `services\layer1-ingestion\tests\integration\test_skill_pipeline.py` (service)

**Total imports**: 7

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 19 | `from value_fabric.layer1.shared.models import (` |
| 1 | 95 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 201 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 309 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 379 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 440 | `from value_fabric.layer1.api.main import router, get_tenant_id, get_db_from_c...` |
| 1 | 526 | `from value_fabric.layer1.api.main import router` |

### `services\layer1-ingestion\tests\observability\test_alert_contracts.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 18 | `from value_fabric.layer1.metrics.prometheus_metrics import (` |

### `services\layer1-ingestion\tests\pipeline\test_terminal_state_reconciliation.py` (service)

**Total imports**: 13

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 18 | `from value_fabric.layer1.shared.models import (` |
| 1 | 36 | `from value_fabric.layer1.shared.tasks import compliance_check_stage` |
| 1 | 61 | `from value_fabric.layer1.shared.tasks import _fail_job` |
| 1 | 90 | `from value_fabric.layer1.shared.tasks import _update_stage` |
| 1 | 134 | `from value_fabric.layer1.shared.tasks import _fail_job` |
| 1 | 161 | `from value_fabric.layer1.shared.tasks import _update_stage` |
| 1 | 162 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 219 | `from value_fabric.layer1.shared.tasks import _fail_job` |
| 1 | 250 | `from value_fabric.layer1.shared.tasks import _update_stage` |
| 1 | 251 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 302 | `from value_fabric.layer1.shared.tasks import _fail_job` |
| 1 | 342 | `from value_fabric.layer1.shared import tasks` |
| 1 | 373 | `from value_fabric.layer1.shared.database import get_db_session as real_get_db...` |

### `services\layer1-ingestion\tests\security\conftest.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 23 | `from value_fabric.layer1.api.app_monolith import app` |
| 1 | 28 | `from value_fabric.layer1.shared.models import Base` |
| 1 | 33 | `from value_fabric.layer1.shared.database import get_db_from_context_sync` |
| 1 | 38 | `from value_fabric.layer1.shared.models import create_scraping_target` |
| 1 | 128 | `from value_fabric.layer1.shared.models import ScrapingJob, JobStatus` |

### `services\layer1-ingestion\tests\security\conftest_postgres.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 30 | `from value_fabric.layer1.api.app_monolith import app` |
| 1 | 35 | `from value_fabric.layer1.shared.models import Base` |
| 1 | 40 | `from value_fabric.layer1.shared.database import get_db_from_context_sync` |
| 1 | 45 | `from value_fabric.layer1.shared.models import create_scraping_target` |
| 1 | 185 | `from value_fabric.layer1.shared.models import ScrapingJob, JobStatus` |

### `services\layer1-ingestion\tests\security\test_celery_tenant_isolation_postgres.py` (service)

**Total imports**: 16

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 19 | `from value_fabric.layer1.shared.database import get_db_session, TenantContext...` |
| 1 | 20 | `from value_fabric.layer1.shared.models import ScrapingJob, ScrapingTarget, Jo...` |
| 1 | 31 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 41 | `from value_fabric.layer1.shared.tasks import compliance_check_stage` |
| 1 | 50 | `from value_fabric.layer1.shared.tasks import browser_crawl_stage` |
| 1 | 59 | `from value_fabric.layer1.shared.tasks import ai_extraction_stage` |
| 1 | 68 | `from value_fabric.layer1.shared.tasks import post_processing_stage` |
| 1 | 77 | `from value_fabric.layer1.shared.tasks import validation_stage` |
| 1 | 86 | `from value_fabric.layer1.shared.tasks import storage_stage` |
| 1 | 95 | `from value_fabric.layer1.shared.tasks import notification_stage` |
| 1 | 144 | `from value_fabric.layer1.shared.tasks import (` |
| 1 | 242 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 281 | `from value_fabric.layer1.shared.tasks import dispatch_outbox_event` |
| 1 | 304 | `from value_fabric.layer1.shared.tasks import _fail_job` |
| 1 | 329 | `from value_fabric.layer1.shared.tasks import crawl_url_with_routing` |
| 1 | 354 | `from value_fabric.layer1.crawler.decision_store import (` |

### `services\layer1-ingestion\tests\security\test_crawl_decisions_tenant_isolation_postgres.py` (service)

**Total imports**: 7

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 17 | `from value_fabric.layer1.crawler.decision_store import (` |
| 1 | 21 | `from value_fabric.layer1.shared.models import CrawlDecision` |
| 1 | 60 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 133 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 201 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 244 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 289 | `from value_fabric.layer1.shared.database import get_db_session` |

### `services\layer1-ingestion\tests\security\test_global_robots_cache_isolation_postgres.py` (service)

**Total imports**: 11

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 15 | `from value_fabric.layer1.shared.exceptions import (` |
| 1 | 20 | `from value_fabric.layer1.compliance.robots_checker import RobotsChecker` |
| 1 | 21 | `from value_fabric.layer1.shared.models import RobotsTxtCache` |
| 1 | 82 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 110 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 123 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 150 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 194 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 312 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 333 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 364 | `from value_fabric.layer1.shared.database import get_db_session` |

### `services\layer1-ingestion\tests\security\test_maintenance_tenant_enumeration.py` (service)

**Total imports**: 9

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 17 | `from value_fabric.layer1.shared.models import (` |
| 1 | 21 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 94 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 180 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 202 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 242 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 266 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 279 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 307 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |

### `services\layer1-ingestion\tests\security\test_production_gates_postgres.py` (service)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 26 | `from value_fabric.layer1.shared.exceptions import (` |
| 1 | 36 | `from value_fabric.layer1.shared.maintenance import (` |
| 1 | 49 | `from value_fabric.layer1.shared.database import get_db_session, validate_tena...` |
| 1 | 50 | `from value_fabric.layer1.shared.models import (` |
| 1 | 643 | `from value_fabric.layer1.shared.exceptions import (` |
| 1 | 659 | `from value_fabric.layer1.shared.exceptions import (` |

### `services\layer1-ingestion\tests\security\test_require_tenant_false_allowlist_postgres.py` (service)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 44 | `from value_fabric.layer1.shared import tasks` |
| 1 | 87 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 143 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 152 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 240 | `from value_fabric.layer1.shared import tasks` |
| 1 | 303 | `from value_fabric.layer1.crawler.decision_store import CrawlDecisionRepository` |

### `services\layer1-ingestion\tests\security\test_rls_enforcement_postgres.py` (service)

**Total imports**: 10

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 20 | `from value_fabric.layer1.shared.database import get_db_session` |
| 1 | 21 | `from value_fabric.layer1.shared.models import ScrapingJob, ScrapingTarget, Jo...` |
| 1 | 32 | `from value_fabric.layer1.shared.database import TenantContextError` |
| 1 | 40 | `from value_fabric.layer1.shared.database import TenantContextError` |
| 1 | 173 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 174 | `from value_fabric.layer1.shared.database import TenantContextError` |
| 1 | 192 | `from value_fabric.layer1.shared import tasks` |
| 1 | 213 | `from value_fabric.layer1.shared.tasks import _fail_job` |
| 1 | 222 | `from value_fabric.layer1.shared.tasks import dispatch_outbox_event` |
| 1 | 235 | `from value_fabric.layer1.shared import tasks` |

### `services\layer1-ingestion\tests\security\test_system_maintenance_authorization_postgres.py` (service)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 16 | `from value_fabric.layer1.shared.exceptions import (` |
| 1 | 20 | `from value_fabric.layer1.shared.maintenance import (` |
| 1 | 261 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 282 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 293 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 305 | `from value_fabric.layer1.shared.tasks import _enumerate_authorized_tenants_fo...` |

### `services\layer1-ingestion\tests\security\test_targets_tenant_isolation.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 78 | `from value_fabric.layer1.api.app_monolith import app` |
| 1 | 157 | `from value_fabric.layer1.shared.models import ScrapingJob` |
| 1 | 171 | `from value_fabric.layer1.api.app_monolith import app` |

### `services\layer1-ingestion\tests\security\test_tenant_isolation_bypass_attempts_postgres.py` (service)

**Total imports**: 12

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 15 | `from value_fabric.layer1.shared.exceptions import (` |
| 1 | 21 | `from value_fabric.layer1.shared.database import get_db_session, validate_tena...` |
| 1 | 22 | `from value_fabric.layer1.shared.models import ScrapingJob, ScrapingTarget, Ra...` |
| 1 | 23 | `from value_fabric.layer1.shared.tasks import process_scraping_job, cleanup_ol...` |
| 1 | 174 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 224 | `from value_fabric.layer1.shared.maintenance import authorize_maintenance_oper...` |
| 1 | 279 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 289 | `from value_fabric.layer1.shared.tasks import crawl_url_with_routing` |
| 1 | 305 | `from value_fabric.layer1.shared import tasks` |
| 1 | 394 | `from value_fabric.layer1.shared.maintenance import maintenance_audit_log` |
| 1 | 412 | `from value_fabric.layer1.shared.maintenance import maintenance_audit_log` |
| 1 | 474 | `from value_fabric.layer1.shared.maintenance import MaintenanceOperation` |

### `services\layer1-ingestion\tests\test_observability_contract_integration.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 3 | `from value_fabric.layer1.api.app_monolith import app` |

### `services\layer1-ingestion\tests\unit\test_adapters.py` (service)

**Total imports**: 9

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 9 | `from value_fabric.layer1.adapters.base import AdapterType` |
| 1 | 10 | `from value_fabric.layer1.adapters.sec_edgar import SECEdgarAdapter` |
| 1 | 154 | `from value_fabric.layer1.adapters.xbrl_parser import XBRLParser` |
| 1 | 218 | `from value_fabric.layer1.adapters.registry import AdapterRegistry` |
| 1 | 223 | `from value_fabric.layer1.adapters.base import DataSourceAdapter` |
| 1 | 228 | `from value_fabric.layer1.adapters.base import AdapterType` |
| 1 | 244 | `from value_fabric.layer1.adapters.base import AdapterType` |
| 1 | 251 | `from value_fabric.layer1.adapters.base import AdapterType` |
| 1 | 260 | `from value_fabric.layer1.adapters.base import AdapterType` |

### `services\layer1-ingestion\tests\unit\test_batch_operations.py` (service)

**Total imports**: 7

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 7 | `from value_fabric.layer1.shared.models import JobStatus, TargetStatus, Scrapi...` |
| 1 | 8 | `from value_fabric.layer1.api.app_monolith import (` |
| 1 | 30 | `from value_fabric.layer1.shared.models import create_scraping_target` |
| 1 | 48 | `from value_fabric.layer1.shared.models import create_scraping_job` |
| 1 | 68 | `from value_fabric.layer1.shared.models import ScrapingJob` |
| 1 | 104 | `from value_fabric.layer1.shared.models import ScrapingJob` |
| 1 | 177 | `from value_fabric.layer1.shared.models import ScrapingJob` |

### `services\layer1-ingestion\tests\unit\test_canonical_imports.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 102 | `import value_fabric.layer1.crawler.httpx_crawler as shim_mod` |

### `services\layer1-ingestion\tests\unit\test_celery_dispatch_regression.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 11 | `from value_fabric.layer1.shared.config import Settings` |

### `services\layer1-ingestion\tests\unit\test_celery_tasks.py` (service)

**Total imports**: 33

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 46 | `from value_fabric.layer1.shared.tasks import celery_app` |
| 1 | 51 | `from value_fabric.layer1.shared.tasks import celery_app` |
| 1 | 56 | `from value_fabric.layer1.shared.tasks import celery_app` |
| 1 | 61 | `from value_fabric.layer1.shared.tasks import celery_app` |
| 1 | 67 | `from value_fabric.layer1.shared.tasks import celery_app` |
| 1 | 78 | `from value_fabric.layer1.shared.tasks import compliance_check_stage, execute_...` |
| 1 | 96 | `from value_fabric.layer1.shared.tasks import browser_crawl_stage, execute_pip...` |
| 1 | 115 | `from value_fabric.layer1.shared.tasks import execute_pipeline_stage` |
| 1 | 122 | `from value_fabric.layer1.shared.tasks import execute_pipeline_stage` |
| 1 | 134 | `from value_fabric.layer1.shared.tasks import (` |
| 1 | 160 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 174 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 214 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 241 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 260 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 273 | `from value_fabric.layer1.shared.tasks import compliance_check_stage` |
| 1 | 304 | `from value_fabric.layer1.shared.tasks import compliance_check_stage` |
| 1 | 325 | `from value_fabric.layer1.shared.tasks import crawl_url_with_routing` |
| 1 | 332 | `from value_fabric.layer1.shared.tasks import crawl_url_with_routing` |
| 1 | 361 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 369 | `from value_fabric.layer1.shared.tasks import compliance_check_stage` |
| 1 | 382 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 409 | `from value_fabric.layer1.shared.tasks import compliance_check_stage` |
| 1 | 433 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 448 | `from value_fabric.layer1.shared.tasks import cleanup_old_content` |
| 1 | 465 | `from value_fabric.layer1.shared.tasks import (` |
| 1 | 490 | `from value_fabric.layer1.shared.tasks import execute_pipeline_stage` |
| 1 | 520 | `from value_fabric.layer1.shared.tasks import celery_app` |
| 1 | 526 | `from value_fabric.layer1.shared.tasks import celery_app` |
| 1 | 538 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 547 | `from value_fabric.layer1.shared.tasks import process_scraping_job` |
| 1 | 558 | `from value_fabric.layer1.shared.tasks import compliance_check_stage` |
| 1 | 598 | `from value_fabric.layer1.shared.tasks import celery_app` |

### `services\layer1-ingestion\tests\unit\test_content_extractor.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 18 | `from value_fabric.layer1.post_processor.content_extractor import (` |

### `services\layer1-ingestion\tests\unit\test_crawler_config.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 11 | `from value_fabric.layer1.crawler.crawler_config import CrawlerConfig, load_co...` |

### `services\layer1-ingestion\tests\unit\test_crawler_telemetry.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 11 | `from value_fabric.layer1.crawler.telemetry import (` |
| 1 | 50 | `import value_fabric.layer1.crawler.telemetry as telemetry` |

### `services\layer1-ingestion\tests\unit\test_event_outbox.py` (service)

**Total imports**: 14

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 21 | `from value_fabric.layer1.shared.models import (` |
| 1 | 134 | `from value_fabric.layer1.shared.tasks import dispatch_outbox_event` |
| 1 | 153 | `from value_fabric.layer1.shared.tasks import dispatch_outbox_event` |
| 1 | 172 | `from value_fabric.layer1.shared.tasks import dispatch_outbox_event` |
| 1 | 190 | `from value_fabric.layer1.shared.tasks import dispatch_outbox_event` |
| 1 | 211 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 246 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 247 | `from value_fabric.layer1.shared.tasks import MAX_DISPATCH_ATTEMPTS` |
| 1 | 286 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 353 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 401 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 445 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 480 | `import value_fabric.layer1.shared.tasks as tasks_module` |
| 1 | 514 | `import value_fabric.layer1.shared.tasks as tasks_module` |

### `services\layer1-ingestion\tests\unit\test_l2_celery_dispatch.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 7 | `from value_fabric.layer1.shared.config import Settings` |

### `services\layer1-ingestion\tests\unit\test_m02_exception_remediation.py` (service)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 18 | `from value_fabric.layer1.crawler.execution_logger import NoOpExecutionLogger` |
| 1 | 24 | `from value_fabric.layer1.crawler.execution_logger import NoOpExecutionLogger` |
| 1 | 31 | `from value_fabric.layer1.crawler.execution_logger import NoOpExecutionLogger` |
| 1 | 40 | `from value_fabric.layer1.shared.database import REDIS_AVAILABLE` |
| 1 | 45 | `from value_fabric.layer1.shared.database import redis_client` |
| 1 | 57 | `from value_fabric.layer1.post_processor.content_extractor import ContentExtra...` |

### `services\layer1-ingestion\tests\unit\test_models.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 5 | `from value_fabric.layer1.shared.models import (` |

### `services\layer1-ingestion\tests\unit\test_pdf_adapter.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 39 | `from value_fabric.layer1.adapters.base import AdapterType, FilingDocument` |
| 1 | 45 | `from value_fabric.layer1.adapters.pdf_adapter import PDFAdapter, PDFAdapterCo...` |

### `services\layer1-ingestion\tests\unit\test_pii_scanner.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 55 | `from value_fabric.layer1.compliance.pii_scanner import (  # noqa: E402` |
| 1 | 61 | `from value_fabric.layer1.shared.models import PIIStatus  # noqa: E402` |
| 1 | 322 | `import value_fabric.layer1.compliance.pii_scanner as pii_mod` |
| 1 | 329 | `import value_fabric.layer1.compliance.pii_scanner as pii_mod` |

### `services\layer1-ingestion\tests\unit\test_playwright_crawler.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 24 | `from value_fabric.layer1.crawler.crawler_config import CrawlerConfig` |
| 1 | 31 | `from value_fabric.layer1.crawler.playwright_crawler import CrawlResult, Playw...` |

### `services\layer1-ingestion\tests\unit\test_quality_gate.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 14 | `from value_fabric.layer1.crawler.httpx_crawler import FastPathResult` |
| 1 | 15 | `from value_fabric.layer1.crawler.quality_gate import (` |

### `services\layer1-ingestion\tests\unit\test_robots_checker_modes.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 7 | `from value_fabric.layer1.compliance.robots_checker import RobotsChecker` |
| 1 | 8 | `from value_fabric.layer1.shared.exceptions import RobotsFetchError` |

### `services\layer1-ingestion\tests\unit\test_scheduler.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 5 | `from value_fabric.layer1.scheduler.priority_queue import PriorityScheduler, R...` |

### `services\layer1-ingestion\tests\unit\test_skill_list_endpoints.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 21 | `from value_fabric.layer1.api.main import router` |
| 1 | 22 | `from value_fabric.layer1.api.main import (` |

### `services\layer1-ingestion\tests\unit\test_smart_router.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 20 | `from value_fabric.layer1.crawler.smart_router import (` |

### `services\layer1-ingestion\tests\unit\test_target_status_transitions.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 7 | `from value_fabric.layer1.shared.models import TargetStatus, ScrapingTarget` |
| 1 | 26 | `from value_fabric.layer1.shared.models import create_scraping_target` |

### `services\layer1-ingestion\tests\unit\test_task_unavailable_error_sanitization.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 3 | `from value_fabric.layer1.api.main import _UnavailableTask, _build_task_unavai...` |

### `services\layer1-ingestion\tests\unit\test_validation.py` (service)

**Total imports**: 13

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 28 | `from value_fabric.layer1.api.main import _validate_cron_expression` |
| 1 | 148 | `from value_fabric.layer1.api.main import ScheduleInput` |
| 1 | 243 | `from value_fabric.layer1.shared.tasks import _validate_payload_against_schema` |
| 1 | 435 | `from value_fabric.layer1.shared.tasks import validation_stage` |
| 1 | 450 | `from value_fabric.layer1.shared.tasks import validation_stage` |
| 1 | 471 | `from value_fabric.layer1.shared.tasks import validation_stage` |
| 1 | 495 | `from value_fabric.layer1.shared.tasks import validation_stage` |
| 1 | 508 | `from value_fabric.layer1.shared.tasks import validation_stage` |
| 1 | 524 | `from value_fabric.layer1.shared.tasks import validation_stage` |
| 1 | 537 | `from value_fabric.layer1.shared.tasks import validation_stage` |
| 1 | 544 | `from value_fabric.layer1.shared.tasks import validation_stage` |
| 1 | 551 | `from value_fabric.layer1.shared.tasks import validation_stage` |
| 1 | 565 | `from value_fabric.layer1.shared.tasks import validation_stage` |

### `services\layer1-ingestion\tests\unit\test_xbrl_parser_extended.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 1 | 15 | `from value_fabric.layer1.adapters.xbrl_parser import (` |
| 1 | 70 | `from value_fabric.layer1.shared.exceptions import XBRLParseError` |
| 1 | 237 | `from value_fabric.layer1.adapters.xbrl_parser import FinancialStatement` |
| 1 | 246 | `from value_fabric.layer1.adapters.xbrl_parser import FinancialStatement` |
| 1 | 255 | `from value_fabric.layer1.adapters.xbrl_parser import FinancialStatement` |

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

### `services\layer3-knowledge\tests\conftest.py` (service)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 54 | `from value_fabric.layer3.api.dependencies import AppState` |
| 3 | 55 | `from value_fabric.layer3.config import Settings, get_settings` |
| 3 | 179 | `from value_fabric.layer3.api.main import app` |
| 3 | 185 | `from value_fabric.layer3.api.dependencies import (` |
| 3 | 215 | `from value_fabric.layer3.api.main import app` |
| 3 | 221 | `from value_fabric.layer3.api.dependencies import (` |

### `services\layer3-knowledge\tests\test_account_authorization.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 13 | `from value_fabric.layer3.schema.entity_scope import (` |
| 3 | 22 | `from value_fabric.layer3.security.account_authorization import (` |

### `services\layer3-knowledge\tests\test_api_wrapper_startup_regression.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.api.main import app` |

### `services\layer3-knowledge\tests\test_audited_graph_mutation.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 9 | `from value_fabric.layer3.db.audited_mutation import AuditedGraphMutation` |
| 3 | 10 | `from value_fabric.layer3.utils.cypher_security import ALLOWED_REL_TYPES` |

### `services\layer3-knowledge\tests\test_backup_runtime_bindings.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.backup.backup_manager import BackupConfig as Service...` |
| 3 | 2 | `from value_fabric.layer3.backup.backup_manager import BackupManager as Servic...` |
| 3 | 3 | `from value_fabric.layer3.backup.backup_manager import LocalStorage as Service...` |
| 3 | 4 | `from value_fabric.layer3.backup.backup_manager import BackupConfig, BackupMan...` |

### `services\layer3-knowledge\tests\test_backup_tenant_scoping.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.backup.backup_manager import (` |

### `services\layer3-knowledge\tests\test_benchmark_policies_route.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 6 | `from value_fabric.layer3.api.routes.benchmarks import list_benchmark_policies` |

### `services\layer3-knowledge\tests\test_cache_characterization.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 15 | `from value_fabric.layer3.cache.redis_cache import CacheManager, RequestDedupl...` |

### `services\layer3-knowledge\tests\test_cache_oss1_parity.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 14 | `from value_fabric.layer3.cache import (` |

### `services\layer3-knowledge\tests\test_cache_ports.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 10 | `from value_fabric.layer3.cache.ports import CachePort, LegacyCacheAdapter, as...` |

### `services\layer3-knowledge\tests\test_canonical_endpoint_surface.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 11 | `from value_fabric.layer3.api.routes.entities import router as entities_router` |
| 3 | 12 | `from value_fabric.layer3.api.routes.calculators import router as calculators_...` |
| 3 | 13 | `from value_fabric.layer3.api.routes.graph_viz import router as graph_viz_router` |

### `services\layer3-knowledge\tests\test_config.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 9 | `from value_fabric.layer3.config import Settings, get_settings` |

### `services\layer3-knowledge\tests\test_config_import_surface.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.config import Settings, get_settings` |

### `services\layer3-knowledge\tests\test_cross_tenant_hostile_behavioral.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 41 | `from value_fabric.layer3.api.dependencies_tenant import Neo4jTenantSession` |
| 3 | 57 | `from value_fabric.layer3.api.dependencies_tenant import Neo4jTenantSession` |
| 3 | 85 | `from value_fabric.layer3.api.dependencies_tenant import Neo4jTenantSession` |

### `services\layer3-knowledge\tests\test_cypher_scope_remediation.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 8 | `from value_fabric.layer3.db.tenant_queries import get_entity_context` |
| 3 | 9 | `from value_fabric.layer3.retrieval.graph_rag import GraphRAGEngine` |
| 3 | 51 | `from value_fabric.layer3.retrieval.graph_rag import _validate_relationship_types` |
| 3 | 58 | `from value_fabric.layer3.retrieval.graph_rag import _validate_entity_type` |
| 3 | 65 | `from value_fabric.layer3.retrieval.graph_rag import _validate_hops` |

### `services\layer3-knowledge\tests\test_dil_phase1.py` (service)

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

### `services\layer3-knowledge\tests\test_dil_phase2.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 28 | `from value_fabric.layer3.services.competitive_intel_service import (` |
| 3 | 34 | `from value_fabric.layer3.services.roi_calculator_service import (` |

### `services\layer3-knowledge\tests\test_e2e_pipeline.py` (service)

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

### `services\layer3-knowledge\tests\test_entities_route_tenant_scoped_regression.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.api.routes.entities import list_entities, query_enti...` |
| 3 | 6 | `from value_fabric.layer3.api.models import EntityFilterRequest` |

### `services\layer3-knowledge\tests\test_entity_resolution.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 12 | `from value_fabric.layer3.schema.entity_resolution import (` |
| 3 | 21 | `from value_fabric.layer3.services.entity_resolution import EntityResolutionSe...` |

### `services\layer3-knowledge\tests\test_entrypoint_route_resolution_regression.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.api.main import app` |

### `services\layer3-knowledge\tests\test_evidence_embedding_failure.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.services.embedding_errors import EmbeddingProviderUn...` |

### `services\layer3-knowledge\tests\test_evidence_links_tenant_isolation.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 8 | `from value_fabric.layer3.api.dependencies import get_neo4j_driver` |
| 3 | 9 | `from value_fabric.layer3.api.main import app` |

### `services\layer3-knowledge\tests\test_exception_handlers.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 8 | `from value_fabric.layer3.api.exceptions import ValueFabricException` |
| 3 | 9 | `from value_fabric.layer3.api.main import (` |

### `services\layer3-knowledge\tests\test_exception_mapping.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.api.exception_mapping import map_exception_to_http_e...` |
| 3 | 2 | `from value_fabric.layer3.api.exceptions import (` |

### `services\layer3-knowledge\tests\test_exceptions.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 3 | `from value_fabric.layer3.api.exceptions import (` |

### `services\layer3-knowledge\tests\test_formula_governance_tenant_extraction.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 11 | `from value_fabric.layer3.api.routes.formula_governance import list_pending_ap...` |

### `services\layer3-knowledge\tests\test_graph_alias_deprecation_policy.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.api.models import (` |

### `services\layer3-knowledge\tests\test_graph_viz_security_boundaries.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 21 | `from value_fabric.layer3.api.dependencies_tenant_secured import require_reque...` |
| 3 | 22 | `from value_fabric.layer3.api.routes.graph_viz import (` |
| 3 | 28 | `from value_fabric.layer3.db.query_execution import MAX_QUERY_DEPTH` |

### `services\layer3-knowledge\tests\test_hybrid_search_api_compat.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.config import Settings` |
| 3 | 6 | `from value_fabric.layer3.retrieval.hybrid_search import HybridSearch` |

### `services\layer3-knowledge\tests\test_i03_variables_production_fail_closed.py` (service)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 29 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |
| 3 | 38 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |
| 3 | 47 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |
| 3 | 56 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |
| 3 | 65 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |
| 3 | 73 | `from value_fabric.layer3.api.routes.variables import _is_production_like` |

### `services\layer3-knowledge\tests\test_ingestion.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 8 | `from value_fabric.layer3.ingestion import Neo4jLoader, RDFLoadError` |
| 3 | 9 | `from value_fabric.layer3.ingestion.neo4j_loader import (` |

### `services\layer3-knowledge\tests\test_ingestion_route_docstring_policy.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 3 | `from value_fabric.layer3.api.routes import ingestion` |

### `services\layer3-knowledge\tests\test_knowledge_subgraph_routes.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 22 | `from value_fabric.layer3.api.routes.knowledge import (` |

### `services\layer3-knowledge\tests\test_layer3_compat_deprecation_phases.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 3 | `from value_fabric.layer3.api.models import GraphEdge, GraphNode, get_deprecat...` |
| 3 | 4 | `from value_fabric.layer3.api.main import app` |

### `services\layer3-knowledge\tests\test_layer3_compat_metrics_thresholds.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 1 | `from value_fabric.layer3.services.compat_metrics import deprecation_ready_for...` |

### `services\layer3-knowledge\tests\test_monolith_route_delegation_guardrail.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 29 | `from value_fabric.layer3.api.routes import (  # noqa: F401` |
| 3 | 40 | `from value_fabric.layer3.api.main import app  # noqa: F401` |

### `services\layer3-knowledge\tests\test_neo4j_integration.py` (service)

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

### `services\layer3-knowledge\tests\test_neo4j_schema_integration.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 29 | `from value_fabric.layer3.config import Settings` |
| 3 | 30 | `from value_fabric.layer3.schema.initializer import SchemaInitializer` |
| 3 | 283 | `from value_fabric.layer3.schema.constraints import get_tenant_constraints` |
| 3 | 291 | `from value_fabric.layer3.schema.constraints import TENANT_CONSTRAINTS, get_te...` |

### `services\layer3-knowledge\tests\test_observability_contract_integration.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 4 | `from value_fabric.layer3.api.main import app` |
| 3 | 25 | `from value_fabric.layer3.metrics.prometheus_metrics import PrometheusMetrics,...` |

### `services\layer3-knowledge\tests\test_pack_loader.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 18 | `from value_fabric.layer3.api.routes import pack_loader` |
| 3 | 19 | `from value_fabric.layer3.api.routes.pack_loader import (` |

### `services\layer3-knowledge\tests\test_packaged_system_routes.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 11 | `from value_fabric.layer3.api.routes import system as system_routes` |
| 3 | 12 | `from value_fabric.layer3.api.models import ServiceMetrics` |

### `services\layer3-knowledge\tests\test_query_search_error_context.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 6 | `from value_fabric.layer3.api.exceptions import SearchError` |
| 3 | 7 | `from value_fabric.layer3.api.models import GraphRAGQuery, SearchRequest` |
| 3 | 8 | `from value_fabric.layer3.api.routes import query_search` |

### `services\layer3-knowledge\tests\test_query_validator.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 11 | `from value_fabric.layer3.security.query_validator import (` |

### `services\layer3-knowledge\tests\test_required_field_validator.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 9 | `from value_fabric.layer3.ingestion.validators import RequiredFieldValidator, ...` |
| 3 | 99 | `from value_fabric.layer3.api.exceptions import IngestionError` |

### `services\layer3-knowledge\tests\test_retrieval.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 9 | `from value_fabric.layer3.retrieval.graph_rag import GraphRAGResult` |
| 3 | 29 | `from value_fabric.layer3.retrieval.hybrid_search import HybridSearchResult` |
| 3 | 49 | `from value_fabric.layer3.retrieval.vector_store import VectorStoreError` |

### `services\layer3-knowledge\tests\test_roi_formula_security.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 14 | `from value_fabric.layer3.agents.roi_calculation import ROICalculationAgent` |

### `services\layer3-knowledge\tests\test_scenario_engine.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.agents.scenario_engine import (` |
| 3 | 122 | `from value_fabric.layer3.agents.scenario_engine import SavedScenario` |

### `services\layer3-knowledge\tests\test_strict_builder_enforcement.py` (service)

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

### `services\layer3-knowledge\tests\test_sync_manager_tenant_isolation.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 6 | `from value_fabric.layer3.ingestion.sync_manager import SyncManager` |

### `services\layer3-knowledge\tests\test_system_routes.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 12 | `from value_fabric.layer3.api.dependencies import get_schema_initializer` |
| 3 | 13 | `from value_fabric.layer3.api.routes import system as system_routes` |

### `services\layer3-knowledge\tests\test_tenant_context_extraction.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 17 | `from value_fabric.layer3.api.dependencies import _extract_tenant_id` |

### `services\layer3-knowledge\tests\test_tenant_id_migration_expansion_labels.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 5 | `from value_fabric.layer3.migrations.migrate_tenant_ids import TenantIdMigration` |

### `services\layer3-knowledge\tests\test_tenant_isolation.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 14 | `from value_fabric.layer3.api.dependencies_tenant_secured import require_reque...` |
| 3 | 15 | `from value_fabric.layer3.api.routes.graph_viz import get_entity_subgraph, get...` |
| 3 | 16 | `from value_fabric.layer3.api.routes.query_search import graph_rag_query_impl,...` |
| 3 | 17 | `from value_fabric.layer3.api.models import GraphRAGQuery, SearchRequest, Sear...` |
| 3 | 18 | `from value_fabric.layer3.api.routes.entities import list_entities` |

### `services\layer3-knowledge\tests\test_tenant_read_isolation.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 10 | `from value_fabric.layer3.db.tenant_queries import (` |

### `services\layer3-knowledge\tests\test_trace_context_propagation_integration.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 8 | `from value_fabric.layer3.tracing.middleware import TracingMiddleware` |

### `services\layer3-knowledge\tests\test_value_packs.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 16 | `from value_fabric.layer3.api.routes.value_packs import (` |

### `services\layer3-knowledge\tests\test_value_packs_tenant_extraction.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 16 | `from value_fabric.layer3.api.routes.value_packs import _tenant_id_from_api_key` |

### `services\layer3-knowledge\tests\test_valuepack_model_forwarder_guard.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 10 | `assert "from value_fabric.layer3.models.valuepack import *" in content` |

### `services\layer3-knowledge\tests\test_vault_config_source.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 16 | `from value_fabric.layer3.config.manager import (` |

### `services\layer3-knowledge\tests\test_vector_e2e.py` (service)

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

### `services\layer3-knowledge\tests\test_vector_store_tenant_write_isolation.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 7 | `from value_fabric.layer3.retrieval.vector_store import Neo4jVectorStore` |

### `services\layer3-knowledge\tests\test_versioning_registration.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 7 | `from value_fabric.layer3.api import main as main_module` |
| 3 | 8 | `from value_fabric.layer3.api import versioning as versioning_module` |
| 3 | 9 | `from value_fabric.layer3.api.versioning import VersionCompatibility` |

### `services\layer4-agents\src\contracts\__init__.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 16 | `from value_fabric.layer4.contracts import (` |

### `services\layer4-agents\tests\conftest.py` (service)

**Total imports**: 9

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 95 | `from value_fabric.layer4.models.account import CRMProvider` |
| 4 | 346 | `from value_fabric.layer4.tools.registry import ToolRegistry` |
| 4 | 390 | `from value_fabric.layer4.workflows.business_case import BusinessCaseGenerator...` |
| 4 | 400 | `from value_fabric.layer4.workflows.roi_calculator import ROICalculatorWorkflow` |
| 4 | 415 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 416 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 417 | `from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowSt...` |
| 4 | 557 | `from value_fabric.layer4.models.workflow_config import EdgeConfig, NodeConfig...` |
| 4 | 558 | `from value_fabric.layer4.workflows.base import BaseWorkflow, WorkflowConfig` |

### `services\layer4-agents\tests\security\test_layer4_tenant_scoped_services.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 7 | `from value_fabric.layer4.interfaces.formula_governance import FormulaStatus` |
| 4 | 8 | `from value_fabric.layer4.interfaces.value_pack_service import (` |
| 4 | 13 | `from value_fabric.layer4.services.formula_governance_service import Neo4jForm...` |
| 4 | 14 | `from value_fabric.layer4.services.value_pack_service import Neo4jValuePackSer...` |

### `services\layer4-agents\tests\test_accounts_api.py` (service)

**Total imports**: 10

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 36 | `from value_fabric.layer4.api.main import app as production_app` |
| 4 | 37 | `from value_fabric.layer4.api.routes.accounts import router as accounts_router` |
| 4 | 38 | `from value_fabric.layer4.api.routes.analysis import get_executor` |
| 4 | 39 | `from value_fabric.layer4.database import Base, get_db_from_context, _mark_ses...` |
| 4 | 40 | `from value_fabric.layer4.models.business_case_record import BusinessCaseRecord` |
| 4 | 41 | `from value_fabric.layer4.models.account import Account, AccountSyncStatus, CR...` |
| 4 | 584 | `from value_fabric.layer4.services.crm_sync_service import CRMSyncService` |
| 4 | 609 | `from value_fabric.layer4.services.crm_sync_service import CRMSyncService` |
| 4 | 635 | `from value_fabric.layer4.services.crm_sync_service import CRMSyncService` |
| 4 | 696 | `from value_fabric.layer4.services.crm_sync_service import CRMSyncService` |

### `services\layer4-agents\tests\test_action_level_approval.py` (service)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.harness.models import ActionClass, GateStatus, GateType` |
| 4 | 11 | `from value_fabric.layer4.policies.approval_actions import (` |
| 4 | 80 | `from value_fabric.layer4.harness.human_gates import HumanGateManager` |
| 4 | 92 | `from value_fabric.layer4.harness.human_gates import HumanGateManager` |
| 4 | 104 | `from value_fabric.layer4.harness.human_gates import HumanGateManager` |
| 4 | 105 | `from value_fabric.layer4.metrics.prometheus_metrics import MetricsConfig, Pro...` |

### `services\layer4-agents\tests\test_admin_tool_h01.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 11 | `from value_fabric.layer4.tools import admin` |

### `services\layer4-agents\tests\test_agent_grounding_and_refusal.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `import value_fabric.layer4.services.conversation as conversation_module` |
| 4 | 11 | `from value_fabric.layer4.services.conversation import ConversationService` |

### `services\layer4-agents\tests\test_agent_mutation_approval_audit.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 14 | `import value_fabric.layer4.services.conversation as conversation_module` |
| 4 | 15 | `from value_fabric.layer4.api.routes import analysis` |
| 4 | 16 | `from value_fabric.layer4.services.conversation import ConversationService` |

### `services\layer4-agents\tests\test_agent_output_traceability.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 20 | `from value_fabric.layer4.agents.base import AgentResult` |

### `services\layer4-agents\tests\test_agent_tenant_isolation.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 14 | `from value_fabric.layer4.api.routes import agent_stream` |
| 4 | 15 | `from value_fabric.layer4.services.conversation import (` |
| 4 | 19 | `from value_fabric.layer4.tools.registry import TenantAwareTool, ToolResult` |

### `services\layer4-agents\tests\test_agent_tool_result_contracts.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `import value_fabric.layer4.tools.registry as registry_module` |
| 4 | 11 | `from value_fabric.layer4.models.tool_schemas import ToolCategory` |
| 4 | 12 | `from value_fabric.layer4.tools.registry import BaseTool, ToolRegistry, ToolRe...` |

### `services\layer4-agents\tests\test_agent_workflow_traceability.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 19 | `from value_fabric.layer4.agents.base import AgentResult` |

### `services\layer4-agents\tests\test_analysis_routes.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 16 | `from value_fabric.layer4.api.routes import analysis` |
| 4 | 17 | `from value_fabric.layer4.api.common.db import get_route_db` |
| 4 | 18 | `from value_fabric.layer4.config.settings import settings` |

### `services\layer4-agents\tests\test_analysis_smoke_mode_service_routes.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 20 | `from value_fabric.layer4.api.routes import analysis` |
| 4 | 21 | `from value_fabric.layer4.config.settings import settings` |
| 4 | 23 | `from value_fabric.layer4.database import get_db_from_context` |

### `services\layer4-agents\tests\test_app_title_contract.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `from value_fabric.layer4.api.app_factory import create_app` |

### `services\layer4-agents\tests\test_audit_route_h01.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 19 | `from value_fabric.layer4.api.routes import audit` |

### `services\layer4-agents\tests\test_authorization_adversarial.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 30 | `from value_fabric.layer4.api.routes.accounts import router as accounts_router` |
| 4 | 31 | `from value_fabric.layer4.database import get_db_from_context` |

### `services\layer4-agents\tests\test_billing_security_exceptions.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 4 | `from value_fabric.layer4.services.billing_security import validate_webhook_re...` |

### `services\layer4-agents\tests\test_billing_service.py` (service)

**Total imports**: 10

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 27 | `from value_fabric.layer4.api.main import app` |
| 4 | 28 | `from value_fabric.layer4.models.billing import (` |
| 4 | 38 | `from value_fabric.layer4.services.billing_service import BillingService, Webh...` |
| 4 | 39 | `from value_fabric.layer4.services.stripe_client import StripeError` |
| 4 | 61 | `from value_fabric.layer4.database import get_db_from_context` |
| 4 | 651 | `from value_fabric.layer4.config.plans import PLANS, FEATURES, get_plan, check...` |
| 4 | 672 | `from value_fabric.layer4.config.plans import get_plan_features` |
| 4 | 686 | `from value_fabric.layer4.config.plans import get_plan_features, check_entitle...` |
| 4 | 695 | `from value_fabric.layer4.models.billing import BillingSubscription, Subscript...` |
| 4 | 710 | `from value_fabric.layer4.models.billing import BillingSubscription, Subscript...` |

### `services\layer4-agents\tests\test_billing_tenant_scoped_customer_keys.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 7 | `from value_fabric.layer4.models.billing import (` |
| 4 | 35 | `from value_fabric.layer4.database import _mark_session_tenant_bypass` |

### `services\layer4-agents\tests\test_billing_webhook_security_consistency.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.api.routes import billing as billing_route` |
| 4 | 11 | `from value_fabric.layer4.services import billing_security, billing_webhook_se...` |

### `services\layer4-agents\tests\test_business_case_claim_promotion.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 11 | `from value_fabric.layer4.services.export_provenance import build_export_prove...` |
| 4 | 12 | `from value_fabric.layer4.workflows.business_case import (` |

### `services\layer4-agents\tests\test_c1_proxy.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `from value_fabric.layer4.api.routes.c1 import C1Message, C1StreamRequest, router` |

### `services\layer4-agents\tests\test_case_permissions_and_audit.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 18 | `from value_fabric.layer4.api.main import app` |
| 4 | 19 | `from value_fabric.layer4.api.routes import analysis` |

### `services\layer4-agents\tests\test_checkpoint_boundary.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 24 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 25 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 85 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 86 | `from value_fabric.layer4.engine.state_manager import StateManager` |

### `services\layer4-agents\tests\test_checkpoint_resume.py` (service)

**Total imports**: 8

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 16 | `from value_fabric.layer4.config.checkpoint import CheckpointConfig, Checkpoin...` |
| 4 | 17 | `from value_fabric.layer4.engine.executor import (` |
| 4 | 22 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 23 | `from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowSt...` |
| 4 | 24 | `from value_fabric.layer4.tools.registry import ToolRegistry` |
| 4 | 25 | `from value_fabric.layer4.workflows.base import BaseWorkflow` |
| 4 | 476 | `from value_fabric.layer4.models.agent_state import WorkflowStatus` |
| 4 | 524 | `from value_fabric.layer4.models.agent_state import WorkflowStatus` |

### `services\layer4-agents\tests\test_checkpoint_resume_failure_paths.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 16 | `from value_fabric.layer4.engine.executor import OrchestrationController, Work...` |
| 4 | 17 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 18 | `from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowSt...` |
| 4 | 19 | `from value_fabric.layer4.tools.registry import ToolRegistry` |

### `services\layer4-agents\tests\test_checkpoint_resume_restart.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 18 | `from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowSt...` |
| 4 | 19 | `from value_fabric.layer4.models.workflow_config import EdgeConfig, NodeConfig...` |
| 4 | 20 | `from value_fabric.layer4.tools.registry import ToolRegistry` |
| 4 | 21 | `from value_fabric.layer4.workflows.base import BaseWorkflow` |

### `services\layer4-agents\tests\test_checkpoints_route_errors.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.api.main import app` |
| 4 | 11 | `from value_fabric.layer4.api.routes.checkpoints import get_executor` |

### `services\layer4-agents\tests\test_code_quality.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 78 | `This allows 'from value_fabric.layer4.interfaces' to work when running from l...` |

### `services\layer4-agents\tests\test_comments_route.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 16 | `from value_fabric.layer4.api.routes import comments` |

### `services\layer4-agents\tests\test_company_knowledge.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 35 | `from value_fabric.layer4.api.routes import company_knowledge as company_knowl...` |
| 4 | 36 | `from value_fabric.layer4.database import get_db_from_context, _mark_session_t...` |
| 4 | 37 | `from value_fabric.layer4.models.company_knowledge import (` |
| 4 | 43 | `from value_fabric.layer4.models.company_knowledge import (` |
| 4 | 53 | `from value_fabric.layer4.services.company_knowledge_service import CompanyKno...` |

### `services\layer4-agents\tests\test_compat_app_surface_contract.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 7 | `from value_fabric.layer4.api.app_factory import create_app` |

### `services\layer4-agents\tests\test_crm_sync_service.py` (service)

**Total imports**: 8

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 27 | `from value_fabric.layer4.api.main import app` |
| 4 | 28 | `from value_fabric.layer4.models.account import (` |
| 4 | 33 | `from value_fabric.layer4.services.crm_sync_service import CRMSyncService` |
| 4 | 80 | `from value_fabric.layer4.database import get_db_from_context` |
| 4 | 147 | `from value_fabric.layer4.models.tool_schemas import GetProspectDataOutput` |
| 4 | 398 | `from value_fabric.layer4.models.integration import Integration, IntegrationSt...` |
| 4 | 639 | `from value_fabric.layer4.services.account_service import AccountService` |
| 4 | 668 | `from value_fabric.layer4.services.account_service import AccountService` |

### `services\layer4-agents\tests\test_crm_tools_pagination.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 19 | `from value_fabric.layer4.models.tool_schemas import GetProspectDataInput` |
| 4 | 20 | `from value_fabric.layer4.tools.crm_tools import GetProspectDataTool` |

### `services\layer4-agents\tests\test_crm_webhook_tenant_isolation.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 24 | `from value_fabric.layer4.api.routes import crm_webhooks as crm_webhooks_module` |
| 4 | 25 | `from value_fabric.layer4.models.account import CRMProvider` |
| 4 | 26 | `from value_fabric.layer4.models.integration import Integration, IntegrationSt...` |

### `services\layer4-agents\tests\test_cross_tenant_hostile.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 11 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 12 | `from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowSt...` |
| 4 | 13 | `from value_fabric.layer4.tools.registry import ToolRegistry` |

### `services\layer4-agents\tests\test_database_session_tenant_enforcement.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 9 | `from value_fabric.layer4.database import (` |
| 4 | 38 | `from value_fabric.layer4.database import _engine` |

### `services\layer4-agents\tests\test_dil_phase3.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 37 | `from value_fabric.layer4.services.narrative_builder_service import (` |
| 4 | 46 | `from value_fabric.layer4.services.intelligence_orchestrator import (` |

### `services\layer4-agents\tests\test_encryption_service.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 23 | `from value_fabric.layer4.services.encryption_service import (` |

### `services\layer4-agents\tests\test_enrichment.py` (service)

**Total imports**: 14

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 115 | `from value_fabric.layer4.services.enrichment_orchestrator import EnrichmentOr...` |
| 4 | 129 | `from value_fabric.layer4.services.enrichment_orchestrator import EnrichmentOr...` |
| 4 | 145 | `from value_fabric.layer4.services.enrichment_orchestrator import (` |
| 4 | 172 | `from value_fabric.layer4.services.enrichment_orchestrator import (` |
| 4 | 200 | `from value_fabric.layer4.services.enrichment_orchestrator import EnrichmentOr...` |
| 4 | 216 | `from value_fabric.layer4.services.enrichment_orchestrator import EnrichmentOr...` |
| 4 | 235 | `from value_fabric.layer4.services.enrichment_orchestrator import EnrichmentOr...` |
| 4 | 260 | `from value_fabric.layer4.services.enrichment_orchestrator import EnrichmentOr...` |
| 4 | 274 | `from value_fabric.layer4.services.enrichment_orchestrator import (` |
| 4 | 290 | `from value_fabric.layer4.services.enrichment_orchestrator import (` |
| 4 | 305 | `from value_fabric.layer4.services.enrichment_orchestrator import (` |
| 4 | 329 | `from value_fabric.layer4.services.enrichment_orchestrator import EnrichmentSt...` |
| 4 | 339 | `from value_fabric.layer4.services.enrichment_orchestrator import EnrichmentSo...` |
| 4 | 348 | `from value_fabric.layer4.services.enrichment_orchestrator import EnrichmentSo...` |

### `services\layer4-agents\tests\test_error_handling_paths.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 7 | `from value_fabric.layer4.services.usage_service import UsageService` |
| 4 | 8 | `from value_fabric.layer4.services.billing_service import BillingService` |

### `services\layer4-agents\tests\test_error_response_shape_canonical.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 18 | `from value_fabric.layer4.api.common.errors import normalize_exception, raise_...` |

### `services\layer4-agents\tests\test_executor_lifecycle_facade.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 7 | `from value_fabric.layer4.engine.execution_dispatch import build_workflow_task` |
| 4 | 8 | `from value_fabric.layer4.engine.execution_validation import ensure_controller...` |
| 4 | 9 | `from value_fabric.layer4.engine.executor import WorkflowExecutionError` |

### `services\layer4-agents\tests\test_export_provenance.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 8 | `from value_fabric.layer4.services.export_provenance import build_export_prove...` |

### `services\layer4-agents\tests\test_feature_flags.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 29 | `from value_fabric.layer4.api.main import app` |
| 4 | 30 | `from value_fabric.layer4.database import Base, get_db_from_context` |
| 4 | 31 | `from value_fabric.layer4.feature_flags.service import FeatureFlagService` |
| 4 | 62 | `from value_fabric.layer4.database import _mark_session_tenant_bypass` |

### `services\layer4-agents\tests\test_frontend_endpoint_contracts.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `from value_fabric.layer4.api.main import app` |

### `services\layer4-agents\tests\test_governance_workflow_contracts.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `from value_fabric.layer4.api.main import app` |

### `services\layer4-agents\tests\test_health_tracker.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 13 | `from value_fabric.layer4.services.health_tracker import (` |
| 4 | 242 | `from value_fabric.layer4.services.health_tracker import HealthBadge` |
| 4 | 294 | `import value_fabric.layer4.services.health_tracker as ht_module` |

### `services\layer4-agents\tests\test_input_validation_adversarial.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 31 | `from value_fabric.layer4.api.routes.company_knowledge import router as compan...` |
| 4 | 32 | `from value_fabric.layer4.database import get_db_from_context` |

### `services\layer4-agents\tests\test_integration_service.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 11 | `from value_fabric.layer4.models.account import CRMProvider` |
| 4 | 12 | `from value_fabric.layer4.services.encryption_service import DEFAULT_KEY_ID, E...` |
| 4 | 13 | `from value_fabric.layer4.services.integration_service import (` |

### `services\layer4-agents\tests\test_interfaces_exports.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 11 | `from value_fabric.layer4.interfaces import (` |

### `services\layer4-agents\tests\test_isolation_tier_provisioning.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 19 | `from value_fabric.layer4.services.tenant_provisioning import (` |
| 4 | 117 | `from value_fabric.layer4.database import get_tiered_db_session` |
| 4 | 133 | `from value_fabric.layer4.database import get_tiered_db_session` |
| 4 | 150 | `from value_fabric.layer4.database import get_tiered_db_session` |
| 4 | 175 | `from value_fabric.layer4.database import db_session_for_context` |

### `services\layer4-agents\tests\test_knowledge_tool_persistence.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 9 | `from value_fabric.layer4.tools import knowledge` |

### `services\layer4-agents\tests\test_langgraph_execution.py` (service)

**Total imports**: 35

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 22 | `from value_fabric.layer4.models.agent_state import (` |
| 4 | 27 | `from value_fabric.layer4.tools.registry import ToolRegistry` |
| 4 | 28 | `from value_fabric.layer4.workflows.business_case import BusinessCaseGenerator...` |
| 4 | 29 | `from value_fabric.layer4.workflows.roi_calculator import ROICalculatorWorkflow` |
| 4 | 30 | `from value_fabric.layer4.workflows.whitespace import WhitespaceAnalysisWorkflow` |
| 4 | 217 | `from value_fabric.layer4.tools.registry import ToolResult` |
| 4 | 687 | `from value_fabric.layer4.models.tool_schemas import GenerateSectionInput` |
| 4 | 688 | `from value_fabric.layer4.tools.generation_tools import GenerateSectionTool` |
| 4 | 707 | `from value_fabric.layer4.models.tool_schemas import GenerateSectionInput` |
| 4 | 708 | `from value_fabric.layer4.tools.generation_tools import GenerateSectionTool` |
| 4 | 734 | `from value_fabric.layer4.models.tool_schemas import GenerateSectionInput` |
| 4 | 735 | `from value_fabric.layer4.tools.generation_tools import GenerateSectionTool` |
| 4 | 753 | `from value_fabric.layer4.tools.generation_tools import GenerateSectionTool` |
| 4 | 777 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 778 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 839 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 840 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 861 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 862 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 883 | `from value_fabric.layer4.config.settings import settings` |
| 4 | 884 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 899 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 900 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 916 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 917 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 933 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 934 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 1146 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 1147 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 1162 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 1163 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 1183 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 1184 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 1195 | `from value_fabric.layer4.models.agent_state import ROIAgentState, WorkflowSta...` |
| 4 | 1234 | `from value_fabric.layer4.agents.signal_detection import SignalDetectionAgent` |

### `services\layer4-agents\tests\test_llm_budget_guardrails.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 11 | `from value_fabric.layer4.services.llm_budget_guardrails import LLMBudgetExcee...` |

### `services\layer4-agents\tests\test_llm_cost_metrics.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `from value_fabric.layer4.metrics.llm_cost_calculator import LLMCostCalculator` |
| 4 | 16 | `from value_fabric.layer4.metrics.prometheus_metrics import MetricsConfig, Pro...` |

### `services\layer4-agents\tests\test_llm_cost_tracking.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 18 | `from value_fabric.layer4.metrics.llm_cost_metrics import record_cost` |
| 4 | 19 | `from value_fabric.layer4.models.cost_record import CostRecord` |
| 4 | 20 | `from value_fabric.layer4.models.tool_schemas import GenerateSectionInput` |
| 4 | 21 | `from value_fabric.layer4.tools.generation_tools import GenerateSectionTool` |
| 4 | 151 | `from value_fabric.layer4.services.llm_budget_guardrails import LLMBudgetExcee...` |

### `services\layer4-agents\tests\test_messaging.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 11 | `from value_fabric.layer4.messaging.bus import InMemoryMessageBus, create_mess...` |
| 4 | 12 | `from value_fabric.layer4.messaging.router import MessageRouter` |
| 4 | 13 | `from value_fabric.layer4.messaging.types import (` |

### `services\layer4-agents\tests\test_model_registry.py` (service)

**Total imports**: 7

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 16 | `from value_fabric.layer4.registry.eval_gate import _DEFAULT_PROMOTION_THRESHO...` |
| 4 | 17 | `from value_fabric.layer4.registry.models import ModelPromotionLog, ModelVersion` |
| 4 | 18 | `from value_fabric.layer4.registry.service import ModelRegistryService, Promot...` |
| 4 | 146 | `from value_fabric.layer4.tenants.models.tenant import Tenant` |
| 4 | 168 | `from value_fabric.layer4.tenants.models.tenant import Tenant` |
| 4 | 250 | `from value_fabric.layer4.tenants.models.tenant import Tenant` |
| 4 | 272 | `from value_fabric.layer4.tenants.models.tenant import Tenant` |

### `services\layer4-agents\tests\test_narratives_tenant_hardening.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 7 | `from value_fabric.layer4.api.routes import narratives` |
| 4 | 8 | `from value_fabric.layer4.services.narrative_builder_service import (` |

### `services\layer4-agents\tests\test_notification.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 14 | `from value_fabric.layer4.models.pause_point import PauseSeverity` |
| 4 | 15 | `from value_fabric.layer4.services.notification import (` |

### `services\layer4-agents\tests\test_notifications_route.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 16 | `from value_fabric.layer4.api.routes import notifications` |

### `services\layer4-agents\tests\test_observability_contract_integration.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 5 | `from value_fabric.layer4.api.app_factory import create_app` |

### `services\layer4-agents\tests\test_observability_gaps.py` (service)

**Total imports**: 8

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.harness.human_gates import HumanGateManager` |
| 4 | 11 | `from value_fabric.layer4.harness.models import ActionClass, GateType, Harness...` |
| 4 | 12 | `from value_fabric.layer4.metrics.prometheus_metrics import MetricsConfig, Pro...` |
| 4 | 13 | `from value_fabric.layer4.models.agent_state import WorkflowStatus` |
| 4 | 114 | `from value_fabric.layer4.metrics.prometheus_metrics import _derive_tenant_tier` |
| 4 | 125 | `from value_fabric.layer4.engine.execution_checkpointing import record_checkpo...` |
| 4 | 126 | `from value_fabric.layer4.metrics.prometheus_metrics import MetricsConfig, Pro...` |
| 4 | 134 | `from value_fabric.layer4.metrics.prometheus_metrics import MetricsConfig, Pro...` |

### `services\layer4-agents\tests\test_oidc_cleanup.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 18 | `from value_fabric.layer4.services.oidc_cleanup import cleanup_expired_oidc_se...` |

### `services\layer4-agents\tests\test_output_envelope_contract.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 5 | `from value_fabric.layer4.engine.output_contract import validate_final_output` |
| 4 | 6 | `from value_fabric.layer4.models.agent_state import (` |
| 4 | 12 | `from value_fabric.layer4.models.reasoning_trace import ReasoningTrace, ToolCa...` |

### `services\layer4-agents\tests\test_pack_variable_loader.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 22 | `from value_fabric.layer4.services.pack_variable_loader import (` |
| 4 | 141 | `from value_fabric.layer4.interfaces.variable_registry import VariableDataType` |
| 4 | 148 | `from value_fabric.layer4.interfaces.variable_registry import VariableDataType` |
| 4 | 155 | `from value_fabric.layer4.interfaces.variable_registry import VariableDataType` |
| 4 | 162 | `from value_fabric.layer4.interfaces.variable_registry import VariableDataType` |

### `services\layer4-agents\tests\test_plan_version_billing.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 9 | `from value_fabric.layer4.models.billing import BillingPlanVersion, BillingSub...` |
| 4 | 10 | `from value_fabric.layer4.services.billing_service import BillingService` |

### `services\layer4-agents\tests\test_prospects_start_analysis.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 24 | `from value_fabric.layer4.api.routes import prospects` |
| 4 | 25 | `from value_fabric.layer4.models.account import Account` |

### `services\layer4-agents\tests\test_reasoning_trace_schema.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.models.reasoning_trace import (` |
| 4 | 150 | `from value_fabric.layer4.models.reasoning_trace import build_reasoning_trace` |
| 4 | 151 | `from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowType` |

### `services\layer4-agents\tests\test_replay_conflict_policy.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.models.agent_state import WorkflowStatus` |
| 4 | 11 | `from value_fabric.layer4.policies.replay_conflict import (` |

### `services\layer4-agents\tests\test_resilience.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 17 | `from value_fabric.layer4.resilience import (` |

### `services\layer4-agents\tests\test_roi_calculator_workflow.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 20 | `from value_fabric.layer4.models.agent_state import ROIAgentState, WorkflowStatus` |
| 4 | 21 | `from value_fabric.layer4.tools.registry import ToolResult` |
| 4 | 22 | `from value_fabric.layer4.workflows.roi_calculator import (` |

### `services\layer4-agents\tests\test_run_envelope_contract.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 8 | `from value_fabric.layer4.models.run_envelope import RunEnvelope` |
| 4 | 9 | `from value_fabric.layer4.workflows.roi_calculator import ROICalculatorWorkflow` |
| 4 | 10 | `from value_fabric.layer4.tools.registry import ToolRegistry` |

### `services\layer4-agents\tests\test_runtime_hardening.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `import value_fabric.layer4.services.llm_budget_guardrails as budget_module` |
| 4 | 11 | `from value_fabric.layer4.services.llm_budget_guardrails import LLMBudgetGuard...` |
| 4 | 12 | `from value_fabric.layer4.workflows.whitespace import ExtractedNeedsResponse` |

### `services\layer4-agents\tests\test_salesforce_oauth.py` (service)

**Total imports**: 7

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 19 | `from value_fabric.layer4.models.account import CRMProvider` |
| 4 | 20 | `from value_fabric.layer4.models.integration import Integration, IntegrationSt...` |
| 4 | 21 | `from value_fabric.layer4.services.encryption_service import DEFAULT_KEY_ID, E...` |
| 4 | 22 | `from value_fabric.layer4.services.integration_service import (` |
| 4 | 234 | `from value_fabric.layer4.services.crm_sync_scheduler import CRMSyncScheduler` |
| 4 | 266 | `from value_fabric.layer4.services.crm_sync_scheduler import CRMSyncScheduler` |
| 4 | 285 | `from value_fabric.layer4.services.crm_sync_service import CRMSyncService` |

### `services\layer4-agents\tests\test_salesforce_oauth_routes.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 17 | `from value_fabric.layer4.api.routes import integrations as integrations_route` |

### `services\layer4-agents\tests\test_security_fixes.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 29 | `from value_fabric.layer4.api.routes.billing import _get_client_ip, _is_stripe...` |
| 4 | 30 | `from value_fabric.layer4.api.routes.health_badges import dismiss_badge, get_d...` |
| 4 | 31 | `from value_fabric.layer4.config.settings import Settings  # noqa: E402` |
| 4 | 32 | `from value_fabric.layer4.metrics.prometheus_metrics import _derive_tenant_tie...` |

### `services\layer4-agents\tests\test_signal_review_route.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.api.routes import signals` |

### `services\layer4-agents\tests\test_startup_contract.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 6 | `from value_fabric.layer4.api.app_factory import create_app` |
| 4 | 7 | `from value_fabric.layer4.api.startup import (` |

### `services\layer4-agents\tests\test_startup_dependencies.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 5 | `from value_fabric.layer4.startup_dependencies import verify_startup_dependencies` |

### `services\layer4-agents\tests\test_startup_dependency_verifier.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 7 | `from value_fabric.layer4.startup.dependency_verifier import (` |

### `services\layer4-agents\tests\test_tasks_route.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 16 | `from value_fabric.layer4.api.routes import tasks` |

### `services\layer4-agents\tests\test_tenant_api.py` (service)

**Total imports**: 6

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 25 | `from value_fabric.layer4.api.tenants import router` |
| 4 | 26 | `from value_fabric.layer4.services.tenant_provisioning import TenantProvisionR...` |
| 4 | 249 | `from value_fabric.layer4.api.tenants import ProvisionTenantRequest` |
| 4 | 261 | `from value_fabric.layer4.api.tenants import ProvisionTenantResponse` |
| 4 | 278 | `from value_fabric.layer4.api.tenants import TenantSummary` |
| 4 | 375 | `from value_fabric.layer4.api.tenants import _count_tenant_entities` |

### `services\layer4-agents\tests\test_tenant_context_route.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 12 | `from value_fabric.layer4.api.routes import tenant_context as tenant_context_r...` |

### `services\layer4-agents\tests\test_tenant_lifecycle.py` (service)

**Total imports**: 8

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 45 | `from value_fabric.layer4.tenants.models.tenant import Tenant` |
| 4 | 284 | `from value_fabric.layer4.tenants.models.tenant import Tenant` |
| 4 | 299 | `from value_fabric.layer4.tenants.service import update_tenant_status` |
| 4 | 317 | `from value_fabric.layer4.tenants.models.tenant import Tenant` |
| 4 | 331 | `from value_fabric.layer4.tenants.service import update_tenant_status` |
| 4 | 344 | `from value_fabric.layer4.tenants.service import update_tenant_status` |
| 4 | 354 | `from value_fabric.layer4.tenants.models.tenant import Tenant` |
| 4 | 369 | `from value_fabric.layer4.tenants.service import delete_tenant` |

### `services\layer4-agents\tests\test_tenant_provisioning.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 22 | `from value_fabric.layer4.services.tenant_provisioning import (` |

### `services\layer4-agents\tests\test_tenant_rate_limits.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 31 | `from value_fabric.layer4.tenants.settings_schema import (` |

### `services\layer4-agents\tests\test_tiers.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 8 | `from value_fabric.layer4.tenants.tiers import (` |

### `services\layer4-agents\tests\test_tool_execution_contract.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 18 | `from value_fabric.layer4.tools.registry import BaseTool, ToolResult` |

### `services\layer4-agents\tests\test_tool_output_structure_validation.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 20 | `from value_fabric.layer4.tools.registry import ToolResult` |

### `services\layer4-agents\tests\test_tool_result_contract.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 13 | `from value_fabric.layer4.tools import BaseTool, ToolRegistry, ToolResult` |
| 4 | 14 | `from value_fabric.layer4.tools.calculation_tools import CalculateROITool, Eva...` |
| 4 | 15 | `from value_fabric.layer4.tools.competitive_tools import LLMDifferenceItem, LL...` |
| 4 | 358 | `from value_fabric.layer4.tools.competitive_tools import AnalyzeCompetitionTool` |

### `services\layer4-agents\tests\test_tools_authorization.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 9 | `from value_fabric.layer4.api.routes import tools` |
| 4 | 10 | `from value_fabric.layer4.services.agent_tools import AgentToolRegistry` |
| 4 | 11 | `from value_fabric.layer4.tools.registry import BaseTool, ToolCategory, ToolRe...` |

### `services\layer4-agents\tests\test_tools_route_response_models.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 3 | `from value_fabric.layer4.contracts.tool_dto import ToolCategoryListResponse, ...` |

### `services\layer4-agents\tests\test_tools_routes_contract.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 7 | `from value_fabric.layer4.api.routes import tools` |
| 4 | 8 | `from value_fabric.layer4.models.tool_schemas import ToolCategory` |

### `services\layer4-agents\tests\test_trace_header_propagation_integration.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 3 | 13 | `from value_fabric.layer3.tracing.middleware import TracingMiddleware` |

### `services\layer4-agents\tests\test_usage_idempotency.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 21 | `from value_fabric.layer4.models.billing import BillingUsageEvent, UsageEventS...` |
| 4 | 22 | `from value_fabric.layer4.services.usage_service import UsageService, UsageVal...` |

### `services\layer4-agents\tests\test_usage_service.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 21 | `from value_fabric.layer4.models.billing import BillingUsageEvent, UsageEventS...` |
| 4 | 22 | `from value_fabric.layer4.api.routes.billing import UsageBatchRequest, UsageEv...` |
| 4 | 23 | `from value_fabric.layer4.services.usage_service import UsageService, UsageVal...` |
| 4 | 281 | `from value_fabric.layer4.api.main import app` |

### `services\layer4-agents\tests\test_validation_auth_seed.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 19 | `from value_fabric.layer4.api.routes import analysis` |
| 4 | 20 | `from value_fabric.layer4.tenants.models.api_key import APIKey` |
| 4 | 21 | `from value_fabric.layer4.tenants.models.tenant import Tenant` |
| 4 | 22 | `from value_fabric.layer4.tenants.models.user import User` |

### `services\layer4-agents\tests\test_value_flow_facade.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 19 | `from value_fabric.layer4.api.schemas.value_flow import ValueFlowStep` |
| 4 | 20 | `from value_fabric.layer4.services.value_flow_facade import ValueFlowFacadeSer...` |

### `services\layer4-agents\tests\test_value_hypothesis.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 34 | `from value_fabric.layer4.services.value_hypothesis_engine import (` |

### `services\layer4-agents\tests\test_variable_registry_helpers.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 18 | `from value_fabric.layer4.interfaces.variable_registry import (` |
| 4 | 22 | `from value_fabric.layer4.services.variable_registry_service import Neo4jVaria...` |

### `services\layer4-agents\tests\test_webhook_security.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 22 | `from value_fabric.layer4.models.billing import (` |
| 4 | 29 | `from value_fabric.layer4.services.billing_service import BillingService` |

### `services\layer4-agents\tests\test_webhook_security_matrix.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 14 | `from value_fabric.layer4.api.routes import billing as billing_route` |
| 4 | 15 | `from value_fabric.layer4.api.routes import crm_webhooks as crm_route` |
| 4 | 16 | `from value_fabric.layer4.tenants.api.routes import provisioning as prov_route` |

### `services\layer4-agents\tests\test_websocket_auth_routes.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 19 | `from value_fabric.layer4.api.websocket.auth import (` |
| 4 | 24 | `from value_fabric.layer4.api.websocket.routes import workflow_websocket` |

### `services\layer4-agents\tests\test_websocket_manager.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 17 | `from value_fabric.layer4.api.websocket.manager import (` |
| 4 | 640 | `import value_fabric.layer4.api.websocket.manager as manager_module` |

### `services\layer4-agents\tests\test_websocket_multitenant_hostile.py` (service)

**Total imports**: 23

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 106 | `from value_fabric.layer4.api.websocket.routes import workflow_websocket` |
| 4 | 150 | `from value_fabric.layer4.api.websocket.routes import workflow_websocket` |
| 4 | 178 | `from value_fabric.layer4.api.websocket.routes import workflow_websocket` |
| 4 | 224 | `from value_fabric.layer4.api.websocket.routes import workflow_websocket` |
| 4 | 247 | `from value_fabric.layer4.api.websocket.routes import _resolve_workflow_author...` |
| 4 | 265 | `from value_fabric.layer4.api.websocket.routes import _resolve_workflow_author...` |
| 4 | 283 | `from value_fabric.layer4.api.websocket.routes import _resolve_workflow_author...` |
| 4 | 298 | `from value_fabric.layer4.api.websocket.routes import _resolve_workflow_author...` |
| 4 | 317 | `from value_fabric.layer4.api.websocket.routes import _resolve_workflow_author...` |
| 4 | 341 | `from value_fabric.layer4.api.websocket.routes import workflow_websocket` |
| 4 | 360 | `from value_fabric.layer4.api.websocket.routes import workflow_websocket` |
| 4 | 376 | `from value_fabric.layer4.api.websocket.routes import workflow_websocket` |
| 4 | 406 | `from value_fabric.layer4.api.routes.signals import signal_stream_websocket` |
| 4 | 431 | `from value_fabric.layer4.api.routes.signals import signal_stream_websocket` |
| 4 | 458 | `from value_fabric.layer4.api.routes.signals import signal_stream_websocket` |
| 4 | 481 | `from value_fabric.layer4.api.routes.signals import signal_stream_websocket` |
| 4 | 504 | `from value_fabric.layer4.api.routes.signals import signal_stream_websocket` |
| 4 | 539 | `from value_fabric.layer4.api.routes.signals import signal_stream_websocket` |
| 4 | 554 | `from value_fabric.layer4.api.routes.signals import signal_stream_websocket` |
| 4 | 566 | `from value_fabric.layer4.api.routes.signals import signal_stream_websocket` |
| 4 | 582 | `from value_fabric.layer4.api.routes.signals import signal_stream_websocket` |
| 4 | 617 | `from value_fabric.layer4.api.websocket.routes import workflow_websocket` |
| 4 | 630 | `from value_fabric.layer4.api.routes.signals import signal_stream_websocket` |

### `services\layer4-agents\tests\test_workflow_canonical_contract.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 11 | `from value_fabric.layer4.api.routes import workflows` |

### `services\layer4-agents\tests\test_workflow_replay_harness.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 13 | `from value_fabric.layer4.policies.replay_conflict import ReplayConflictError` |

### `services\layer4-agents\tests\test_workflow_resume_checkpoint_conflict_route.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.api.main import app` |
| 4 | 11 | `from value_fabric.layer4.api.routes.workflows import get_executor` |
| 4 | 13 | `from value_fabric.layer4.engine.executor import CheckpointConflictError` |

### `services\layer4-agents\tests\test_workflow_start_tenant_invariant.py` (service)

**Total imports**: 7

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 11 | `from value_fabric.layer4.engine.executor import OrchestrationController, Work...` |
| 4 | 12 | `from value_fabric.layer4.engine.scheduler import TaskPriority` |
| 4 | 13 | `from value_fabric.layer4.models.agent_state import TenantMissingError` |
| 4 | 14 | `from value_fabric.layer4.tools.registry import ToolRegistry` |
| 4 | 15 | `from value_fabric.layer4.workflows.roi_calculator import ROICalculatorWorkflow` |
| 4 | 20 | `from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowType` |
| 4 | 29 | `from value_fabric.layer4.models.agent_state import BaseAgentState, WorkflowType` |

### `services\layer4-agents\tests\test_workflows_real_execution.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 23 | `from value_fabric.layer4.workflows.base import DEFAULT_RECURSION_LIMIT` |

### `services\layer4-agents\tests\unit\test_api_common_helpers.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 8 | `from value_fabric.layer4.api.common import audit as audit_helpers` |
| 4 | 9 | `from value_fabric.layer4.api.common.errors import normalize_exception, raise_...` |

### `services\layer4-agents\tests\unit\test_executor_checkpoint_conflict.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `from value_fabric.layer4.engine.executor import (` |
| 4 | 20 | `from value_fabric.layer4.models.agent_state import (` |
| 4 | 25 | `from value_fabric.layer4.tools.registry import ToolRegistry` |

### `services\layer4-agents\tests\unit\test_executor_controller_invariants.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 16 | `from value_fabric.layer4.engine.executor import (` |
| 4 | 21 | `from value_fabric.layer4.models.agent_state import (` |
| 4 | 26 | `from value_fabric.layer4.tools.registry import ToolRegistry` |

### `services\layer4-agents\tests\unit\test_layer4_correctness_patch.py` (service)

**Total imports**: 74

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 56 | `from value_fabric.layer4.services.governed_llm_client import GovernedLLMClient` |
| 4 | 104 | `from value_fabric.layer4.services.governed_llm_client import _CostCapExceeded` |
| 4 | 117 | `from value_fabric.layer4.services.governed_llm_client import _CostCapExceeded` |
| 4 | 132 | `from value_fabric.layer4.services.governed_llm_client import _CostCapExceeded` |
| 4 | 155 | `from value_fabric.layer4.services.governed_llm_client import _CostCapExceeded` |
| 4 | 173 | `from value_fabric.layer4.services.governed_llm_client import _CostCapExceeded` |
| 4 | 242 | `from value_fabric.layer4.workflows.business_case import BusinessCaseGenerator...` |
| 4 | 389 | `from value_fabric.layer4.workflows.business_case import MissingTenantContextE...` |
| 4 | 407 | `from value_fabric.layer4.workflows.business_case import MissingTenantContextE...` |
| 4 | 423 | `from value_fabric.layer4.workflows.business_case import MissingTenantContextE...` |
| 4 | 441 | `from value_fabric.layer4.workflows.business_case import MissingTenantContextE...` |
| 4 | 457 | `from value_fabric.layer4.workflows.business_case import MissingTenantContextE...` |
| 4 | 479 | `from value_fabric.layer4.agents.signal_detection import SignalDetectionAgent` |
| 4 | 614 | `from value_fabric.layer4.agents.taxonomy import ContextExtractionAgent` |
| 4 | 631 | `from value_fabric.layer4.agents.taxonomy import ContextExtractionAgent` |
| 4 | 648 | `from value_fabric.layer4.agents.taxonomy import ContextExtractionAgent` |
| 4 | 674 | `from value_fabric.layer4.agents.taxonomy import ValueModelAgent` |
| 4 | 690 | `from value_fabric.layer4.agents.taxonomy import ValueModelAgent` |
| 4 | 714 | `from value_fabric.layer4.agents.taxonomy import IntegrityAgent` |
| 4 | 730 | `from value_fabric.layer4.agents.taxonomy import IntegrityAgent` |
| 4 | 755 | `from value_fabric.layer4.agents.taxonomy import NarrativeAgent` |
| 4 | 771 | `from value_fabric.layer4.agents.taxonomy import NarrativeAgent` |
| 4 | 804 | `from value_fabric.layer4.services.governed_llm_client import LLMCallResult` |
| 4 | 811 | `from value_fabric.layer4.services.governed_llm_client import _CostCapExceeded` |
| 4 | 821 | `from value_fabric.layer4.services.governed_llm_client import _CostCapExceeded` |
| 4 | 877 | `from value_fabric.layer4.harness.models import HarnessRun, HarnessWorkflowTyp...` |
| 4 | 890 | `from value_fabric.layer4.harness.models import HarnessRun, HarnessWorkflowTyp...` |
| 4 | 903 | `from value_fabric.layer4.services.governed_llm_client import GovernedLLMClient` |
| 4 | 909 | `from value_fabric.layer4.services.governed_llm_client import GovernedLLMClient` |
| 4 | 936 | `from value_fabric.layer4.agents.taxonomy import ContextExtractionAgent` |
| 4 | 948 | `from value_fabric.layer4.agents.taxonomy import ContextExtractionAgent` |
| 4 | 961 | `from value_fabric.layer4.agents.taxonomy import ContextExtractionAgent` |
| 4 | 972 | `from value_fabric.layer4.agents.taxonomy import ValueModelAgent` |
| 4 | 984 | `from value_fabric.layer4.agents.taxonomy import ValueModelAgent` |
| 4 | 996 | `from value_fabric.layer4.agents.taxonomy import ValueModelAgent` |
| 4 | 1008 | `from value_fabric.layer4.agents.taxonomy import ValueModelAgent` |
| 4 | 1020 | `from value_fabric.layer4.agents.taxonomy import IntegrityAgent` |
| 4 | 1034 | `from value_fabric.layer4.agents.taxonomy import IntegrityAgent` |
| 4 | 1046 | `from value_fabric.layer4.agents.taxonomy import NarrativeAgent` |
| 4 | 1059 | `from value_fabric.layer4.agents.taxonomy import NarrativeAgent` |
| 4 | 1071 | `from value_fabric.layer4.agents.taxonomy import NarrativeAgent` |
| 4 | 1083 | `from value_fabric.layer4.agents.taxonomy import CompetitiveIntelAgent` |
| 4 | 1095 | `from value_fabric.layer4.agents.taxonomy import CompetitiveIntelAgent` |
| 4 | 1107 | `from value_fabric.layer4.agents.taxonomy import CompetitiveIntelAgent` |
| 4 | 1114 | `from value_fabric.layer4.agents.taxonomy import ConversationAgent` |
| 4 | 1126 | `from value_fabric.layer4.agents.taxonomy import ConversationAgent` |
| 4 | 1134 | `from value_fabric.layer4.agents.taxonomy import ConversationAgent` |
| 4 | 1149 | `from value_fabric.layer4.agents.signal_detection import SignalDetectionAgent` |
| 4 | 1205 | `from value_fabric.layer4.agents.taxonomy import _gate_execute` |
| 4 | 1216 | `from value_fabric.layer4.agents.taxonomy import _gate_execute` |
| 4 | 1227 | `from value_fabric.layer4.agents.taxonomy import _gate_execute` |
| 4 | 1234 | `from value_fabric.layer4.agents.taxonomy import _gate_execute` |
| 4 | 1247 | `from value_fabric.layer4.agents.taxonomy import ContextExtractionAgent` |
| 4 | 1271 | `from value_fabric.layer4.agents.taxonomy import ValueModelAgent` |
| 4 | 1287 | `from value_fabric.layer4.agents.taxonomy import ValueModelAgent` |
| 4 | 1305 | `from value_fabric.layer4.agents.taxonomy import IntegrityAgent` |
| 4 | 1322 | `from value_fabric.layer4.agents.taxonomy import IntegrityAgent` |
| 4 | 1345 | `from value_fabric.layer4.agents.taxonomy import IntegrityAgent` |
| 4 | 1366 | `from value_fabric.layer4.agents.taxonomy import ConversationAgent` |
| 4 | 1390 | `from value_fabric.layer4.agents.taxonomy import ConversationAgent` |
| 4 | 1416 | `from value_fabric.layer4.agents.taxonomy import OrchestrationController` |
| 4 | 1439 | `from value_fabric.layer4.agents.taxonomy import OrchestrationController` |
| 4 | 1458 | `from value_fabric.layer4.agents.taxonomy import OrchestrationController` |
| 4 | 1480 | `from value_fabric.layer4.agents.taxonomy import OrchestrationController` |
| 4 | 1498 | `from value_fabric.layer4.agents.taxonomy import OrchestrationController` |
| 4 | 1552 | `from value_fabric.layer4.agents.signal_detection import SignalDetectionAgent` |
| 4 | 1569 | `from value_fabric.layer4.models.pain_signal import PainSignal, SignalCategory...` |
| 4 | 1598 | `from value_fabric.layer4.models.pain_signal import PainSignal` |
| 4 | 1765 | `from value_fabric.layer4.services.governed_llm_client import LLMCallResult` |
| 4 | 1844 | `from value_fabric.layer4.agents.signal_detection import SignalDetectionAgent` |
| 4 | 1852 | `from value_fabric.layer4.agents.signal_detection import SignalDetectionAgent` |
| 4 | 1863 | `from value_fabric.layer4.agents.signal_detection import SignalDetectionAgent` |
| 4 | 1876 | `from value_fabric.layer4.agents.signal_detection import SignalDetectionAgent` |
| 4 | 1904 | `from value_fabric.layer4.models.pain_signal import SignalCategory, TrendDirec...` |

### `services\layer4-agents\tests\unit\test_layer4_observability_schema.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 3 | `from value_fabric.layer4.observability import Layer4EventContext` |

### `services\layer4-agents\tests\unit\test_observability_schema_legacy.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 8 | `from value_fabric.layer4.observability import Layer4EventContext, Layer4Lifec...` |

### `services\layer4-agents\tests\unit\test_oss0_ports.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 11 | `from value_fabric.layer4.engine.ports import (` |
| 4 | 16 | `from value_fabric.layer4.engine.scheduler import ScheduledTask, TaskPriority,...` |
| 4 | 17 | `from value_fabric.layer4.resilience import CircuitBreaker, TenantRateLimiter` |
| 4 | 18 | `from value_fabric.layer4.resilience_ports import (` |

### `services\layer4-agents\tests\unit\test_overage_service.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 16 | `from value_fabric.layer4.services.overage_service import OverageService, Usag...` |
| 4 | 159 | `from value_fabric.layer4.config.plans import Plan` |
| 4 | 277 | `from value_fabric.layer4.config.plans import Plan, UsageLimit` |

### `services\layer4-agents\tests\unit\test_production_readiness_fixes.py` (service)

**Total imports**: 13

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 25 | `from value_fabric.layer4.api.routes.workflows import WorkflowEvent, WorkflowE...` |
| 4 | 26 | `from value_fabric.layer4.config.checkpoint import CheckpointConfig` |
| 4 | 27 | `from value_fabric.layer4.engine.executor import OrchestrationController` |
| 4 | 28 | `from value_fabric.layer4.engine.scheduler import ScheduledTask, TaskScheduler...` |
| 4 | 29 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 30 | `from value_fabric.layer4.models.agent_state import (` |
| 4 | 35 | `from value_fabric.layer4.workflows.base import BaseWorkflow, WorkflowBuilder` |
| 4 | 36 | `from value_fabric.layer4.workflows import WORKFLOW_TYPES` |
| 4 | 49 | `from value_fabric.layer4.config import settings as settings_mod` |
| 4 | 57 | `from value_fabric.layer4.config.settings import configure_settings` |
| 4 | 74 | `from value_fabric.layer4.models.agent_state import ROIAgentState` |
| 4 | 91 | `from value_fabric.layer4.models.agent_state import ROIAgentState` |
| 4 | 185 | `from value_fabric.layer4.models.workflow_config import EdgeConfig, EdgeType` |

### `services\layer4-agents\tests\unit\test_scheduler_execution.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 10 | `from value_fabric.layer4.engine.scheduler import ScheduledTask, TaskScheduler` |

### `services\layer4-agents\tests\unit\test_services_unit.py` (service)

**Total imports**: 12

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 24 | `from value_fabric.layer4.services.value_pack_service import Neo4jValuePackSer...` |
| 4 | 84 | `from value_fabric.layer4.models.business_case_record import BusinessCaseRecord` |
| 4 | 99 | `from value_fabric.layer4.services.business_case_service import BusinessCaseSe...` |
| 4 | 121 | `from value_fabric.layer4.services.business_case_service import BusinessCaseSe...` |
| 4 | 147 | `from value_fabric.layer4.services.business_case_service import BusinessCaseSe...` |
| 4 | 170 | `from value_fabric.layer4.services.business_case_service import BusinessCaseSe...` |
| 4 | 199 | `from value_fabric.layer4.services.encryption_service import EncryptionService` |
| 4 | 215 | `from value_fabric.layer4.services.encryption_service import EncryptionService` |
| 4 | 229 | `from value_fabric.layer4.services.encryption_service import EncryptionService` |
| 4 | 242 | `from value_fabric.layer4.services.encryption_service import EncryptionService` |
| 4 | 253 | `from value_fabric.layer4.services.encryption_service import EncryptionService` |
| 4 | 263 | `from value_fabric.layer4.services.encryption_service import EncryptionService` |

### `services\layer4-agents\tests\unit\test_state_manager.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `from value_fabric.layer4.engine.state_manager import StateManager` |
| 4 | 16 | `from value_fabric.layer4.models.agent_state import (` |

### `services\layer4-agents\tests\unit\test_task_scheduler.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `from value_fabric.layer4.engine.scheduler import (` |

### `services\layer4-agents\tests\unit\test_value_flow_facade.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 14 | `from value_fabric.layer4.api.schemas.value_flow import ValueFlowStep` |
| 4 | 15 | `from value_fabric.layer4.services.value_flow_facade import ValueFlowFacadeSer...` |

### `services\layer4-agents\tests\unit\test_variable_registry_service.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 18 | `from value_fabric.layer4.services.variable_registry_service import Neo4jVaria...` |
| 4 | 19 | `from value_fabric.layer4.interfaces.variable_registry import (` |
| 4 | 268 | `from value_fabric.layer4.interfaces.variable_registry import Variable` |

### `services\layer4-agents\tests\unit\test_workflow_routes.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 13 | `from value_fabric.layer4.api.routes.workflows import (` |
| 4 | 81 | `from value_fabric.layer4.api.schemas.workflow_progress import WorkflowProgres...` |

### `services\layer4-agents\tests\unit\test_workflow_state_machine.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 4 | 15 | `from value_fabric.layer4.models.agent_state import (` |
| 4 | 26 | `from value_fabric.layer4.workflows.base import BaseWorkflow, WorkflowError, N...` |
| 4 | 27 | `from value_fabric.layer4.models.workflow_config import WorkflowConfig, NodeCo...` |
| 4 | 28 | `from value_fabric.layer4.tools.registry import ToolRegistry` |

### `services\layer6-benchmarks\tests\conftest.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 44 | `import value_fabric.layer6.database as database` |
| 6 | 85 | `import value_fabric.layer6.api.main as main_module` |

### `services\layer6-benchmarks\tests\test_api_schemas.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 6 | `from value_fabric.layer6.api.schemas import (` |

### `services\layer6-benchmarks\tests\test_api_tenant_propagation.py` (service)

**Total imports**: 4

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 12 | `from value_fabric.layer6.api.deps import get_request_context` |
| 6 | 13 | `from value_fabric.layer6.api.main import app` |
| 6 | 14 | `from value_fabric.layer6.models.benchmark_dataset import (` |
| 6 | 218 | `import value_fabric.layer6.api.main as main_module` |

### `services\layer6-benchmarks\tests\test_benchmark_api.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 7 | `import value_fabric.layer6.api.main as main_module` |
| 6 | 9 | `from value_fabric.layer6.api.main import app` |
| 6 | 11 | `from value_fabric.layer6.models.benchmark_dataset import (` |

### `services\layer6-benchmarks\tests\test_benchmark_edge_cases.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 9 | `import value_fabric.layer6.api.main as main_module` |
| 6 | 11 | `from value_fabric.layer6.api.main import app` |

### `services\layer6-benchmarks\tests\test_benchmark_route_matrix.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 5 | `import value_fabric.layer6.api.main as main_module` |
| 6 | 7 | `from value_fabric.layer6.api.main import app` |
| 6 | 8 | `from value_fabric.layer6.models.benchmark_dataset import BenchmarkDataset, Be...` |

### `services\layer6-benchmarks\tests\test_benchmark_route_matrix_and_contracts.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 9 | `import value_fabric.layer6.api.main as main_module` |
| 6 | 11 | `from value_fabric.layer6.api.main import app` |
| 6 | 12 | `from value_fabric.layer6.models.benchmark_dataset import BenchmarkDataset, Be...` |

### `services\layer6-benchmarks\tests\test_database_driver.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 8 | `import value_fabric.layer6.database as db_module` |
| 6 | 9 | `from value_fabric.layer6.database import close_driver, create_driver, get_dri...` |

### `services\layer6-benchmarks\tests\test_metrics_contract.py` (service)

**Total imports**: 5

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 7 | `import value_fabric.layer6.api.main as main_module` |
| 6 | 10 | `from value_fabric.layer6.api.main import app` |
| 6 | 11 | `from value_fabric.layer6.metrics.prometheus_metrics import (` |
| 6 | 16 | `from value_fabric.layer6.models.benchmark_dataset import (` |
| 6 | 21 | `from value_fabric.layer6.observability.metrics_contract import metric_names` |

### `services\layer6-benchmarks\tests\test_metrics_prometheus.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 6 | `from value_fabric.layer6.metrics.prometheus_metrics import (` |

### `services\layer6-benchmarks\tests\test_models_benchmark_dataset.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 8 | `from value_fabric.layer6.models.benchmark_dataset import (` |

### `services\layer6-benchmarks\tests\test_observability_metrics_contract.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 3 | `from value_fabric.layer6.observability.metrics_contract import (` |

### `services\layer6-benchmarks\tests\test_repository_pures.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 8 | `from value_fabric.layer6.models.benchmark_dataset import (` |
| 6 | 13 | `from value_fabric.layer6.repositories.benchmark_repository import (` |

### `services\layer6-benchmarks\tests\test_repository_tenant_isolation.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 7 | `from value_fabric.layer6.models.benchmark_dataset import (` |
| 6 | 12 | `from value_fabric.layer6.repositories.benchmark_repository import BenchmarkRe...` |

### `services\layer6-benchmarks\tests\test_scope_authorization.py` (service)

**Total imports**: 3

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 9 | `import value_fabric.layer6.api.main as main_module` |
| 6 | 10 | `from value_fabric.layer6.api.schemas import ComparisonRequestPayload` |
| 6 | 11 | `from value_fabric.layer6.models.benchmark_dataset import BenchmarkDataset, Be...` |

### `services\layer6-benchmarks\tests\test_settings_validation.py` (service)

**Total imports**: 1

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 7 | `from value_fabric.layer6.settings import (` |

### `services\layer6-benchmarks\tests\test_startup_logging.py` (service)

**Total imports**: 2

| Layer | Line | Import Statement |
|-------|------|-----------------|
| 6 | 4 | `import value_fabric.layer6.api.main as main_module` |
| 6 | 5 | `from value_fabric.layer6.api.startup_logging import config_fingerprint, emit_...` |

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

- **Runtime/Service imports**: 282
- **Test imports**: 5
- **CI Script imports**: 8

## Migration Priority

Based on file type classification:

1. **HIGH PRIORITY - Runtime/Service code**
   - 282 files
   - Must migrate first to ensure services work without facades

2. **MEDIUM PRIORITY - CI Scripts**
   - 8 files
   - Migrate in batches by category

3. **LOWER PRIORITY - Test code**
   - 5 files
   - Migrate layer by layer after runtime is clean
