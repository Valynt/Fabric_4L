from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
ALLOWLIST_FILE = REPO_ROOT / "config" / "ci" / "workflow-write-permissions.yaml"


def _load_allowlist() -> dict[str, dict[str, str]]:
    assert ALLOWLIST_FILE.exists(), f"Missing allowlist config file at {ALLOWLIST_FILE}"
    data = yaml.safe_load(ALLOWLIST_FILE.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{ALLOWLIST_FILE} did not parse as a YAML mapping"
    return data


ALLOWED_WRITE_PERMISSIONS: dict[str, dict[str, str]] = _load_allowlist()


def _workflow_files() -> list[Path]:
    return sorted(
        [
            *WORKFLOW_DIR.glob("*.yml"),
            *WORKFLOW_DIR.glob("*.yaml"),
        ]
    )


def _load_workflow(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} did not parse as a YAML mapping"
    return data


def _permission_scopes(
    workflow_name: str, permissions: object, location: str
) -> list[tuple[str, str]]:
    assert permissions != "write-all", f"{workflow_name} {location} uses write-all"
    if permissions in (None, "read-all"):
        return []
    assert isinstance(
        permissions, dict
    ), f"{workflow_name} {location} permissions must be a mapping or read-all"
    writes: list[tuple[str, str]] = []
    for scope, level in permissions.items():
        assert level != "write-all", f"{workflow_name} {location} uses write-all"
        if str(level).lower() == "write":
            writes.append((location, str(scope)))
    return writes


def test_every_workflow_has_explicit_top_level_permissions() -> None:
    missing: list[str] = []
    for path in _workflow_files():
        workflow = _load_workflow(path)
        if "permissions" not in workflow:
            missing.append(path.name)
    assert not missing, "workflows missing top-level permissions: " + ", ".join(missing)


def test_no_workflow_uses_write_all() -> None:
    for path in _workflow_files():
        workflow = _load_workflow(path)
        _permission_scopes(path.name, workflow.get("permissions"), "top-level")
        for job_name, job in (workflow.get("jobs") or {}).items():
            if isinstance(job, dict):
                _permission_scopes(path.name, job.get("permissions"), f"job:{job_name}")


def test_write_permissions_are_allowlisted_with_reasons() -> None:
    violations: list[str] = []
    allowlist = _load_allowlist()
    for path in _workflow_files():
        workflow = _load_workflow(path)
        writes = _permission_scopes(path.name, workflow.get("permissions"), "top-level")
        for job_name, job in (workflow.get("jobs") or {}).items():
            if isinstance(job, dict):
                writes.extend(
                    _permission_scopes(path.name, job.get("permissions"), f"job:{job_name}")
                )

        allowed = allowlist.get(path.name, {})
        for location, scope in writes:
            reason = allowed.get(scope)
            if not reason:
                violations.append(f"{path.name} {location} grants {scope}: write")

    assert not violations, "unallowlisted write permissions: " + "; ".join(violations)


def test_no_stale_allowlist_entries() -> None:
    """Every entry in config/ci/workflow-write-permissions.yaml must correspond to an actual write grant."""
    allowlist = _load_allowlist()
    actual_writes: dict[str, set[str]] = {}
    for path in _workflow_files():
        workflow = _load_workflow(path)
        writes = _permission_scopes(path.name, workflow.get("permissions"), "top-level")
        for job_name, job in (workflow.get("jobs") or {}).items():
            if isinstance(job, dict):
                writes.extend(
                    _permission_scopes(path.name, job.get("permissions"), f"job:{job_name}")
                )
        if writes:
            actual_writes[path.name] = {scope for _, scope in writes}

    stale: list[str] = []
    for wf_name, scopes in allowlist.items():
        if wf_name not in actual_writes:
            stale.append(f"{wf_name} has no write permissions in repository workflows")
            continue
        for scope in scopes:
            if scope not in actual_writes[wf_name]:
                stale.append(f"{wf_name} allowlists '{scope}' but does not grant it")

    assert not stale, "stale workflow-write-permissions.yaml entries: " + "; ".join(stale)



def _workflow_files() -> list[Path]:
    return sorted(
        [
            *WORKFLOW_DIR.glob("*.yml"),
            *WORKFLOW_DIR.glob("*.yaml"),
        ]
    )


def _load_workflow(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} did not parse as a YAML mapping"
    return data


def _permission_scopes(
    workflow_name: str, permissions: object, location: str
) -> list[tuple[str, str]]:
    assert permissions != "write-all", f"{workflow_name} {location} uses write-all"
    if permissions in (None, "read-all"):
        return []
    assert isinstance(
        permissions, dict
    ), f"{workflow_name} {location} permissions must be a mapping or read-all"
    writes: list[tuple[str, str]] = []
    for scope, level in permissions.items():
        assert level != "write-all", f"{workflow_name} {location} uses write-all"
        if str(level).lower() == "write":
            writes.append((location, str(scope)))
    return writes


def test_every_workflow_has_explicit_top_level_permissions() -> None:
    missing: list[str] = []
    for path in _workflow_files():
        workflow = _load_workflow(path)
        if "permissions" not in workflow:
            missing.append(path.name)
    assert not missing, "workflows missing top-level permissions: " + ", ".join(missing)


def test_no_workflow_uses_write_all() -> None:
    for path in _workflow_files():
        workflow = _load_workflow(path)
        _permission_scopes(path.name, workflow.get("permissions"), "top-level")
        for job_name, job in (workflow.get("jobs") or {}).items():
            if isinstance(job, dict):
                _permission_scopes(path.name, job.get("permissions"), f"job:{job_name}")


def test_write_permissions_are_allowlisted_with_reasons() -> None:
    violations: list[str] = []
    for path in _workflow_files():
        workflow = _load_workflow(path)
        writes = _permission_scopes(path.name, workflow.get("permissions"), "top-level")
        for job_name, job in (workflow.get("jobs") or {}).items():
            if isinstance(job, dict):
                writes.extend(
                    _permission_scopes(path.name, job.get("permissions"), f"job:{job_name}")
                )

        allowed = ALLOWED_WRITE_PERMISSIONS.get(path.name, {})
        for location, scope in writes:
            reason = allowed.get(scope)
            if not reason:
                violations.append(f"{path.name} {location} grants {scope}: write")

    assert not violations, "unallowlisted write permissions: " + "; ".join(violations)
