"""Value Fabric authorization control plane.

A single typed decision and enforcement layer (PBAC) that composes:

* RBAC  — job authority via workflow roles
* ReBAC — tenant/opportunity/account/resource relationships
* ABAC  — request-time state, ownership, amount, version, risk, time, ceilings
* PBAC  — the one decision point (``authorize`` / ``CommandGuard``)
* RLS   — PostgreSQL tenant-containment backstop (see migration)

Public surface (:func:`authorize`, :class:`CommandGuard`, decision models) is
stable. Policy internals (Rego bundle under ``policies/authorization/bundle``)
are mirrored by the pure-Python engine for parity and fail-closed operation
without a live OPA server.
"""

from __future__ import annotations

from .actions import (
    AGENT_FORBIDDEN_ACTIONS,
    PROTECTED_DOMAIN_COMMANDS,
    UNCACHEABLE_ACTIONS,
    Action,
    ACTION_CATALOG,
    PrincipalType,
    WorkflowRole,
    PRINCIPAL_TYPES,
)
from .attribute_resolver import AttributeResolver, StaticAttributeResolver
from .cache import InMemoryAuthzCache
from .client import (
    AuthorizationClient,
    authorize,
    configure_authorization_client,
    get_authorization_client,
    reset_authorization_client,
)
from .command_guard import CommandGuard, GuardResult
from .decisions import (
    AuthzDecisionSink,
    CorrelatedDecisionSink,
    DecisionStore,
    LoggingDecisionStore,
)
from .engine import DecisionEngine, PolicyBundle, load_bundle
from .errors import (
    AuthorizationDeniedError,
    AuthorizationError,
    PDUnavailableError,
    PolicyBundleUnavailableError,
    ReasonCode,
    REASON_CODES,
)
from .models import (
    DECISION_SCHEMA_VERSION,
    AuthzDecision,
    AuthzEnvironment,
    AuthzRequest,
    Obligation,
)
from .principal_context import (
    PrincipalContext,
    principal_context_from_request,
)
from .resource_projections import (
    ResourceProjection,
    claim_projection,
    exception_projection,
    opportunity_projection,
)

__all__ = [
    # actions / catalog
    "Action",
        "ACTION_CATALOG",
        "PrincipalType",
        "WorkflowRole",
    "PRINCIPAL_TYPES",
    "AGENT_FORBIDDEN_ACTIONS",
    "PROTECTED_DOMAIN_COMMANDS",
    "UNCACHEABLE_ACTIONS",
    # engine / bundle
    "DecisionEngine",
    "PolicyBundle",
    "load_bundle",
    # client / facade
    "AuthorizationClient",
    "authorize",
    "get_authorization_client",
    "configure_authorization_client",
    "reset_authorization_client",
    # guard
    "CommandGuard",
    "GuardResult",
    # errors
    "AuthorizationError",
    "AuthorizationDeniedError",
    "PDUnavailableError",
    "PolicyBundleUnavailableError",
    "ReasonCode",
    "REASON_CODES",
    # decisions / obligations / cache
    "AuthzDecisionSink",
    "CorrelatedDecisionSink",
    "DecisionStore",
    "LoggingDecisionStore",
    "Obligation",
    "InMemoryAuthzCache",
    # attributes / projections
    "AttributeResolver",
    "StaticAttributeResolver",
    "ResourceProjection",
    "claim_projection",
    "exception_projection",
    "opportunity_projection",
    # models
    "DECISION_SCHEMA_VERSION",
    "AuthzDecision",
    "AuthzEnvironment",
    "AuthzRequest",
    "PrincipalContext",
    "principal_context_from_request",
]