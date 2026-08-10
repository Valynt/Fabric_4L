"""Comprehensive API load balancing and auto-scaling system for high availability."""

import asyncio
import logging
import random
import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.models.typed_dict import TypedDictModel


class LoadBalancingSystem_get_system_statsResult(TypedDictModel):
    auto_scaler: dict[str, Any]
    load_balancer: Any
    system: dict[str, Any]

logger = logging.getLogger(__name__)


class LoadBalanceStrategy(str, Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"


class ScalingPolicy(str, Enum):
    """Auto-scaling policies."""

    CPU_BASED = "cpu_based"
    MEMORY_BASED = "memory_based"
    REQUEST_RATE_BASED = "request_rate_based"
    RESPONSE_TIME_BASED = "response_time_based"
    QUEUE_LENGTH_BASED = "queue_length_based"
    CUSTOM = "custom"


class HealthStatus(str, Enum):
    """Health status of backend servers."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"


class ScaleDirection(str, Enum):
    """Scaling direction."""

    UP = "up"
    DOWN = "down"
    NONE = "none"


@dataclass
class BackendServer:
    """Backend server information."""

    id: str
    host: str
    port: int
    weight: int = 1
    max_connections: int = 1000
    current_connections: int = 0
    health_status: HealthStatus = HealthStatus.HEALTHY
    last_health_check: datetime | None = None
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    error_count: int = 0
    success_count: int = 0
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        """Check if server is healthy."""
        return self.health_status == HealthStatus.HEALTHY

    @property
    def is_available(self) -> bool:
        """Check if server can accept connections."""
        return (
            self.is_healthy
            and self.current_connections < self.max_connections
            and self.health_status != HealthStatus.DRAINING
        )

    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return statistics.mean(self.response_times)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total_requests = self.success_count + self.error_count
        if total_requests == 0:
            return 100.0
        return (self.success_count / total_requests) * 100

    def update_response_time(self, response_time: float):
        """Update response time statistics."""
        self.response_times.append(response_time)

    def record_success(self):
        """Record successful request."""
        self.success_count += 1

    def record_error(self, error: str | None = None):
        """Record failed request."""
        self.error_count += 1
        self.last_error = error


class LoadBalancerConfig(BaseModel):
    """Load balancer configuration."""

    strategy: LoadBalanceStrategy = Field(
        default=LoadBalanceStrategy.ROUND_ROBIN, description="Load balancing strategy"
    )
    health_check_interval: int = Field(
        default=30, description="Health check interval in seconds"
    )
    health_check_timeout: int = Field(
        default=5, description="Health check timeout in seconds"
    )
    health_check_path: str = Field(
        default="/health", description="Health check endpoint"
    )
    max_retries: int = Field(default=3, description="Maximum retries per request")
    retry_delay: float = Field(default=1.0, description="Retry delay in seconds")
    circuit_breaker_threshold: int = Field(
        default=5, description="Circuit breaker failure threshold"
    )
    circuit_breaker_timeout: int = Field(
        default=60, description="Circuit breaker timeout in seconds"
    )
    enable_sticky_sessions: bool = Field(
        default=False, description="Enable sticky sessions"
    )
    session_affinity_timeout: int = Field(
        default=3600, description="Session affinity timeout in seconds"
    )

    model_config = ConfigDict(use_enum_values=True)


class AutoScalingConfig(BaseModel):
    """Auto-scaling configuration."""

    enabled: bool = Field(default=True, description="Enable auto-scaling")
    policy: ScalingPolicy = Field(
        default=ScalingPolicy.CPU_BASED, description="Scaling policy"
    )
    min_instances: int = Field(default=1, description="Minimum number of instances")
    max_instances: int = Field(default=10, description="Maximum number of instances")
    scale_up_threshold: float = Field(
        default=80.0, description="Scale up threshold percentage"
    )
    scale_down_threshold: float = Field(
        default=20.0, description="Scale down threshold percentage"
    )
    scale_up_cooldown: int = Field(
        default=300, description="Scale up cooldown in seconds"
    )
    scale_down_cooldown: int = Field(
        default=600, description="Scale down cooldown in seconds"
    )
    evaluation_interval: int = Field(
        default=60, description="Evaluation interval in seconds"
    )
    target_cpu_utilization: float = Field(
        default=70.0, description="Target CPU utilization"
    )
    target_memory_utilization: float = Field(
        default=80.0, description="Target memory utilization"
    )
    target_response_time: float = Field(
        default=500.0, description="Target response time in ms"
    )
    target_request_rate: int = Field(
        default=1000, description="Target request rate per minute"
    )

    model_config = ConfigDict(use_enum_values=True)


class LoadBalancerStats(BaseModel):
    """Load balancer statistics."""

    total_requests: int = Field(default=0, description="Total requests handled")
    successful_requests: int = Field(default=0, description="Successful requests")
    failed_requests: int = Field(default=0, description="Failed requests")
    avg_response_time: float = Field(default=0.0, description="Average response time")
    requests_per_second: float = Field(default=0.0, description="Requests per second")
    active_connections: int = Field(default=0, description="Active connections")
    healthy_backends: int = Field(default=0, description="Number of healthy backends")
    total_backends: int = Field(default=0, description="Total number of backends")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class CircuitBreaker:
    """Circuit breaker for backend servers."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call_allowed(self) -> bool:
        """Check if call is allowed.

        Returns:
            True if call is allowed
        """
        if self.state == "closed":
            return True
        elif self.state == "open":
            if (
                datetime.utcnow() - self.last_failure_time
            ).total_seconds() > self.timeout:
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True

    def record_success(self):
        """Record successful call."""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0

    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class LoadBalancer:
    """Load balancer for distributing requests across backend servers."""

    def __init__(self, config: LoadBalancerConfig):
        """Initialize load balancer.

        Args:
            config: Load balancer configuration
        """
        self.config = config
        self.backends: dict[str, BackendServer] = {}
        self.round_robin_index = 0
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.session_affinity: dict[str, str] = {}
        self.stats = LoadBalancerStats()
        self.health_check_task: asyncio.Task | None = None

        # Start health check task
        self.health_check_task = asyncio.create_task(self._health_check_loop())

    def add_backend(self, server: BackendServer):
        """Add backend server.

        Args:
            server: Backend server to add
        """
        self.backends[server.id] = server
        self.circuit_breakers[server.id] = CircuitBreaker(
            self.config.circuit_breaker_threshold, self.config.circuit_breaker_timeout
        )
        logger.info(f"Added backend server: {server.host}:{server.port}")

    def remove_backend(self, server_id: str) -> bool:
        """Remove backend server.

        Args:
            server_id: Server ID to remove

        Returns:
            True if removed
        """
        if server_id in self.backends:
            del self.backends[server_id]
            if server_id in self.circuit_breakers:
                del self.circuit_breakers[server_id]
            logger.info(f"Removed backend server: {server_id}")
            return True
        return False

    async def select_backend(
        self, client_ip: str | None = None, session_id: str | None = None
    ) -> BackendServer | None:
        """Select backend server based on strategy.

        Args:
            client_ip: Client IP address
            session_id: Session ID for sticky sessions

        Returns:
            Selected backend server or None
        """
        available_backends = [
            backend
            for backend in self.backends.values()
            if backend.is_available and self.circuit_breakers[backend.id].call_allowed()
        ]

        if not available_backends:
            logger.warning("No available backends")
            return None

        # Sticky sessions
        if self.config.enable_sticky_sessions and session_id:
            if session_id in self.session_affinity:
                backend_id = self.session_affinity[session_id]
                if (
                    backend_id in self.backends
                    and self.backends[backend_id].is_available
                ):
                    return self.backends[backend_id]

        # Select based on strategy
        if self.config.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            backend = self._round_robin_select(available_backends)
        elif self.config.strategy == LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN:
            backend = self._weighted_round_robin_select(available_backends)
        elif self.config.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            backend = self._least_connections_select(available_backends)
        elif self.config.strategy == LoadBalanceStrategy.LEAST_RESPONSE_TIME:
            backend = self._least_response_time_select(available_backends)
        elif self.config.strategy == LoadBalanceStrategy.IP_HASH:
            backend = self._ip_hash_select(available_backends, client_ip)
        elif self.config.strategy == LoadBalanceStrategy.RANDOM:
            backend = self._random_select(available_backends)
        else:
            backend = available_backends[0]

        # Update session affinity
        if self.config.enable_sticky_sessions and session_id and backend:
            self.session_affinity[session_id] = backend.id

        return backend

    def _round_robin_select(self, backends: list[BackendServer]) -> BackendServer:
        """Round-robin selection."""
        backend = backends[self.round_robin_index % len(backends)]
        self.round_robin_index += 1
        return backend

    def _weighted_round_robin_select(
        self, backends: list[BackendServer]
    ) -> BackendServer:
        """Weighted round-robin selection."""
        total_weight = sum(backend.weight for backend in backends)
        if total_weight == 0:
            return backends[0]

        random_weight = random.randint(1, total_weight)
        current_weight = 0

        for backend in backends:
            current_weight += backend.weight
            if random_weight <= current_weight:
                return backend

        return backends[0]

    def _least_connections_select(self, backends: list[BackendServer]) -> BackendServer:
        """Least connections selection."""
        return min(backends, key=lambda b: b.current_connections)

    def _least_response_time_select(
        self, backends: list[BackendServer]
    ) -> BackendServer:
        """Least response time selection."""
        return min(backends, key=lambda b: b.avg_response_time)

    def _ip_hash_select(
        self, backends: list[BackendServer], client_ip: str | None
    ) -> BackendServer:
        """IP hash selection."""
        if not client_ip:
            return random.choice(backends)

        hash_value = hash(client_ip) % len(backends)
        return backends[hash_value]

    def _random_select(self, backends: list[BackendServer]) -> BackendServer:
        """Random selection."""
        return random.choice(backends)

    async def _health_check_loop(self):
        """Health check loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _perform_health_checks(self):
        """Perform health checks on all backends."""
        async with httpx.AsyncClient(
            timeout=self.config.health_check_timeout
        ) as client:
            tasks = []
            for backend in self.backends.values():
                tasks.append(self._check_backend_health(client, backend))

            await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_backend_health(
        self, client: httpx.AsyncClient, backend: BackendServer
    ):
        """Check health of a specific backend.

        Args:
            client: HTTP client
            backend: Backend server to check
        """
        try:
            url = f"http://{backend.host}:{backend.port}{self.config.health_check_path}"
            response = await client.get(url)

            if response.status_code == 200:
                backend.health_status = HealthStatus.HEALTHY
                backend.last_health_check = datetime.utcnow()
            else:
                backend.health_status = HealthStatus.UNHEALTHY
                backend.last_health_check = datetime.utcnow()
                logger.warning(
                    f"Backend {backend.id} health check failed: {response.status_code}"
                )

        except Exception as e:
            backend.health_status = HealthStatus.UNHEALTHY
            backend.last_health_check = datetime.utcnow()
            logger.error(f"Backend {backend.id} health check error: {e}")

    def get_stats(self) -> LoadBalancerStats:
        """Get load balancer statistics.

        Returns:
            Load balancer statistics
        """
        healthy_backends = sum(1 for b in self.backends.values() if b.is_healthy)
        total_backends = len(self.backends)

        return LoadBalancerStats(
            total_requests=self.stats.total_requests,
            successful_requests=self.stats.successful_requests,
            failed_requests=self.stats.failed_requests,
            avg_response_time=self.stats.avg_response_time,
            requests_per_second=self.stats.requests_per_second,
            active_connections=sum(
                b.current_connections for b in self.backends.values()
            ),
            healthy_backends=healthy_backends,
            total_backends=total_backends,
            last_updated=datetime.utcnow(),
        )

    async def close(self):
        """Close load balancer and cleanup resources."""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        logger.info("Load balancer closed")


class AutoScaler:
    """Auto-scaling manager for dynamic resource allocation."""

    def __init__(self, config: AutoScalingConfig, load_balancer: LoadBalancer):
        """Initialize auto scaler.

        Args:
            config: Auto-scaling configuration
            load_balancer: Load balancer instance
        """
        self.config = config
        self.load_balancer = load_balancer
        self.scaling_history: deque = field(default_factory=lambda: deque(maxlen=100))
        self.last_scale_time: dict[str, datetime] = {}
        self.scaling_task: asyncio.Task | None = None

        # Start scaling task
        if config.enabled:
            self.scaling_task = asyncio.create_task(self._scaling_loop())

    async def _scaling_loop(self):
        """Auto-scaling evaluation loop."""
        while True:
            try:
                await asyncio.sleep(self.config.evaluation_interval)
                await self._evaluate_scaling()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-scaling evaluation error: {e}")

    async def _evaluate_scaling(self):
        """Evaluate if scaling is needed."""
        if not self.config.enabled:
            return

        # Get current metrics
        metrics = await self._collect_metrics()

        # Determine scaling action
        scale_direction = await self._determine_scaling_action(metrics)

        if scale_direction != ScaleDirection.NONE:
            await self._execute_scaling(scale_direction, metrics)

    async def _collect_metrics(self) -> dict[str, Any]:
        """Collect metrics for scaling decisions.

        Returns:
            Metrics dictionary
        """
        stats = self.load_balancer.get_stats()
        current_instances = len(self.load_balancer.backends)

        metrics = {
            "current_instances": current_instances,
            "requests_per_second": stats.requests_per_second,
            "avg_response_time": stats.avg_response_time,
            "active_connections": stats.active_connections,
            "cpu_utilization": await self._get_cpu_utilization(),
            "memory_utilization": await self._get_memory_utilization(),
            "queue_length": await self._get_queue_length(),
        }

        return metrics

    async def _determine_scaling_action(
        self, metrics: dict[str, Any]
    ) -> ScaleDirection:
        """Determine scaling action based on metrics.

        Args:
            metrics: Current metrics

        Returns:
            Scaling direction
        """
        current_instances = metrics["current_instances"]

        # Check cooldown periods
        if not self._can_scale_up():
            return ScaleDirection.NONE
        if not self._can_scale_down():
            return ScaleDirection.NONE

        # Check instance limits
        if current_instances >= self.config.max_instances:
            return ScaleDirection.NONE
        if current_instances <= self.config.min_instances:
            return ScaleDirection.NONE

        # Evaluate based on policy
        if self.config.policy == ScalingPolicy.CPU_BASED:
            return self._evaluate_cpu_scaling(metrics)
        elif self.config.policy == ScalingPolicy.MEMORY_BASED:
            return self._evaluate_memory_scaling(metrics)
        elif self.config.policy == ScalingPolicy.REQUEST_RATE_BASED:
            return self._evaluate_request_rate_scaling(metrics)
        elif self.config.policy == ScalingPolicy.RESPONSE_TIME_BASED:
            return self._evaluate_response_time_scaling(metrics)
        elif self.config.policy == ScalingPolicy.QUEUE_LENGTH_BASED:
            return self._evaluate_queue_length_scaling(metrics)
        else:
            return ScaleDirection.NONE

    def _evaluate_cpu_scaling(self, metrics: dict[str, Any]) -> ScaleDirection:
        """Evaluate CPU-based scaling.

        Args:
            metrics: Current metrics

        Returns:
            Scaling direction
        """
        cpu_util = metrics["cpu_utilization"]

        if cpu_util > self.config.scale_up_threshold:
            return ScaleDirection.UP
        elif cpu_util < self.config.scale_down_threshold:
            return ScaleDirection.DOWN

        return ScaleDirection.NONE

    def _evaluate_memory_scaling(self, metrics: dict[str, Any]) -> ScaleDirection:
        """Evaluate memory-based scaling.

        Args:
            metrics: Current metrics

        Returns:
            Scaling direction
        """
        memory_util = metrics["memory_utilization"]

        if memory_util > self.config.scale_up_threshold:
            return ScaleDirection.UP
        elif memory_util < self.config.scale_down_threshold:
            return ScaleDirection.DOWN

        return ScaleDirection.NONE

    def _evaluate_request_rate_scaling(self, metrics: dict[str, Any]) -> ScaleDirection:
        """Evaluate request rate-based scaling.

        Args:
            metrics: Current metrics

        Returns:
            Scaling direction
        """
        rps = metrics["requests_per_second"]
        target_rps = self.config.target_request_rate / 60  # Convert to per second

        if rps > target_rps * 1.2:  # 20% buffer
            return ScaleDirection.UP
        elif rps < target_rps * 0.5:  # 50% utilization
            return ScaleDirection.DOWN

        return ScaleDirection.NONE

    def _evaluate_response_time_scaling(
        self, metrics: dict[str, Any]
    ) -> ScaleDirection:
        """Evaluate response time-based scaling.

        Args:
            metrics: Current metrics

        Returns:
            Scaling direction
        """
        response_time = metrics["avg_response_time"]

        if response_time > self.config.target_response_time * 1.5:
            return ScaleDirection.UP
        elif response_time < self.config.target_response_time * 0.5:
            return ScaleDirection.DOWN

        return ScaleDirection.NONE

    def _evaluate_queue_length_scaling(self, metrics: dict[str, Any]) -> ScaleDirection:
        """Evaluate queue length-based scaling.

        Args:
            metrics: Current metrics

        Returns:
            Scaling direction
        """
        queue_length = metrics["queue_length"]
        max_queue_per_instance = 100  # Configurable

        if queue_length > max_queue_per_instance * len(self.load_balancer.backends):
            return ScaleDirection.UP
        elif (
            queue_length
            < max_queue_per_instance * len(self.load_balancer.backends) * 0.3
        ):
            return ScaleDirection.DOWN

        return ScaleDirection.NONE

    def _can_scale_up(self) -> bool:
        """Check if scale up is allowed.

        Returns:
            True if scale up is allowed
        """
        last_scale = self.last_scale_time.get("up")
        if not last_scale:
            return True

        cooldown_passed = (
            datetime.utcnow() - last_scale
        ).total_seconds() > self.config.scale_up_cooldown
        return cooldown_passed

    def _can_scale_down(self) -> bool:
        """Check if scale down is allowed.

        Returns:
            True if scale down is allowed
        """
        last_scale = self.last_scale_time.get("down")
        if not last_scale:
            return True

        cooldown_passed = (
            datetime.utcnow() - last_scale
        ).total_seconds() > self.config.scale_down_cooldown
        return cooldown_passed

    async def _execute_scaling(
        self, direction: ScaleDirection, metrics: dict[str, Any]
    ):
        """Execute scaling action.

        Args:
            direction: Scaling direction
            metrics: Current metrics
        """
        if direction == ScaleDirection.UP:
            await self._scale_up(metrics)
        elif direction == ScaleDirection.DOWN:
            await self._scale_down(metrics)

    async def _scale_up(self, metrics: dict[str, Any]):
        """Scale up by adding new instances.

        Args:
            metrics: Current metrics
        """
        logger.info(f"Scaling up - Current instances: {metrics['current_instances']}")

        # This would integrate with your container orchestration system
        # For now, we'll simulate by creating a new backend
        new_backend = BackendServer(
            id=f"backend_{int(time.time())}", host="new-instance", port=8080, weight=1
        )

        self.load_balancer.add_backend(new_backend)
        self.last_scale_time["up"] = datetime.utcnow()

        # Record scaling event
        self.scaling_history.append(
            {
                "timestamp": datetime.utcnow(),
                "action": "scale_up",
                "instances_before": metrics["current_instances"],
                "instances_after": metrics["current_instances"] + 1,
                "metrics": metrics,
            }
        )

        logger.info(f"Scaled up to {metrics['current_instances'] + 1} instances")

    async def _scale_down(self, metrics: dict[str, Any]):
        """Scale down by removing instances.

        Args:
            metrics: Current metrics
        """
        if len(self.load_balancer.backends) <= self.config.min_instances:
            logger.warning("Cannot scale down - minimum instances reached")
            return

        logger.info(f"Scaling down - Current instances: {metrics['current_instances']}")

        # Find least loaded backend to remove
        available_backends = [
            backend
            for backend in self.load_balancer.backends.values()
            if backend.current_connections == 0
            and backend.health_status == HealthStatus.HEALTHY
        ]

        if not available_backends:
            logger.warning("Cannot scale down - no idle backends available")
            return

        backend_to_remove = min(available_backends, key=lambda b: b.current_connections)

        # Set to draining first
        backend_to_remove.health_status = HealthStatus.DRAINING

        # Wait for connections to drain (simplified)
        await asyncio.sleep(10)

        # Remove backend
        self.load_balancer.remove_backend(backend_to_remove.id)
        self.last_scale_time["down"] = datetime.utcnow()

        # Record scaling event
        self.scaling_history.append(
            {
                "timestamp": datetime.utcnow(),
                "action": "scale_down",
                "instances_before": metrics["current_instances"],
                "instances_after": metrics["current_instances"] - 1,
                "metrics": metrics,
            }
        )

        logger.info(f"Scaled down to {metrics['current_instances'] - 1} instances")

    async def _get_cpu_utilization(self) -> float:
        """Get CPU utilization.

        Returns:
            CPU utilization percentage
        """
        # This would integrate with your monitoring system
        # For now, return a simulated value
        return random.uniform(20, 90)

    async def _get_memory_utilization(self) -> float:
        """Get memory utilization.

        Returns:
            Memory utilization percentage
        """
        # This would integrate with your monitoring system
        # For now, return a simulated value
        return random.uniform(30, 85)

    async def _get_queue_length(self) -> int:
        """Get request queue length.

        Returns:
            Queue length
        """
        # This would integrate with your monitoring system
        # For now, return a simulated value
        return random.randint(0, 500)

    def get_scaling_history(self) -> list[dict[str, Any]]:
        """Get scaling history.

        Returns:
            List of scaling events
        """
        return list(self.scaling_history)

    async def close(self):
        """Close auto scaler and cleanup resources."""
        if self.scaling_task:
            self.scaling_task.cancel()
            try:
                await self.scaling_task
            except asyncio.CancelledError:
                pass

        logger.info("Auto scaler closed")


class LoadBalancingSystem:
    """Main load balancing and auto-scaling system."""

    def __init__(
        self,
        load_balancer_config: LoadBalancerConfig,
        auto_scaling_config: AutoScalingConfig,
    ):
        """Initialize load balancing system.

        Args:
            load_balancer_config: Load balancer configuration
            auto_scaling_config: Auto scaling configuration
        """
        self.load_balancer = LoadBalancer(load_balancer_config)
        self.auto_scaler = AutoScaler(auto_scaling_config, self.load_balancer)
        self.request_count = 0
        self.start_time = datetime.utcnow()

    async def start(self):
        """Start load balancing system."""
        logger.info("Load balancing system started")

    async def stop(self):
        """Stop load balancing system."""
        await self.auto_scaler.close()
        await self.load_balancer.close()
        logger.info("Load balancing system stopped")

    async def handle_request(
        self, client_ip: str | None = None, session_id: str | None = None
    ) -> BackendServer | None:
        """Handle incoming request.

        Args:
            client_ip: Client IP address
            session_id: Session ID

        Returns:
            Selected backend server or None
        """
        self.request_count += 1

        # Select backend
        backend = await self.load_balancer.select_backend(client_ip, session_id)

        if backend:
            backend.current_connections += 1
            start_time = time.time()

            # Simulate request processing
            await asyncio.sleep(random.uniform(0.01, 0.1))

            # Update statistics
            response_time = (time.time() - start_time) * 1000
            backend.update_response_time(response_time)
            backend.record_success()
            backend.current_connections -= 1

            self.load_balancer.stats.total_requests += 1
            self.load_balancer.stats.successful_requests += 1

        return backend

    def get_system_stats(self) -> dict[str, Any]:
        """Get comprehensive system statistics.

        Returns:
            System statistics
        """
        lb_stats = self.load_balancer.get_stats()
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return LoadBalancingSystem_get_system_statsResult.model_validate({
            "load_balancer": lb_stats.dict(),
            "auto_scaler": {
                "scaling_history": self.auto_scaler.get_scaling_history(),
                "current_instances": len(self.load_balancer.backends),
            },
            "system": {
                "uptime_seconds": uptime,
                "total_requests": self.request_count,
                "requests_per_second": self.request_count / max(uptime, 1),
            },
        })


# Global load balancing system instance
_load_balancing_system: LoadBalancingSystem | None = None


def get_load_balancing_system() -> LoadBalancingSystem | None:
    """Get global load balancing system instance.

    Returns:
        Load balancing system instance
    """
    return _load_balancing_system


async def initialize_load_balancing(
    load_balancer_config: LoadBalancerConfig, auto_scaling_config: AutoScalingConfig
) -> LoadBalancingSystem:
    """Initialize global load balancing system.

    Args:
        load_balancer_config: Load balancer configuration
        auto_scaling_config: Auto scaling configuration

    Returns:
        Load balancing system instance
    """
    global _load_balancing_system
    _load_balancing_system = LoadBalancingSystem(
        load_balancer_config, auto_scaling_config
    )
    await _load_balancing_system.start()
    logger.info("Load balancing system initialized")
    return _load_balancing_system
