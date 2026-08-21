"""MCP Gateway - Main entry point for secure tool invocation.

Orchestrates authentication, authorization, token exchange, and audit logging
for all tool invocations. This is the primary interface for tool execution.

Example:
    >>> gateway = MCPGateway(
    ...     auth_handler=OAuthHandler(config),
    ...     token_exchanger=TokenExchanger(endpoint),
    ...     manifest_verifier=ManifestVerifier(public_key),
    ...     tool_registry=ToolRegistry()
    ... )
    >>> result = await gateway.invoke_tool(
    ...     tool_name="search",
    ...     request={"query": "example"},
    ...     tenant_id=tenant_uuid,
    ...     user_token=user_access_token
    ... )
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID, uuid4

from .auth import OAuthHandler
from .manifest import ManifestVerifier
from .registry import ToolRegistry
from .token_exchange import TokenExchanger
from .mcp_types import (
    AuthenticationError,
    DelegatedToken,
    GatewayError,
    ManifestValidationError,
    ToolAccessDeniedError,
    ToolManifest,
    ToolRequest,
    ToolResponse,
)

logger = logging.getLogger(__name__)


class MCPGateway:
    """Secure gateway for Model Context Protocol tool invocation.
    
    Implements the complete security flow for tool execution:
    1. Authenticate the request (via OAuth 2.1)
    2. Authorize tenant access to tool (via ToolRegistry)
    3. Verify tool manifest signature (via ManifestVerifier)
    4. Exchange token for tool-scoped delegation (via TokenExchanger)
    5. Execute tool with delegated token
    6. Audit log the invocation
    
    Security Properties:
    - All tools run with tenant-scoped tokens (not original user tokens)
    - Tool-to-tool calls are auditable via token exchange
    - Manifest signatures ensure tool provenance
    - Per-tenant tool enablement prevents unauthorized access
    
    Example:
        >>> # Initialize gateway
        >>> gateway = MCPGateway(
        ...     auth_handler=oauth_handler,
        ...     token_exchanger=token_exchanger,
        ...     manifest_verifier=ManifestVerifier(public_key),
        ...     tool_registry=tool_registry
        ... )
        >>>
        >>> # Invoke a tool
        >>> result = await gateway.invoke_tool(
        ...     tool_name="search",
        ...     request={"query": "machine learning"},
        ...     tenant_id=tenant_uuid,
        ...     user_id="user-123",
        ...     user_token=access_token
        ... )
        >>>
        >>> if result.success:
        ...     print(result.result)
        ... else:
        ...     print(f"Tool failed: {result.error}")
    """
    
    def __init__(
        self,
        auth_handler: OAuthHandler | None = None,
        token_exchanger: TokenExchanger | None = None,
        manifest_verifier: ManifestVerifier | None = None,
        tool_registry: ToolRegistry | None = None,
        enable_audit_logging: bool = True,
        tool_timeout_seconds: float = 30.0,
    ):
        """Initialize MCP Gateway with required components.
        
        Args:
            auth_handler: OAuth 2.1 + PKCE handler (optional if using direct tokens)
            token_exchanger: RFC 8693 token exchange handler
            manifest_verifier: JWS manifest verification
            tool_registry: Tenant-scoped tool registry
            enable_audit_logging: Whether to emit audit events
            tool_timeout_seconds: HTTP timeout for dispatching to tool endpoints
        """
        self.auth_handler = auth_handler
        self.token_exchanger = token_exchanger
        self.manifest_verifier = manifest_verifier
        self.tool_registry = tool_registry or ToolRegistry()
        self.enable_audit_logging = enable_audit_logging
        self.tool_timeout_seconds = tool_timeout_seconds
        
        # Metrics for monitoring
        self._metrics = {
            "invocations_total": 0,
            "invocations_success": 0,
            "invocations_failed": 0,
            "auth_failures": 0,
            "access_denied": 0,
            "manifest_failures": 0,
            "executions_success": 0,
            "execution_failures": 0,
        }
        
        logger.info("MCP Gateway initialized")
    
    async def invoke_tool(
        self,
        tool_name: str,
        request: dict[str, Any],
        tenant_id: UUID,
        user_token: str | None = None,
        user_id: str | None = None,
        delegated_token: DelegatedToken | None = None,
        request_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> ToolResponse:
        """Invoke a tool with full security controls.
        
        This is the main entry point for tool execution. It performs:
        1. Tenant authorization check
        2. Manifest signature verification
        3. Token exchange (if user_token provided)
        4. Tool execution
        5. Audit logging
        
        Args:
            tool_name: Name of the tool to invoke
            request: Tool parameters
            tenant_id: Tenant UUID for isolation
            user_token: Original user access token (for token exchange)
            user_id: User ID for audit trail
            delegated_token: Pre-exchanged delegated token (alternative to user_token)
            request_id: Optional request ID for tracing
            parent_span_id: Optional parent span for distributed tracing
            
        Returns:
            ToolResponse with result or error
            
        Example:
            >>> result = await gateway.invoke_tool(
            ...     tool_name="database_query",
            ...     request={"sql": "SELECT * FROM users LIMIT 10"},
            ...     tenant_id=tenant_uuid,
            ...     user_token=user_access_token,
            ...     user_id="user-123"
            ... )
        """
        start_time = time.time()
        request_id = request_id or str(uuid4())
        
        self._metrics["invocations_total"] += 1
        
        try:
            # Step 1: Create tenant-scoped tool request
            tool_request = self.tool_registry.get_tenant_scoped_request(
                tool_name=tool_name,
                tenant_id=tenant_id,
                user_id=user_id,
                parameters=request,
                request_id=request_id,
            )
            
            # Step 2: Verify manifest signature (if verifier configured)
            if self.manifest_verifier:
                await self._verify_manifest(tool_name)
            
            # Step 3: Get or create delegated token
            if delegated_token:
                token = delegated_token
            elif user_token and self.token_exchanger:
                token = await self._exchange_token(
                    user_token=user_token,
                    tool_name=tool_name,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
            else:
                # No token exchange - use direct invocation (less secure)
                logger.warning(
                    f"Tool '{tool_name}' invoked without token exchange - "
                    "audit trail may be incomplete"
                )
                token = None
            
            # Step 4: Execute tool
            response = await self._execute_tool(
                tool_request=tool_request,
                delegated_token=token,
                start_time=start_time,
            )
            
            self._metrics["invocations_success"] += 1
            
            # Step 5: Audit logging
            if self.enable_audit_logging:
                await self._emit_audit_event(tool_request, response, token)
            
            return response
            
        except ToolAccessDeniedError as e:
            self._metrics["access_denied"] += 1
            logger.warning(
                f"Access denied for tool '{tool_name}': {e}",
                extra={"tool_name": tool_name, "tenant_id": str(tenant_id)}
            )
            return ToolResponse(
                tool_name=tool_name,
                error=f"Access denied: {e}",
                execution_time_ms=(time.time() - start_time) * 1000,
                request_id=request_id,
            )
            
        except AuthenticationError as e:
            self._metrics["auth_failures"] += 1
            logger.error(f"Authentication failed for tool '{tool_name}': {e}")
            return ToolResponse(
                tool_name=tool_name,
                error=f"Authentication failed: {e}",
                execution_time_ms=(time.time() - start_time) * 1000,
                request_id=request_id,
            )
            
        except Exception as e:
            self._metrics["invocations_failed"] += 1
            logger.exception(f"Tool '{tool_name}' invocation failed: {e}")
            return ToolResponse(
                tool_name=tool_name,
                error=f"Tool execution failed: {e}",
                execution_time_ms=(time.time() - start_time) * 1000,
                request_id=request_id,
            )
    
    async def _verify_manifest(self, tool_name: str) -> None:
        """Verify tool manifest signature.
        
        Args:
            tool_name: Tool to verify
            
        Raises:
            ManifestValidationError: If verification fails
        """
        if not self.manifest_verifier:
            return
        
        # Get manifest from registry (without tenant check - admin operation)
        if tool_name not in self.tool_registry._tools:
            raise ManifestValidationError(f"Tool '{tool_name}' not found")
        
        manifest = self.tool_registry._tools[tool_name]
        
        if not manifest.signature:
            raise ManifestValidationError(
                f"Tool '{tool_name}' has no signed manifest"
            )
        
        if not self.manifest_verifier.verify_manifest(manifest):
            self._metrics["manifest_failures"] += 1
            raise ManifestValidationError(
                f"Tool '{tool_name}' manifest signature verification failed"
            )
        
        logger.debug(f"Manifest signature verified for tool '{tool_name}'")
    
    async def _exchange_token(
        self,
        user_token: str,
        tool_name: str,
        tenant_id: UUID,
        user_id: str | None = None,
    ) -> DelegatedToken:
        """Exchange user token for tool-scoped delegated token.
        
        Args:
            user_token: Original user access token
            tool_name: Tool to scope token for
            tenant_id: Tenant UUID
            user_id: User ID for audit
            
        Returns:
            DelegatedToken for tool invocation
            
        Raises:
            AuthenticationError: If exchange fails
        """
        if not self.token_exchanger:
            raise AuthenticationError("Token exchanger not configured")
        
        # Get tool's required scopes
        manifest = self.tool_registry._tools.get(tool_name)
        scope = " ".join(manifest.required_scopes) if manifest else "tools:execute"
        
        try:
            delegated = await self.token_exchanger.exchange_token(
                subject_token=user_token,
                subject_token_type="urn:ietf:params:oauth:token-type:access_token",
                tool_name=tool_name,
                tenant_id=tenant_id,
                user_id=user_id,
                scope=scope,
            )
            
            logger.debug(f"Token exchanged for tool '{tool_name}'")
            return delegated
            
        except Exception as e:
            raise AuthenticationError(f"Token exchange failed: {e}") from e
    
    async def _execute_tool(
        self,
        tool_request: ToolRequest,
        delegated_token: DelegatedToken | None,
        start_time: float,
    ) -> ToolResponse:
        """Execute the tool invocation by dispatching to the tool endpoint.

        Args:
            tool_request: Prepared tool request
            delegated_token: Token for tool authentication
            start_time: Timestamp for duration calculation

        Returns:
            ToolResponse
        """
        tool_name = tool_request.tool_name

        # Look up the tool manifest for the endpoint URL.
        manifest = self.tool_registry._tools.get(tool_name)
        if not manifest:
            return ToolResponse(
                tool_name=tool_name,
                error=f"Tool '{tool_name}' endpoint not configured",
                execution_time_ms=(time.time() - start_time) * 1000,
                request_id=tool_request.request_id,
            )

        # Dispatch to the real tool endpoint with the delegated token.
        # The tool is responsible for its own tenant isolation; the gateway
        # authenticates, authorizes, and delegates a scoped token.
        try:
            import httpx

            headers = {"content-type": "application/json"}
            if delegated_token:
                headers["authorization"] = f"{delegated_token.token_type} {delegated_token.access_token}"
            if tool_request.tenant_id:
                headers["x-tenant-id"] = str(tool_request.tenant_id)
            if tool_request.user_id:
                headers["x-user-id"] = tool_request.user_id
            if tool_request.request_id:
                headers["x-request-id"] = tool_request.request_id

            async with httpx.AsyncClient(timeout=self.tool_timeout_seconds, follow_redirects=False) as client:
                upstream = await client.post(
                    manifest.endpoint,
                    json=tool_request.parameters,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            self._metrics["execution_failures"] += 1
            logger.warning(
                f"Tool '{tool_name}' HTTP dispatch failed: {exc}",
                extra={
                    "tool_name": tool_name,
                    "endpoint": manifest.endpoint,
                    "tenant_id": str(tool_request.tenant_id),
                },
            )
            return ToolResponse(
                tool_name=tool_name,
                error=f"Tool dispatch failed: {exc}",
                execution_time_ms=(time.time() - start_time) * 1000,
                request_id=tool_request.request_id,
            )

        if upstream.status_code >= 400:
            self._metrics["execution_failures"] += 1
            return ToolResponse(
                tool_name=tool_name,
                error=f"Tool endpoint returned HTTP {upstream.status_code}",
                execution_time_ms=(time.time() - start_time) * 1000,
                request_id=tool_request.request_id,
            )

        try:
            result = upstream.json()
        except ValueError:
            result = {"_text": upstream.text}

        self._metrics["executions_success"] += 1
        return ToolResponse(
            tool_name=tool_name,
            result=result,
            execution_time_ms=(time.time() - start_time) * 1000,
            request_id=tool_request.request_id,
        )
    
    async def _emit_audit_event(
        self,
        tool_request: ToolRequest,
        response: ToolResponse,
        delegated_token: DelegatedToken | None,
    ) -> None:
        """Emit audit event for tool invocation.
        
        Args:
            tool_request: Tool request details
            response: Tool response
            delegated_token: Token used for invocation
        """
        try:
            # Import audit emitter if available
            from value_fabric.shared.audit import (
                AuditAction,
                AuditOutcome,
                emit_audit_event,
            )
            
            await emit_audit_event(
                action=AuditAction.TOOL_INVOCATION,
                outcome=AuditOutcome.SUCCESS if response.success else AuditOutcome.FAILURE,
                resource_type="tool",
                resource_id=tool_request.tool_name,
                actor_id=tool_request.user_id,
                tenant_id=tool_request.tenant_id,
                request_id=tool_request.request_id,
                details={
                    "execution_time_ms": response.execution_time_ms,
                    "has_delegated_token": delegated_token is not None,
                    "tool_scope": delegated_token.scope if delegated_token else None,
                    "error": response.error,
                }
            )
            
        except Exception as e:
            # Audit emission failure is non-critical
            logger.debug(f"Audit emission failed (non-critical): {e}")
    
    def get_metrics(self) -> dict[str, int]:
        """Get gateway invocation metrics.
        
        Returns:
            Dictionary of metric counters
        """
        return self._metrics.copy()
    
    async def close(self) -> None:
        """Close gateway resources."""
        if self.auth_handler:
            await self.auth_handler.close()
        if self.token_exchanger:
            await self.token_exchanger.close()
        logger.info("MCP Gateway closed")
