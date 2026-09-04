package fabric.authz.evidence

import rego.v1

# Evidence-backed claims: any domain action on a claim that demands evidence
# must have the required evidence satisfied. This is exercised by the
# "missing relationship" path: a claim cannot advance to approve/publish
# without its supporting evidence binding. Domain policies call this helper;
# it is not itself an authorization rule for arbitrary actions.

evidence_satisfied if {
	required := object.get(input.environment, "required_evidence", [])
	provided := object.get(input.environment, "provided_evidence", object.get(input.resource, "evidence", []))
	not some { some r in required; not array_contains(provided, r) }
}
# No required evidence → satisfied by default (base rule).
evidence_satisfied if {
	object.get(input.environment, "required_evidence", null) == null
	object.get(input.resource, "requires_evidence", false) == false
}

array_contains(haystack, needle) if haystack[_] == needle
