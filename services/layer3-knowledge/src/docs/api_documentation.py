"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Comprehensive API documentation with interactive examples and developer guides.
"""

from typing import Any

from pydantic import BaseModel, Field


class APIExample(BaseModel):
    """API example with request/response."""

    title: str = Field(..., description="Example title")
    description: str = Field(..., description="Example description")
    request: dict[str, Any] = Field(..., description="Request body/parameters")
    response: dict[str, Any] = Field(..., description="Expected response")
    headers: dict[str, str] | None = Field(None, description="Required headers")
    curl_command: str | None = Field(None, description="cURL command")
    python_code: str | None = Field(None, description="Python code example")
    javascript_code: str | None = Field(None, description="JavaScript code example")


class APITutorial(BaseModel):
    """Step-by-step API tutorial."""

    title: str = Field(..., description="Tutorial title")
    description: str = Field(..., description="Tutorial description")
    difficulty: str = Field(
        ..., description="Difficulty level (beginner, intermediate, advanced)"
    )
    estimated_time: str = Field(..., description="Estimated completion time")
    steps: list[dict[str, Any]] = Field(..., description="Tutorial steps")
    examples: list[APIExample] = Field(..., description="Related examples")
    prerequisites: list[str] = Field(default_factory=list, description="Prerequisites")


class APIError(BaseModel):
    """API error documentation."""

    status_code: int = Field(..., description="HTTP status code")
    error_code: str = Field(..., description="Application error code")
    message: str = Field(..., description="Error message")
    description: str = Field(..., description="Detailed description")
    causes: list[str] = Field(default_factory=list, description="Common causes")
    solutions: list[str] = Field(default_factory=list, description="Solutions")
    example_response: dict[str, Any] = Field(..., description="Example error response")


class APIEndpoint(BaseModel):
    """Comprehensive API endpoint documentation."""

    path: str = Field(..., description="Endpoint path")
    method: str = Field(..., description="HTTP method")
    title: str = Field(..., description="Endpoint title")
    description: str = Field(..., description="Detailed description")
    summary: str = Field(..., description="Brief summary")
    tags: list[str] = Field(..., description="Endpoint tags")
    parameters: list[dict[str, Any]] = Field(
        default_factory=list, description="Parameters"
    )
    request_body: dict[str, Any] | None = Field(None, description="Request body schema")
    responses: dict[int, dict[str, Any]] = Field(..., description="Response schemas")
    examples: list[APIExample] = Field(
        default_factory=list, description="Usage examples"
    )
    errors: list[APIError] = Field(default_factory=list, description="Possible errors")
    rate_limiting: dict[str, Any] | None = Field(None, description="Rate limiting info")
    authentication: dict[str, Any] | None = Field(
        None, description="Authentication requirements"
    )
    version_info: dict[str, Any] | None = Field(None, description="Version information")


class APIGuide(BaseModel):
    """Developer guide section."""

    title: str = Field(..., description="Guide title")
    content: str = Field(..., description="Guide content (Markdown)")
    sections: list[dict[str, Any]] = Field(
        default_factory=list, description="Guide sections"
    )
    code_examples: list[dict[str, Any]] = Field(
        default_factory=list, description="Code examples"
    )
    related_endpoints: list[str] = Field(
        default_factory=list, description="Related endpoints"
    )


# Comprehensive API documentation
API_DOCUMENTATION = {
    "overview": {
        "title": "Value Fabric Layer 3 API",
        "description": """
        The Value Fabric Layer 3 API provides intelligent semantic search, graph-based question answering,
        and knowledge graph management capabilities. This API serves as the semantic layer of the Value Fabric,
        enabling advanced knowledge discovery and analysis.
        
        ## Key Features
        
        - **Semantic Search**: Hybrid search combining vector similarity, keyword matching, and graph traversal
        - **Graph-based Question Answering**: Natural language queries with graph context
        - **Knowledge Graph Management**: RDF data ingestion and schema management
        - **Analytics & Insights**: Graph analytics and similarity analysis
        - **Real-time Monitoring**: Health checks, metrics, and performance monitoring
        
        ## Architecture
        
        The Layer 3 API is built on:
        - **Neo4j**: Graph database for knowledge storage and native vector indexes for semantic search
        - **FastAPI**: Modern Python web framework
        - **Redis**: Caching and session management
        - **Prometheus**: Metrics collection
        
        ## Getting Started
        
        1. **Authentication**: Obtain an API key from the admin panel
        2. **Base URL**: `https://api.valuefabric.ai/v1`
        3. **Authentication**: Include API key in `Authorization: Bearer <key>` header
        4. **First Request**: Try the health check endpoint to verify connectivity
        """,
        "version": "1.0.0",
        "base_url": "https://api.valuefabric.ai/v1",
        "contact": {
            "name": "Value Fabric Team",
            "email": "api-support@valuefabric.ai",
            "url": "https://valuefabric.ai/support",
        },
        "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    },
    "authentication": {
        "title": "Authentication & Authorization",
        "content": """
        ## API Key Authentication
        
        All API requests must include an API key for authentication. API keys are role-based and provide
        different levels of access to the API.
        
        ### Getting an API Key
        
        1. Contact your Value Fabric administrator
        2. Specify your use case and required permissions
        3. Receive your API key (shown only once)
        4. Store your API key securely
        
        ### Using API Keys
        
        Include the API key in one of these ways:
        
        **Bearer Token (Recommended):**
        ```http
        Authorization: Bearer your_api_key_here
        ```
        
        **Custom Header:**
        ```http
        X-API-Key: your_api_key_here
        ```
        
        **Query Parameter (Not Recommended):**
        ```http
        ?api_key=your_api_key_here
        ```
        
        ## Roles and Permissions
        
        ### Read Only Role
        - View health status and metrics
        - Perform search queries
        - Access GraphRAG functionality
        - View schema information
        
        ### Analyst Role
        - All Read Only permissions
        - Run analytics operations
        - Access ingestion status
        - Export data
        
        ### Developer Role
        - All Analyst permissions
        - Ingest RDF data
        - Modify schema (limited)
        - Full API access
        
        ### Admin Role
        - All Developer permissions
        - Manage API keys
        - User management
        - System administration
        
        ## Rate Limiting
        
        API keys have rate limits to ensure fair usage:
        - **Default**: 100 requests per minute
        - **Burst**: 200 requests in short bursts
        - **Custom limits**: Available for enterprise plans
        
        Rate limit headers are included in responses:
        ```http
        X-RateLimit-Limit: 100
        X-RateLimit-Remaining: 95
        X-RateLimit-Reset: 1640995200
        ```
        """,
    },
    "endpoints": {
        "health": APIEndpoint(
            path="/health",
            method="GET",
            title="Health Check",
            description="Check the health status of the API and its dependencies",
            summary="Basic health check for monitoring systems",
            tags=["Health", "Monitoring"],
            parameters=[],
            request_body=None,
            responses={
                200: {
                    "description": "Service is healthy",
                    "content": {
                        "application/json": {
                            "example": {
                                "status": "healthy",
                                "version": "1.0.0",
                                "timestamp": "2024-01-01T12:00:00.000Z",
                                "uptime_seconds": 3600.0,
                                "dependencies": [
                                    {
                                        "name": "neo4j",
                                        "status": "healthy",
                                        "response_time_ms": 15.5,
                                        "error": None,
                                        "details": {
                                            "uri": "bolt://localhost:7687",
                                            "database": "neo4j",
                                        },
                                    }
                                ],
                                "metrics": {
                                    "uptime_seconds": 3600.0,
                                    "memory_usage_mb": 1024.5,
                                    "cpu_percent": 25.0,
                                    "active_connections": 10,
                                    "total_requests": 1500,
                                    "error_rate_percent": 0.1,
                                },
                                "neo4j": {
                                    "status": "healthy",
                                    "database": "neo4j",
                                    "uri": "bolt://localhost:7687",
                                },
                                "schema_status": {
                                    "constraints": {
                                        "expected": 10,
                                        "found": 10,
                                        "missing": [],
                                    },
                                    "indexes": {
                                        "expected": 15,
                                        "found": 15,
                                        "missing": [],
                                    },
                                    "valid": True,
                                },
                            }
                        }
                    },
                }
            },
            examples=[
                APIExample(
                    title="Basic Health Check",
                    description="Check if the API is running and healthy",
                    request={},
                    response={
                        "status": "healthy",
                        "version": "1.0.0",
                        "timestamp": "2024-01-01T12:00:00.000Z",
                        "uptime_seconds": 3600.0,
                        "dependencies": [],
                        "metrics": {
                            "uptime_seconds": 3600.0,
                            "memory_usage_mb": 1024.5,
                            "cpu_percent": 25.0,
                            "active_connections": 10,
                            "total_requests": 1500,
                            "error_rate_percent": 0.1,
                        },
                        "neo4j": {
                            "status": "healthy",
                            "database": "neo4j",
                            "uri": "bolt://localhost:7687",
                        },
                        "schema_status": {
                            "constraints": {"expected": 10, "found": 10, "missing": []},
                            "indexes": {"expected": 15, "found": 15, "missing": []},
                            "valid": True,
                        },
                    },
                    curl_command='curl -X GET "https://api.valuefabric.ai/v1/health" -H "Authorization: Bearer your_api_key"',
                    python_code="""
import requests

headers = {"Authorization": "Bearer your_api_key"}
response = requests.get("https://api.valuefabric.ai/v1/health", headers=headers)
print(response.json())
                    """,
                    javascript_code="""
const response = await fetch('https://api.valuefabric.ai/v1/health', {
  headers: {
    'Authorization': 'Bearer your_api_key'
  }
});
const data = await response.json();
console.log(data);
                    """,
                )
            ],
            errors=[
                APIError(
                    status_code=503,
                    error_code="SERVICE_UNAVAILABLE",
                    message="Service temporarily unavailable",
                    description="The API or one of its dependencies is currently unavailable",
                    causes=[
                        "Database connection failed",
                        "High system load",
                        "Maintenance mode",
                    ],
                    solutions=[
                        "Try again later",
                        "Check status page",
                        "Contact support",
                    ],
                    example_response={
                        "error": "SERVICE_UNAVAILABLE",
                        "message": "Neo4j database connection failed",
                        "details": {"service": "neo4j", "error": "Connection timeout"},
                    },
                )
            ],
            rate_limiting={
                "requests_per_minute": 60,
                "burst_size": 120,
                "per_api_key": True,
            },
            authentication={
                "required": False,
                "roles": ["read_only", "analyst", "developer", "admin", "system"],
            },
        ),
        "search": APIEndpoint(
            path="/v1/search",
            method="POST",
            title="Semantic Search",
            description="Perform semantic search across the knowledge graph using hybrid search algorithms",
            summary="Hybrid vector, keyword, and graph search",
            tags=["Search", "Discovery"],
            parameters=[
                {
                    "name": "query",
                    "in": "body",
                    "required": True,
                    "schema": {"type": "string", "minLength": 1, "maxLength": 500},
                    "description": "Search query string",
                },
                {
                    "name": "search_type",
                    "in": "body",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "enum": ["hybrid", "vector", "fulltext", "graph"],
                        "default": "hybrid",
                    },
                    "description": "Search algorithm to use",
                },
                {
                    "name": "top_k",
                    "in": "body",
                    "required": False,
                    "schema": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    },
                    "description": "Number of results to return",
                },
                {
                    "name": "entity_type",
                    "in": "body",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "enum": [
                            "Capability",
                            "UseCase",
                            "Persona",
                            "ValueDriver",
                            "DataSource",
                            "ExtractionEvent",
                        ],
                    },
                    "description": "Filter by entity type",
                },
            ],
            request_body={
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["query"],
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": 500,
                                },
                                "search_type": {
                                    "type": "string",
                                    "enum": ["hybrid", "vector", "fulltext", "graph"],
                                    "default": "hybrid",
                                },
                                "top_k": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 50,
                                    "default": 10,
                                },
                                "entity_type": {
                                    "type": "string",
                                    "enum": [
                                        "Capability",
                                        "UseCase",
                                        "Persona",
                                        "ValueDriver",
                                        "DataSource",
                                        "ExtractionEvent",
                                    ],
                                },
                                "weights": {
                                    "type": "object",
                                    "properties": {
                                        "bm25": {
                                            "type": "number",
                                            "minimum": 0,
                                            "maximum": 1,
                                        },
                                        "vector": {
                                            "type": "number",
                                            "minimum": 0,
                                            "maximum": 1,
                                        },
                                        "graph": {
                                            "type": "number",
                                            "minimum": 0,
                                            "maximum": 1,
                                        },
                                    },
                                },
                                "filters": {
                                    "type": "object",
                                    "additionalProperties": True,
                                },
                            },
                        }
                    }
                },
            },
            responses={
                200: {
                    "description": "Search results",
                    "content": {
                        "application/json": {
                            "example": {
                                "query": "automated invoice processing",
                                "results": [
                                    {
                                        "entity_id": "capability_123",
                                        "entity_type": "Capability",
                                        "name": "Automated Invoice Processing",
                                        "bm25_score": 0.8,
                                        "vector_score": 0.9,
                                        "graph_score": 0.7,
                                        "combined_score": 0.8,
                                        "metadata": {
                                            "description": "Processes invoices automatically",
                                            "domain": "finance",
                                        },
                                        "confidence": 0.85,
                                    }
                                ],
                                "total_results": 1,
                                "search_type": "hybrid",
                                "processing_time_ms": 150.5,
                            }
                        }
                    },
                }
            },
            examples=[
                APIExample(
                    title="Basic Semantic Search",
                    description="Search for capabilities related to invoice processing",
                    request={
                        "query": "automated invoice processing",
                        "search_type": "hybrid",
                        "top_k": 5,
                    },
                    response={
                        "query": "automated invoice processing",
                        "results": [
                            {
                                "entity_id": "capability_123",
                                "entity_type": "Capability",
                                "name": "Automated Invoice Processing",
                                "bm25_score": 0.8,
                                "vector_score": 0.9,
                                "graph_score": 0.7,
                                "combined_score": 0.8,
                                "metadata": {
                                    "description": "Processes invoices automatically",
                                    "domain": "finance",
                                },
                                "confidence": 0.85,
                            }
                        ],
                        "total_results": 1,
                        "search_type": "hybrid",
                        "processing_time_ms": 150.5,
                    },
                    curl_command="""curl -X POST "https://api.valuefabric.ai/v1/search" \\
  -H "Authorization: Bearer your_api_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "automated invoice processing",
    "search_type": "hybrid",
    "top_k": 5
  }'
""",
                    python_code="""
import requests

headers = {
    "Authorization": "Bearer your_api_key",
    "Content-Type": "application/json"
}

data = {
    "query": "automated invoice processing",
    "search_type": "hybrid",
    "top_k": 5
}

response = requests.post(
    "https://api.valuefabric.ai/v1/search",
    headers=headers,
    json=data
)
print(response.json())
""",
                    javascript_code="""
const response = await fetch('https://api.valuefabric.ai/v1/search', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer your_api_key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'automated invoice processing',
    search_type: 'hybrid',
    top_k: 5
  })
});
const data = await response.json();
console.log(data);
                    """,
                ),
                APIExample(
                    title="Filtered Search by Entity Type",
                    description="Search only for UseCase entities",
                    request={
                        "query": "customer onboarding",
                        "entity_type": "UseCase",
                        "top_k": 10,
                    },
                    response={
                        "query": "customer onboarding",
                        "results": [
                            {
                                "entity_id": "usecase_456",
                                "entity_type": "UseCase",
                                "name": "Customer Onboarding Automation",
                                "bm25_score": 0.9,
                                "vector_score": 0.85,
                                "graph_score": 0.8,
                                "combined_score": 0.85,
                                "metadata": {
                                    "description": "Automates customer onboarding process",
                                    "industry": "banking",
                                },
                                "confidence": 0.9,
                            }
                        ],
                        "total_results": 1,
                        "search_type": "hybrid",
                        "processing_time_ms": 120.0,
                    },
                ),
            ],
            errors=[
                APIError(
                    status_code=400,
                    error_code="VALIDATION_ERROR",
                    message="Invalid search parameters",
                    description="The search request contains invalid parameters",
                    causes=[
                        "Empty query",
                        "Invalid search type",
                        "Invalid top_k value",
                    ],
                    solutions=[
                        "Provide a non-empty query",
                        "Use valid search type",
                        "Use top_k between 1-50",
                    ],
                    example_response={
                        "error": "VALIDATION_ERROR",
                        "message": "Query cannot be empty",
                        "details": {"field": "query", "validation_rule": "minLength=1"},
                    },
                ),
                APIError(
                    status_code=429,
                    error_code="RATE_LIMIT_ERROR",
                    message="Rate limit exceeded",
                    description="Too many requests, please try again later",
                    causes=["High request volume", "Insufficient rate limit"],
                    solutions=["Wait and retry", "Upgrade plan", "Use caching"],
                    example_response={
                        "error": "RATE_LIMIT_ERROR",
                        "message": "Rate limit exceeded",
                        "details": {
                            "limit": 100,
                            "window_seconds": 60,
                            "retry_after": 30,
                        },
                    },
                ),
            ],
            rate_limiting={
                "requests_per_minute": 100,
                "burst_size": 200,
                "per_api_key": True,
            },
            authentication={
                "required": True,
                "roles": ["read_only", "analyst", "developer", "admin", "system"],
            },
        ),
    },
    "tutorials": [
        APITutorial(
            title="Getting Started with Semantic Search",
            description="Learn how to perform semantic searches across the knowledge graph",
            difficulty="beginner",
            estimated_time="15 minutes",
            steps=[
                {
                    "step": 1,
                    "title": "Set up authentication",
                    "description": "Configure your API key and make your first authenticated request",
                    "code": """import requests

# Configure API key
API_KEY = "your_api_key_here"
BASE_URL = "https://api.valuefabric.ai/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Test authentication with health check
response = requests.get(f"{BASE_URL}/health", headers=headers)
print("Health check:", response.json())""",
                },
                {
                    "step": 2,
                    "title": "Perform basic search",
                    "description": "Make your first semantic search query",
                    "code": """# Basic semantic search
search_data = {
    "query": "automated invoice processing",
    "search_type": "hybrid",
    "top_k": 5
}

response = requests.post(
    f"{BASE_URL}/search",
    headers=headers,
    json=search_data
)

results = response.json()
print(f"Found {results['total_results']} results")
for result in results['results']:
    print(f"- {result['name']} (confidence: {result['confidence']:.2f})")""",
                },
                {
                    "step": 3,
                    "title": "Explore search options",
                    "description": "Try different search types and filters",
                    "code": """# Try different search types
search_types = ["hybrid", "vector", "fulltext", "graph"]

for search_type in search_types:
    search_data = {
        "query": "customer analytics",
        "search_type": search_type,
        "top_k": 3
    }
    
    response = requests.post(
        f"{BASE_URL}/search",
        headers=headers,
        json=search_data
    )
    
    results = response.json()
    print(f"{search_type.upper()} search: {results['total_results']} results")""",
                },
            ],
            examples=[
                APIExample(
                    title="Complete Search Workflow",
                    description="End-to-end search example",
                    request={
                        "query": "financial automation",
                        "search_type": "hybrid",
                        "entity_type": "Capability",
                        "top_k": 10,
                        "weights": {"bm25": 0.3, "vector": 0.5, "graph": 0.2},
                    },
                    response={
                        "query": "financial automation",
                        "results": [],
                        "total_results": 0,
                        "search_type": "hybrid",
                        "processing_time_ms": 45.2,
                    },
                )
            ],
            prerequisites=["Basic Python knowledge", "API key", "HTTP client library"],
        ),
        APITutorial(
            title="Graph-based Question Answering",
            description="Learn how to use GraphRAG for natural language queries",
            difficulty="intermediate",
            estimated_time="30 minutes",
            steps=[
                {
                    "step": 1,
                    "title": "Understand GraphRAG",
                    "description": "Learn how GraphRAG combines graph traversal with language models",
                    "code": """# GraphRAG queries use natural language
# The system finds relevant graph context and generates answers

query = "What capabilities enable real-time financial reporting?"
print("This query will:")
print("1. Find entities related to 'real-time financial reporting'")
print("2. Traverse the graph to find connected capabilities")
print("3. Generate a natural language answer with context")""",
                },
                {
                    "step": 2,
                    "title": "Make GraphRAG queries",
                    "description": "Send natural language questions to the GraphRAG endpoint",
                    "code": """# GraphRAG query
graphrag_data = {
    "query": "What capabilities enable automated invoice processing?",
    "max_hops": 3,
    "max_results": 10,
    "confidence_threshold": 0.7
}

response = requests.post(
    f"{BASE_URL}/v1/graphrag",
    headers=headers,
    json=graphrag_data
)

result = response.json()
print("Answer:", result.get("answer", "No answer generated"))
print("Confidence:", result.get("confidence_score", 0))
print("Entities found:", len(result.get("entities", [])))""",
                },
                {
                    "step": 3,
                    "title": "Analyze results",
                    "description": "Understand the GraphRAG response structure",
                    "code": """# Analyze GraphRAG results
result = response.json()

# Check entities and relationships
print("Entities:")
for entity in result.get("entities", []):
    print(f"  - {entity.get('name')} ({entity.get('type')})")

print("\\nRelationships:")
for rel in result.get("relationships", []):
    print(f"  - {rel.get('source')} -> {rel.get('target')} ({rel.get('type')})")

# Check context graph
context = result.get("context_graph", {})
print(f"Context: {context.get('nodes', 0)} nodes, {context.get('edges', 0)} edges")""",
                },
            ],
            examples=[
                APIExample(
                    title="Complex GraphRAG Query",
                    description="Ask about complex relationships",
                    request={
                        "query": "How do data sources support regulatory compliance capabilities?",
                        "max_hops": 4,
                        "max_results": 15,
                        "confidence_threshold": 0.8,
                        "entity_type": "Capability",
                    },
                    response={
                        "query": "How do data sources support regulatory compliance capabilities?",
                        "entities": [
                            {
                                "id": "datasource_1",
                                "type": "DataSource",
                                "name": "Regulatory Data Feed",
                                "properties": {
                                    "type": "real-time",
                                    "compliance": "SOX",
                                },
                            }
                        ],
                        "relationships": [
                            {
                                "source": "datasource_1",
                                "target": "capability_1",
                                "type": "enables",
                            }
                        ],
                        "context_graph": {"nodes": 2, "edges": 1},
                        "confidence_score": 0.85,
                        "sources": ["datasource_1", "capability_1"],
                        "processing_time_ms": 250.0,
                        "answer": "Regulatory data feeds enable compliance capabilities by providing real-time monitoring and audit trails.",
                    },
                )
            ],
            prerequisites=[
                "Completed semantic search tutorial",
                "Basic graph concepts",
                "API key",
            ],
        ),
    ],
    "guides": [
        APIGuide(
            title="Best Practices",
            content="""
            # API Best Practices
            
            ## Performance Optimization
            
            ### 1. Use Appropriate Search Types
            - **Hybrid**: Best for general semantic search
            - **Vector**: Best for similarity-based search
            - **Fulltext**: Best for keyword matching
            - **Graph**: Best for relationship-based queries
            
            ### 2. Optimize Query Parameters
            - Use realistic `top_k` values (5-20 is usually sufficient)
            - Filter by `entity_type` when possible
            - Adjust search weights for your specific use case
            
            ### 3. Handle Rate Limits
            - Implement exponential backoff for retries
            - Cache frequently requested results
            - Use batch operations when available
            
            ## Error Handling
            
            ### 1. HTTP Status Codes
            - `200`: Success
            - `400`: Bad request (validation error)
            - `401`: Authentication failed
            - `403`: Insufficient permissions
            - `429`: Rate limit exceeded
            - `500`: Internal server error
            - `503`: Service unavailable
            
            ### 2. Error Response Format
            ```json
            {
              "error": "ERROR_CODE",
              "message": "Human-readable error message",
              "details": {
                "field": "query",
                "validation_rule": "minLength=1"
              }
            }
            ```
            
            ### 3. Retry Strategy
            ```python
            import time
            import requests
            
            def api_call_with_retry(url, headers, data, max_retries=3):
                for attempt in range(max_retries + 1):
                    try:
                        response = requests.post(url, headers=headers, json=data)
                        if response.status_code == 429:
                            # Rate limited - wait and retry
                            retry_after = int(response.headers.get('Retry-After', 5))
                            time.sleep(retry_after)
                            continue
                        response.raise_for_status()
                        return response.json()
                    except requests.exceptions.RequestException as e:
                        if attempt == max_retries:
                            raise
                        time.sleep(2 ** attempt)  # Exponential backoff
            ```
            
            ## Security Best Practices
            
            ### 1. API Key Management
            - Store API keys securely (environment variables, secret managers)
            - Never commit API keys to version control
            - Use different keys for different environments
            - Rotate API keys regularly
            
            ### 2. Request Validation
            - Always validate user input before sending to API
            - Use parameterized queries to prevent injection
            - Implement client-side validation for better UX
            
            ### 3. HTTPS Only
            - Always use HTTPS in production
            - Verify SSL certificates
            - Never send API keys over HTTP
            
            ## Monitoring and Debugging
            
            ### 1. Use Request Headers
            - Include `X-Request-ID` for tracing
            - Check `X-RateLimit-*` headers for rate limiting
            - Monitor `X-API-Version` for version changes
            
            ### 2. Logging
            - Log API requests and responses (without sensitive data)
            - Include request IDs for debugging
            - Monitor error rates and response times
            
            ### 3. Health Checks
            - Monitor `/health` endpoint for service status
            - Set up alerts for service degradation
            - Use `/metrics` endpoint for detailed monitoring
            """,
            sections=[
                {
                    "title": "Performance",
                    "content": "Optimize API performance with proper query design",
                },
                {
                    "title": "Error Handling",
                    "content": "Implement robust error handling and retry logic",
                },
                {
                    "title": "Security",
                    "content": "Secure API key management and request validation",
                },
                {
                    "title": "Monitoring",
                    "content": "Monitor API health and performance metrics",
                },
            ],
            code_examples=[
                {
                    "title": "Retry Logic",
                    "language": "python",
                    "code": """def api_call_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 5))
                time.sleep(retry_after)
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                raise
            time.sleep(2 ** attempt)""",
                }
            ],
            related_endpoints=["/health", "/v1/search", "/v1/graphrag"],
        ),
        APIGuide(
            title="Data Ingestion",
            content="""
            # Data Ingestion Guide
            
            ## Overview
            
            The Layer 3 API supports ingestion of RDF/Turtle data from Layer 2. This guide covers how to format,
            validate, and ingest knowledge graph data.
            
            ## RDF Data Format
            
            ### Basic Structure
            RDF data should be in Turtle format (.ttl):
            ```turtle
            @prefix ex: <http://example.com/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            
            ex:capability1 rdf:type ex:Capability ;
                ex:name "Automated Invoice Processing" ;
                ex:description "Processes invoices automatically" ;
                rdfs:label "Invoice Automation" .
            ```
            
            ### Supported Entity Types
            - **Capability**: Business capabilities and functions
            - **UseCase**: Specific use cases and scenarios
            - **Persona**: User roles and stakeholders
            - **ValueDriver**: Business value drivers
            - **DataSource**: Data sources and systems
            - **ExtractionEvent**: Data extraction events
            
            ### Supported Relationships
            - **enables**: Capability enables use case
            - **requires**: Use case requires capability
            - **supports**: Data source supports capability
            - **involves**: Persona involved in use case
            - **drives**: Value driver drives use case
            
            ## Ingestion Process
            
            ### 1. Prepare RDF Data
            Ensure your RDF data follows the Value Fabric schema:
            ```turtle
            @prefix vf: <http://valuefabric.ai/ontology/> .
            
            vf:capability1 rdf:type vf:Capability ;
                vf:name "Customer Analytics" ;
                vf:description "Analyzes customer behavior patterns" .
            
            vf:usecase1 rdf:type vf:UseCase ;
                vf:name "Customer Segmentation" ;
                vf:enables vf:capability1 .
            ```
            
            ### 2. Create Ingestion Request
            ```python
            import requests
            
            headers = {
                "Authorization": "Bearer your_api_key",
                "Content-Type": "application/json"
            }
            
            data = {
                "rdf_data": rdf_content,
                "source_id": "document_123",
                "extraction_job_id": "job_456",
                "content_hash": "abc123def456"
            }
            
            response = requests.post(
                "https://api.valuefabric.ai/v1/ingest",
                headers=headers,
                json=data
            )
            ```
            
            ### 3. Monitor Ingestion Status
            ```python
            # Check ingestion status
            response = requests.get(
                f"https://api.valuefabric.ai/v1/sync/{source_id}",
                headers=headers
            )
            
            status = response.json()
            print(f"Status: {status['status']}")
            print(f"Synced at: {status['synced_at']}")
            ```
            
            ## Best Practices
            
            ### 1. Data Validation
            - Validate RDF syntax before ingestion
            - Check for required predicates
            - Ensure proper entity types
            
            ### 2. Batch Processing
            - Ingest data in reasonable batches (1000-5000 triples)
            - Use content hashes for change detection
            - Handle partial failures gracefully
            
            ### 3. Error Handling
            - Monitor for validation errors
            - Implement retry logic for transient failures
            - Log ingestion metrics
            
            ## Common Issues
            
            ### RDF Syntax Errors
            ```turtle
            # Invalid - missing semicolon
            ex:entity1 rdf:type ex:Type
            ex:entity2 rdf:type ex:Type .
            
            # Valid
            ex:entity1 rdf:type ex:Type ;
            ex:entity2 rdf:type ex:Type .
            ```
            
            ### Missing Predicates
            ```turtle
            # Invalid - missing required name
            ex:capability1 rdf:type ex:Capability .
            
            # Valid
            ex:capability1 rdf:type ex:Capability ;
                ex:name "Capability Name" .
            ```
            
            ### Type Mismatches
            ```turtle
            # Invalid - wrong entity type
            ex:entity1 rdf:type ex:InvalidType .
            
            # Valid
            ex:entity1 rdf:type ex:Capability .
            ```
            """,
            sections=[
                {
                    "title": "RDF Format",
                    "content": "Understanding RDF/Turtle syntax and structure",
                },
                {"title": "Ingestion API", "content": "Using the ingestion endpoints"},
                {
                    "title": "Best Practices",
                    "content": "Tips for successful data ingestion",
                },
                {"title": "Troubleshooting", "content": "Common issues and solutions"},
            ],
            code_examples=[
                {
                    "title": "RDF Data Example",
                    "language": "turtle",
                    "code": """@prefix vf: <http://valuefabric.ai/ontology/> .

vf:capability1 rdf:type vf:Capability ;
    vf:name "Customer Analytics" ;
    vf:description "Analyzes customer behavior patterns" ;
    vf:domain "retail" .

vf:usecase1 rdf:type vf:UseCase ;
    vf:name "Customer Segmentation" ;
    vf:description "Segments customers based on behavior" ;
    vf:enables vf:capability1 .""",
                },
                {
                    "title": "Ingestion Request",
                    "language": "python",
                    "code": """import requests

def ingest_rdf_data(rdf_content, source_id, job_id):
    headers = {
        "Authorization": "Bearer your_api_key",
        "Content-Type": "application/json"
    }
    
    data = {
        "rdf_data": rdf_content,
        "source_id": source_id,
        "extraction_job_id": job_id,
        "content_hash": hashlib.sha256(rdf_content.encode()).hexdigest()
    }
    
    response = requests.post(
        "https://api.valuefabric.ai/v1/ingest",
        headers=headers,
        json=data
    )
    
    return response.json()""",
                },
            ],
            related_endpoints=[
                "/v1/ingest",
                "/v1/sync/{source_id}",
                "/v1/schema/status",
            ],
        ),
    ],
    "errors": {
        "authentication_errors": [
            APIError(
                status_code=401,
                error_code="AUTHENTICATION_REQUIRED",
                message="API key required for this endpoint",
                description="The endpoint requires authentication but no API key was provided",
                causes=["Missing API key", "Invalid API key format", "Expired API key"],
                solutions=[
                    "Include API key in Authorization header",
                    "Check API key format",
                    "Get new API key",
                ],
                example_response={
                    "error": "AUTHENTICATION_REQUIRED",
                    "message": "API key required for this endpoint",
                    "schemes": ["Bearer", "X-API-Key"],
                },
            ),
            APIError(
                status_code=401,
                error_code="AUTHENTICATION_FAILED",
                message="Invalid or expired API key",
                description="The provided API key is invalid, expired, or has been revoked",
                causes=[
                    "Invalid API key",
                    "Expired API key",
                    "Revoked API key",
                    "Disabled API key",
                ],
                solutions=["Check API key", "Get new API key", "Contact administrator"],
                example_response={
                    "error": "AUTHENTICATION_FAILED",
                    "message": "Invalid API key",
                },
            ),
        ],
        "authorization_errors": [
            APIError(
                status_code=403,
                error_code="INSUFFICIENT_PERMISSIONS",
                message="API key lacks required permissions",
                description="The API key does not have permission to perform this operation",
                causes=[
                    "Insufficient role",
                    "Missing permission",
                    "Permission revoked",
                ],
                solutions=[
                    "Upgrade API key role",
                    "Contact administrator",
                    "Check permissions",
                ],
                example_response={
                    "error": "INSUFFICIENT_PERMISSIONS",
                    "message": "API key lacks required permissions",
                    "required_permission": "write:ingestion",
                    "current_permissions": ["read:search", "read:health"],
                },
            )
        ],
        "validation_errors": [
            APIError(
                status_code=400,
                error_code="VALIDATION_ERROR",
                message="Request validation failed",
                description="The request contains invalid data or parameters",
                causes=[
                    "Missing required fields",
                    "Invalid data format",
                    "Constraint violations",
                ],
                solutions=[
                    "Check request format",
                    "Validate data before sending",
                    "Review API documentation",
                ],
                example_response={
                    "error": "VALIDATION_ERROR",
                    "message": "Query cannot be empty",
                    "details": {"field": "query", "validation_rule": "minLength=1"},
                },
            )
        ],
        "rate_limit_errors": [
            APIError(
                status_code=429,
                error_code="RATE_LIMIT_ERROR",
                message="Rate limit exceeded",
                description="Too many requests have been made within the time window",
                causes=[
                    "High request volume",
                    "Insufficient rate limit",
                    "Burst traffic",
                ],
                solutions=[
                    "Wait and retry",
                    "Implement exponential backoff",
                    "Upgrade plan",
                ],
                example_response={
                    "error": "RATE_LIMIT_ERROR",
                    "message": "Rate limit exceeded",
                    "details": {"limit": 100, "window_seconds": 60, "retry_after": 30},
                },
            )
        ],
        "server_errors": [
            APIError(
                status_code=500,
                error_code="INTERNAL_SERVER_ERROR",
                message="Internal server error",
                description="An unexpected error occurred on the server",
                causes=[
                    "Database connection failed",
                    "Service unavailable",
                    "Bug in application",
                ],
                solutions=["Try again later", "Contact support", "Check status page"],
                example_response={
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": "req_123456",
                },
            ),
            APIError(
                status_code=503,
                error_code="SERVICE_UNAVAILABLE",
                message="Service temporarily unavailable",
                description="The service is temporarily down for maintenance or overload",
                causes=["Maintenance", "High load", "Dependency failure"],
                solutions=["Try again later", "Check status page", "Contact support"],
                example_response={
                    "error": "SERVICE_UNAVAILABLE",
                    "message": "Service temporarily unavailable",
                    "details": {"service": "neo4j", "error": "Connection timeout"},
                },
            ),
        ],
    },
}


def get_documentation() -> dict[str, Any]:
    """Get comprehensive API documentation.

    Returns:
        API documentation dictionary
    """
    return API_DOCUMENTATION


def get_endpoint_documentation(path: str, method: str) -> APIEndpoint | None:
    """Get documentation for specific endpoint.

    Args:
        path: Endpoint path
        method: HTTP method

    Returns:
        Endpoint documentation or None
    """
    endpoints = API_DOCUMENTATION.get("endpoints", {})

    for endpoint in endpoints.values():
        if endpoint.path == path and endpoint.method.upper() == method.upper():
            return endpoint

    return None


def get_error_documentation(error_code: str) -> APIError | None:
    """Get documentation for specific error.

    Args:
        error_code: Error code

    Returns:
        Error documentation or None
    """
    errors = API_DOCUMENTATION.get("errors", {})

    for error_category in errors.values():
        for error in error_category:
            if error.error_code == error_code:
                return error

    return None


def get_tutorial(title: str) -> APITutorial | None:
    """Get tutorial by title.

    Args:
        title: Tutorial title

    Returns:
        Tutorial or None
    """
    tutorials = API_DOCUMENTATION.get("tutorials", [])

    for tutorial in tutorials:
        if tutorial.title == title:
            return tutorial

    return None


def get_guide(title: str) -> APIGuide | None:
    """Get guide by title.

    Args:
        title: Guide title

    Returns:
        Guide or None
    """
    guides = API_DOCUMENTATION.get("guides", [])

    for guide in guides:
        if guide.title == title:
            return guide

    return None
