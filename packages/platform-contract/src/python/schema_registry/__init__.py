"""Schema Registry engine for Fabric 4L.

Provides:
- Registry catalog loading and validation (loader)
- Compatibility checking against ADDITIVE_WITHIN_MAJOR and other policies (compatibility)
- Deterministic bundle building with $ref resolution (bundler)
- Impact analysis for schema changes (impact)
"""

from .loader import RegistryLoader
from .compatibility import CompatibilityChecker
from .bundler import BundleBuilder
from .impact import ImpactAnalyzer

__all__ = ["RegistryLoader", "CompatibilityChecker", "BundleBuilder", "ImpactAnalyzer"]
