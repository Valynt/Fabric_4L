# This file is a compatibility shim. New code must import from layer4_agents.*
# ruff: noqa: F401,F403

# INTENTIONAL_DB_ADAPTER_BYPASS: This shim intentionally re-exports the Layer 4
# database module directly, bypassing the shared RuntimeDatabaseAdapter. The
# marker is required by the runtime DB contract test so that deliberately
# non-shared database entrypoints are explicitly flagged and reviewed.
INTENTIONAL_DB_ADAPTER_BYPASS = True

from layer4_agents.database import *  # noqa: F401,F403

# Re-export private symbols that tests patch via this shim path.
# Wildcard imports do not include names starting with '_'.
from layer4_agents.database import (  # noqa: F401
    _TENANT_BYPASS_REASON_KEY,
    _TENANT_CONTEXT_STATE_KEY,
    _TENANT_CONTEXT_VALUE_KEY,
    _emit_tenant_context_set_audit,
    get_session_factory,
)

INTENTIONAL_DB_ADAPTER_BYPASS = True
