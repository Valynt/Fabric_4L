"""Public orchestration exports.

``OrchestrationController`` alignment is intentionally deferred: the live
startup path still constructs the legacy ``StateManager`` and changing that
composition would alter persisted-state semantics.  The runtime's
``AgentRuntimeImpl`` is exposed through the runtime package and the migration
will happen once startup wiring can switch atomically with a compatibility
adapter.
"""

from ...engine.state_manager import StateManager

__all__ = ["StateManager"]
