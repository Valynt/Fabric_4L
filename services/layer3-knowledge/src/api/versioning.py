from value_fabric.shared.error_handling.exceptions import ValidationError

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: API versioning and backward compatibility utilities.
"""

import inspect
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Union

from fastapi import Request
from pydantic import BaseModel, Field
from value_fabric.shared.probes import normalize_probe_response

from src.logging_config import get_logger

logger = get_logger(__name__)


MigrationHandler = Union[
    Callable[[dict[str, Any]], dict[str, Any]],
    Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
]


class APIVersion(str, Enum):
    """Supported API versions."""

    V1 = "v1"
    V2 = "v2"  # Future version
    LATEST = "latest"


class VersionedResponse(BaseModel):
    """Versioned API response wrapper."""

    api_version: str = Field(..., description="API version used for this response")
    data: dict[str, Any] = Field(..., description="Response data")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Response metadata"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Backward compatibility warnings"
    )
    deprecated: dict[str, Any] | None = Field(
        None, description="Deprecation information if applicable"
    )


class DeprecationInfo(BaseModel):
    """Deprecation information for API features."""

    deprecated_since: str = Field(
        ..., description="Version when feature was deprecated"
    )
    removal_version: str | None = Field(
        None, description="Version when feature will be removed"
    )
    message: str = Field(..., description="Deprecation message")
    alternatives: list[str] = Field(
        default_factory=list, description="Alternative approaches"
    )
    sunset_date: datetime | None = Field(
        None, description="When feature will be removed"
    )


class VersionCompatibility:
    """Manages API version compatibility and migrations."""

    def __init__(self, current_version: str = "v1"):
        """Initialize version compatibility manager.

        Args:
            current_version: Current API version
        """
        self.current_version = current_version
        self.supported_versions = ["v1"]
        self.deprecated_features = {}
        self.migration_handlers = {}
        self.response_transformers = {}

        # Initialize default deprecation warnings
        self._setup_deprecations()

    def _setup_deprecations(self) -> None:
        """Setup default deprecation information."""
        # Example deprecations for future use
        self.deprecated_features.update(
            {
                "v1.search.query_string": DeprecationInfo(
                    deprecated_since="v1",
                    removal_version="v2",
                    message="query_string parameter is deprecated, use 'query' instead",
                    alternatives=["Use the 'query' parameter"],
                ),
                "v1.ingestion.rdf_format": DeprecationInfo(
                    deprecated_since="v1",
                    removal_version="v2",
                    message="rdf_format parameter is deprecated, format is now auto-detected",
                    alternatives=["Remove rdf_format parameter"],
                ),
            }
        )

    def is_version_supported(self, version: str) -> bool:
        """Check if API version is supported.

        Args:
            version: Version to check

        Returns:
            True if version is supported
        """
        return version in self.supported_versions

    def get_latest_version(self) -> str:
        """Get the latest supported API version.

        Returns:
            Latest version string
        """
        return self.supported_versions[-1]

    def normalize_version(self, version: str) -> str:
        """Normalize version string.

        Args:
            version: Version string to normalize

        Returns:
            Normalized version string
        """
        if version == "latest":
            return self.get_latest_version()

        # Ensure version starts with 'v'
        if not version.startswith("v"):
            version = f"v{version}"

        return version

    def check_deprecation(
        self, version: str, feature_path: str
    ) -> DeprecationInfo | None:
        """Check if a feature is deprecated in the given version.

        Args:
            version: API version
            feature_path: Feature path (e.g., "v1.search.query")

        Returns:
            Deprecation info if deprecated, None otherwise
        """
        full_path = f"{version}.{feature_path}"
        return self.deprecated_features.get(full_path)

    def add_deprecation(
        self,
        feature_path: str,
        deprecated_since: str,
        message: str,
        removal_version: str | None = None,
        alternatives: list[str] | None = None,
        sunset_date: datetime | None = None,
    ) -> None:
        """Add a deprecation warning.

        Args:
            feature_path: Feature path
            deprecated_since: Version when deprecated
            message: Deprecation message
            removal_version: Version when feature will be removed
            alternatives: Alternative approaches
            sunset_date: When feature will be removed
        """
        self.deprecated_features[feature_path] = DeprecationInfo(
            deprecated_since=deprecated_since,
            removal_version=removal_version,
            message=message,
            alternatives=alternatives or [],
            sunset_date=sunset_date,
        )

    @staticmethod
    def _validate_migration_handler(
        handler: Any, from_version: str, to_version: str
    ) -> None:
        """Validate migration handler contract at registration boundary."""
        expected_interface = (
            "Callable[[Dict[str, Any]], Dict[str, Any]] or "
            "Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]"
        )
        handler_name = getattr(handler, "__name__", repr(handler))
        actual_type = type(handler).__name__

        if not callable(handler):
            raise TypeError(
                "Invalid migration handler registration "
                f"for {from_version}->{to_version}: handler '{handler_name}' "
                f"must implement {expected_interface}; got {actual_type}."
            )

        try:
            signature = inspect.signature(handler)
        except (TypeError, ValueError):
            # Some callables cannot be introspected; allow callable boundary above.
            return

        parameters = list(signature.parameters.values())
        has_var_positional = any(
            param.kind == inspect.Parameter.VAR_POSITIONAL for param in parameters
        )
        positional = [
            param
            for param in parameters
            if param.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        required_positional = [
            param for param in positional if param.default is inspect.Parameter.empty
        ]

        accepts_one_argument = has_var_positional or len(positional) >= 1
        requires_too_many_arguments = (
            not has_var_positional and len(required_positional) > 1
        )

        if not accepts_one_argument or requires_too_many_arguments:
            raise TypeError(
                "Invalid migration handler registration "
                f"for {from_version}->{to_version}: handler '{handler_name}' "
                f"must implement {expected_interface}; got callable signature {signature}."
            )

    def register_migration_handler(
        self,
        from_version: str,
        to_version: str,
        handler: MigrationHandler | None = None,
        *,
        migration_handler: MigrationHandler | None = None,
    ) -> None:
        """Register a migration handler for version upgrades.

        Multiple handlers can be registered for the same version transition.
        They will be executed in registration order.

        Args:
            from_version: Source version
            to_version: Target version
            handler: Migration function
        """
        if handler is not None and migration_handler is not None:
            raise TypeError(
                "Provide either 'handler' or 'migration_handler', not both."
            )

        selected_handler = handler if handler is not None else migration_handler
        if selected_handler is None:
            raise TypeError(
                "Missing migration handler: provide 'handler' or 'migration_handler'."
            )

        self._validate_migration_handler(selected_handler, from_version, to_version)

        key = f"{from_version}->{to_version}"
        if key not in self.migration_handlers:
            self.migration_handlers[key] = []
        self.migration_handlers[key].append(selected_handler)

    async def migrate_request_data_async(
        self,
        data: dict[str, Any],
        from_version: str,
        to_version: str,
    ) -> dict[str, Any]:
        """Async variant of request-data migration with sync/async handler support."""
        if from_version == to_version:
            return data

        key = f"{from_version}->{to_version}"
        handlers = self.migration_handlers.get(key, [])

        if not handlers:
            return data

        result = data
        failed_handlers = []

        for i, handler in enumerate(handlers):
            try:
                handler_result = handler(result)
                if inspect.isawaitable(handler_result):
                    result = await handler_result
                else:
                    result = handler_result
            except Exception as e:
                handler_name = getattr(handler, "__name__", f"handler_{i}")
                logger.warning(
                    f"Migration handler '{handler_name}' failed from {from_version} to {to_version}: {e}",
                    exc_info=True,
                )
                failed_handlers.append(handler_name)

        if failed_handlers:
            logger.warning(
                f"Migration from {from_version} to {to_version} completed with {len(failed_handlers)} failed handlers: {failed_handlers}"
            )

        return result

    def register_response_transformer(
        self,
        version: str,
        endpoint: str,
        transformer: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Register a response transformer for version compatibility.

        Args:
            version: API version
            endpoint: Endpoint path
            transformer: Transform function
        """
        key = f"{version}:{endpoint}"
        self.response_transformers[key] = transformer

    async def migrate_request_data(
        self, data: dict[str, Any], from_version: str, to_version: str
    ) -> dict[str, Any]:
        """Migrate request data from one version to another.

        Applies all registered migration handlers in sequence.
        If a handler fails, subsequent handlers are still applied to the last
        successful result. Failed handlers are logged for debugging.

        Args:
            data: Request data
            from_version: Source version
            to_version: Target version

        Returns:
            Migrated data (may be partially migrated if handlers failed)
        """
        if from_version == to_version:
            return data

        key = f"{from_version}->{to_version}"
        handlers = self.migration_handlers.get(key, [])

        if not handlers:
            return data

        result = data
        failed_handlers = []

        for i, handler in enumerate(handlers):
            try:
                handler_result = handler(result)
                if inspect.isawaitable(handler_result):
                    # Always await in async context (FastAPI handler)
                    result = await handler_result
                else:
                    result = handler_result
            except Exception as e:
                handler_name = getattr(handler, "__name__", f"handler_{i}")
                logger.warning(
                    f"Migration handler '{handler_name}' failed from {from_version} to {to_version}: {e}",
                    exc_info=True,
                )
                failed_handlers.append(handler_name)
                # Continue with other handlers - partial migration is attempted

        if failed_handlers:
            logger.warning(
                f"Migration from {from_version} to {to_version} completed with {len(failed_handlers)} failed handlers: {failed_handlers}"
            )

        return result

    def transform_response(
        self, data: dict[str, Any], version: str, endpoint: str
    ) -> dict[str, Any]:
        """Transform response data for specific version.

        Args:
            data: Response data
            version: API version
            endpoint: Endpoint path

        Returns:
            Transformed data
        """
        key = f"{version}:{endpoint}"
        transformer = self.response_transformers.get(key)

        if transformer:
            try:
                return transformer(data)
            except Exception as e:
                logger.warning(
                    f"Response transform failed for {version}:{endpoint}: {e}"
                )
                return data

        return data

    def create_versioned_response(
        self,
        data: dict[str, Any],
        version: str,
        endpoint: str,
        warnings: list[str] | None = None,
    ) -> VersionedResponse:
        """Create a versioned API response.

        Args:
            data: Response data
            version: API version
            endpoint: Endpoint path
            warnings: Additional warnings

        Returns:
            Versioned response
        """
        # Transform data for version compatibility
        transformed_data = self.transform_response(data, version, endpoint)

        # Collect deprecation warnings
        all_warnings = warnings or []

        # Check for endpoint-specific deprecations
        feature_path = endpoint.replace("/", ".").strip(".")
        deprecation = self.check_deprecation(version, feature_path)
        if deprecation:
            all_warnings.append(f"Deprecated: {deprecation.message}")

        return VersionedResponse(
            api_version=version,
            data=transformed_data,
            metadata={
                "endpoint": endpoint,
                "timestamp": datetime.now(UTC).isoformat(),
                "supported_versions": self.supported_versions,
                "latest_version": self.get_latest_version(),
            },
            warnings=all_warnings,
            deprecated=deprecation.model_dump() if deprecation else None,
        )


def versioned_route(
    version: str = "v1",
    deprecated_since: str | None = None,
    removal_version: str | None = None,
    deprecation_message: str | None = None,
):
    """Decorator to create versioned API routes.

    Args:
        version: API version
        deprecated_since: Version when route was deprecated
        removal_version: Version when route will be removed
        deprecation_message: Deprecation message

    Returns:
        Decorated function
    """

    def decorator(func):
        # Create deprecation info if provided
        deprecated = None
        if deprecated_since:
            deprecated = DeprecationInfo(
                deprecated_since=deprecated_since,
                removal_version=removal_version,
                message=deprecation_message or "This endpoint is deprecated",
                alternatives=[],
            )

        # Store versioning metadata
        func._version = version
        func._deprecated = deprecated

        return func

    return decorator


class VersionMiddleware:
    """Middleware to handle API versioning."""

    def __init__(self, compatibility: VersionCompatibility):
        """Initialize version middleware.

        Args:
            compatibility: Version compatibility manager
        """
        self.compatibility = compatibility

    async def __call__(self, request: Request, call_next):
        """Process request with version handling."""
        # Extract version from header or URL
        api_version = self._extract_version(request)

        # Validate version
        if not self.compatibility.is_version_supported(api_version):
            raise ValidationError(message = "Request failed", details = {
                    "error": "UNSUPPORTED_VERSION",
                    "message": f"API version '{api_version}' is not supported",
                    "supported_versions": self.compatibility.supported_versions,
                    "latest_version": self.compatibility.get_latest_version(),
                })

        # Add version to request state
        request.state.api_version = api_version
        request.state.version_compatibility = self.compatibility

        # Process request
        response = await call_next(request)

        # Add version headers
        response.headers["X-API-Version"] = api_version
        response.headers["X-Supported-Versions"] = ",".join(
            self.compatibility.supported_versions
        )
        response.headers["X-Latest-Version"] = self.compatibility.get_latest_version()

        return response

    def _extract_version(self, request: Request) -> str:
        """Extract API version from request.

        Args:
            request: FastAPI request

        Returns:
            API version string
        """
        # Try header first
        version = request.headers.get("X-API-Version")
        if version:
            return self.compatibility.normalize_version(version)

        # Try URL path
        path_parts = request.url.path.strip("/").split("/")
        if len(path_parts) >= 1 and path_parts[0].startswith("v"):
            return self.compatibility.normalize_version(path_parts[0])

        # Default to latest
        return self.compatibility.get_latest_version()


# Global version compatibility instance
_version_compatibility: VersionCompatibility | None = None


def get_version_compatibility() -> VersionCompatibility:
    """Get global version compatibility instance.

    Returns:
        Version compatibility instance
    """
    global _version_compatibility
    if _version_compatibility is None:
        _version_compatibility = VersionCompatibility()
    return _version_compatibility


def initialize_versioning(current_version: str = "v1") -> VersionCompatibility:
    """Initialize global versioning system.

    Args:
        current_version: Current API version

    Returns:
        Version compatibility instance
    """
    global _version_compatibility
    _version_compatibility = VersionCompatibility(current_version)
    logger.info(f"API versioning initialized with current version: {current_version}")
    return _version_compatibility


# Migration handlers for common patterns
def migrate_v1_to_v2_search_request(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate v1 search request to v2 format."""
    migrated = data.copy()

    # Example migration: rename query_string to query
    if "query_string" in migrated:
        migrated["query"] = migrated.pop("query_string")
        migrated["_migration_note"] = "query_string renamed to query"

    return migrated


def migrate_v1_to_v2_ingestion_request(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate v1 ingestion request to v2 format."""
    migrated = data.copy()

    # Example migration: remove deprecated rdf_format
    if "rdf_format" in migrated:
        migrated.pop("rdf_format")
        migrated["_migration_note"] = "rdf_format removed (auto-detected)"

    return migrated


# Response transformers for backward compatibility
def transform_v1_search_response(data: dict[str, Any]) -> dict[str, Any]:
    """Transform search response for v1 compatibility."""
    transformed = data.copy()

    # Example: ensure old field names exist
    if "results" in transformed and "hits" not in transformed:
        transformed["hits"] = transformed["results"]

    return transformed


def transform_v1_health_response(data: dict[str, Any]) -> dict[str, Any]:
    """Transform health response for v1 compatibility."""
    transformed = normalize_probe_response(data, default_service="layer3-knowledge")
    transformed["healthy"] = transformed["readiness"]["is_ready"]
    return transformed
