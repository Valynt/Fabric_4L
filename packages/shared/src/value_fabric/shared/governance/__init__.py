"""GATE governance components: ABOM, policy engine, invariants, gateways, replay.

Submodules are imported lazily so Layer 1 / DAST startup can load
``deprecation_register`` without pulling cryptography or pydantic.
"""

from __future__ import annotations

__all__ = [
    "AgentBillOfMaterials",
    "InvariantEvaluator",
    "InvariantResult",
    "InvariantViolation",
    "MemoryGateway",
    "PolicyDecision",
    "PolicyEngineClient",
    "ReplayRecorder",
    "ToolGateway",
    "ToolGatewayDenied",
    "load_abom",
]

_LAZY_EXPORTS = {
    "AgentBillOfMaterials": (".abom", "AgentBillOfMaterials"),
    "load_abom": (".abom", "load_abom"),
    "InvariantEvaluator": (".invariants", "InvariantEvaluator"),
    "InvariantResult": (".invariants", "InvariantResult"),
    "MemoryGateway": (".memory_gateway", "MemoryGateway"),
    "PolicyDecision": (".policy_engine", "PolicyDecision"),
    "PolicyEngineClient": (".policy_engine", "PolicyEngineClient"),
    "ReplayRecorder": (".replay", "ReplayRecorder"),
    "InvariantViolation": (".tool_gateway", "InvariantViolation"),
    "ToolGateway": (".tool_gateway", "ToolGateway"),
    "ToolGatewayDenied": (".tool_gateway", "ToolGatewayDenied"),
}


def __getattr__(name: str) -> object:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr = target
    from importlib import import_module

    value = getattr(import_module(module_name, __name__), attr)
    globals()[name] = value
    return value
