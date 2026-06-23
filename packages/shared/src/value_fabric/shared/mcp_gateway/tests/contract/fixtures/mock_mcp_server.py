"""Mock MCP server for contract testing.

Provides configurable upstream MCP server behavior for testing gateway
routing, aggregation, and error handling without real network dependencies.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum

from .mock_mcp_client import MCPMessage, MCPErrorCode
from value_fabric.shared.models.typed_dict import TypedDictModel


class MockMCPServer__handle_initializeResult(TypedDictModel):
    capabilities: Any
    protocolVersion: Any
    serverInfo: dict[str, Any]

class MockMCPServer__handle_pingResult(TypedDictModel):
    pass

class MockMCPServer__handle_tools_callResult(TypedDictModel):
    content: list[Any]
    isError: bool

class MockMCPServer__handle_resources_listResult(TypedDictModel):
    resources: Any

class MockMCPServer__handle_resources_readResult(TypedDictModel):
    contents: list[Any]

class MockMCPServer__handle_prompts_listResult(TypedDictModel):
    prompts: Any

class MockMCPServer__handle_prompts_getResult(TypedDictModel):
    description: Any
    messages: list[Any]

class MockMCPServer__handle_set_levelResult(TypedDictModel):
    pass


class ServerBehavior(Enum):
    """Predefined server behaviors for testing."""
    HEALTHY = "healthy"  # Normal operation
    SLOW = "slow"  # Slow responses
    ERROR = "error"  # Always returns errors
    FLAKY = "flaky"  # Intermittent failures
    TIMEOUT = "timeout"  # Never responds
    GARBAGE = "garbage"  # Returns invalid data


@dataclass
class MockTool:
    """Definition of a mock tool."""
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], dict] = field(default_factory=lambda: lambda x: {"result": "ok"})
    should_fail: bool = False
    failure_message: str = "Tool execution failed"


@dataclass
class MockResource:
    """Definition of a mock resource."""
    uri: str
    name: str
    mime_type: str = "text/plain"
    content: str | bytes = ""
    handler: Optional[Callable[[], str | bytes]] = None


class MockMCPServer:
    """Configurable mock MCP upstream server.
    
    This server simulates an upstream MCP server for testing gateway
    routing, aggregation, and error handling. It can be configured
    to exhibit various behaviors (slow, flaky, error-prone) for
    resilience testing.
    
    Example:
        >>> server = MockMCPServer(name="upstream-tools")
        >>> server.add_tool(MockTool(
        ...     name="search",
        ...     description="Search documents",
        ...     input_schema={"type": "object", "properties": {}},
        ...     handler=lambda args: {"results": []}
        ... ))
        >>> 
        >>> # Test with flaky behavior
        >>> server.set_behavior(ServerBehavior.FLAKY, fault_rate=0.3)
        >>> response = await server.handle_request(request)
    """
    
    def __init__(
        self,
        name: str,
        protocol_version: str = "2024-11-05",
        behavior: ServerBehavior = ServerBehavior.HEALTHY,
    ):
        """Initialize mock server.
        
        Args:
            name: Server identifier for logging/debugging
            protocol_version: MCP protocol version
            behavior: Initial server behavior
        """
        self.name = name
        self.protocol_version = protocol_version
        self._behavior = behavior
        self._fault_rate = 0.0
        self._delay_ms = 0
        
        # MCP entities
        self._tools: dict[str, MockTool] = {}
        self._resources: dict[str, MockResource] = {}
        self._prompts: dict[str, dict] = {}
        
        # Request tracking for observability tests
        self._request_count = 0
        self._error_count = 0
        self._requests: list[dict] = []
        
        # Capabilities
        self._capabilities = {
            "tools": {},
            "resources": {},
            "prompts": {},
            "logging": {},
            "completion": {},
        }
        
    def set_behavior(
        self,
        behavior: ServerBehavior,
        fault_rate: float = 0.0,
        delay_ms: int = 0,
    ):
        """Configure server behavior for resilience testing.
        
        Args:
            behavior: Server behavior mode
            fault_rate: Probability of failure (0.0-1.0) for FLAKY mode
            delay_ms: Response delay in milliseconds for SLOW mode
        """
        self._behavior = behavior
        self._fault_rate = max(0.0, min(1.0, fault_rate))
        self._delay_ms = max(0, delay_ms)
    
    # =========================================================================
    # Entity Registration
    # =========================================================================
    
    def add_tool(self, tool: MockTool):
        """Register a tool with the server."""
        self._tools[tool.name] = tool
        self._capabilities["tools"]["listChanged"] = True
    
    def add_resource(self, resource: MockResource):
        """Register a resource with the server."""
        self._resources[resource.uri] = resource
        self._capabilities["resources"]["listChanged"] = True
        self._capabilities["resources"]["subscribe"] = True
    
    def add_prompt(self, name: str, description: str, arguments: list | None = None):
        """Register a prompt template."""
        self._prompts[name] = {
            "name": name,
            "description": description,
            "arguments": arguments or [],
        }
        self._capabilities["prompts"]["listChanged"] = True
    
    # =========================================================================
    # Request Handling
    # =========================================================================
    
    async def handle_request(self, request: MCPMessage) -> MCPMessage:
        """Handle an incoming MCP request.
        
        This is the main entry point for gateway-to-upstream communication.
        Applies behavior simulation (delays, faults) before processing.
        
        Args:
            request: Incoming MCP message
            
        Returns:
            MCP response message
        """
        self._request_count += 1
        
        # Record request for observability
        self._requests.append({
            "timestamp": time.time(),
            "method": request.method,
            "id": request.id,
        })
        
        # Apply behavior simulation
        if self._behavior == ServerBehavior.TIMEOUT:
            # Never respond - caller must timeout
            await asyncio.sleep(3600)
            return self._create_error(
                request.id,
                MCPErrorCode.INTERNAL_ERROR,
                "Server timeout",
            )
        
        if self._behavior == ServerBehavior.SLOW or self._delay_ms > 0:
            await asyncio.sleep(self._delay_ms / 1000.0)
        
        if self._behavior == ServerBehavior.FLAKY:
            if random.random() < self._fault_rate:
                self._error_count += 1
                return self._create_error(
                    request.id,
                    MCPErrorCode.SERVER_ERROR,
                    "Flaky server simulated failure",
                )
        
        if self._behavior == ServerBehavior.ERROR:
            self._error_count += 1
            return self._create_error(
                request.id,
                MCPErrorCode.SERVER_ERROR,
                "Server in error mode",
            )
        
        if self._behavior == ServerBehavior.GARBAGE:
            # Return invalid response
            return MCPMessage(
                id=request.id,
                result="not valid json { garbage data",
            )
        
        # Normal processing
        return await self._process_request(request)
    
    async def _process_request(self, request: MCPMessage) -> MCPMessage:
        """Process a request based on method."""
        method = request.method
        params = request.params or {}
        
        handlers = {
            "initialize": self._handle_initialize,
            "ping": self._handle_ping,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
            "prompts/list": self._handle_prompts_list,
            "prompts/get": self._handle_prompts_get,
            "logging/setLevel": self._handle_set_level,
        }
        
        handler = handlers.get(method)
        if handler is None:
            return self._create_error(
                request.id,
                MCPErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {method}",
            )
        
        try:
            result = await handler(params)
            return MCPMessage(id=request.id, result=result)
        except Exception as e:
            self._error_count += 1
            return self._create_error(
                request.id,
                MCPErrorCode.INTERNAL_ERROR,
                repr(e),
            )
    
    # =========================================================================
    # Method Handlers
    # =========================================================================
    
    async def _handle_initialize(self, params: dict) -> dict:
        """Handle initialize request."""
        client_version = params.get("protocolVersion", "2024-11-05")
        
        # Negotiate version
        if client_version not in ["2024-11-05"]:
            raise ValueError(f"Unsupported protocol version: {client_version}")
        
        return MockMCPServer__handle_initializeResult.model_validate({
            "protocolVersion": self.protocol_version,
            "capabilities": self._capabilities,
            "serverInfo": {
                "name": self.name,
                "version": "1.0.0",
            },
        })


    
    async def _handle_ping(self, params: dict) -> dict:
        """Handle ping request."""
        return MockMCPServer__handle_pingResult.model_validate({})  # Empty result per spec
    
    async def _handle_tools_list(self, params: dict) -> dict:
        """Handle tools/list request."""
        tools = [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
            }
            for t in self._tools.values()
        ]
        
        result = {"tools": tools}
        
        # Add pagination if cursor provided
        cursor = params.get("cursor")
        if cursor:
            result["nextCursor"] = None  # No more pages in mock
        
        return result
    
    async def _handle_tools_call(self, params: dict) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")
        
        if tool.should_fail:
            return MockMCPServer__handle_tools_callResult.model_validate({
                "content": [
                    {
                        "type": "text",
                        "text": tool.failure_message,
                    }
                ],
                "isError": True,
            })


        
        # Execute tool handler
        result = tool.handler(arguments)
        
        return MockMCPServer__handle_tools_callResult.model_validate({
            "content": [
                {
                    "type": "text",
                    "text": str(result),
                }
            ],
            "isError": False,
        })


    
    async def _handle_resources_list(self, params: dict) -> dict:
        """Handle resources/list request."""
        resources = [
            {
                "uri": r.uri,
                "name": r.name,
                "mimeType": r.mime_type,
            }
            for r in self._resources.values()
        ]
        
        return MockMCPServer__handle_resources_listResult.model_validate({"resources": resources})
    
    async def _handle_resources_read(self, params: dict) -> dict:
        """Handle resources/read request."""
        uri = params.get("uri")
        resource = self._resources.get(uri)
        
        if resource is None:
            raise ValueError(f"Resource not found: {uri}")
        
        content = resource.handler() if resource.handler else resource.content
        
        if isinstance(content, bytes):
            import base64
            text = None
            blob = base64.b64encode(content).decode()
        else:
            text = str(content)
            blob = None
        
        return MockMCPServer__handle_resources_readResult.model_validate({
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource.mime_type,
                    "text": text,
                    "blob": blob,
                }
            ]
        })


    
    async def _handle_prompts_list(self, params: dict) -> dict:
        """Handle prompts/list request."""
        prompts = [
            {
                "name": p["name"],
                "description": p["description"],
                "arguments": p.get("arguments", []),
            }
            for p in self._prompts.values()
        ]
        
        return MockMCPServer__handle_prompts_listResult.model_validate({"prompts": prompts})
    
    async def _handle_prompts_get(self, params: dict) -> dict:
        """Handle prompts/get request."""
        name = params.get("name")
        prompt = self._prompts.get(name)
        
        if prompt is None:
            raise ValueError(f"Prompt not found: {name}")
        
        return MockMCPServer__handle_prompts_getResult.model_validate({
            "description": prompt["description"],
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Prompt: {name}",
                    }
                }
            ]
        })


    
    async def _handle_set_level(self, params: dict) -> dict:
        """Handle logging/setLevel request."""
        level = params.get("level", "info")
        # In real implementation, would set log level
        return MockMCPServer__handle_set_levelResult.model_validate({})
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _create_error(
        self,
        id: str | int | None,
        code: MCPErrorCode | int,
        message: str,
    ) -> MCPMessage:
        """Create an error response."""
        if isinstance(code, MCPErrorCode):
            code = code.value
        
        return MCPMessage(
            id=id,
            error={
                "code": code,
                "message": message,
            },
        )
    
    @property
    def request_count(self) -> int:
        """Total requests received."""
        return self._request_count
    
    @property
    def error_count(self) -> int:
        """Total errors generated."""
        return self._error_count
    
    @property
    def error_rate(self) -> float:
        """Error rate (0.0-1.0)."""
        if self._request_count == 0:
            return 0.0
        return self._error_count / self._request_count
    
    def get_requests(self, method: str | None = None) -> list[dict]:
        """Get recorded requests, optionally filtered by method."""
        if method is None:
            return self._requests.copy()
        return [r for r in self._requests if r["method"] == method]
    
    def reset_stats(self):
        """Reset request/error counters."""
        self._request_count = 0
        self._error_count = 0
        self._requests.clear()
