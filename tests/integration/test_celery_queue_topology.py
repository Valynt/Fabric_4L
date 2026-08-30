"""Static Celery queue topology checks for L1/L2 background jobs."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = [pytest.mark.integration, pytest.mark.celery]

ROOT = Path(__file__).resolve().parents[2]
L1_TASKS = "services/layer1-ingestion/src/layer1_ingestion/shared/tasks/__init__.py"
L1_CONFIG = "services/layer1-ingestion/src/layer1_ingestion/shared/config.py"
L2_TASKS = "services/layer2-extraction/src/layer2_extraction/shared/tasks.py"


def _read(relative_path: str) -> str:
    """Read a repository file as UTF-8 text."""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _l1_task_sources() -> str:
    """Aggregate the split tasks package sources for the original megafile guards."""
    return "\n".join(
        _read(f"services/layer1-ingestion/src/layer1_ingestion/shared/tasks/{name}")
        for name in ("__init__.py", "extraction.py")
    )


def _yaml_documents(relative_path: str) -> list[Any]:
    """Load every YAML document from a repository file."""
    return list(yaml.safe_load_all(_read(relative_path)))


def _compose_service(relative_path: str, service_name: str) -> dict[str, Any]:
    """Return one Docker Compose service definition."""
    document = _yaml_documents(relative_path)[0]
    return document["services"][service_name]


def _queue_list_from_command(command: str | list[str]) -> set[str]:
    """Extract Celery queue names from a worker startup command."""
    tokens = command if isinstance(command, list) else shlex.split(command)
    if "-Q" not in tokens:
        return set()
    queue_arg = tokens[tokens.index("-Q") + 1]
    return {queue.strip() for queue in queue_arg.split(",") if queue.strip()}


def test_celery_runtime_is_declared_in_source_and_dependencies() -> None:
    """Celery must be directly discoverable in source and service dependencies."""
    l1_tasks = _read(L1_TASKS)
    l2_tasks = _read(L2_TASKS)
    l1_pyproject = _read("services/layer1-ingestion/pyproject.toml")
    l2_pyproject = _read("services/layer2-extraction/pyproject.toml")

    assert "from celery import Celery" in l1_tasks
    assert "celery_app = Celery(" in l1_tasks
    assert "from celery import Celery" in l2_tasks
    assert "celery_app = Celery(" in l2_tasks
    assert '"celery>=5.3.0"' in l1_pyproject
    assert '"redis>=5.0.0"' in l1_pyproject
    assert '"celery>=5.4.0"' in l2_pyproject
    assert '"redis>=5.2.0"' in l2_pyproject


def test_broker_and_backend_use_redis_configuration() -> None:
    """L1 and L2 Celery apps must use Redis URLs as broker and backend."""
    l1_tasks = _read(L1_TASKS)
    l1_config = _read(L1_CONFIG)
    l2_tasks = _read(L2_TASKS)

    assert "get_celery_redis_broker_config(settings.redis_url)" in l1_tasks
    assert "broker=_celery_broker_url" in l1_tasks
    assert "backend=_celery_broker_url" in l1_tasks
    assert 'redis_url: str = Field(default="redis://localhost:6379/0"' in l1_config
    assert "REDIS_URL must be set in production-like environments" in l1_config

    assert 'redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")' in l2_tasks
    assert "get_celery_redis_broker_config(redis_url)" in l2_tasks
    assert "broker=celery_broker_url" in l2_tasks
    assert "backend=celery_broker_url" in l2_tasks


def test_l1_queue_names_are_declared_and_consumed_by_constrained_workers() -> None:
    """Workers using explicit queue lists must consume every L1 runtime queue."""
    l1_tasks = _read(L1_TASKS)
    expected_queues = {"default", "ingestion", "processing", "layer1_dlq"}

    for queue in expected_queues:
        assert f'"{queue}"' in l1_tasks
        assert f'"routing_key": "{queue}"' in l1_tasks

    compose_worker = _compose_service(
        "infra/compose/docker-compose.full.yml", "layer1-celery-worker"
    )
    compose_queues = _queue_list_from_command(compose_worker["command"])
    assert {"default", "ingestion", "processing"}.issubset(compose_queues)

    celery_manifest = _yaml_documents("k8s/base/layer1-celery.yaml")[0]
    worker_container = celery_manifest["spec"]["template"]["spec"]["containers"][0]
    k8s_queues = _queue_list_from_command(worker_container["args"])
    assert {"default", "ingestion", "processing"}.issubset(k8s_queues)


def test_l2_queue_names_and_dead_letter_queue_are_declared() -> None:
    """L2 Celery app must declare its default queue and DLQ."""
    l2_tasks = _read(L2_TASKS)

    assert '"default"' in l2_tasks
    assert '"routing_key": "default"' in l2_tasks
    assert '"layer2_dlq"' in l2_tasks
    assert '"routing_key": "layer2_dlq"' in l2_tasks


def test_retry_dead_letter_and_worker_loss_policies_are_configured() -> None:
    """Celery tasks must retain retry, late-ack, and worker-loss policies."""
    l1_tasks = _read(L1_TASKS)
    l2_tasks = _read(L2_TASKS)

    for source in (l1_tasks, l2_tasks):
        assert 'task_acks_late=True' in source
        assert 'task_reject_on_worker_lost=True' in source
        assert 'task_default_retry_delay=60' in source
        assert 'task_max_retries=3' in source
        assert '@celery_app.task(bind=True, max_retries=3)' in source

    assert "MAX_DISPATCH_ATTEMPTS = 5" in l1_tasks
    assert "OutboxStatus.DEAD_LETTER.value" in l1_tasks


def test_l1_worker_manifests_expose_unprefixed_redis_url() -> None:
    """L1 worker/API environments must expose REDIS_URL for Settings.redis_url."""
    compose_targets = [
        ("infra/compose/docker-compose.live.yml", "layer1"),
        ("infra/compose/docker-compose.live.yml", "layer1-worker"),
        ("infra/compose/docker-compose.backend-integrated.yml", "layer1"),
        ("infra/compose/docker-compose.backend-integrated.yml", "layer1-worker"),
        ("infra/compose/docker-compose.full.yml", "layer1-ingestion"),
        ("infra/compose/docker-compose.full.yml", "layer1-celery-worker"),
        ("services/layer1-ingestion/docker-compose.yml", "api"),
        ("services/layer1-ingestion/docker-compose.yml", "worker"),
        ("services/layer1-ingestion/docker-compose.yml", "beat"),
    ]

    for compose_file, service_name in compose_targets:
        environment = _compose_service(compose_file, service_name)["environment"]
        if isinstance(environment, list):
            env_names = {entry.split("=", 1)[0] for entry in environment}
        else:
            env_names = set(environment)
        assert "REDIS_URL" in env_names, f"{compose_file}:{service_name}"

    # The root compose file inherits REDIS_URL by extending the live compose services.
    for service_name in ("layer1", "layer1-worker"):
        root_service = _compose_service("docker-compose.yml", service_name)
        extends = root_service["extends"]
        assert extends["file"] == "./infra/compose/docker-compose.live.yml"
        assert extends["service"] == service_name

    for bunnyshell_file in (
        ".deployments/bunnyshell.yaml",
        ".deployments/bunnyshell-pr.yaml",
    ):
        components = _yaml_documents(bunnyshell_file)[0]["components"]
        by_name = {component["name"]: component for component in components}
        for component_name in ("layer1", "layer1-worker"):
            env = by_name[component_name]["dockerCompose"]["environment"]
            assert "REDIS_URL" in env, f"{bunnyshell_file}:{component_name}"


def test_worker_startup_and_broker_configuration_exist_in_kubernetes() -> None:
    """Kubernetes must define L1 worker startup and Redis broker env."""
    celery_worker = _yaml_documents("k8s/base/layer1-celery.yaml")[0]
    container = celery_worker["spec"]["template"]["spec"]["containers"][0]
    env_names = {entry["name"] for entry in container["env"]}

    assert container["command"] == ["celery"]
    assert "layer1_ingestion.shared.tasks" in container["args"]
    assert "worker" in container["args"]
    assert "REDIS_URL" in env_names


def test_tenant_context_and_idempotency_are_preserved() -> None:
    """Celery dispatch must propagate tenant context and keep idempotency guards."""
    l1_tasks = _l1_task_sources()
    l1_target_handlers = _read(
        "services/layer1-ingestion/src/layer1_ingestion/api/target_handlers.py"
    )
    l2_tasks = _read(L2_TASKS)

    assert 'def process_scraping_job(self, job_id: str, tenant_id: str)' in l1_tasks
    assert "get_db_session(tenant_id=tenant_uuid, require_tenant=True)" in l1_tasks
    assert '"tenant_id": str(job.tenant_id)' in l1_tasks
    assert "layer2_extraction.shared.tasks.run_extraction_task" in l1_tasks

    assert 'tenant_id = config.get("tenant_id")' in l2_tasks
    assert 'raise ValueError("tenant_id is required in config for extraction task")' in l2_tasks

    assert "request.idempotency_key" in l1_target_handlers
    assert "_check_idempotency_key(" in l1_target_handlers
    assert "_update_idempotency_key(" in l1_target_handlers
