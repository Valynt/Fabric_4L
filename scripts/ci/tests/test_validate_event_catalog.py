from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "validate-event-catalog.py"
SPEC = importlib.util.spec_from_file_location("validate_event_catalog", MODULE_PATH)
validate_event_catalog = importlib.util.module_from_spec(SPEC)
sys.modules["validate_event_catalog"] = validate_event_catalog
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_event_catalog)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_ENTRY = {
    "event_type": "billing.subscription.activated.v1",
    "name": "Subscription Activated",
    "domain": "billing.subscriptions",
    "owner": "layer7-billing/subscriptions",
    "producer": "services/layer7-billing",
    "triggered_by": ["subscription.activate"],
    "schema_ref": "jsonschema://billing/events/subscription-activated@1.1.0",
    "envelope_ref": "jsonschema://common/event-envelope@1.0.0",
    "subject_type": "subscription",
    "tenant_scope": "TENANT_AND_BILLING_ACCOUNT",
    "delivery": "AT_LEAST_ONCE",
    "partition_key": "billing_account_id",
    "consumer_effect_key": "event.id",
    "expected_latency_ms": 500,
    "criticality": "HIGH",
    "consumers": [
        {"service": "services/api", "purpose": "projection", "supported_versions": ["v1"]}
    ],
    "status": "ACTIVE",
    "event_class": "DOMAIN_EVENT",
    "sensitive_payload": False,
    "replay_behavior": "IDEMPOTENT_REPLAY",
    "retention_classification": "STANDARD",
    "transport_channel": "events.billing",
    "ordering_guarantee": "PARTITION_ORDERED",
}


def make_entry(**overrides):
    entry = dict(VALID_ENTRY)
    entry.update(overrides)
    return entry


# ---------------------------------------------------------------------------
# Rule 1 — Entry validity
# ---------------------------------------------------------------------------


def test_rule_1_valid_entry_passes():
    violations = validate_event_catalog.check_rule_1_entries_valid([("billing", VALID_ENTRY)])
    assert violations == []


def test_rule_1_missing_required_fields():
    entry = {k: v for k, v in VALID_ENTRY.items() if k != "event_type"}
    violations = validate_event_catalog.check_rule_1_entries_valid([("billing", entry)])
    assert any("Missing required fields" in v.message for v in violations)


def test_rule_1_invalid_event_type_format():
    entry = make_entry(event_type="bad-format")
    violations = validate_event_catalog.check_rule_1_entries_valid([("billing", entry)])
    assert any("Invalid event_type format" in v.message for v in violations)


def test_rule_1_invalid_status():
    entry = make_entry(status="UNKNOWN")
    violations = validate_event_catalog.check_rule_1_entries_valid([("billing", entry)])
    assert any("Invalid status" in v.message for v in violations)


def test_rule_1_invalid_event_class():
    entry = make_entry(event_class="AUDIT_EVENT")
    violations = validate_event_catalog.check_rule_1_entries_valid([("billing", entry)])
    assert any("Invalid event_class" in v.message for v in violations)


def test_rule_1_consumer_missing_field():
    entry = make_entry(consumers=[{"service": "svc", "purpose": "p"}])
    violations = validate_event_catalog.check_rule_1_entries_valid([("billing", entry)])
    assert any("missing field: supported_versions" in v.message for v in violations)


# ---------------------------------------------------------------------------
# Rule 2 — Schema registered
# ---------------------------------------------------------------------------


def test_rule_2_envelope_not_in_index():
    entry = make_entry(envelope_ref="jsonschema://common/unknown-envelope@1.0.0")
    schema_index = {"entries": [{"path": "contracts/jsonschema/common/event-envelope@1.0.0.schema.json"}]}
    violations = validate_event_catalog.check_rule_2_schema_registered([("billing", entry)], schema_index)
    assert any("Envelope schema not in schema-index" in v.message for v in violations)


def test_rule_2_envelope_in_index_passes():
    entry = make_entry(envelope_ref="jsonschema://common/event-envelope@1.0.0")
    schema_index = {
        "entries": [
            {"path": "contracts/jsonschema/common/event-envelope@1.0.0.schema.json"},
            {"path": "contracts/jsonschema/billing/events/subscription-activated@1.1.0.schema.json"},
        ]
    }
    violations = validate_event_catalog.check_rule_2_schema_registered([("billing", entry)], schema_index)
    assert violations == []


def test_rule_2_payload_schema_missing_from_index_fails():
    """schema_ref hard-check: a payload schema not present in the schema-index is a Rule 2 violation."""
    entry = make_entry(schema_ref="jsonschema://billing/events/subscription-activated@1.1.0")
    schema_index = {"entries": [{"path": "contracts/jsonschema/common/event-envelope@1.0.0.schema.json"}]}
    violations = validate_event_catalog.check_rule_2_schema_registered([("billing", entry)], schema_index)
    assert any("Payload schema not in schema-index" in v.message for v in violations)


def test_rule_2_payload_schema_in_index_passes():
    entry = make_entry(schema_ref="jsonschema://billing/events/subscription-activated@1.1.0")
    schema_index = {
        "entries": [
            {"path": "contracts/jsonschema/common/event-envelope@1.0.0.schema.json"},
            {"path": "contracts/jsonschema/billing/events/subscription-activated@1.1.0.schema.json"},
        ]
    }
    violations = validate_event_catalog.check_rule_2_schema_registered([("billing", entry)], schema_index)
    assert violations == []


def test_rule_2_payload_schema_stripped_version_match_passes():
    """A payload schema indexed without the @version suffix must still resolve."""
    entry = make_entry(schema_ref="jsonschema://billing/events/subscription-activated@1.1.0")
    schema_index = {
        "entries": [
            {"path": "contracts/jsonschema/common/event-envelope@1.0.0.schema.json"},
            {"path": "contracts/jsonschema/billing/events/subscription-activated.schema.json"},
        ]
    }
    violations = validate_event_catalog.check_rule_2_schema_registered([("billing", entry)], schema_index)
    assert violations == []


def test_rule_2_schema_ref_missing_prefix_fails():
    """schema_ref without the jsonschema:// prefix is rejected."""
    entry = make_entry(schema_ref="billing/events/subscription-activated@1.1.0")
    schema_index = {"entries": [{"path": "contracts/jsonschema/common/event-envelope@1.0.0.schema.json"}]}
    violations = validate_event_catalog.check_rule_2_schema_registered([("billing", entry)], schema_index)
    assert any("must use the jsonschema:// prefix" in v.message for v in violations)


# ---------------------------------------------------------------------------
# Rule 3 — Owner present
# ---------------------------------------------------------------------------


def test_rule_3_missing_owner():
    entry = make_entry(owner="")
    violations = validate_event_catalog.check_rule_3_owner_present([("billing", entry)])
    assert any("Missing or invalid bounded-context owner" in v.message for v in violations)


def test_rule_3_valid_owner_passes():
    violations = validate_event_catalog.check_rule_3_owner_present([("billing", VALID_ENTRY)])
    assert violations == []


# ---------------------------------------------------------------------------
# Rule 4 — Unique producer
# ---------------------------------------------------------------------------


def test_rule_4_multiple_producers_for_same_event():
    entries = [
        ("billing", make_entry(event_type="billing.subscription.activated.v1", producer="svc-a")),
        ("billing", make_entry(event_type="billing.subscription.activated.v1", producer="svc-b")),
    ]
    violations = validate_event_catalog.check_rule_4_unique_producer(entries)
    assert any("Multiple producers" in v.message for v in violations)


def test_rule_4_unique_producer_passes():
    entries = [
        ("billing", make_entry(event_type="billing.subscription.activated.v1", producer="svc-a")),
        ("billing", make_entry(event_type="billing.subscription.created.v1", producer="svc-b")),
    ]
    violations = validate_event_catalog.check_rule_4_unique_producer(entries)
    assert violations == []


# ---------------------------------------------------------------------------
# Rule 5 — Active consumer versions
# ---------------------------------------------------------------------------


def test_rule_5_consumer_missing_version():
    entries = [("billing", VALID_ENTRY)]
    subs = [("api", {"event_type": "billing.subscription.activated.v1", "supported_versions": []})]
    violations = validate_event_catalog.check_rule_5_active_consumer_versions(entries, subs)
    assert any("does not support expected versions" in v.message for v in violations)


def test_rule_5_consumer_correct_version_passes():
    entries = [("billing", VALID_ENTRY)]
    subs = [("api", {"event_type": "billing.subscription.activated.v1", "supported_versions": ["v1"]})]
    violations = validate_event_catalog.check_rule_5_active_consumer_versions(entries, subs)
    assert violations == []


# ---------------------------------------------------------------------------
# Rule 6 — No active removal
# ---------------------------------------------------------------------------


def test_rule_6_consumer_subscribes_to_nonexistent_event():
    entries = [("billing", make_entry(event_type="billing.subscription.activated.v1", status="ACTIVE"))]
    subs = [("api", {"event_type": "billing.subscription.deleted.v1"})]
    violations = validate_event_catalog.check_rule_6_no_active_removal(entries, subs)
    assert any("subscribes to non-existent event" in v.message for v in violations)


def test_rule_6_valid_subscription_passes():
    entries = [("billing", VALID_ENTRY)]
    subs = [("api", {"event_type": "billing.subscription.activated.v1"})]
    violations = validate_event_catalog.check_rule_6_no_active_removal(entries, subs)
    assert violations == []


# ---------------------------------------------------------------------------
# Rule 7 — No name reuse
# ---------------------------------------------------------------------------


def test_rule_7_name_reuse_different_domain():
    entries = [
        ("billing", make_entry(event_type="billing.subscription.activated.v1", domain="billing.subscriptions")),
        ("billing", make_entry(event_type="billing.subscription.activated.v1", domain="billing.legacy")),
    ]
    violations = validate_event_catalog.check_rule_7_no_name_reuse(entries)
    assert any("reused with different domain" in v.message for v in violations)


def test_rule_7_no_reuse_passes():
    entries = [
        ("billing", make_entry(event_type="billing.subscription.activated.v1")),
        ("billing", make_entry(event_type="billing.subscription.created.v1")),
    ]
    violations = validate_event_catalog.check_rule_7_no_name_reuse(entries)
    assert violations == []


# ---------------------------------------------------------------------------
# Rule 8 — Sensitive payload consistency
# ---------------------------------------------------------------------------


def test_rule_8_sensitive_payload_not_bool():
    entry = make_entry(sensitive_payload="yes")
    violations = validate_event_catalog.check_rule_8_sensitive_consistency([("billing", entry)])
    assert any("sensitive_payload must be a boolean" in v.message for v in violations)


def test_rule_8_sensitive_event_with_examples():
    entry = make_entry(sensitive_payload=True, examples=[{"id": "ex-1"}])
    violations = validate_event_catalog.check_rule_8_sensitive_consistency([("billing", entry)])
    assert any("Sensitive event has examples" in v.message for v in violations)


def test_rule_8_valid_passes():
    violations = validate_event_catalog.check_rule_8_sensitive_consistency([("billing", VALID_ENTRY)])
    assert violations == []


# ---------------------------------------------------------------------------
# Rule 9 — Documentation complete
# ---------------------------------------------------------------------------


def test_rule_9_missing_documentation_fields():
    entry = {k: v for k, v in VALID_ENTRY.items() if k not in ("transport_channel", "ordering_guarantee")}
    violations = validate_event_catalog.check_rule_9_documentation_complete([("billing", entry)])
    assert any("Missing documentation fields" in v.message for v in violations)


def test_rule_9_complete_passes():
    violations = validate_event_catalog.check_rule_9_documentation_complete([("billing", VALID_ENTRY)])
    assert violations == []


# ---------------------------------------------------------------------------
# Rule 10 — Consumer subscriptions in catalog
# ---------------------------------------------------------------------------


def test_rule_10_unknown_event_in_subscription():
    entries = [("billing", VALID_ENTRY)]
    subs = [("api", {"event_type": "billing.subscription.deleted.v1"})]
    violations = validate_event_catalog.check_rule_10_consumer_subscriptions_in_catalog(entries, subs)
    assert any("subscribes to event not in catalog" in v.message for v in violations)


def test_rule_10_known_event_passes():
    entries = [("billing", VALID_ENTRY)]
    subs = [("api", {"event_type": "billing.subscription.activated.v1"})]
    violations = validate_event_catalog.check_rule_10_consumer_subscriptions_in_catalog(entries, subs)
    assert violations == []


# ---------------------------------------------------------------------------
# Integration — full run against production catalog
# ---------------------------------------------------------------------------


def test_main_happy_path_against_production_catalog():
    """Run the gate against the committed catalog and assert it passes."""
    with patch.object(sys, "argv", ["validate-event-catalog.py"]):
        assert validate_event_catalog.main() == 0


def test_main_strict_flag_does_not_change_exit_code_on_clean_catalog():
    with patch.object(sys, "argv", ["validate-event-catalog.py", "--strict"]):
        assert validate_event_catalog.main() == 0
