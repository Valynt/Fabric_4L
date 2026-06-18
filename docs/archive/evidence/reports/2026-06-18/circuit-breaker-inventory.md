# Circuit Breaker Inventory

## Overview
This document inventories existing circuit breaker implementations across Value Fabric layers to identify the most mature abstraction for standardization.

## Implementations

### Layer 1: AsyncCircuitBreaker
**Location:** `services/layer1-ingestion/src/shared/circuit_breaker.py`

**Features:**
- Async implementation with states (closed, open, half-open)
- Configurable failure threshold, recovery timeout, success threshold
- Locking to prevent race conditions
- Metrics integration
- Decorator for applying to async functions
- Raises CircuitBreakerError when open

**State Management:**
- Tracks failure count and last failure time
- Automatic state transitions based on thresholds
- Half-open state allows test calls before full recovery

**Maturity:** High - production-ready with metrics and decorator support

---

### Layer 3: Load Balancing CircuitBreaker
**Location:** `services/layer3-knowledge/src/load_balancing/manager.py`

**Features:**
- Synchronous implementation
- Per-server circuit breaking
- Configurable threshold and timeout
- Simple call_allowed() check
- Integrated with load balancer manager

**State Management:**
- Tracks failure count and last failure time
- Simple open/closed states (no half-open)
- Manual reset capability

**Maturity:** Medium - functional but simpler, no half-open state

---

### Layer 3: Gateway CircuitBreaker
**Location:** `services/layer3-knowledge/src/gateway/api_gateway.py`

**Features:**
- Synchronous implementation
- Configurable threshold and timeout
- Simple state tracking
- Service protection focus

**State Management:**
- Tracks failure count and last failure time
- Simple open/closed states (no half-open)

**Maturity:** Medium - similar to load balancer version

---

### Layer 4: CircuitBreaker
**Location:** `services/layer4-agents/src/resilience.py`

**Features:**
- Async implementation
- States: CLOSED, OPEN, HALF_OPEN
- Configurable failure threshold, recovery timeout, half-open max calls
- Per-service circuit breaking
- State inspection for monitoring
- Call method with exception handling

**State Management:**
- Tracks failures, last failure time, half-open call count
- Automatic state transitions
- Half-open state with configurable test calls

**Maturity:** High - production-ready with full state machine

---

## Comparison

| Feature | L1 AsyncCircuitBreaker | L3 Load Balancer | L3 Gateway | L4 CircuitBreaker |
|---------|------------------------|------------------|------------|-------------------|
| Async/Sync | Async | Sync | Sync | Async |
| States | 3 (closed, open, half-open) | 2 (open, closed) | 2 (open, closed) | 3 (closed, open, half-open) |
| Decorator Support | Yes | No | No | No |
| Metrics Integration | Yes | No | No | No |
| Locking | Yes | No | No | No |
| Half-Open Max Calls | Yes | No | No | Yes |
| Monitoring API | get_state() | N/A | N/A | get_state() |

## Recommendation

**Standardize on Layer 4's CircuitBreaker** with enhancements from Layer 1:

**Rationale:**
1. Both L1 and L4 have async implementations (required for FastAPI services)
2. L4 has cleaner state management with half-open max calls
3. L1 has valuable decorator support and metrics integration
4. L4 is more recently developed and aligned with current architecture

**Pilot Integration Plan:**
1. Extract L4's CircuitBreaker to shared location (packages/shared)
2. Add decorator support from L1
3. Add metrics integration from L1
4. Apply to one external dependency path (e.g., LLM API calls in Layer 4)
5. Add tests for state transitions and fallback behavior

## Next Steps

1. Create shared circuit breaker module
2. Add pilot integration to Layer 4 LLM calls
3. Add monitoring and metrics
4. Document usage patterns
5. Roll out to other layers incrementally
