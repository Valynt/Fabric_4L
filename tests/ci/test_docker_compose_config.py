from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "check_docker_compose_config.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_docker_compose_config", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def repo_tmp_path(name: str) -> Path:
    path = REPO_ROOT / ".tmp" / "docker-compose-config-tests" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_bind_mount_classification_ignores_named_and_anonymous_volumes():
    module = load_module()

    service = {
        "volumes": [
            "named-data:/var/lib/data",
            "/app/node_modules",
            "./scripts/init.sh:/docker-entrypoint-initdb.d/init.sh:ro",
            {"type": "volume", "source": "cache", "target": "/cache"},
            {"type": "bind", "source": "./config.yml", "target": "/etc/config.yml"},
        ]
    }

    assert module.iter_bind_sources(service, {"named-data", "cache"}) == [
        "./scripts/init.sh",
        "./config.yml",
    ]


def test_missing_bind_source_fails():
    module = load_module()
    tmp_path = repo_tmp_path("missing-bind")
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    image: alpine:3.20
    volumes:
      - ./missing.yml:/etc/missing.yml:ro
    healthcheck:
      test: ["CMD", "true"]
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert [failure.message for failure in failures] == [
        "bind-mount source does not exist: ./missing.yml"
    ]


def test_absolute_host_bind_is_not_checked_on_ci_runner(monkeypatch):
    module = load_module()
    tmp_path = repo_tmp_path("absolute-host-bind")
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    image: alpine:3.20
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    healthcheck:
      test: ["CMD", "true"]
""",
    )
    original_exists = Path.exists

    def guarded_exists(path: Path) -> bool:
        if path == Path("/var/lib/docker/containers"):
            raise PermissionError("deployment host path is not readable in CI")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", guarded_exists)

    assert module.validate_compose_contract(compose, tmp_path) == []


def test_target_compose_files_pass_static_contract():
    module = load_module()

    failures = []
    for compose_name in module.TARGET_COMPOSE_FILES:
        failures.extend(
            module.validate_compose_contract(REPO_ROOT / compose_name, REPO_ROOT)
        )

    assert failures == []


def test_missing_build_context_and_dockerfile_fail():
    module = load_module()
    tmp_path = repo_tmp_path("missing-build")
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    build:
      context: ./missing-context
      dockerfile: ./Dockerfile
    healthcheck:
      test: ["CMD", "true"]
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    messages = [failure.message for failure in failures]
    assert any(message.startswith("build context does not exist:") for message in messages)
    assert any(message.startswith("Dockerfile does not exist:") for message in messages)


def test_healthcheck_exemption_applies_only_to_one_shot_services():
    module = load_module()
    tmp_path = repo_tmp_path("health-exemption")
    write_file(
        tmp_path / "service" / "Dockerfile",
        "FROM alpine:3.20\nCMD [\"sh\"]\n",
    )
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    build:
      context: ./service
      dockerfile: ./Dockerfile
  layer5-migrate:
    build:
      context: ./service
      dockerfile: ./Dockerfile
    command: alembic upgrade head
    restart: "no"
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert len(failures) == 1
    assert failures[0].service == "api"
    assert "has no compose healthcheck" in failures[0].message


def test_long_running_service_with_backup_in_name_requires_healthcheck():
    module = load_module()
    tmp_path = repo_tmp_path("long-running-backup")
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  wal-g-backup:
    image: alpine:3.20
    restart: unless-stopped
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert len(failures) == 1
    assert failures[0].service == "wal-g-backup"
    assert "has no compose healthcheck" in failures[0].message


def test_backup_profile_with_disabled_restart_is_one_shot():
    module = load_module()
    tmp_path = repo_tmp_path("backup-profile-one-shot")
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  archive-wal:
    image: alpine:3.20
    profiles: [backup]
    restart: "no"
""",
    )

    assert module.validate_compose_contract(compose, tmp_path) == []
    for restart in ("no", "none", "false"):
        assert module.is_one_shot_service(
            "archive-wal",
            {"profiles": ["backup"], "restart": restart},
        )


def test_disabled_restart_without_backup_profile_is_not_one_shot():
    module = load_module()

    assert not module.is_one_shot_service("archive-wal", {"restart": "no"})


def test_extends_inherits_healthcheck_from_one_level_base():
    module = load_module()
    tmp_path = repo_tmp_path("extends-one-level")
    write_file(
        tmp_path / "base.yml",
        """
services:
  healthy-base:
    image: alpine:3.20
    healthcheck:
      test: ["CMD", "true"]
""",
    )
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    extends:
      file: ./base.yml
      service: healthy-base
""",
    )

    assert module.validate_compose_contract(compose, tmp_path) == []


def test_extends_inherits_healthcheck_through_chain():
    module = load_module()
    tmp_path = repo_tmp_path("extends-chain")
    write_file(
        tmp_path / "base.yml",
        """
services:
  healthy-base:
    image: alpine:3.20
    healthcheck:
      test: ["CMD", "true"]
""",
    )
    write_file(
        tmp_path / "middle.yml",
        """
services:
  middle:
    extends:
      file: ./base.yml
      service: healthy-base
""",
    )
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    extends:
      file: ./middle.yml
      service: middle
""",
    )

    assert module.validate_compose_contract(compose, tmp_path) == []


def test_extends_healthcheck_lookup_fails_closed_for_missing_file():
    module = load_module()
    tmp_path = repo_tmp_path("extends-missing-file")
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    extends:
      file: ./missing.yml
      service: healthy-base
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert any(
        failure.service == "api" and "has no compose healthcheck" in failure.message
        for failure in failures
    )


def test_extends_healthcheck_lookup_fails_closed_for_missing_service():
    module = load_module()
    tmp_path = repo_tmp_path("extends-missing-service")
    write_file(tmp_path / "base.yml", "services: {}\n")
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    extends:
      file: ./base.yml
      service: missing
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert any(
        failure.service == "api" and "has no compose healthcheck" in failure.message
        for failure in failures
    )


def test_extends_healthcheck_lookup_fails_closed_for_malformed_yaml():
    module = load_module()
    tmp_path = repo_tmp_path("extends-malformed-yaml")
    write_file(tmp_path / "base.yml", "services: [\n")
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    extends:
      file: ./base.yml
      service: healthy-base
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert any(
        failure.service == "api" and "has no compose healthcheck" in failure.message
        for failure in failures
    )


def test_extends_healthcheck_lookup_fails_closed_for_cycle():
    module = load_module()
    tmp_path = repo_tmp_path("extends-cycle")
    write_file(
        tmp_path / "first.yml",
        """
services:
  first:
    extends:
      file: ./second.yml
      service: second
""",
    )
    write_file(
        tmp_path / "second.yml",
        """
services:
  second:
    extends:
      file: ./first.yml
      service: first
""",
    )
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    extends:
      file: ./first.yml
      service: first
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert any(
        failure.service == "api" and "has no compose healthcheck" in failure.message
        for failure in failures
    )


def test_canonical_raw_content_bind_target_exists():
    assert (REPO_ROOT / "raw-content").is_dir()


def test_dockerfile_healthcheck_satisfies_long_running_service():
    module = load_module()
    tmp_path = repo_tmp_path("dockerfile-healthcheck")
    write_file(
        tmp_path / "service" / "Dockerfile",
        "FROM alpine:3.20\nHEALTHCHECK CMD true\nCMD [\"sh\"]\n",
    )
    compose = write_file(
        tmp_path / "docker-compose.test.yml",
        """
services:
  api:
    build:
      context: ./service
      dockerfile: ./Dockerfile
""",
    )

    assert module.validate_compose_contract(compose, tmp_path) == []


def test_devcontainer_compose_inherits_dockerfile_healthcheck():
    module = load_module()
    compose = REPO_ROOT / ".devcontainer" / "docker-compose.yml"

    failures = module.validate_compose_contract(compose, REPO_ROOT)

    assert not any(
        failure.service == "dev"
        and "has no compose healthcheck or Dockerfile HEALTHCHECK" in failure.message
        for failure in failures
    ), failures


def test_required_env_defaults_are_safe_and_do_not_use_real_env(monkeypatch):
    module = load_module()
    for key in module.SAFE_REQUIRED_ENV_DEFAULTS:
        monkeypatch.delenv(key, raising=False)

    env = module.docker_env()

    for key, expected in module.SAFE_REQUIRED_ENV_DEFAULTS.items():
        assert env[key] == expected
        assert expected.startswith(
            (
                "compose-contract",
                "compose_contract",
                "composecontract",
                "00000000-0000-4000-8000-000000000001",
                "http://localhost",
                "https://compose-contract.",
                "postgresql+asyncpg://compose_contract_",
            )
        )
        assert expected != os.environ.get(key)


def test_full_compose_rejects_unapproved_host_ports():
    module = load_module()
    tmp_path = repo_tmp_path("full-ports")
    compose = write_file(
        tmp_path / module.FULL_COMPOSE_FILE,
        """
services:
  layer4-agents:
    image: alpine:3.20
    ports:
      - "8004:8000"
    healthcheck:
      test: ["CMD", "true"]
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "true"]
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert any(failure.service == "redis" and "host-published ports" in failure.message for failure in failures)
    assert not any(
        failure.service == "layer4-agents" and "host-published ports" in failure.message
        for failure in failures
    )


def test_full_compose_rejects_placeholder_secrets_and_optional_secret_defaults():
    module = load_module()
    tmp_path = repo_tmp_path("full-secret-placeholders")
    compose = write_file(
        tmp_path / module.FULL_COMPOSE_FILE,
        """
services:
  api:
    image: alpine:3.20
    environment:
      - JWT_SECRET=${JWT_SECRET:-changeme}
      - POSTGRES_PASSWORD=postgres
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/app
    healthcheck:
      test: ["CMD", "true"]
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)
    messages = [failure.message for failure in failures]

    assert "JWT_SECRET must use required env interpolation" in messages
    assert "JWT_SECRET must not use an optional default" in messages
    assert "JWT_SECRET contains a production-forbidden placeholder value" in messages
    assert "POSTGRES_PASSWORD must use required env interpolation" in messages
    assert "POSTGRES_PASSWORD contains a production-forbidden placeholder value" in messages
    assert "DATABASE_URL contains a production-forbidden placeholder value" in messages


def test_full_compose_accepts_required_secret_interpolation():
    module = load_module()
    tmp_path = repo_tmp_path("full-required-secrets")
    compose = write_file(
        tmp_path / module.FULL_COMPOSE_FILE,
        """
services:
  api:
    image: alpine:3.20
    environment:
      - JWT_SECRET=${JWT_SECRET:?JWT_SECRET is required}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      - DATABASE_URL=postgresql://${POSTGRES_USER:?POSTGRES_USER is required}:${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}@postgres:5432/app
    healthcheck:
      test: ["CMD", "true"]
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert failures == []


def test_live_compose_rejects_fail_open_runtime_secrets():
    module = load_module()
    tmp_path = repo_tmp_path("live-fail-open")
    compose = write_file(
        tmp_path / module.LIVE_COMPOSE_FILE,
        """
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_HOST_AUTH_METHOD: trust
    healthcheck:
      test: ["CMD", "true"]
  minio-init:
    image: minio/mc:latest
    entrypoint: mc config host add myminio http://minio:9000 minioadmin minioadmin
  api:
    image: alpine:3.20
    environment:
      JWT_SECRET: ${JWT_SECRET:-live-local-secret-do-not-use-in-production-minimum-32-chars}
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/app
      NEO4J_PASSWORD: devpassword
    healthcheck:
      test: ["CMD", "true"]
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)
    messages = [failure.message for failure in failures]

    assert "live compose must not use trust database authentication" in messages
    assert "live compose must not hardcode MinIO default credentials" in messages
    assert "live compose must not provide fallback JWT secrets" in messages
    assert "live compose database URLs must not hardcode postgres credentials" in messages
    assert "live compose must not hardcode Neo4j development credentials" in messages


def test_full_compose_rejects_unguarded_embedded_required_secret_reference():
    module = load_module()
    tmp_path = repo_tmp_path("full-unguarded-embedded-secret")
    compose = write_file(
        tmp_path / module.FULL_COMPOSE_FILE,
        """
services:
  api:
    image: alpine:3.20
    environment:
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "true"]
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "true"]
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert any(
        failure.service == "api"
        and failure.message == "REDIS_PASSWORD reference must use required env interpolation"
        for failure in failures
    )


def test_full_compose_requires_redis_dependency_for_redis_runtime_reference():
    module = load_module()
    tmp_path = repo_tmp_path("full-redis-dependency")
    compose = write_file(
        tmp_path / module.FULL_COMPOSE_FILE,
        """
services:
  layer6-benchmarks:
    image: alpine:3.20
    environment:
      - REDIS_URL=redis://:secret@redis:6379/0
    healthcheck:
      test: ["CMD", "true"]
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "true"]
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert any(
        failure.service == "layer6-benchmarks" and "depends_on.redis" in failure.message
        for failure in failures
    )


def test_full_compose_requires_custom_service_runtime_hardening():
    module = load_module()
    tmp_path = repo_tmp_path("full-runtime-hardening")
    write_file(
        tmp_path / "service" / "Dockerfile",
        "FROM alpine:3.20\nHEALTHCHECK CMD true\nCMD [\"sh\"]\n",
    )
    compose = write_file(
        tmp_path / module.FULL_COMPOSE_FILE,
        """
services:
  api:
    build:
      context: ./service
      dockerfile: ./Dockerfile
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)
    messages = [failure.message for failure in failures]

    assert "custom long-running service must drop all Linux capabilities" in messages
    assert "custom long-running service must set no-new-privileges" in messages
    assert "custom long-running service must use read_only: true" in messages


def test_full_compose_hardening_exemption_allows_migration_runner():
    module = load_module()
    tmp_path = repo_tmp_path("full-runtime-hardening-exemption")
    write_file(
        tmp_path / "service" / "Dockerfile",
        "FROM alpine:3.20\nCMD [\"sh\"]\n",
    )
    compose = write_file(
        tmp_path / module.FULL_COMPOSE_FILE,
        """
services:
  layer5-migrate:
    build:
      context: ./service
      dockerfile: ./Dockerfile
    command: alembic upgrade head
    restart: "no"
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)

    assert failures == []


def test_pythonpath_missing_volume_mount_fails():
    module = load_module()
    tmp_path = repo_tmp_path("pythonpath-missing-mount")
    compose = write_file(
        tmp_path / "docker-compose.dev.yml",
        """
services:
  api:
    image: alpine:3.20
    environment:
      - PYTHONPATH=/app:/app/src:/app/value_fabric
    volumes:
      - ./api/src:/app/src:ro
    healthcheck:
      test: ["CMD", "true"]
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)
    messages = [failure.message for failure in failures]

    assert any("PYTHONPATH entry '/app/value_fabric' is not backed by a volume mount" in m for m in messages)


def test_pythonpath_with_valid_mounts_passes():
    module = load_module()
    tmp_path = repo_tmp_path("pythonpath-valid-mounts")
    write_file(tmp_path / "packages" / "shared" / "src" / "value_fabric" / "__init__.py", "")
    compose = write_file(
        tmp_path / "docker-compose.dev.yml",
        """
services:
  api:
    image: alpine:3.20
    environment:
      - PYTHONPATH=/app:/app/src:/app/value_fabric
    volumes:
      - ./api/src:/app/src:ro
      - ./packages/shared/src/value_fabric:/app/value_fabric:ro
    healthcheck:
      test: ["CMD", "true"]
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)
    messages = [failure.message for failure in failures]

    assert not any("PYTHONPATH" in m for m in messages)


def test_frontend_env_completeness_missing_vars_fails():
    module = load_module()
    tmp_path = repo_tmp_path("frontend-env-incomplete")
    compose = write_file(
        tmp_path / "docker-compose.dev.yml",
        """
services:
  frontend:
    image: node:22-alpine
    environment:
      - VITE_API_BASE=/api/v1
      - VITE_USE_MOCKS=false
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)
    messages = [failure.message for failure in failures]

    assert any("required frontend env variable 'VITE_L1_PREFIX' is missing" in m for m in messages)
    assert any("required frontend env variable 'VITE_ENABLE_CRM_SYNC' is missing" in m for m in messages)


def test_frontend_env_completeness_all_vars_passes():
    module = load_module()
    tmp_path = repo_tmp_path("frontend-env-complete")
    compose = write_file(
        tmp_path / "docker-compose.dev.yml",
        """
services:
  frontend:
    image: node:22-alpine
    environment:
      - VITE_API_BASE=/api/v1
      - VITE_L1_PREFIX=/ingest
      - VITE_L2_PREFIX=/extract
      - VITE_L2_5_PREFIX=/signals
      - VITE_L3_PREFIX=/graph
      - VITE_L4_PREFIX=/agents
      - VITE_L5_PREFIX=/truths
      - VITE_L6_PREFIX=/benchmarks
      - VITE_L7_PREFIX=/billing
      - VITE_ENABLE_CRM_SYNC=false
      - VITE_CRM_PROVIDER=salesforce
      - VITE_CRM_API_PROXY=/api/crm
      - VITE_ENABLE_C1_REPORTS=false
      - VITE_USE_MOCKS=false
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)
    messages = [failure.message for failure in failures]

    assert not any("frontend env variable" in m for m in messages)


def test_malformed_env_interpolation_fails():
    module = load_module()
    tmp_path = repo_tmp_path("malformed-env-interpolation")
    compose = write_file(
        tmp_path / "docker-compose.dev.yml",
        """
services:
  frontend-list:
    image: node:22-alpine
    environment:
      - VITE_CLERK_PUBLISHABLE_KEY=${VITE_CLERK_PUBLISHABLE_KEY}}
  frontend-map:
    image: node:22-alpine
    environment:
      VITE_AUTH_PROVIDER: ${VITE_AUTH_PROVIDER}}
""",
    )

    failures = module.validate_compose_contract(compose, tmp_path)
    messages = [failure.message for failure in failures]

    assert "VITE_CLERK_PUBLISHABLE_KEY has malformed env interpolation syntax" in messages
    assert "VITE_AUTH_PROVIDER has malformed env interpolation syntax" in messages
