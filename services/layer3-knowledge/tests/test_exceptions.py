"""Unit tests for exception classes."""

from api.exceptions import (
    AnalyticsError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    DatabaseError,
    IngestionError,
    Neo4jError,
    RateLimitError,
    SearchError,
    ServiceUnavailableError,
    ValidationError,
    ValueFabricException,
    VectorStoreError,
    create_conflict_http_exception,
    create_http_exception,
    create_not_found_http_exception,
    create_rate_limit_http_exception,
    create_service_unavailable_http_exception,
    create_validation_http_exception,
)


class TestValueFabricException:
    """Test base ValueFabricException class."""
    
    def test_basic_exception(self):
        """Test basic exception creation."""
        exc = ValueFabricException("Test message")
        
        assert exc.message == "Test message"
        assert exc.error_code == "ValueFabricException"
        assert exc.details == {}
        assert exc.cause is None
    
    def test_exception_with_all_fields(self):
        """Test exception with all fields."""
        cause = ValueError("Original error")
        exc = ValueFabricException(
            message="Test message",
            error_code="CUSTOM_ERROR",
            details={"field": "value"},
            cause=cause
        )
        
        assert exc.message == "Test message"
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == {"field": "value"}
        assert exc.cause is cause
    
    def test_exception_to_dict(self):
        """Test exception to_dict method."""
        exc = ValueFabricException(
            message="Test message",
            error_code="CUSTOM_ERROR",
            details={"field": "value"},
            cause=ValueError("Original")
        )
        
        result = exc.to_dict()
        
        assert result["error"] == "CUSTOM_ERROR"
        assert result["message"] == "Test message"
        assert result["type"] == "ValueFabricException"
        assert result["details"] == {"field": "value"}
        assert "cause" in result
        assert result["cause"] == "Original"
    
    def test_exception_to_dict_minimal(self):
        """Test exception to_dict with minimal fields."""
        exc = ValueFabricException("Test message")
        result = exc.to_dict()
        
        assert result["error"] == "ValueFabricException"
        assert result["message"] == "Test message"
        assert result["type"] == "ValueFabricException"
        assert "details" not in result
        assert "cause" not in result


class TestValidationError:
    """Test ValidationError class."""
    
    def test_validation_error_basic(self):
        """Test basic validation error."""
        exc = ValidationError("Invalid input")
        
        assert exc.message == "Invalid input"
        assert exc.error_code == "VALIDATION_ERROR"
    
    def test_validation_error_with_details(self):
        """Test validation error with details."""
        exc = ValidationError(
            message="Invalid email",
            field="email",
            value="bad@",
            validation_rule="email_regex"
        )
        
        assert exc.message == "Invalid email"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details["field"] == "email"
        assert exc.details["invalid_value"] == "bad@"
        assert exc.details["validation_rule"] == "email_regex"
    
    def test_validation_error_to_dict(self):
        """Test validation error to_dict."""
        exc = ValidationError(
            message="Invalid input",
            field="test_field",
            value="bad_value"
        )
        
        result = exc.to_dict()
        
        assert result["error"] == "VALIDATION_ERROR"
        assert result["details"]["field"] == "test_field"
        assert result["details"]["invalid_value"] == "bad_value"


class TestDatabaseError:
    """Test DatabaseError class."""
    
    def test_database_error_basic(self):
        """Test basic database error."""
        exc = DatabaseError("Connection failed")
        
        assert exc.message == "Connection failed"
        assert exc.error_code == "DATABASE_ERROR"
    
    def test_database_error_with_details(self):
        """Test database error with details."""
        exc = DatabaseError(
            message="Query failed",
            operation="SELECT",
            query="SELECT * FROM users",
            database="neo4j"
        )
        
        assert exc.message == "Query failed"
        assert exc.error_code == "DATABASE_ERROR"
        assert exc.details["operation"] == "SELECT"
        assert exc.details["query"] == "SELECT * FROM users"
        assert exc.details["database"] == "neo4j"
    
    def test_database_error_long_query_truncation(self):
        """Test database error truncates long queries."""
        long_query = "SELECT " + "x" * 200  # Make query very long
        exc = DatabaseError(
            message="Query failed",
            operation="SELECT",
            query=long_query
        )
        
        query_in_details = exc.details["query"]
        assert len(query_in_details) <= 103  # "..." added for truncation
        assert "..." in query_in_details


class TestNeo4jError:
    """Test Neo4jError class."""
    
    def test_neo4j_error_basic(self):
        """Test basic Neo4j error."""
        exc = Neo4jError("Constraint violation")
        
        assert exc.message == "Constraint violation"
        assert exc.error_code == "NEO4J_ERROR"
    
    def test_neo4j_error_with_details(self):
        """Test Neo4j error with details."""
        exc = Neo4jError(
            message="Index creation failed",
            constraint="unique_name",
            index="entity_name_idx"
        )
        
        assert exc.message == "Index creation failed"
        assert exc.error_code == "NEO4J_ERROR"
        assert exc.details["constraint"] == "unique_name"
        assert exc.details["index"] == "entity_name_idx"


class TestVectorStoreError:
    """Test VectorStoreError class."""
    
    def test_vector_store_error_basic(self):
        """Test basic vector store error."""
        exc = VectorStoreError("Index not found")
        
        assert exc.message == "Index not found"
        assert exc.error_code == "VECTOR_STORE_ERROR"
    
    def test_vector_store_error_with_details(self):
        """Test vector store error with details."""
        exc = VectorStoreError(
            message="Query failed",
            index="value-fabric",
            namespace="production",
            operation="search"
        )
        
        assert exc.message == "Query failed"
        assert exc.error_code == "VECTOR_STORE_ERROR"
        assert exc.details["index"] == "value-fabric"
        assert exc.details["namespace"] == "production"
        assert exc.details["operation"] == "search"


class TestIngestionError:
    """Test IngestionError class."""
    
    def test_ingestion_error_basic(self):
        """Test basic ingestion error."""
        exc = IngestionError("RDF parsing failed")
        
        assert exc.message == "RDF parsing failed"
        assert exc.error_code == "INGESTION_ERROR"
    
    def test_ingestion_error_with_details(self):
        """Test ingestion error with details."""
        exc = IngestionError(
            message="Processing failed",
            source_id="doc_123",
            job_id="job_456",
            stage="validation"
        )
        
        assert exc.message == "Processing failed"
        assert exc.error_code == "INGESTION_ERROR"
        assert exc.details["source_id"] == "doc_123"
        assert exc.details["job_id"] == "job_456"
        assert exc.details["stage"] == "validation"


class TestSearchError:
    """Test SearchError class."""
    
    def test_search_error_basic(self):
        """Test basic search error."""
        exc = SearchError("Query timeout")
        
        assert exc.message == "Query timeout"
        assert exc.error_code == "SEARCH_ERROR"
    
    def test_search_error_with_details(self):
        """Test search error with details."""
        exc = SearchError(
            message="Invalid query syntax",
            query="invalid syntax query",
            search_type="hybrid",
            index="value-fabric"
        )
        
        assert exc.message == "Invalid query syntax"
        assert exc.error_code == "SEARCH_ERROR"
        assert exc.details["query"] == "invalid syntax query"
        assert exc.details["search_type"] == "hybrid"
        assert exc.details["index"] == "value-fabric"


class TestAnalyticsError:
    """Test AnalyticsError class."""
    
    def test_analytics_error_basic(self):
        """Test basic analytics error."""
        exc = AnalyticsError("Algorithm failed")
        
        assert exc.message == "Algorithm failed"
        assert exc.error_code == "ANALYTICS_ERROR"
    
    def test_analytics_error_with_details(self):
        """Test analytics error with details."""
        exc = AnalyticsError(
            message="Centrality calculation failed",
            algorithm="betweenness",
            parameters={"nodes": 1000, "directed": True}
        )
        
        assert exc.message == "Centrality calculation failed"
        assert exc.error_code == "ANALYTICS_ERROR"
        assert exc.details["algorithm"] == "betweenness"
        assert "parameters" in exc.details
        assert exc.details["parameters"]["nodes"] == "1000"  # Sanitized to string
        assert exc.details["parameters"]["directed"] == "True"  # Sanitized to string


class TestConfigurationError:
    """Test ConfigurationError class."""
    
    def test_configuration_error_basic(self):
        """Test basic configuration error."""
        exc = ConfigurationError("Invalid setting")
        
        assert exc.message == "Invalid setting"
        assert exc.error_code == "CONFIGURATION_ERROR"
    
    def test_configuration_error_with_details(self):
        """Test configuration error with details."""
        exc = ConfigurationError(
            message="Invalid port",
            setting="api_port",
            expected_type="integer",
            current_value="invalid"
        )
        
        assert exc.message == "Invalid port"
        assert exc.error_code == "CONFIGURATION_ERROR"
        assert exc.details["setting"] == "api_port"
        assert exc.details["expected_type"] == "integer"
        assert exc.details["current_value"] == "invalid"


class TestAuthenticationError:
    """Test AuthenticationError class."""
    
    def test_authentication_error_basic(self):
        """Test basic authentication error."""
        exc = AuthenticationError()
        
        assert exc.message == "Authentication failed"
        assert exc.error_code == "AUTHENTICATION_ERROR"
    
    def test_authentication_error_with_details(self):
        """Test authentication error with details."""
        exc = AuthenticationError(
            message="Token expired",
            method="JWT",
            reason="Token has expired"
        )
        
        assert exc.message == "Token expired"
        assert exc.error_code == "AUTHENTICATION_ERROR"
        assert exc.details["method"] == "JWT"
        assert exc.details["reason"] == "Token has expired"


class TestAuthorizationError:
    """Test AuthorizationError class."""
    
    def test_authorization_error_basic(self):
        """Test basic authorization error."""
        exc = AuthorizationError()
        
        assert exc.message == "Access denied"
        assert exc.error_code == "AUTHORIZATION_ERROR"
    
    def test_authorization_error_with_details(self):
        """Test authorization error with details."""
        exc = AuthorizationError(
            message="Insufficient permissions",
            resource="admin_endpoint",
            action="DELETE",
            required_permission="admin"
        )
        
        assert exc.message == "Insufficient permissions"
        assert exc.error_code == "AUTHORIZATION_ERROR"
        assert exc.details["resource"] == "admin_endpoint"
        assert exc.details["action"] == "DELETE"
        assert exc.details["required_permission"] == "admin"


class TestRateLimitError:
    """Test RateLimitError class."""
    
    def test_rate_limit_error_basic(self):
        """Test basic rate limit error."""
        exc = RateLimitError()
        
        assert exc.message == "Rate limit exceeded"
        assert exc.error_code == "RATE_LIMIT_ERROR"
    
    def test_rate_limit_error_with_details(self):
        """Test rate limit error with details."""
        exc = RateLimitError(
            limit=100,
            window_seconds=60,
            retry_after=30
        )
        
        assert exc.message == "Rate limit exceeded"
        assert exc.error_code == "RATE_LIMIT_ERROR"
        assert exc.details["limit"] == 100
        assert exc.details["window_seconds"] == 60
        assert exc.details["retry_after"] == 30


class TestServiceUnavailableError:
    """Test ServiceUnavailableError class."""
    
    def test_service_unavailable_error_basic(self):
        """Test basic service unavailable error."""
        exc = ServiceUnavailableError("Service down")
        
        assert exc.message == "Service down"
        assert exc.error_code == "SERVICE_UNAVAILABLE"
    
    def test_service_unavailable_error_with_details(self):
        """Test service unavailable error with details."""
        exc = ServiceUnavailableError(
            message="Database unavailable",
            service="neo4j",
            retry_after=120
        )
        
        assert exc.message == "Database unavailable"
        assert exc.error_code == "SERVICE_UNAVAILABLE"
        assert exc.details["service"] == "neo4j"
        assert exc.details["retry_after"] == 120


class TestHTTPExceptionHelpers:
    """Test HTTP exception helper functions."""
    
    def test_create_http_exception(self):
        """Test create_http_exception helper."""
        exc = ValueFabricException("Test error", error_code="TEST_ERROR")
        http_exc = create_http_exception(400, exc)
        
        assert http_exc.status_code == 400
        assert http_exc.detail["error"] == "TEST_ERROR"
        assert http_exc.detail["message"] == "Test error"
    
    def test_create_validation_http_exception(self):
        """Test create_validation_http_exception helper."""
        http_exc = create_validation_http_exception(
            "Invalid input",
            field="email",
            value="bad@"
        )
        
        assert http_exc.status_code == 400
        assert http_exc.detail["error"] == "VALIDATION_ERROR"
        assert http_exc.detail["message"] == "Invalid input"
        assert http_exc.detail["details"]["field"] == "email"
        assert http_exc.detail["details"]["invalid_value"] == "bad@"
    
    def test_create_not_found_http_exception(self):
        """Test create_not_found_http_exception helper."""
        http_exc = create_not_found_http_exception(
            "Entity not found",
            resource_type="Capability",
            resource_id="cap_123"
        )
        
        assert http_exc.status_code == 404
        assert http_exc.detail["error"] == "NOT_FOUND"
        assert http_exc.detail["message"] == "Entity not found"
        assert http_exc.detail["details"]["resource_type"] == "Capability"
        assert http_exc.detail["details"]["resource_id"] == "cap_123"
    
    def test_create_conflict_http_exception(self):
        """Test create_conflict_http_exception helper."""
        http_exc = create_conflict_http_exception(
            "Resource already exists",
            conflict_type="duplicate_entity",
            existing_resource="cap_123"
        )
        
        assert http_exc.status_code == 409
        assert http_exc.detail["error"] == "CONFLICT"
        assert http_exc.detail["message"] == "Resource already exists"
        assert http_exc.detail["details"]["conflict_type"] == "duplicate_entity"
        assert http_exc.detail["details"]["existing_resource"] == "cap_123"
    
    def test_create_rate_limit_http_exception(self):
        """Test create_rate_limit_http_exception helper."""
        http_exc = create_rate_limit_http_exception(
            limit=100,
            window_seconds=60,
            retry_after=30
        )
        
        assert http_exc.status_code == 429
        assert http_exc.detail["error"] == "RATE_LIMIT_ERROR"
        assert http_exc.detail["details"]["limit"] == 100
        assert http_exc.detail["details"]["window_seconds"] == 60
        assert http_exc.detail["details"]["retry_after"] == 30
        assert "Retry-After" in http_exc.headers
        assert http_exc.headers["Retry-After"] == "30"
    
    def test_create_service_unavailable_http_exception(self):
        """Test create_service_unavailable_http_exception helper."""
        http_exc = create_service_unavailable_http_exception(
            message="Service down",
            service="neo4j",
            retry_after=120
        )
        
        assert http_exc.status_code == 503
        assert http_exc.detail["error"] == "SERVICE_UNAVAILABLE"
        assert http_exc.detail["message"] == "Service down"
        assert http_exc.detail["details"]["service"] == "neo4j"
        assert http_exc.detail["details"]["retry_after"] == 120
        assert "Retry-After" in http_exc.headers
        assert http_exc.headers["Retry-After"] == "120"
    
    def test_create_service_unavailable_http_exception_no_retry(self):
        """Test create_service_unavailable_http_exception without retry."""
        http_exc = create_service_unavailable_http_exception(
            message="Service down",
            service="neo4j"
        )
        
        assert http_exc.status_code == 503
        assert "Retry-After" not in http_exc.headers

