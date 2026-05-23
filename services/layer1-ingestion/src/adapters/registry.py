"""Adapter registry for discovering and managing data source adapters."""

import structlog

from .base import AdapterType, DataSourceAdapter

try:
    from .pdf_adapter import PDFAdapter
except ImportError:
    PDFAdapter = None  # type: ignore[assignment,misc]
from .sec_edgar import SECEdgarAdapter

logger = structlog.get_logger()


class AdapterRegistry:
    """Registry for data source adapters.

    Provides centralized access to all available adapters and
    allows runtime registration of new adapters.
    """

    def __init__(self):
        self._adapters: dict[AdapterType, type[DataSourceAdapter]] = {}
        self._instances: dict[AdapterType, DataSourceAdapter] = {}
        self.logger = logger

        # Register built-in adapters
        self._register_builtin_adapters()

    def _register_builtin_adapters(self):
        """Register all built-in adapters."""
        self.register(AdapterType.SEC_EDGAR, SECEdgarAdapter)
        if PDFAdapter is not None:
            self.register(AdapterType.PDF, PDFAdapter)
        self.logger.info("Built-in adapters registered")

    def register(self, adapter_type: AdapterType, adapter_class: type[DataSourceAdapter]):
        """Register an adapter class.

        Args:
            adapter_type: The adapter type identifier
            adapter_class: The adapter class (not instance)
        """
        self._adapters[adapter_type] = adapter_class
        self.logger.debug("Adapter registered", adapter_type=adapter_type.value)

    def get_adapter(self, adapter_type: AdapterType) -> DataSourceAdapter | None:
        """Get or create an adapter instance.

        Args:
            adapter_type: Type of adapter to retrieve

        Returns:
            Adapter instance or None if not found
        """
        # Return cached instance
        if adapter_type in self._instances:
            return self._instances[adapter_type]

        # Create new instance
        adapter_class = self._adapters.get(adapter_type)
        if not adapter_class:
            self.logger.error("Adapter not found", adapter_type=adapter_type.value)
            return None

        try:
            adapter = adapter_class()
            self._instances[adapter_type] = adapter
            return adapter
        except Exception as e:
            self.logger.error(
                "Failed to create adapter instance", adapter_type=adapter_type.value, error_code="ADAPTER_CREATE_ERROR"
            )
            return None

    def get_adapter_class(self, adapter_type: AdapterType) -> type[DataSourceAdapter] | None:
        """Get adapter class without instantiation.

        Args:
            adapter_type: Type of adapter

        Returns:
            Adapter class or None
        """
        return self._adapters.get(adapter_type)

    def list_adapters(self) -> list:
        """List all registered adapter types."""
        return list(self._adapters.keys())

    def clear_instances(self):
        """Clear all cached adapter instances.

        Useful for testing or reconfiguration.
        """
        self._instances.clear()
        self.logger.info("Adapter instances cleared")


# Global registry instance
_registry = None


def get_registry() -> AdapterRegistry:
    """Get the global adapter registry."""
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry
