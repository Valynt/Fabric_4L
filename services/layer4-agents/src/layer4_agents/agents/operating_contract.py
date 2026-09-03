"""Agent operating-contract loader.

Loads declarative per-agent operating contracts from the canonical agent
registry.  The loader is used by ``BaseAgent`` at initialization and can be
imported directly by agents (such as ``AuditOrchestrator``) that do not inherit
from ``BaseAgent``.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, cast

_PLATFORM_CONTRACT_PYTHON = next(
    (
        parent / "packages" / "platform-contract" / "src" / "python"
        for parent in Path(__file__).resolve().parents
        if (parent / "packages" / "platform-contract" / "src" / "python").exists()
    ),
    None,
)
if _PLATFORM_CONTRACT_PYTHON and str(_PLATFORM_CONTRACT_PYTHON) not in sys.path:
    sys.path.append(str(_PLATFORM_CONTRACT_PYTHON))

try:  # pragma: no cover - contract package may be unavailable in some runtimes
    from agent_contracts import AgentOperatingContract
    from pydantic import ValidationError
except Exception:  # pragma: no cover
    AgentOperatingContract = None  # type: ignore[assignment, misc]
    ValidationError = Exception  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def _default_registry_root() -> Path:
    """Return the repo root from this file's location."""
    # operating_contract.py is at services/layer4-agents/src/layer4_agents/agents/
    # repo root is five parents above.
    return Path(__file__).resolve().parents[5]


def _default_manifest_path() -> Path:
    """Return the canonical agent-registry manifest path."""
    return _default_registry_root() / "contracts" / "agent-registry" / "agents" / "manifest.json"


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _env_override_path(agent_type: str) -> Path | None:
    """Resolve an environment-variable override for a specific agent type."""
    env_name = f"AGENT_OPERATING_CONTRACT_PATH__{agent_type}"
    value = os.getenv(env_name)
    if value:
        return Path(value)
    generic = os.getenv("AGENT_OPERATING_CONTRACT_PATH")
    if generic:
        return Path(generic)
    return None


def _load_manifest(manifest_path: Path | None) -> dict[str, Any]:
    """Load and return the agent-registry manifest JSON."""
    path = manifest_path or _default_manifest_path()
    if not path.exists():
        raise FileNotFoundError(f"Agent registry manifest not found: {path}")
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _contract_path_for_agent(
    agent_type: str,
    manifest: dict[str, Any],
    manifest_path: Path,
    override: Path | None = None,
) -> Path:
    """Resolve the operating-contract file path for an agent type."""
    if override:
        return override

    agents = manifest.get("agents", [])
    for entry in agents:
        if entry.get("agent_type") == agent_type:
            relative = entry.get("operating_contract_path")
            if not relative:
                raise FileNotFoundError(
                    f"Agent {agent_type} has no operating_contract_path in the manifest"
                )
            return manifest_path.parent / str(relative)

    raise FileNotFoundError(
        f"Agent {agent_type} not found in manifest: {manifest_path}"
    )


def load_operating_contract(
    agent_type: str,
    *,
    manifest_path: Path | None = None,
    contract_path: Path | None = None,
) -> AgentOperatingContract | None:
    """Load and validate the operating contract for ``agent_type``.

    Resolution order:
    1. ``contract_path`` argument.
    2. Environment variable ``AGENT_OPERATING_CONTRACT_PATH__<agent_type>``
       (or the generic ``AGENT_OPERATING_CONTRACT_PATH``).
    3. ``operating_contract_path`` declared in ``contracts/agent-registry/agents/manifest.json``.

    Returns ``None`` only when the contract package is unavailable or the
    manifest/agent is missing and the runtime is in warning mode.  In strict
    mode, missing contracts raise ``FileNotFoundError`` or validation errors.
    """
    if AgentOperatingContract is None:
        logger.warning(
            "Agent operating-contract package unavailable; skipping contract load for %s",
            agent_type,
        )
        return None

    strict = os.getenv("AGENT_OPERATING_CONTRACT_MODE", "warn").strip().lower() == "strict"

    try:
        resolved_contract_path = contract_path or _env_override_path(agent_type)
        if not resolved_contract_path:
            manifest = _load_manifest(manifest_path)
            resolved_contract_path = _contract_path_for_agent(
                agent_type, manifest, manifest_path or _default_manifest_path()
            )

        if not resolved_contract_path.exists():
            raise FileNotFoundError(
                f"Operating contract file not found for {agent_type}: {resolved_contract_path}"
            )

        payload = json.loads(resolved_contract_path.read_text(encoding="utf-8"))
        model = AgentOperatingContract.model_validate(payload)
        if model.agent_type != agent_type:
            raise ValueError(
                f"Contract agent_type mismatch: expected {agent_type}, got {model.agent_type}"
            )
        return model
    except (FileNotFoundError, ValueError, ValidationError) as exc:
        if strict:
            raise
        logger.warning(
            "Could not load operating contract for %s (warning mode): %s",
            agent_type,
            exc,
        )
        return None
