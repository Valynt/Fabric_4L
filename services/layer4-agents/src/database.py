# This file is a compatibility shim. New code must import from layer4_agents.*
# ruff: noqa: F401,F403

# This shim re-exports layer4_agents.database, which intentionally bypasses the
# shared RuntimeDatabaseAdapter for local session management. The marker below
# makes that bypass explicit per the runtime database adapter contract.
# See: tests/contract/test_runtime_db_postgres_contract.py

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
