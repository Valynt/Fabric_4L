"""Guard: LAYER4_AUTO_APPROVE_IRREVERSIBLE_TOOLS must fail closed in
production-like environments (same doctrine as INV-SEC-001 dev auth bypass).

The tool-approval bypass empties the human-in-the-loop approval set for
irreversible CRM/INTEGRATION tools. Enabling it in production must raise at
registry construction time, not silently disable approvals.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.security, pytest.mark.p0, pytest.mark.unit]

import importlib.util

_SERVICE_DEPS_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None
requires_service_deps = pytest.mark.skipif(
    not _SERVICE_DEPS_AVAILABLE, reason="requires layer4 service dependencies (sqlalchemy et al.; runs in CI)"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "services" / "layer4-agents" / "src" / "layer4_agents" / "tools" / "registry.py"


def test_registry_source_enforces_production_guard() -> None:
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    assert "LAYER4_AUTO_APPROVE_IRREVERSIBLE_TOOLS" in text
    assert 'environment == "production"' in text, (
        "registry must raise when the auto-approve flag is set in a production environment"
    )
    assert "unsafe_production_configuration" in text
    # The guard must run BEFORE the approval set is emptied.
    flag_pos = text.index("auto_approve = os.getenv")
    guard_pos = text.index('environment == "production"')
    empty_pos = text.index("self._approval_required_categories: set[ToolCategory] = set()")
    assert flag_pos < guard_pos < empty_pos


@requires_service_deps
def test_registry_raises_in_production_when_flag_set() -> None:
    """Functional proof: constructing ToolRegistry with the flag in production raises."""
    code = (
        "import os, sys\n"
        "sys.path.insert(0, 'services/layer4-agents/src')\n"
        "sys.path.insert(0, 'packages/shared/src')\n"
        "os.environ['ENVIRONMENT'] = 'production'\n"
        "os.environ['LAYER4_AUTO_APPROVE_IRREVERSIBLE_TOOLS'] = 'true'\n"
        "from layer4_agents.tools.registry import ToolRegistry\n"
        "try:\n"
        "    ToolRegistry()\n"
        "except RuntimeError as exc:\n"
        "    print('GUARDED:', exc)\n"
        "    sys.exit(0)\n"
        "print('UNGUARDED')\n"
        "sys.exit(1)\n"
    )
    env = {**os.environ, "ENVIRONMENT": "production", "LAYER4_AUTO_APPROVE_IRREVERSIBLE_TOOLS": "true"}
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0 and "GUARDED" in proc.stdout, (
        f"ToolRegistry did not fail closed in production: stdout={proc.stdout[-300:]} stderr={proc.stderr[-300:]}"
    )


@requires_service_deps
def test_registry_permits_flag_in_development() -> None:
    """The flag remains available for local/dev/test use."""
    code = (
        "import os, sys\n"
        "sys.path.insert(0, 'services/layer4-agents/src')\n"
        "sys.path.insert(0, 'packages/shared/src')\n"
        "os.environ['ENVIRONMENT'] = 'development'\n"
        "os.environ['LAYER4_AUTO_APPROVE_IRREVERSIBLE_TOOLS'] = 'true'\n"
        "from layer4_agents.tools.registry import ToolRegistry\n"
        "registry = ToolRegistry()\n"
        "print('ALLOWED:', len(registry._approval_required_categories))\n"
    )
    env = {**os.environ, "ENVIRONMENT": "development", "LAYER4_AUTO_APPROVE_IRREVERSIBLE_TOOLS": "true"}
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0 and proc.stdout.startswith("ALLOWED: 0"), (
        f"dev-mode auto-approve unexpectedly blocked: stdout={proc.stdout[-300:]} stderr={proc.stderr[-300:]}"
    )
