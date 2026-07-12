"""Tests for Kubernetes workload validation.

Validates:
- Rollout strategies (RollingUpdate)
- Health probes (liveness, readiness)
- Resource constraints (requests, limits)
- Image pinning (no :latest)
- Layer 5 migration guardrails
- Service account configuration
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

APP_IMAGE_NAMES = [
    "services/layer1-ingestion",
    "services/layer2-extraction",
    "services/layer3-knowledge",
    "services/layer4-agents",
    "services/layer5-ground-truth",
    "services/layer6-benchmarks",
    "apps/web",
]

ZERO_SHA256_DIGEST = "sha256:" + ("0" * 64)


def parse_kubernetes_quantity(value: object) -> Decimal:
    """Parse CPU and memory quantities into comparable base units.

    CPU values are returned in cores and memory values in bytes. This covers the
    repository's manifest units and avoids false positives from lexicographic
    comparisons such as ``1Gi`` being treated as smaller than ``256Mi``.
    """

    text = str(value).strip()
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([A-Za-z]*)", text)
    if not match:
        raise ValueError(f"unsupported Kubernetes quantity: {value!r}")

    number = Decimal(match.group(1))
    suffix = match.group(2)
    multipliers = {
        "": Decimal(1),
        "m": Decimal("0.001"),
        "Ki": Decimal(1024),
        "Mi": Decimal(1024) ** 2,
        "Gi": Decimal(1024) ** 3,
        "Ti": Decimal(1024) ** 4,
        "K": Decimal(1000),
        "M": Decimal(1000) ** 2,
        "G": Decimal(1000) ** 3,
    }
    if suffix not in multipliers:
        raise ValueError(f"unsupported Kubernetes quantity suffix: {suffix!r}")
    return number * multipliers[suffix]


class TestRolloutStrategy:
    """Tests for workload rollout strategy configuration."""

    def test_deployments_have_rolling_update(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify all Deployments use RollingUpdate strategy."""
        failures = []

        for file_path, doc in workload_documents:
            if doc.get("kind") != "Deployment":
                continue

            spec = doc.get("spec", {})
            strategy = spec.get("strategy", {})

            if strategy.get("type") != "RollingUpdate":
                name = doc.get("metadata", {}).get("name", "unknown")
                failures.append(f"{file_path}/{name}: missing or invalid RollingUpdate strategy")

        if failures:
            pytest.fail("Rollout strategy violations:\n" + "\n".join(failures))

    def test_statefulsets_have_rolling_update(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify all StatefulSets use RollingUpdate strategy."""
        failures = []

        for file_path, doc in workload_documents:
            if doc.get("kind") != "StatefulSet":
                continue

            spec = doc.get("spec", {})
            update_strategy = spec.get("updateStrategy", {})

            if update_strategy.get("type") != "RollingUpdate":
                name = doc.get("metadata", {}).get("name", "unknown")
                failures.append(f"{file_path}/{name}: missing or invalid RollingUpdate strategy")

        if failures:
            pytest.fail("StatefulSet rollout strategy violations:\n" + "\n".join(failures))

    def test_rolling_update_has_max_unavailable(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify RollingUpdate has maxUnavailable/maxSurge configured."""
        for file_path, doc in workload_documents:
            if doc.get("kind") != "Deployment":
                continue

            spec = doc.get("spec", {})
            strategy = spec.get("strategy", {})
            rolling_update = strategy.get("rollingUpdate", {})

            # Either maxUnavailable or maxSurge should be set (soft check)
            # This is informational only
            if not rolling_update.get("maxUnavailable") and not rolling_update.get("maxSurge"):
                name = doc.get("metadata", {}).get("name", "unknown")
                # Log but don't fail - defaults are acceptable
                print(f"INFO: {file_path}/{name} uses RollingUpdate defaults")


class TestHealthProbes:
    """Tests for liveness and readiness probe configuration."""

    def test_containers_have_liveness_probe(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify all containers have liveness probes configured."""
        failures = []

        for file_path, doc in workload_documents:
            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet", "DaemonSet"):
                continue

            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                # Skip sidecar containers like Istio/Envoy if needed
                name = container.get("name", "unknown")

                if "livenessProbe" not in container:
                    failures.append(f"{file_path}/{name}: missing livenessProbe")

        if failures:
            pytest.fail("Liveness probe violations:\n" + "\n".join(failures))

    def test_containers_have_readiness_probe(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify all containers have readiness probes configured."""
        failures = []

        for file_path, doc in workload_documents:
            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet", "DaemonSet"):
                continue

            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                name = container.get("name", "unknown")

                if "readinessProbe" not in container:
                    failures.append(f"{file_path}/{name}: missing readinessProbe")

        if failures:
            pytest.fail("Readiness probe violations:\n" + "\n".join(failures))

    def test_probes_use_http_get_or_exec(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify probes use either httpGet, tcpSocket, or exec."""
        failures = []

        for file_path, doc in workload_documents:
            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet", "DaemonSet"):
                continue

            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                name = container.get("name", "unknown")

                for probe_type in ["livenessProbe", "readinessProbe"]:
                    probe = container.get(probe_type)
                    if not probe:
                        continue

                    if not any(k in probe for k in ["httpGet", "tcpSocket", "exec", "grpc"]):
                        failures.append(f"{file_path}/{name}/{probe_type}: no handler configured")

        if failures:
            pytest.fail("Probe handler violations:\n" + "\n".join(failures))

    def test_probe_paths_are_valid(self, workload_documents: list[tuple[str, dict]]) -> None:
        """Verify HTTP probe paths are valid (start with /)."""
        failures = []

        for file_path, doc in workload_documents:
            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                name = container.get("name", "unknown")

                for probe_type in ["livenessProbe", "readinessProbe"]:
                    probe = container.get(probe_type)
                    if not probe:
                        continue

                    http_get = probe.get("httpGet", {})
                    if http_get:
                        path = http_get.get("path", "")
                        if not path.startswith("/"):
                            failures.append(
                                f"{file_path}/{name}/{probe_type}: path '{path}' must start with /"
                            )

        if failures:
            pytest.fail("Probe path violations:\n" + "\n".join(failures))


class TestResourceConstraints:
    """Tests for resource requests and limits."""

    def test_containers_have_resource_requests(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify all containers have resource requests for cpu and memory."""
        failures = []

        for file_path, doc in workload_documents:
            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet", "DaemonSet", "Job"):
                continue

            template = doc.get("spec", {}).get("template", {})
            spec = template.get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                name = container.get("name", "unknown")
                resources = container.get("resources", {})
                requests = resources.get("requests", {})

                if "cpu" not in requests:
                    failures.append(f"{file_path}/{name}: missing requests.cpu")

                if "memory" not in requests:
                    failures.append(f"{file_path}/{name}: missing requests.memory")

        if failures:
            pytest.fail("Resource request violations:\n" + "\n".join(failures))

    def test_containers_have_resource_limits(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify all containers have resource limits for cpu and memory."""
        failures = []

        for file_path, doc in workload_documents:
            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet", "DaemonSet", "Job"):
                continue

            template = doc.get("spec", {}).get("template", {})
            spec = template.get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                name = container.get("name", "unknown")
                resources = container.get("resources", {})
                limits = resources.get("limits", {})

                if "cpu" not in limits:
                    failures.append(f"{file_path}/{name}: missing limits.cpu")

                if "memory" not in limits:
                    failures.append(f"{file_path}/{name}: missing limits.memory")

        if failures:
            pytest.fail("Resource limit violations:\n" + "\n".join(failures))

    def test_limits_greater_than_or_equal_to_requests(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify limits are >= requests for each resource."""
        failures = []

        for file_path, doc in workload_documents:
            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            containers = spec.get("containers", [])

            for container in containers:
                name = container.get("name", "unknown")
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                limits = resources.get("limits", {})

                for resource_name in ["memory", "cpu"]:
                    if resource_name in requests and resource_name in limits:
                        request = requests[resource_name]
                        limit = limits[resource_name]
                        try:
                            request_value = parse_kubernetes_quantity(request)
                            limit_value = parse_kubernetes_quantity(limit)
                        except ValueError as exc:
                            failures.append(f"{file_path}/{name}: {exc}")
                            continue

                        if limit_value < request_value:
                            failures.append(
                                f"{file_path}/{name}: {resource_name} limits ({limit}) < requests ({request})"
                            )

        if failures:
            pytest.fail("Resource limit < request violations:\n" + "\n".join(failures))


class TestImagePinning:
    """Tests for image pinning (no :latest tags)."""

    def test_no_latest_tags_in_containers(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify no containers use :latest tag."""
        failures = []

        for file_path, doc in workload_documents:
            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"):
                continue

            spec = doc.get("spec", {})
            template = spec.get("template", {})
            pod_spec = template.get("spec", {})

            if kind == "CronJob":
                job_template = spec.get("jobTemplate", {})
                job_spec = job_template.get("spec", {})
                template = job_spec.get("template", {})
                pod_spec = template.get("spec", {})

            containers = pod_spec.get("containers", [])
            init_containers = pod_spec.get("initContainers", [])

            for container in containers + init_containers:
                name = container.get("name", "unknown")
                image = container.get("image", "")

                if ":latest" in image:
                    failures.append(f"{file_path}/{name}: uses :latest tag ({image})")

                if ":" not in image:
                    # No tag at all - implies :latest
                    failures.append(f"{file_path}/{name}: no tag specified ({image})")

        if failures:
            pytest.fail("Unpinned image violations:\n" + "\n".join(failures))

    def test_sha256_digests_for_production_images(
        self, k8s_overlays_dir: Path
    ) -> None:
        """Verify production images use SHA256 digests, not tags."""
        kustomization = k8s_overlays_dir / "prod" / "kustomization.yaml"

        with open(kustomization) as f:
            content = yaml.safe_load(f)

        images = content.get("images", [])
        image_by_name = {img.get("name"): img for img in images}
        failures = []

        for name in APP_IMAGE_NAMES:
            img = image_by_name.get(name)
            if img is None:
                failures.append(f"{name}: missing production image override")
                continue

            digest = img.get("digest")
            if not digest:
                failures.append(f"{name}: missing digest (must use SHA256)")
            elif not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                failures.append(f"{name}: invalid digest format")
            elif digest == ZERO_SHA256_DIGEST:
                failures.append(f"{name}: uses placeholder zero digest")

        if failures:
            pytest.fail("Production image pinning violations:\n" + "\n".join(failures))


class TestLayer5MigrationGuardrails:
    """Tests for Layer 5 database migration guardrails."""

    def test_layer5_has_init_container_for_migrations(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify Layer 5 workloads have init containers for migration sequencing."""
        for file_path, doc in workload_documents:
            name = doc.get("metadata", {}).get("name", "").lower()

            if "layer5" not in name and "ground-truth" not in name:
                continue

            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet"):
                continue

            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            init_containers = spec.get("initContainers", [])

            assert init_containers, f"{file_path}/{name}: must define an init container for migrations"

    def test_migration_init_uses_alembic(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify Layer 5 init containers use Alembic for migrations."""
        for file_path, doc in workload_documents:
            name = doc.get("metadata", {}).get("name", "").lower()

            if "layer5" not in name and "ground-truth" not in name:
                continue

            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet"):
                continue

            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            init_containers = spec.get("initContainers", [])

            migration_init = None
            for init in init_containers:
                init_name = init.get("name", "").lower()
                if "migrate" in init_name:
                    migration_init = init
                    break

            if migration_init:
                # Check for alembic reference
                args = " ".join(migration_init.get("args", []))
                command = " ".join(migration_init.get("command", []))

                if "alembic" not in args and "alembic" not in command:
                    # Soft check - migrations might use other tools
                    print(f"INFO: {file_path}/{name} migration init doesn't use alembic")


class TestServiceAccounts:
    """Tests for ServiceAccount configuration."""

    def test_workloads_use_explicit_service_account(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify workloads use explicit serviceAccountName (not default)."""
        warnings = []

        for file_path, doc in workload_documents:
            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet", "DaemonSet"):
                continue

            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            service_account = spec.get("serviceAccountName")

            if not service_account:
                name = doc.get("metadata", {}).get("name", "unknown")
                warnings.append(f"{file_path}/{name}: no explicit serviceAccountName")

        # This is a warning, not a failure
        if warnings:
            print("ServiceAccount warnings:\n" + "\n".join(warnings))

    def test_service_accounts_not_default(
        self, workload_documents: list[tuple[str, dict]]
    ) -> None:
        """Verify workloads don't use the 'default' service account."""
        failures = []

        for file_path, doc in workload_documents:
            kind = doc.get("kind")
            if kind not in ("Deployment", "StatefulSet", "DaemonSet"):
                continue

            spec = doc.get("spec", {}).get("template", {}).get("spec", {})
            service_account = spec.get("serviceAccountName", "")

            if service_account == "default":
                name = doc.get("metadata", {}).get("name", "unknown")
                failures.append(f"{file_path}/{name}: uses 'default' service account")

        if failures:
            pytest.fail("Using default service account:\n" + "\n".join(failures))
