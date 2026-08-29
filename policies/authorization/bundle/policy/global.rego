# fabric.authz ? global deny rules (design Section 11.1).
#
# This package owns deny-by-default, tenant equality (necessary, never
# sufficient), the agent categorical-forbidden action set, and known-action
# gating. Domain packages (`claims`, `deliverables`, `exceptions`,
# `opportunities`) own the per-action allow rules and are referenced here so
# every module reports its deny reasons through the same `deny_reason` set.

package fabric.authz

import rego.v1

default allow := false

known_principal_types := {"human", "agent", "service", "external_viewer", "system_control"}

# Categorically forbidden agent actions (design Section 11.1). These are the
# protected transitions that agents may never perform.
agent_forbidden_actions := {"claim.validate", "claim.approve", "claim.include_in_case", "claim.resolve_dispute", "model.mark_canonical", "deliverable.publish_external", "exception.submit", "exception.approve", "exception.activate", "opportunity.lock_realization"}

# The four critical protected-transition verbs (design Section 21, Phase 2).
protected_actions := {"claim.approve", "deliverable.publish_external", "exception.activate", "opportunity.lock_realization"}

# ??? Validity ?????????????????????????????????????????????????????????????

# Tenant equality is necessary but never sufficient. Presence of a matching
# tenant alone grants nothing.
valid_input if {
    input.schema_version == "fabric.authz.request.v1"
    input.principal.type in known_principal_types
    input.principal.tenant_id == input.resource.tenant_id
}

# A known action is one present in the bundled action catalog.
known_action(action) if {
    action in data.action_catalog.actions
}

# Block unknown actions and unknown resource types regardless of everything
# else so an unmodeled capability can never slip through.
action_and_resource_valid if {
    known_action(input.action)
    resource_type_for_action(input.action) == input.resource.type
}

resource_type_for_action(action) := type if {
    entry := data.action_catalog.actions_by_resource[action]
    type := entry.resource_type
}

# ??? Global deny reasons ??????????????????????????????????????????????????

deny_reason contains "TENANT_MISMATCH" if {
    not input.principal.tenant_id == input.resource.tenant_id
}

deny_reason contains "AGENT_ACTION_FORBIDDEN" if {
    input.principal.type == "agent"
    input.action in agent_forbidden_actions
}

deny_reason contains "UNKNOWN_ACTION" if {
    not known_action(input.action)
}

deny_reason contains "UNKNOWN_RESOURCE_TYPE" if {
    known_action(input.action)
    not resource_type_for_action(input.action) == input.resource.type
}

deny_reason contains "PRINCIPAL_INACTIVE" if {
    not input.principal.status == "active"
    not input.action in protected_actions
}

# Union deny reasons from the domain packages so callers get one set.
deny_reason contains rc if {
    data.fabric.authz.claims.deny_reason[rc]
}
deny_reason contains rc if {
    data.fabric.authz.deliverables.deny_reason[rc]
}
deny_reason contains rc if {
    data.fabric.authz.exceptions.deny_reason[rc]
}
deny_reason contains rc if {
    data.fabric.authz.opportunities.deny_reason[rc]
}

# ??? Allow (default deny) ?????????????????????????????????????????????????

# Non-critical known actions: active, same-tenant principal with any
# recognized workflow or platform role. Attribute checks are attached in later
# milestones; tenant equality plus a recognized role is the floor.
allow if {
    valid_input
    action_and_resource_valid
    not input.action in protected_actions
    input.principal.status == "active"
    any_recognized_role
    not agent_categorical
}

agent_categorical if {
    input.principal.type == "agent"
    input.action in agent_forbidden_actions
}

# Domain packages decide the critical four verbs.
allow if {
    data.fabric.authz.claims.allow
}
allow if {
    data.fabric.authz.deliverables.allow
}
allow if {
    data.fabric.authz.exceptions.allow
}
allow if {
    data.fabric.authz.opportunities.allow
}

# Principal has at least one recognized workflow role or any platform role.
any_recognized_role if {
    some role in input.principal.workflow_roles
    role in data.baseline_roles.workflow
}
any_recognized_role if {
    count(input.principal.platform_roles) > 0
}

# ??? Response ?????????????????????????????????????????????????????????????

reason := concat("; ", sort(deny_reason)) if {
    count(deny_reason) > 0
}

reason := "allowed" if {
    count(deny_reason) == 0
    allow
}
