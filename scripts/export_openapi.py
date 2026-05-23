#!/usr/bin/env python3
"""Export OpenAPI specifications from Value Fabric service applications.

The frontend generated-client pipeline consumes committed JSON files in
``contracts/openapi``. This exporter is the repository-owned source-of-truth
refresh command for backend-owned FastAPI contracts that have a concrete service
application in ``services/``.

Each service is exported in an isolated Python subprocess. That isolation keeps
module-level metrics registries, OpenTelemetry state, and service settings from
leaking between layer imports during a full repository export. Signals currently
has a committed OpenAPI contract but no corresponding FastAPI application in the
repository, so it is retained and reported as a static contract.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICES_ROOT = REPO_ROOT / "services"
SHARED_SRC = REPO_ROOT / "packages" / "shared" / "src"
EXPORT_DIR = REPO_ROOT / "contracts" / "openapi"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class OpenApiExportSpec:
    """Configuration for one exportable FastAPI service contract."""

    label: str
    layer_dir: str
    module_key: str
    main_path: str
    output_filename: str
    canonical_module: str | None = None

    @property
    def src_path(self) -> Path:
        return SERVICES_ROOT / self.layer_dir / "src"

    @property
    def module_path(self) -> Path:
        return self.src_path / self.main_path


EXPORT_SPECS: tuple[OpenApiExportSpec, ...] = (
    OpenApiExportSpec("Layer 1", "layer1-ingestion", "layer1_ingestion", "api/app_monolith.py", "layer1-ingestion.json"),
    OpenApiExportSpec("Layer 2", "layer2-extraction", "layer2_extraction", "layer2_extraction/api/main.py", "layer2-extraction.json"),
    OpenApiExportSpec("Layer 3", "layer3-knowledge", "layer3_knowledge", "api/app_monolith.py", "layer3-knowledge.json"),
    OpenApiExportSpec("Layer 4", "layer4-agents", "layer4_agents", "api/main.py", "layer4-agents.json"),
    OpenApiExportSpec("Layer 5", "layer5-ground-truth", "layer5_ground_truth", "layer5_ground_truth/api/main.py", "layer5-ground-truth.json"),
    OpenApiExportSpec(
        "Layer 6",
        "layer6-benchmarks",
        "layer6_benchmarks",
        "api/main.py",
        "layer6-benchmarks.json",
        canonical_module="value_fabric.layer6.api.main",
    ),
)

STATIC_CONTRACTS: tuple[str, ...] = ("signals.json",)

# Safe local-only defaults for import-time settings validation. These values are
# intentionally non-production and are used only to materialize OpenAPI schemas.
EXPORT_ENV: dict[str, str] = {
    "ENVIRONMENT": "development",
    "ENV": "development",
    "APP_ENV": "development",
    "OPENAPI_EXPORT": "1",
    "ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT": "true",
    "LAYER1_ENVIRONMENT": "development",
    "LAYER1_JWT_SECRET": "openapi-export-local-secret-with-32-characters",
    "LAYER1_DATABASE_URL": "postgresql://fabric_export:fabric_export_secret@localhost:5432/layer1_ingestion",
    "LAYER1_S3_ACCESS_KEY": "fabric_export_access_key",
    "LAYER1_S3_SECRET_KEY": "fabric_export_secret_key",
    "LAYER1_CORS_ORIGINS": '["http://localhost:5173"]',
    "JWT_SECRET": "openapi-export-local-secret-with-32-characters",
    "JWT_SECRET_KEY": "openapi-export-local-secret-with-32-characters",
    "DATABASE_URL": "postgresql://fabric_export:fabric_export_secret@localhost:5432/value_fabric",
    "DATABASE_URL_SYNC": "postgresql://fabric_export:fabric_export_secret@localhost:5432/value_fabric",
    "CORS_ORIGINS": "http://localhost:5173",
    "S3_ACCESS_KEY": "fabric_export_access_key",
    "S3_SECRET_KEY": "fabric_export_secret_key",
    "MINIO_ACCESS_KEY": "fabric_export_access_key",
    "MINIO_SECRET_KEY": "fabric_export_secret_key",
    "API_KEY_HMAC_SECRET": "openapi-export-local-secret-with-32-characters",
    "SERVICE_AUTH_SECRET": "openapi-export-local-secret-with-32-characters",
    "LAYER3_API_KEY": "openapi-export-layer3-key",
    "LAYER5_API_KEY": "openapi-export-layer5-key",
    "NEO4J_URI": "neo4j+s://neo4j.example.com:7687",
    "NEO4J_PASSWORD": "openapi-export-neo4j-password",
    "LAYER1_API_URL": "http://localhost:8001",
    "LAYER2_API_URL": "http://localhost:8002",
    "LAYER3_API_URL": "http://localhost:8003",
    "LAYER4_API_URL": "http://localhost:8004",
    "LAYER5_GROUND_TRUTH_URL": "http://localhost:8005",
    "LAYER6_API_URL": "http://localhost:8006",
}

def _module_stub(name: str, **attrs: Any) -> ModuleType:
    """Create an importable module stub for OpenAPI export subprocesses."""

    module = ModuleType(name)
    module.__dict__.update(attrs)
    module.__spec__ = importlib.util.spec_from_loader(name, loader=None)
    sys.modules[name] = module
    return module


class _MockPsycopg2:
    paramstyle = "pyformat"
    extras = type("MockModule", (), {})()


class _MockLanggraphCheckpoint:
    class BaseCheckpointSaver:
        pass

    class AsyncPostgresSaver:
        pass


class _MockStateGraph:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def add_node(self, *args: Any, **kwargs: Any) -> None:
        pass

    def add_edge(self, *args: Any, **kwargs: Any) -> None:
        pass

    def add_conditional_edges(self, *args: Any, **kwargs: Any) -> None:
        pass

    def set_entry_point(self, *args: Any, **kwargs: Any) -> None:
        pass

    def compile(self, *args: Any, **kwargs: Any) -> Any:
        return self

    async def ainvoke(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        return value


class _MockAsyncGraphDatabase:
    @staticmethod
    def driver(*args: Any, **kwargs: Any) -> Any:
        return None


class _MockS3Client:
    def put_object(self, *args: Any, **kwargs: Any) -> dict[str, str]:
        return {"ETag": "mock"}

    def generate_presigned_url(self, *args: Any, **kwargs: Any) -> str:
        return "https://example.com/mock"


class _MockConfig:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass


def _mock_retry(*args: Any, **kwargs: Any) -> Any:
    def decorator(func: Any) -> Any:
        return func

    return decorator


def _mock_policy(*args: Any, **kwargs: Any) -> Any:
    return None


def _install_email_validator_shim() -> None:
    """Keep Pydantic EmailStr schema generation working in slim export envs."""

    if importlib.util.find_spec("email_validator") is not None:
        return

    from pydantic import networks as pydantic_networks

    class _MockEmailParts:
        def __init__(self, email: str) -> None:
            self.normalized = email
            self.local_part = email.split("@", 1)[0]

    class _MockEmailValidator:
        class EmailNotValidError(ValueError):
            pass

        @staticmethod
        def validate_email(email: str, check_deliverability: bool = False) -> _MockEmailParts:
            return _MockEmailParts(email)

    pydantic_networks.email_validator = _MockEmailValidator
    pydantic_networks.import_email_validator = lambda: None


def _install_common_openapi_dependency_shims() -> None:
    """Install only the dependency shims required inside export subprocesses."""

    if importlib.util.find_spec("psycopg2") is None:
        psycopg2 = _MockPsycopg2()
        psycopg2.__spec__ = importlib.util.spec_from_loader("psycopg2", loader=None)  # type: ignore[attr-defined]
        sys.modules["psycopg2"] = psycopg2
        sys.modules["psycopg2.extras"] = _MockPsycopg2.extras

    _install_email_validator_shim()


def _install_layer4_openapi_dependency_shims() -> None:
    """Shim optional Layer 4 runtime integrations for schema-only export."""

    if importlib.util.find_spec("langgraph") is None:
        _module_stub("langgraph")
        _module_stub("langgraph.checkpoint")
        _module_stub("langgraph.checkpoint.base", BaseCheckpointSaver=_MockLanggraphCheckpoint.BaseCheckpointSaver)
        _module_stub("langgraph.checkpoint.postgres")
        _module_stub("langgraph.checkpoint.postgres.aio", AsyncPostgresSaver=_MockLanggraphCheckpoint.AsyncPostgresSaver)
        _module_stub("langgraph.graph", StateGraph=_MockStateGraph)

    if importlib.util.find_spec("neo4j") is None:
        _module_stub("neo4j", AsyncGraphDatabase=_MockAsyncGraphDatabase)

    if importlib.util.find_spec("boto3") is None:
        class _MockBoto3(ModuleType):
            @staticmethod
            def client(*args: Any, **kwargs: Any) -> _MockS3Client:
                return _MockS3Client()

        boto3 = _MockBoto3("boto3")
        boto3.__spec__ = importlib.util.spec_from_loader("boto3", loader=None)
        sys.modules["boto3"] = boto3

    if importlib.util.find_spec("botocore") is None:
        _module_stub("botocore")
        _module_stub("botocore.client", BaseClient=_MockS3Client)
        _module_stub("botocore.config", Config=_MockConfig)

    if importlib.util.find_spec("tenacity") is None:
        _module_stub(
            "tenacity",
            retry=_mock_retry,
            retry_if_exception_type=_mock_policy,
            stop_after_attempt=_mock_policy,
            wait_exponential=_mock_policy,
        )


def _install_openapi_dependency_shims(spec: OpenApiExportSpec) -> None:
    _install_common_openapi_dependency_shims()
    if spec.output_filename == "layer4-agents.json":
        _install_layer4_openapi_dependency_shims()


def _spec_by_output(output_filename: str) -> OpenApiExportSpec:
    for spec in EXPORT_SPECS:
        if spec.output_filename == output_filename:
            return spec
    raise KeyError(f"unknown OpenAPI export target: {output_filename}")


def _package_root(spec: OpenApiExportSpec) -> Path:
    nested_root = spec.src_path / spec.module_key
    if nested_root.exists():
        return nested_root
    return spec.src_path


def _install_synthetic_package(name: str, package_path: Path) -> None:
    module = ModuleType(name)
    init_path = package_path / "__init__.py"
    module.__file__ = str(init_path)
    module.__package__ = name
    module.__path__ = [str(package_path)]  # type: ignore[attr-defined]
    if init_path.exists():
        init_text = init_path.read_text(encoding="utf-8")
        version_match = re.search(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", init_text, flags=re.MULTILINE)
        if version_match:
            module.__version__ = version_match.group(1)  # type: ignore[attr-defined]
    sys.modules[name] = module


def _setup_package_hierarchy(spec: OpenApiExportSpec) -> None:
    """Create import package scaffolding without executing package initializers."""

    root_path = _package_root(spec)
    root_init = root_path / "__init__.py"
    if not root_init.exists():
        raise RuntimeError(f"package __init__.py missing at {root_init}")

    _install_synthetic_package(spec.module_key, root_path)

    module_name = _module_name_for(spec)
    package_parts = module_name.split(".")[:-1]
    for index in range(2, len(package_parts) + 1):
        package_name = ".".join(package_parts[:index])
        rel_parts = package_parts[1:index]
        package_path = root_path.joinpath(*rel_parts)
        if (package_path / "__init__.py").exists():
            _install_synthetic_package(package_name, package_path)


def _module_name_for(spec: OpenApiExportSpec) -> str:
    parts = list(Path(spec.main_path).with_suffix("").parts)
    if parts and parts[0] == spec.module_key:
        parts = parts[1:]
    return ".".join([spec.module_key, *parts])


def _load_main_module(spec: OpenApiExportSpec) -> ModuleType:
    full_name = _module_name_for(spec)
    module_spec = importlib.util.spec_from_file_location(full_name, spec.module_path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"could not create import spec for {spec.module_path}")

    module = importlib.util.module_from_spec(module_spec)
    module.__package__ = full_name.rpartition(".")[0]  # type: ignore[attr-defined]

    if spec.output_filename == "layer3-knowledge.json":
        # ``api.routes.system`` imports these names while ``api.app_monolith`` is
        # still executing. Pre-seeding them keeps schema export deterministic
        # without changing application behavior; the monolith redefines the
        # helper later in the same module for normal runtime use.
        module._app_metrics = None  # type: ignore[attr-defined]

        def _set_app_metrics(metrics: Any | None) -> None:
            module._app_metrics = metrics  # type: ignore[attr-defined]

        module.set_app_metrics = _set_app_metrics  # type: ignore[attr-defined]

    sys.modules[full_name] = module
    module_spec.loader.exec_module(module)
    return module


def _atomic_write_json(data: dict[str, Any], output_path: Path) -> None:
    temp_fd, temp_path = tempfile.mkstemp(dir=output_path.parent, suffix=".tmp", prefix=f"{output_path.stem}-")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, output_path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def _export_service_in_process(spec: OpenApiExportSpec) -> bool:
    if spec.canonical_module is None and not spec.module_path.exists():
        logger.error("[%s] app module not found at %s", spec.label, spec.module_path)
        return False

    for key, value in EXPORT_ENV.items():
        os.environ.setdefault(key, value)

    for path in (spec.src_path, SHARED_SRC, REPO_ROOT):
        sys.path.insert(0, str(path))

    _install_openapi_dependency_shims(spec)

    try:
        if spec.canonical_module is not None:
            logger.info("[%s] Loading canonical module %s", spec.label, spec.canonical_module)
            main_module = importlib.import_module(spec.canonical_module)
        else:
            _setup_package_hierarchy(spec)
            logger.info("[%s] Loading module from %s", spec.label, spec.module_path)
            main_module = _load_main_module(spec)

        app = getattr(main_module, "app", None)
        if app is None:
            raise RuntimeError(f"{spec.module_path} does not define 'app'")
        if not hasattr(app, "openapi") or not callable(app.openapi):
            raise RuntimeError(f"{spec.module_path} app does not expose callable openapi()")

        output_path = EXPORT_DIR / spec.output_filename
        _atomic_write_json(app.openapi(), output_path)
        logger.info("[OK] %s exported: %s", spec.label, output_path)
        return True
    except Exception as exc:
        logger.error("[%s] Export failed: %s", spec.label, exc, exc_info=True)
        return False


def _export_service_subprocess(spec: OpenApiExportSpec) -> bool:
    env = os.environ.copy()
    env.update(EXPORT_ENV)
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--single", spec.output_filename],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode == 0


def _validate_static_contracts(selected_static: tuple[str, ...]) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for static_contract in selected_static:
        static_path = EXPORT_DIR / static_contract
        if static_path.exists():
            logger.info("[STATIC] %s retained: no repository FastAPI source configured", static_contract)
            results[static_contract] = True
        else:
            logger.error("[STATIC] %s missing from %s", static_contract, EXPORT_DIR)
            results[static_contract] = False
    return results


def _export_specs(specs: tuple[OpenApiExportSpec, ...], selected_static: tuple[str, ...]) -> int:
    print("Exporting Value Fabric OpenAPI specifications...")
    print(f"Export directory: {EXPORT_DIR}")
    print()

    results = {spec.output_filename: _export_service_subprocess(spec) for spec in specs}
    results.update(_validate_static_contracts(selected_static))

    print()
    success_count = sum(results.values())
    total_count = len(results)
    print(f"Exported {success_count}/{total_count} OpenAPI specifications")
    return 0 if success_count == total_count else 1


def _export_all() -> int:
    return _export_specs(EXPORT_SPECS, STATIC_CONTRACTS)


def _export_selected(output_filenames: tuple[str, ...]) -> int:
    selected_specs = tuple(
        spec for spec in EXPORT_SPECS if spec.output_filename in output_filenames
    )
    selected_static = tuple(
        output for output in output_filenames if output in STATIC_CONTRACTS
    )
    return _export_specs(selected_specs, selected_static)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Value Fabric OpenAPI specifications")
    parser.add_argument("--single", choices=[spec.output_filename for spec in EXPORT_SPECS])
    parser.add_argument(
        "--only",
        nargs="+",
        choices=[spec.output_filename for spec in EXPORT_SPECS] + list(STATIC_CONTRACTS),
        help="Export or validate only the selected OpenAPI artifacts.",
    )
    args = parser.parse_args()

    if args.single:
        spec = _spec_by_output(args.single)
        sys.exit(0 if _export_service_in_process(spec) else 1)

    if args.only:
        sys.exit(_export_selected(tuple(dict.fromkeys(args.only))))

    sys.exit(_export_all())


if __name__ == "__main__":
    main()
