"""Teeth test for the infra secret-audit CI gate (PR4)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "audit_infra_secrets.py"


def _load_module():
    name = "_vf_infra_secret_gate"
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_gate_passes_on_clean_baseline() -> None:
    mod = _load_module()
    rc = mod.main(["--quiet"])
    assert rc == 0


def test_gate_enforce_flag_blocks_new_offender(tmp_path, monkeypatch) -> None:
    mod = _load_module()

    docker_compose = tmp_path / "docker-compose.test.yml"
    docker_compose.write_text(
        "services:\n"
        "  db:\n"
        "    environment:\n"
        "      POSTGRES_PASSWORD: hunter2hardcoded\n",
        encoding="utf-8",
    )

    baseline = tmp_path / "config" / "ci" / "infra_secret_baseline.txt"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text("# empty\n", encoding="utf-8")

    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mod, "BASELINE_FILE", baseline)

    rc = mod.main(["--enforce", "--quiet"])
    assert rc == 1


def test_gate_treats_env_reference_as_safe(tmp_path, monkeypatch) -> None:
    mod = _load_module()
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        "services:\n"
        "  db:\n"
        "    environment:\n"
        "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}\n"
        "      VAULT_TOKEN: ${VAULT_TOKEN}\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "config" / "ci" / "infra_secret_baseline.txt"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text("# empty\n", encoding="utf-8")

    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mod, "BASELINE_FILE", baseline)

    rc = mod.main(["--enforce", "--quiet"])
    assert rc == 0


def test_gate_treats_placeholder_as_safe(tmp_path, monkeypatch) -> None:
    mod = _load_module()
    f = tmp_path / "services" / "svc" / ".env.example"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(
        "DB_PASSWORD=<CHANGE_ME>\n" "API_KEY=changeme\n" "VAULT_TOKEN=\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "config" / "ci" / "infra_secret_baseline.txt"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text("# empty\n", encoding="utf-8")

    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mod, "BASELINE_FILE", baseline)

    rc = mod.main(["--enforce", "--quiet"])
    assert rc == 0


def test_gate_detects_k8s_env_array_literal(tmp_path, monkeypatch) -> None:
    mod = _load_module()
    f = tmp_path / "k8s" / "deployment.yml"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(
        "apiVersion: apps/v1\n"
        "spec:\n"
        "  template:\n"
        "    spec:\n"
        "      containers:\n"
        "        - name: api\n"
        "          env:\n"
        "            - name: POSTGRES_PASSWORD\n"
        "              value: hunter2hardcoded\n"
        "            - name: SAFE_VAR\n"
        "              value: ${SAFE_VAR}\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "config" / "ci" / "infra_secret_baseline.txt"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text("# empty\n", encoding="utf-8")

    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mod, "BASELINE_FILE", baseline)

    rc = mod.main(["--enforce", "--quiet"])
    assert rc == 1


def test_gate_accepts_explicit_baseline_path(tmp_path, monkeypatch) -> None:
    mod = _load_module()

    docker_compose = tmp_path / "docker-compose.yml"
    docker_compose.write_text(
        "services:\n"
        "  db:\n"
        "    environment:\n"
        "      POSTGRES_PASSWORD: hunter2hardcoded\n",
        encoding="utf-8",
    )

    baseline = tmp_path / "custom" / "infra_secret_baseline.txt"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text("docker-compose.yml:4:POSTGRES_PASSWORD\n", encoding="utf-8")

    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    rc = mod.main(["--baseline", str(baseline), "--enforce", "--quiet"])
    assert rc == 0
