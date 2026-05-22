<!-- Migrated from services/ADRs/ during legacy path cleanup. -->

# ADR-012: Circuit Breaker Pattern for External Service Resilience

**Status:** Accepted  
**Date:** April 2026  
**Authors:** Distinguished Engineering Team  
**Reviewers:** Platform Reliability Committee

---

## Context

Value Fabric depends on multiple external services:
- LLM providers (OpenAI, Anthropic) for entity extraction
- CRM systems (Salesforce, HubSpot) for data sync
- Search engines for competitive research
- Vault for secrets management

These services can fail due to:
- Network timeouts
- Rate limiting
- Service degradation
- Regional outages

Without protection, cascading failures can take down the entire platform.

We evaluated:
1. **Circuit Breaker Pattern** (Fail fast when service unhealthy)
2. **Retry with Exponential Backoff** (Keep trying)
3. **Bulkhead Pattern** (Isolate resource pools)
4. **Simple Timeout** (Just set timeouts)

## Decision

We chose **Circuit Breaker Pattern** with the following configuration:

```python
@dataclass
class CircuitBreaker:
    """Circuit breaker for external service resilience."""
    
    service_name: str
    failure_threshold: int = 5          # Open after 5 failures
    recovery_timeout: float = 60.0       # Try again after 60s
    half_open_max_calls: int = 3       # Test with 3 calls
```

## Rationale

### Why Circuit Breaker?

1. **Fail Fast**: Don't waste resources on failing calls
   ```python
   # Without circuit breaker
   try:
       result = await openai.chat.completions.create(...)  # 30s timeout
   except TimeoutError:
       # Wasted 30 seconds
   
   # With circuit breaker
   if circuit_breaker.is_open:
       raise ServiceUnavailableError("OpenAI unavailable")
   # Fails immediately, preserves resources
   ```

2. **Automatic Recovery**: Detects when service recovers
   ```
   CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing) → CLOSED (recovered)
                     ↑_________________________________________|
   ```

3. **Graceful Degradation**: Provide fallbacks when services fail
   ```python
   try:
       result = await circuit_breaker.call(openai_client.complete, prompt)
   except CircuitBreakerOpen:
       # Use fallback: cached result, local model, or degraded response
       return await cached_result_or_fallback(prompt)
   ```

4. **Cascading Failure Prevention**: One service failure doesn't overload others
   - Prevents thread pool exhaustion
   - Preserves database connections
   - Maintains platform stability

### Why Not Just Retry?

- Retries can amplify load on failing services
- Doesn't provide feedback to callers about service health
- Can cause thundering herd on recovery
- Circuit breaker composes better with retry (retry inside circuit)

### Why Not Bulkhead?

- Higher complexity (resource pool management)
- Overkill for our API call patterns
- Circuit breaker + timeout sufficient for our use case

### Why Not Just Timeout?

- Timeouts alone don't prevent repeated attempts
- Don't provide service health visibility
- No automatic recovery detection

## Trade-offs

### Positive
- Fast failure prevents resource exhaustion
- Automatic recovery detection
- Health visibility for monitoring
- Graceful degradation support

### Negative
- Additional complexity in call sites
- Potential for premature failure detection
- State management overhead
- Configuration tuning required

## Implementation

### Circuit Breaker State Machine

```python
class CircuitState(Enum):
    """Circuit breaker states."""
    
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject calls
    HALF_OPEN = "half_open" # Testing if recovered

class CircuitBreaker:
    """Production circuit breaker implementation."""
    
    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        
        async with self._lock:
            await self._update_state()
            
            if self._state == CircuitState.OPEN:
                retry_after = self._calculate_retry_after()
                raise CircuitBreakerOpen(self.service_name, retry_after)
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpen(self.service_name, self.recovery_timeout)
                self._half_open_calls += 1
        
        # Execute outside lock
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise
    
    async def _update_state(self) -> None:
        """Update circuit state based on time."""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
    
    async def _on_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # Success in half-open closes the circuit
                self._state = CircuitState.CLOSED
                self._failures = 0
                self._half_open_calls = 0
            else:
                # Reset failures on success
                self._failures = 0
    
    async def _on_failure(self) -> None:
        """Record failed call."""
        async with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Failure in half-open reopens circuit
                self._state = CircuitState.OPEN
            elif self._failures >= self.failure_threshold:
                # Exceeded threshold, open circuit
                self._state = CircuitState.OPEN
```

### Circuit Breaker Registry

```python
class CircuitBreakerRegistry:
    """Registry for managing circuit breakers by service."""
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        async with self._lock:
            if service_name not in self._breakers:
                self._breakers[service_name] = CircuitBreaker(service_name)
            return self._breakers[service_name]
    
    async def call(
        self,
        service_name: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """Call function with circuit breaker for service."""
        breaker = await self.get_breaker(service_name)
        return await breaker.call(func, *args, **kwargs)
    
    def get_all_states(self) -> dict[str, dict]:
        """Get states of all circuit breakers for health monitoring."""
        return {
            name: breaker.get_state()
            for name, breaker in self._breakers.items()
        }

# Global registry
_circuit_breaker_registry = CircuitBreakerRegistry()

async def with_circuit_breaker(service_name: str):
    """Decorator/factory for circuit breaker usage."""
    return await _circuit_breaker_registry.get_breaker(service_name)
```

### Usage in External Service Calls

```python
class LLMExtractor:
    """LLM extraction with circuit breaker protection."""
    
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            service_name="openai",
            failure_threshold=5,
            recovery_timeout=60.0,
        )
    
    async def extract_entities(
        self,
        text: str,
        schema: type[T],
    ) -> T:
        """Extract entities with resilience."""
        
        try:
            return await self.circuit_breaker.call(
                self._call_openai,
                text,
                schema,
            )
        except CircuitBreakerOpen as e:
            logger.warning(
                "OpenAI circuit breaker open, using fallback",
                retry_after=e.retry_after,
            )
            # Fallback to cached results or local model
            return await self._fallback_extraction(text, schema)
        except RateLimitError:
            # Retry with backoff inside circuit
            return await self._extract_with_backoff(text, schema)
    
    async def _call_openai(
        self,
        text: str,
        schema: type[T],
    ) -> T:
        """Direct OpenAI call."""
        return await openai_client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[{"role": "user", "content": self._build_prompt(text)}],
            response_format=schema,
        )
```

### Monitoring and Alerting

```python
# Prometheus metrics for circuit breakers
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Current state of circuit breaker (0=closed, 1=half_open, 2=open)",
    ["service"],
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "circuit_breaker_failures_total",
    "Total failures recorded by circuit breaker",
    ["service"],
)

# Alert when circuit opens
alerting_rules:
  - alert: CircuitBreakerOpen
    expr: circuit_breaker_state == 2
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: "Circuit breaker open for {{ $labels.service }}"
      description: "Service {{ $labels.service }} is experiencing failures"
```

## Configuration by Service

| Service | Failure Threshold | Recovery Timeout | Half-Open Calls |
|---------|------------------|------------------|-----------------|
| OpenAI | 5 | 60s | 3 |
| Anthropic | 5 | 60s | 3 |
| Salesforce | 3 | 120s | 2 |
| HubSpot | 3 | 120s | 2 |
| Vault | 3 | 30s | 2 |
| Neo4j | 10 | 30s | 5 |
| PostgreSQL | 10 | 30s | 5 |

## Consequences

### Accepted
- Additional complexity in service clients
- Configuration tuning overhead
- Potential for premature failure detection (tuning required)

### Mitigated
- Complexity via reusable registry and decorators
- Tuning via metrics and alerting feedback
- Premature detection via conservative defaults

## Related Decisions

- ADR-001: Multi-layer architecture
- ADR-007: OpenTelemetry for observability

---

**Last Updated:** April 21, 2026
