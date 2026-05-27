"""API main module (re-exports from layer2_extraction)."""

from value_fabric.shared.startup import reject_insecure_bypass_in_production

# Defensive guard for compatibility entrypoint imports.
reject_insecure_bypass_in_production(service_name="layer2-extraction-compat")

import sys

# Transparent alias so tests patching this module affect the real implementation
sys.modules[__name__] = __import__("layer2_extraction.api.main", fromlist=["*"])
