"""
FastAPI middleware for tenant-scoped rate limiting (Task 5).

Integrates TenantRateLimiter into FastAPI request pipeline with:
- Automatic tenant context extraction
- Rate limit headers in responses
- 429 responses when limits exceeded
- Monitoring integration
"""

import logging
import re
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .tenant_rate_limiter import TenantRateLimiter, TenantTier

logger = logging.getLogger(__name__)

# UUID pattern for endpoint normalization
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)


class TenantRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant-scoped rate limiting.
    
    Automatically applies rate limits based on tenant context.
    Adds rate limit headers to all responses.
    Returns 429 when limits exceeded.
    """
    
    def __init__(
        self,
        app,
        rate_limiter: TenantRateLimiter,
        exempt_paths: list[str] | None = None,
    ):
        """Initialize rate limit middleware.
        
        Args:
            app: FastAPI application
            rate_limiter: TenantRateLimiter instance
            exempt_paths: Paths exempt from rate limiting (e.g., /health)
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.exempt_paths = exempt_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with rate limiting.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response with rate limit headers
        """
        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Get tenant context
        from value_fabric.shared.boundaries.tenant_boundary import get_tenant_context
        tenant_context = get_tenant_context()
        
        if not tenant_context:
            # No tenant context - skip rate limiting (auth middleware will handle)
            logger.warning(f"No tenant context for rate limiting: {request.url.path}")
            return await call_next(request)
        
        # Extract endpoint pattern (remove IDs for grouping)
        endpoint = self._normalize_endpoint(request.url.path)
        route_group = self._resolve_route_group(endpoint, request.method)
        
        # Validate and normalize tenant tier
        # RequestContext may not have tenant_tier (it has isolation_tier instead);
        # use getattr to avoid AttributeError and safely default to SHARED.
        raw_tier = getattr(tenant_context, "tenant_tier", None)
        try:
            tier = TenantTier(raw_tier or "shared")
        except ValueError:
            logger.warning(
                f"Invalid tenant tier '{raw_tier}' for tenant {tenant_context.tenant_id}, "
                f"defaulting to 'shared'"
            )
            tier = TenantTier.SHARED
        
        # Check rate limit
        result = await self.rate_limiter.check_rate_limit(
            tenant_id=tenant_context.tenant_id,
            tenant_tier=tier,
            endpoint=endpoint,
            user_id=tenant_context.user_id,
            api_key_id=getattr(tenant_context, "api_key_id", None),
            route_group=route_group,
        )
        
        # If rate limit exceeded, return 429
        if not result.allowed:
            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "event_type": "rate_limit_exceeded",
                    "tenant_id": str(tenant_context.tenant_id),
                    "principal_id": str(getattr(tenant_context, "api_key_id", None) or tenant_context.user_id),
                    "route_group": route_group,
                    "endpoint": endpoint,
                    "method": request.method,
                    "limit": result.limit,
                    "retry_after_seconds": result.retry_after_seconds,
                },
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "limit": result.limit,
                    "retry_after_seconds": result.retry_after_seconds,
                    "reset_at": result.reset_at.isoformat(),
                },
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(result.reset_at.timestamp())),
                    "Retry-After": str(result.retry_after_seconds),
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(result.reset_at.timestamp()))
        response.headers["X-RateLimit-Route-Group"] = route_group

        logger.info(
            "rate_limit_checked",
            extra={
                "event_type": "rate_limit_checked",
                "tenant_id": str(tenant_context.tenant_id),
                "principal_id": str(getattr(tenant_context, "api_key_id", None) or tenant_context.user_id),
                "route_group": route_group,
                "endpoint": endpoint,
                "method": request.method,
                "allowed": result.allowed,
                "remaining": result.remaining,
                "limit": result.limit,
            },
        )
        
        return response
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for rate limiting.
        
        Removes UUIDs and other variable parts to group similar requests.
        
        Args:
            path: Request path
            
        Returns:
            Normalized endpoint pattern
        """
        parts = path.split("/")
        normalized = []
        
        for part in parts:
            # Replace UUIDs with placeholder (use regex for robust matching)
            if UUID_PATTERN.match(part):
                normalized.append("{id}")
            # Replace numeric IDs
            elif part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)
        
        return "/".join(normalized)

    def _resolve_route_group(self, endpoint: str, method: str) -> str:
        endpoint_lower = endpoint.lower()
        if "/agents" in endpoint_lower and method.upper() in {"POST", "PUT"}:
            return "agent_execution"
        if "/extract" in endpoint_lower:
            return "extraction"
        if "/model-registry" in endpoint_lower and method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            return "model_registry_write"
        return "default"
