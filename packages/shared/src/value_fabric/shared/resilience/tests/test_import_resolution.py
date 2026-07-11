"""Tests that the canonical resilience package is importable and the shadowed
standalone module is gone.

P1-014: Circuit breaker standardization. The ``value_fabric.shared.resilience``
package is the canonical implementation. A historical standalone
``resilience.py`` module was shadowed by the package and has been removed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CANONICAL_PACKAGE_ROOT = Path("packages/shared/src/value_fabric/shared/resilience")


def test_canonical_import_resolves_to_package():
    """``import value_fabric.shared.resilience`` must load the package."""
    import value_fabric.shared.resilience as resilience_module

    assert resilience_module.__file__ is not None
    assert resilience_module.__file__.endswith("resilience/__init__.py")


def test_required_public_symbols_exported():
    """The public API documented in ADR-028 remains importable."""
    from value_fabric.shared.resilience import (
        CircuitBreaker,
        CircuitBreakerOpen,
        CircuitBreakerRegistry,
        CircuitState,
    )

    assert CircuitState.CLOSED.value == "closed"
    assert CircuitState.OPEN.value == "open"
    assert CircuitState.HALF_OPEN.value == "half_open"
    assert isinstance(CircuitBreaker("x"), CircuitBreaker)
    assert issubclass(CircuitBreakerOpen, Exception)
    assert isinstance(CircuitBreakerRegistry(), CircuitBreakerRegistry)


def test_shadowed_standalone_module_is_removed():
    """The historical standalone module must no longer exist on disk."""
    standalone = Path("packages/shared/src/value_fabric/shared/resilience.py")
    assert not standalone.exists(), f"shadowed standalone module still exists: {standalone}"


def test_no_service_circuit_breaker_in_public_api():
    """The dead-code ``ServiceCircuitBreaker`` symbol is no longer reachable."""
    import value_fabric.shared.resilience as resilience_module

    assert not hasattr(resilience_module, "ServiceCircuitBreaker")


@pytest.mark.parametrize(
    "import_path",
    [
        "value_fabric.shared.resilience",
        "value_fabric.shared.resilience.circuit_breaker",
    ],
)
def test_package_modules_are_importable(import_path: str):
    """Both the package and its submodules must import without error."""
    # Remove any cached entry so we exercise a fresh import.
    parts = import_path.split(".")
    for i in range(len(parts)):
        submodule_name = ".".join(parts[: i + 1])
        sys.modules.pop(submodule_name, None)

    __import__(import_path)
