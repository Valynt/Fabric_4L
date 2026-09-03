from __future__ import annotations

"""Message router for intelligent message routing.

Provides routing logic for:
- Load balancing across agents
- Agent capability-based routing
- Workflow-aware message routing
"""


import logging
import random
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel

from .bus import MessageBus
from .types import MessageType


class MessageRouter_get_cluster_healthResult(TypedDictModel):
    avg_load: int
    capabilities: Any | None = None
    overloaded_agents: int
    status: str
    total_agents: int

logger = logging.getLogger(__name__)


class MessageRouter:
    """Routes messages to appropriate agents based on capabilities and load.

    The router maintains a registry of agents and their capabilities,
    enabling intelligent message routing for workflow execution.

    Example:
        router = MessageRouter(message_bus)

        # Register agents with capabilities
        router.register_agent("agent-1", ["document_parsing", "ocr"])
        router.register_agent("agent-2", ["formula_execution"])

        # Route task to appropriate agent
        target_agent = router.route_task("document_parsing")
    """

    def __init__(self, message_bus: MessageBus):
        """Initialize message router.

        Args:
            message_bus: Message bus for communication
        """
        self.message_bus = message_bus
        # agent_id -> List[capabilities]
        self._agent_capabilities: dict[str, list[str]] = {}
        # capability -> List[agent_ids]
        self._capability_agents: dict[str, list[str]] = {}
        # agent_id -> current load (0-100)
        self._agent_load: dict[str, int] = {}
        # agent_id -> metadata
        self._agent_metadata: dict[str, dict[str, Any]] = {}

    def register_agent(
        self,
        agent_id: str,
        capabilities: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register an agent with its capabilities.

        Args:
            agent_id: Unique agent identifier
            capabilities: List of capability names
            metadata: Optional agent metadata (e.g., priority, location)
        """
        self._agent_capabilities[agent_id] = capabilities
        self._agent_load[agent_id] = 0
        self._agent_metadata[agent_id] = metadata or {}

        # Update capability index
        for capability in capabilities:
            if capability not in self._capability_agents:
                self._capability_agents[capability] = []
            if agent_id not in self._capability_agents[capability]:
                self._capability_agents[capability].append(agent_id)

        logger.info(f"Registered agent {agent_id} with capabilities: {capabilities}")

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent.

        Args:
            agent_id: Agent to unregister
        """
        if agent_id not in self._agent_capabilities:
            return

        capabilities = self._agent_capabilities[agent_id]

        # Remove from capability index
        for capability in capabilities:
            if capability in self._capability_agents:
                if agent_id in self._capability_agents[capability]:
                    self._capability_agents[capability].remove(agent_id)

        # Remove from registries
        del self._agent_capabilities[agent_id]
        del self._agent_load[agent_id]
        del self._agent_metadata[agent_id]

        logger.info(f"Unregistered agent {agent_id}")

    def update_agent_load(self, agent_id: str, load: int) -> None:
        """Update agent's current load.

        Args:
            agent_id: Agent identifier
            load: Current load (0-100)
        """
        if agent_id in self._agent_load:
            self._agent_load[agent_id] = max(0, min(100, load))

    def get_agent_load(self, agent_id: str) -> int:
        """Get an agent's current load.

        Args:
            agent_id: Agent identifier

        Returns:
            Current load (0-100), or 0 for an unregistered agent.
        """
        return self._agent_load.get(agent_id, 0)

    def route_task(
        self,
        capability: str,
        strategy: str = "load_balanced",
    ) -> str | None:
        """Route a task to an agent with the required capability.

        Args:
            capability: Required capability
            strategy: Routing strategy ("load_balanced", "round_robin", "random")

        Returns:
            agent_id: Selected agent ID, or None if no agent available
        """
        candidates = self._capability_agents.get(capability, [])

        if not candidates:
            logger.warning(f"No agents available for capability: {capability}")
            return None

        # Filter out overloaded agents (>90% load)
        available = [agent_id for agent_id in candidates if self._agent_load.get(agent_id, 0) < 90]

        if not available:
            logger.warning(f"All agents for {capability} are overloaded")
            available = candidates  # Fall back to all candidates

        if strategy == "load_balanced":
            # Select agent with lowest load
            return min(available, key=lambda a: self._agent_load.get(a, 0))

        elif strategy == "round_robin":
            # Simple round-robin (would need persistent state for true RR)
            return available[0]

        elif strategy == "random":
            return random.choice(available)

        else:
            raise ValueError(f"Unknown routing strategy: {strategy}")

    def get_agents_for_capability(self, capability: str) -> list[str]:
        """Get all agents that support a capability.

        Args:
            capability: Capability to query

        Returns:
            List of agent IDs
        """
        return self._capability_agents.get(capability, [])

    def get_agent_capabilities(self, agent_id: str) -> list[str]:
        """Get capabilities for an agent.

        Args:
            agent_id: Agent to query

        Returns:
            List of capabilities
        """
        return self._agent_capabilities.get(agent_id, [])

    def get_all_capabilities(self) -> list[str]:
        """Get all registered capabilities.

        Returns:
            List of unique capability names
        """
        return list(self._capability_agents.keys())

    async def route_and_send(
        self,
        sender_id: str,
        capability: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> str | None:
        """Route task and send message to selected agent.

        Args:
            sender_id: ID of sending agent
            capability: Required capability
            payload: Message payload
            correlation_id: Optional correlation ID

        Returns:
            recipient_id: ID of selected agent, or None if no agent available
        """
        recipient_id = self.route_task(capability)

        if recipient_id is None:
            logger.error(f"Failed to route task for capability: {capability}")
            return None

        await self.message_bus.publish(
            agent_id=sender_id,
            event_type=MessageType.TASK_ASSIGNMENT,
            payload=payload,
            recipient_id=recipient_id,
            correlation_id=correlation_id,
        )

        return recipient_id

    def get_cluster_health(self) -> dict[str, Any]:
        """Get health status of the agent cluster.

        Returns:
            Health metrics including agent counts, load distribution
        """
        total_agents = len(self._agent_capabilities)

        if total_agents == 0:
            return MessageRouter_get_cluster_healthResult.model_validate({
                "status": "unhealthy",
                "total_agents": 0,
                "avg_load": 0,
                "overloaded_agents": 0,
            })


        loads = list(self._agent_load.values())
        avg_load = sum(loads) / len(loads)
        overloaded = sum(1 for load in loads if load > 80)

        status = "healthy"
        if overloaded > total_agents / 2:
            status = "degraded"
        if overloaded == total_agents:
            status = "critical"

        return MessageRouter_get_cluster_healthResult.model_validate({
            "status": status,
            "total_agents": total_agents,
            "avg_load": round(avg_load, 2),
            "overloaded_agents": overloaded,
            "capabilities": len(self._capability_agents),
        })


