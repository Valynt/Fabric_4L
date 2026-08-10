"""Comprehensive API gateway and service mesh integration for microservices communication."""

import asyncio
import json
import logging
import random
import re
import time
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
import redis.asyncio as redis
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class GatewayProtocol(str, Enum):
    """Gateway protocol types."""

    HTTP = "http"
    HTTPS = "https"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    TCP = "tcp"


class ServiceMeshProtocol(str, Enum):
    """Service mesh protocols."""

    ISTIO = "istio"
    LINKERD = "linkerd"
    CONSUL = "consul"
    KUMA = "kuma"
    CUSTOM = "custom"


class RoutingStrategy(str, Enum):
    """Routing strategies."""

    PATH_BASED = "path_based"
    HEADER_BASED = "header_based"
    QUERY_BASED = "query_based"
    METHOD_BASED = "method_based"
    HOST_BASED = "host_based"
    WEIGHT_BASED = "weight_based"
    FAULT_INJECTION = "fault_injection"


class RetryPolicy(str, Enum):
    """Retry policies."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration."""

    service_name: str
    endpoint_id: str
    host: str
    port: int
    protocol: GatewayProtocol
    path: str = "/"
    weight: int = 1
    healthy: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)

    @property
    def url(self) -> str:
        """Get full URL."""
        return f"{self.protocol.value}://{self.host}:{self.port}{self.path}"


@dataclass
class RouteRule:
    """Routing rule configuration."""

    rule_id: str
    name: str
    target_service: str
    strategy: RoutingStrategy
    priority: int = 0
    conditions: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    timeout: int | None = None
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FaultInjection:
    """Fault injection configuration."""

    fault_id: str
    service: str
    fault_type: str  # delay, error, abort
    probability: float = 0.1
    delay_ms: int | None = None
    error_code: int | None = None
    error_message: str | None = None
    enabled: bool = True


class GatewayConfig(BaseModel):
    """API gateway configuration."""

    enabled: bool = Field(default=True, description="Enable API gateway")
    listen_port: int = Field(default=8080, description="Gateway listen port")
    protocol: GatewayProtocol = Field(
        default=GatewayProtocol.HTTP, description="Gateway protocol"
    )
    enable_cors: bool = Field(default=True, description="Enable CORS")
    enable_compression: bool = Field(default=True, description="Enable compression")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    enable_auth: bool = Field(default=True, description="Enable authentication")
    enable_logging: bool = Field(default=True, description="Enable request logging")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    default_timeout: int = Field(default=30, description="Default request timeout")
    max_request_size: int = Field(
        default=10485760, description="Max request size in bytes"
    )
    max_response_size: int = Field(
        default=10485760, description="Max response size in bytes"
    )

    model_config = ConfigDict(use_enum_values=True)


class ServiceMeshConfig(BaseModel):
    """Service mesh configuration."""

    enabled: bool = Field(default=True, description="Enable service mesh")
    protocol: ServiceMeshProtocol = Field(
        default=ServiceMeshProtocol.ISTIO, description="Service mesh protocol"
    )
    control_plane_url: str = Field(
        default="http://istio-control-plane:15000", description="Control plane URL"
    )
    discovery_enabled: bool = Field(
        default=True, description="Enable service discovery"
    )
    load_balancing_enabled: bool = Field(
        default=True, description="Enable load balancing"
    )
    circuit_breaker_enabled: bool = Field(
        default=True, description="Enable circuit breaker"
    )
    retry_enabled: bool = Field(default=True, description="Enable retry")
    timeout_enabled: bool = Field(default=True, description="Enable timeout")
    tracing_enabled: bool = Field(
        default=True, description="Enable distributed tracing"
    )

    model_config = ConfigDict(use_enum_values=True)


class GatewayStats(BaseModel):
    """Gateway statistics."""

    total_requests: int = Field(default=0, description="Total requests")
    successful_requests: int = Field(default=0, description="Successful requests")
    failed_requests: int = Field(default=0, description="Failed requests")
    avg_response_time: float = Field(default=0.0, description="Average response time")
    requests_per_second: float = Field(default=0.0, description="Requests per second")
    active_connections: int = Field(default=0, description="Active connections")
    services_count: int = Field(default=0, description="Number of services")
    routes_count: int = Field(default=0, description="Number of routes")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )


class CircuitBreaker:
    """Circuit breaker for service protection."""

    def __init__(
        self, failure_threshold: int = 5, timeout: int = 60, success_threshold: int = 2
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time to wait before attempting recovery
            success_threshold: Number of successes to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call_allowed(self) -> bool:
        """Check if call is allowed.

        Returns:
            True if call is allowed
        """
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if (
                datetime.utcnow() - self.last_failure_time
            ).total_seconds() > self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if (
            self.state == CircuitState.HALF_OPEN
            or self.failure_count >= self.failure_threshold
        ):
            self.state = CircuitState.OPEN


class ServiceRegistry:
    """Service registry for managing service endpoints."""

    def __init__(self, redis_url: str | None = None):
        """Initialize service registry.

        Args:
            redis_url: Redis URL for distributed registry
        """
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None
        self.local_registry: dict[str, list[ServiceEndpoint]] = defaultdict(list)
        self.health_check_task: asyncio.Task | None = None

    async def connect(self):
        """Connect to Redis if configured."""
        if self.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url, decode_responses=False
                )
                await self.redis_client.ping()
                logger.info("Connected to Redis for service registry")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis_client = None

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()

    async def register_service(self, endpoint: ServiceEndpoint):
        """Register service endpoint.

        Args:
            endpoint: Service endpoint to register
        """
        # Add to local registry
        self.local_registry[endpoint.service_name].append(endpoint)

        # Add to Redis if available
        if self.redis_client:
            key = f"service:{endpoint.service_name}:{endpoint.endpoint_id}"
            data = {
                "service_name": endpoint.service_name,
                "endpoint_id": endpoint.endpoint_id,
                "host": endpoint.host,
                "port": endpoint.port,
                "protocol": endpoint.protocol.value,
                "path": endpoint.path,
                "weight": endpoint.weight,
                "healthy": endpoint.healthy,
                "metadata": json.dumps(endpoint.metadata),
                "tags": json.dumps(list(endpoint.tags)),
            }
            await self.redis_client.hset(key, mapping=data)
            await self.redis_client.expire(key, 300)  # 5 minutes TTL

        logger.info(f"Registered service: {endpoint.service_name} -> {endpoint.url}")

    async def unregister_service(self, service_name: str, endpoint_id: str):
        """Unregister service endpoint.

        Args:
            service_name: Service name
            endpoint_id: Endpoint ID
        """
        # Remove from local registry
        if service_name in self.local_registry:
            self.local_registry[service_name] = [
                ep
                for ep in self.local_registry[service_name]
                if ep.endpoint_id != endpoint_id
            ]

        # Remove from Redis if available
        if self.redis_client:
            key = f"service:{service_name}:{endpoint_id}"
            await self.redis_client.delete(key)

        logger.info(f"Unregistered service: {service_name}:{endpoint_id}")

    async def get_service_endpoints(self, service_name: str) -> list[ServiceEndpoint]:
        """Get service endpoints.

        Args:
            service_name: Service name

        Returns:
            List of service endpoints
        """
        # Check local registry first
        if service_name in self.local_registry:
            return self.local_registry[service_name]

        # Check Redis if available
        if self.redis_client:
            pattern = f"service:{service_name}:*"
            keys = await self.redis_client.keys(pattern)
            endpoints = []

            for key in keys:
                data = await self.redis_client.hgetall(key)
                if data:
                    try:
                        metadata = json.loads(data.get("metadata", "{}"))
                    except json.JSONDecodeError:
                        metadata = {}
                    try:
                        tags = set(json.loads(data.get("tags", "[]")))
                    except json.JSONDecodeError:
                        tags = set()
                    endpoint = ServiceEndpoint(
                        service_name=data.get("service_name", ""),
                        endpoint_id=data.get("endpoint_id", ""),
                        host=data.get("host", ""),
                        port=int(data.get("port", 0)),
                        protocol=GatewayProtocol(data.get("protocol", "http")),
                        path=data.get("path", "/"),
                        weight=int(data.get("weight", 1)),
                        healthy=data.get("healthy", "true").lower() == "true",
                        metadata=metadata,
                        tags=tags,
                    )
                    endpoints.append(endpoint)

            return endpoints

        return []

    async def discover_services(self) -> dict[str, list[ServiceEndpoint]]:
        """Discover all services.

        Returns:
            Dictionary of service endpoints
        """
        if self.redis_client:
            pattern = "service:*"
            keys = await self.redis_client.keys(pattern)
            services = defaultdict(list)

            for key in keys:
                data = await self.redis_client.hgetall(key)
                if data:
                    service_name = data.get("service_name", "")
                    try:
                        metadata = json.loads(data.get("metadata", "{}"))
                    except json.JSONDecodeError:
                        metadata = {}
                    try:
                        tags = set(json.loads(data.get("tags", "[]")))
                    except json.JSONDecodeError:
                        tags = set()
                    endpoint = ServiceEndpoint(
                        service_name=service_name,
                        endpoint_id=data.get("endpoint_id", ""),
                        host=data.get("host", ""),
                        port=int(data.get("port", 0)),
                        protocol=GatewayProtocol(data.get("protocol", "http")),
                        path=data.get("path", "/"),
                        weight=int(data.get("weight", 1)),
                        healthy=data.get("healthy", "true").lower() == "true",
                        metadata=metadata,
                        tags=tags,
                    )
                    services[service_name].append(endpoint)

            return dict(services)

        return dict(self.local_registry)


class RouteEngine:
    """Route engine for request routing."""

    def __init__(self):
        """Initialize route engine."""
        self.routes: list[RouteRule] = []
        self.fault_injections: list[FaultInjection] = []

    def add_route(self, route: RouteRule):
        """Add routing rule.

        Args:
            route: Routing rule to add
        """
        self.routes.append(route)
        # Sort by priority (higher priority first)
        self.routes.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added route: {route.name} -> {route.target_service}")

    def remove_route(self, rule_id: str) -> bool:
        """Remove routing rule.

        Args:
            rule_id: Rule ID to remove

        Returns:
            True if removed
        """
        for i, route in enumerate(self.routes):
            if route.rule_id == rule_id:
                del self.routes[i]
                logger.info(f"Removed route: {rule_id}")
                return True
        return False

    def add_fault_injection(self, fault: FaultInjection):
        """Add fault injection.

        Args:
            fault: Fault injection to add
        """
        self.fault_injections.append(fault)
        logger.info(f"Added fault injection: {fault.fault_type} for {fault.service}")

    def match_route(
        self,
        request_path: str,
        request_method: str,
        headers: dict[str, str],
        query_params: dict[str, str],
    ) -> RouteRule | None:
        """Match request to routing rule.

        Args:
            request_path: Request path
            request_method: Request method
            headers: Request headers
            query_params: Query parameters

        Returns:
            Matching route rule or None
        """
        for route in self.routes:
            if not route.enabled:
                continue

            if self._match_conditions(
                route, request_path, request_method, headers, query_params
            ):
                return route

        return None

    def _match_conditions(
        self,
        route: RouteRule,
        request_path: str,
        request_method: str,
        headers: dict[str, str],
        query_params: dict[str, str],
    ) -> bool:
        """Check if route conditions match request.

        Args:
            route: Route rule
            request_path: Request path
            request_method: Request method
            headers: Request headers
            query_params: Query parameters

        Returns:
            True if conditions match
        """
        conditions = route.conditions

        # Path-based matching
        if route.strategy == RoutingStrategy.PATH_BASED:
            path_pattern = conditions.get("path", "")
            if path_pattern and not re.match(path_pattern, request_path):
                return False

        # Method-based matching
        elif route.strategy == RoutingStrategy.METHOD_BASED:
            methods = conditions.get("methods", [])
            if methods and request_method not in methods:
                return False

        # Header-based matching
        elif route.strategy == RoutingStrategy.HEADER_BASED:
            header_conditions = conditions.get("headers", {})
            for header_name, expected_value in header_conditions.items():
                actual_value = headers.get(header_name, "")
                if expected_value and actual_value != expected_value:
                    return False

        # Query-based matching
        elif route.strategy == RoutingStrategy.QUERY_BASED:
            query_conditions = conditions.get("query", {})
            for query_name, expected_value in query_conditions.items():
                actual_value = query_params.get(query_name, "")
                if expected_value and actual_value != expected_value:
                    return False

        # Host-based matching
        elif route.strategy == RoutingStrategy.HOST_BASED:
            host_pattern = conditions.get("host", "")
            if host_pattern:
                host = headers.get("host", "")
                if not re.match(host_pattern, host):
                    return False

        return True

    def check_fault_injection(self, service_name: str) -> FaultInjection | None:
        """Check if fault injection should be applied.

        Args:
            service_name: Service name

        Returns:
            Fault injection or None
        """
        for fault in self.fault_injections:
            if fault.enabled and fault.service == service_name:
                if random.random() < fault.probability:
                    return fault
        return None


class APIGateway:
    """Main API gateway implementation."""

    def __init__(
        self, gateway_config: GatewayConfig, service_mesh_config: ServiceMeshConfig
    ):
        """Initialize API gateway.

        Args:
            gateway_config: Gateway configuration
            service_mesh_config: Service mesh configuration
        """
        self.config = gateway_config
        self.mesh_config = service_mesh_config
        self.service_registry = ServiceRegistry()
        self.route_engine = RouteEngine()
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.stats = GatewayStats()
        self.request_count = 0
        self.start_time = datetime.utcnow()

    async def start(self):
        """Start API gateway."""
        await self.service_registry.connect()
        logger.info("API gateway started")

    async def stop(self):
        """Stop API gateway."""
        await self.service_registry.disconnect()
        logger.info("API gateway stopped")

    async def handle_request(
        self,
        request_path: str,
        request_method: str,
        headers: dict[str, str],
        query_params: dict[str, str],
        body: bytes | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        """Handle incoming request.

        Args:
            request_path: Request path
            request_method: Request method
            headers: Request headers
            query_params: Query parameters
            body: Request body

        Returns:
            Tuple of (status_code, response_headers, response_body)
        """
        start_time = time.time()
        self.request_count += 1

        try:
            # Match route
            route = self.route_engine.match_route(
                request_path, request_method, headers, query_params
            )

            if not route:
                return (
                    404,
                    {"Content-Type": "application/json"},
                    b'{"error": "Route not found"}',
                )

            # Get service endpoints
            endpoints = await self.service_registry.get_service_endpoints(
                route.target_service
            )

            if not endpoints:
                return (
                    503,
                    {"Content-Type": "application/json"},
                    b'{"error": "Service unavailable"}',
                )

            # Select endpoint (simple round-robin for now)
            endpoint = endpoints[0]

            # Check circuit breaker
            circuit_key = f"{route.target_service}:{endpoint.endpoint_id}"
            if circuit_key not in self.circuit_breakers:
                self.circuit_breakers[circuit_key] = CircuitBreaker()

            circuit_breaker = self.circuit_breakers[circuit_key]

            if not circuit_breaker.call_allowed():
                return (
                    503,
                    {"Content-Type": "application/json"},
                    b'{"error": "Circuit breaker open"}',
                )

            # Check fault injection
            fault = self.route_engine.check_fault_injection(route.target_service)

            if fault:
                if fault.fault_type == "delay" and fault.delay_ms:
                    await asyncio.sleep(fault.delay_ms / 1000.0)
                elif fault.fault_type == "abort" and fault.error_code:
                    return (
                        fault.error_code,
                        {"Content-Type": "application/json"},
                        fault.error_message.encode()
                        if fault.error_message
                        else b'{"error": "Service fault injected"}',
                    )

            # Forward request
            response = await self._forward_request(
                endpoint,
                request_path,
                request_method,
                headers,
                query_params,
                body,
                route,
            )

            # Record success
            circuit_breaker.record_success()
            self.stats.successful_requests += 1

            return response

        except Exception as e:
            logger.error(f"Request handling error: {e}")

            # Record failure
            if "circuit_breaker" in locals():
                circuit_breaker.record_failure()

            self.stats.failed_requests += 1
            return (
                500,
                {"Content-Type": "application/json"},
                b'{"error": "Internal server error"}',
            )

        finally:
            # Update statistics
            response_time = (time.time() - start_time) * 1000
            self._update_stats(response_time)

    async def _forward_request(
        self,
        endpoint: ServiceEndpoint,
        request_path: str,
        request_method: str,
        headers: dict[str, str],
        query_params: dict[str, str],
        body: bytes | None,
        route: RouteRule,
    ) -> tuple[int, dict[str, str], bytes]:
        """Forward request to service endpoint.

        Args:
            endpoint: Target endpoint
            request_path: Request path
            request_method: Request method
            headers: Request headers
            query_params: Query parameters
            body: Request body
            route: Route rule

        Returns:
            Tuple of (status_code, response_headers, response_body)
        """
        # Build target URL
        target_url = f"{endpoint.url}{request_path}"
        if query_params:
            target_url += f"?{urllib.parse.urlencode(query_params)}"

        # Prepare headers
        forward_headers = headers.copy()
        forward_headers.pop("host", None)  # Remove host header

        # Set timeout
        timeout = route.timeout or self.config.default_timeout

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=request_method,
                url=target_url,
                headers=forward_headers,
                content=body,
            )

            # Prepare response headers
            response_headers = dict(response.headers)
            response_headers.pop("content-length", None)  # Let client handle this

            return response.status_code, response_headers, response.content

    def _update_stats(self, response_time: float):
        """Update gateway statistics.

        Args:
            response_time: Response time in milliseconds
        """
        self.stats.total_requests = self.request_count
        self.stats.avg_response_time = (
            self.stats.avg_response_time + response_time
        ) / 2

        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        self.stats.requests_per_second = self.request_count / max(uptime, 1)

        self.stats.services_count = len(self.service_registry.local_registry)
        self.stats.routes_count = len(self.route_engine.routes)
        self.stats.last_updated = datetime.utcnow()

    def get_stats(self) -> GatewayStats:
        """Get gateway statistics.

        Returns:
            Gateway statistics
        """
        return self.stats


class ServiceMesh:
    """Service mesh integration."""

    def __init__(self, config: ServiceMeshConfig, gateway: APIGateway):
        """Initialize service mesh.

        Args:
            config: Service mesh configuration
            gateway: API gateway instance
        """
        self.config = config
        self.gateway = gateway
        self.control_plane_client: httpx.AsyncClient | None = None

    async def connect(self):
        """Connect to service mesh control plane."""
        if self.config.enabled:
            self.control_plane_client = httpx.AsyncClient(timeout=30)
            logger.info(f"Connected to service mesh: {self.config.protocol}")

    async def disconnect(self):
        """Disconnect from service mesh control plane."""
        if self.control_plane_client:
            await self.control_plane_client.aclose()

    async def sync_services(self):
        """Sync services with service mesh control plane."""
        if not self.control_plane_client or not self.config.discovery_enabled:
            return

        try:
            # This would integrate with your service mesh control plane
            # For now, we'll simulate service discovery
            logger.info("Syncing services with service mesh")
        except Exception as e:
            logger.error(f"Service mesh sync error: {e}")


# Global instances
_api_gateway: APIGateway | None = None
_service_mesh: ServiceMesh | None = None


def get_api_gateway() -> APIGateway | None:
    """Get global API gateway instance.

    Returns:
        API gateway instance
    """
    return _api_gateway


def get_service_mesh() -> ServiceMesh | None:
    """Get global service mesh instance.

    Returns:
        Service mesh instance
    """
    return _service_mesh


async def initialize_gateway(
    gateway_config: GatewayConfig, service_mesh_config: ServiceMeshConfig
) -> tuple[APIGateway, ServiceMesh]:
    """Initialize global API gateway and service mesh.

    Args:
        gateway_config: Gateway configuration
        service_mesh_config: Service mesh configuration

    Returns:
        API gateway and service mesh instances
    """
    global _api_gateway, _service_mesh

    _api_gateway = APIGateway(gateway_config, service_mesh_config)
    _service_mesh = ServiceMesh(service_mesh_config, _api_gateway)

    await _api_gateway.start()
    await _service_mesh.connect()

    logger.info("API gateway and service mesh initialized")
    return _api_gateway, _service_mesh
