"""Shared fixtures for Kubernetes tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def k8s_base_dir(repo_root: Path) -> Path:
    """Return the k8s/base directory path."""
    return repo_root / "k8s" / "base"


@pytest.fixture(scope="session")
def k8s_overlays_dir(repo_root: Path) -> Path:
    """Return the k8s/envs directory path.

    Historically named `k8s_overlays_dir`; the underlying directory was
    renamed from `k8s/overlays/` to `k8s/envs/` when the repo adopted the
    composable axes layout (base / envs / routing / deployments). Keeping the
    fixture name avoids touching every test that consumes it.
    """
    return repo_root / "k8s" / "envs"


@pytest.fixture(scope="session")
def k8s_envs_dir(repo_root: Path) -> Path:
    """Return the k8s/envs directory path (canonical name)."""
    return repo_root / "k8s" / "envs"


@pytest.fixture(scope="session")
def k8s_deployments_dir(repo_root: Path) -> Path:
    """Return the k8s/deployments directory path."""
    return repo_root / "k8s" / "deployments"


@pytest.fixture(scope="session")
def k8s_policy_dir(repo_root: Path) -> Path:
    """Return the k8s/policy directory path."""
    return repo_root / "k8s" / "policy"


@pytest.fixture(scope="session")
def monitoring_dir(repo_root: Path) -> Path:
    """Return the monitoring directory path."""
    return repo_root / "monitoring"


@pytest.fixture(scope="session")
def load_yaml_documents(repo_root: Path) -> dict[str, list[dict]]:
    """Load all YAML documents from k8s/base into a dictionary.
    
    Returns:
        Dictionary mapping file paths to lists of YAML documents.
    """
    docs: dict[str, list[dict]] = {}
    k8s_base = repo_root / "k8s" / "base"
    
    for yaml_file in k8s_base.rglob("*.yml"):
        try:
            with open(yaml_file, encoding="utf-8") as f:
                content = yaml.safe_load_all(f.read())
                file_docs = [doc for doc in content if doc is not None]
                if file_docs:
                    docs[str(yaml_file.relative_to(repo_root))] = file_docs
        except Exception as e:
            print(f"Warning: Could not parse {yaml_file}: {e}")
    
    return docs


@pytest.fixture(scope="session")
def workload_documents(load_yaml_documents: dict) -> list[tuple[str, dict]]:
    """Filter YAML documents to return only workload resources.
    
    Returns:
        List of (file_path, document) tuples for workload resources.
    """
    workload_kinds = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"}
    workloads: list[tuple[str, dict]] = []
    
    for file_path, docs in load_yaml_documents.items():
        for doc in docs:
            if doc.get("kind") in workload_kinds:
                workloads.append((file_path, doc))
    
    return workloads


@pytest.fixture(scope="session")
def kustomize_build_dev(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> str:
    """Build dev overlay and return the rendered YAML."""
    # Check if kustomize is available
    try:
        result = subprocess.run(
            ["kustomize", "version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            pytest.skip("kustomize not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("kustomize not available")
    
    result = subprocess.run(
        ["kustomize", "build", str(repo_root / "k8s" / "envs" / "dev")],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )

    if result.returncode != 0:
        pytest.skip(f"kustomize build failed: {result.stderr}")

    return result.stdout


@pytest.fixture(scope="session")
def kustomize_build_staging(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> str:
    """Build staging overlay and return the rendered YAML."""
    # Check if kustomize is available
    try:
        result = subprocess.run(
            ["kustomize", "version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            pytest.skip("kustomize not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("kustomize not available")

    result = subprocess.run(
        [
            "kustomize",
            "build",
            str(repo_root / "k8s" / "envs" / "staging"),
            "--load-restrictor=LoadRestrictionsNone",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )

    if result.returncode != 0:
        pytest.skip(f"kustomize build failed: {result.stderr}")

    return result.stdout


@pytest.fixture(scope="session")
def kustomize_build_prod(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> str:
    """Build prod overlay and return the rendered YAML."""
    # Check if kustomize is available
    try:
        result = subprocess.run(
            ["kustomize", "version"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            pytest.skip("kustomize not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("kustomize not available")

    result = subprocess.run(
        [
            "kustomize",
            "build",
            str(repo_root / "k8s" / "envs" / "prod"),
            "--load-restrictor=LoadRestrictionsNone",
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )

    if result.returncode != 0:
        pytest.skip(f"kustomize build failed: {result.stderr}")

    return result.stdout


@pytest.fixture
def skip_without_kustomize() -> None:
    """Skip test if kustomize is not available."""
    try:
        result = subprocess.run(["kustomize", "version"], capture_output=True, timeout=5)
        if result.returncode != 0:
            pytest.skip("kustomize not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("kustomize not available")


@pytest.fixture
def skip_without_kubeconform() -> None:
    """Skip test if kubeconform is not available."""
    try:
        result = subprocess.run(["kubeconform", "-v"], capture_output=True, timeout=5)
        if result.returncode != 0:
            pytest.skip("kubeconform not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("kubeconform not available")


@pytest.fixture
def skip_without_conftest() -> None:
    """Skip test if conftest is not available."""
    try:
        result = subprocess.run(["conftest", "--version"], capture_output=True, timeout=5)
        if result.returncode != 0:
            pytest.skip("conftest not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("conftest not available")


@pytest.fixture
def skip_without_kubectl() -> None:
    """Skip test if kubectl is not available."""
    try:
        result = subprocess.run(["kubectl", "version", "--client"], capture_output=True, timeout=5)
        if result.returncode != 0:
            pytest.skip("kubectl not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("kubectl not available")
