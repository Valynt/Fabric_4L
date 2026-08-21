from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.validate_branch_protection_checks import (
    compute_diff,
    compute_review_policy_drift,
    load_enforced_checks,
    load_enforced_review_policy,
    load_expected_checks,
    load_expected_review_policy,
)


class ValidateBranchProtectionChecksTests(unittest.TestCase):
    def test_load_expected_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "required-checks.json"
            config_path.write_text(
                json.dumps({"required_status_checks": ["check-a", "check-b"]}), encoding="utf-8"
            )
            self.assertEqual(load_expected_checks(config_path), ["check-a", "check-b"])

    def test_compute_diff_detects_missing_and_unexpected(self) -> None:
        missing, unexpected = compute_diff(
            expected=["check-a", "check-b"],
            enforced=["check-b", "check-c"],
        )
        self.assertEqual(missing, ["check-a"])
        self.assertEqual(unexpected, ["check-c"])

    def test_load_enforced_checks_from_api_shape(self) -> None:
        payload = {
            "required_status_checks": {
                "checks": [
                    {"context": "check-a"},
                    {"context": "check-b"},
                ]
            }
        }
        self.assertEqual(load_enforced_checks(payload), ["check-a", "check-b"])

    def test_load_enforced_checks_from_legacy_name_shape(self) -> None:
        payload = {
            "required_status_checks": {
                "checks": [
                    {"name": "check-a"},
                    {"name": "check-b"},
                ]
            }
        }
        self.assertEqual(load_enforced_checks(payload), ["check-a", "check-b"])

    def test_load_expected_review_policy_returns_empty_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "required-checks.json"
            config_path.write_text(
                json.dumps({"required_status_checks": ["check-a"]}), encoding="utf-8"
            )
            self.assertEqual(load_expected_review_policy(config_path), {})

    def test_load_expected_review_policy_reads_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "required-checks.json"
            config_path.write_text(
                json.dumps({
                    "required_status_checks": ["check-a"],
                    "required_pull_request_reviews": {
                        "required_approving_review_count": 1,
                        "dismiss_stale_reviews": True,
                        "require_code_owner_reviews": False,
                    },
                    "required_conversation_resolution": True,
                }),
                encoding="utf-8",
            )
            policy = load_expected_review_policy(config_path)
            self.assertEqual(policy["required_approving_review_count"], 1)
            self.assertTrue(policy["dismiss_stale_reviews"])
            self.assertFalse(policy["require_code_owner_reviews"])
            self.assertTrue(policy["required_conversation_resolution"])

    def test_load_enforced_review_policy_from_api(self) -> None:
        payload = {
            "required_pull_request_reviews": {
                "required_approving_review_count": 2,
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": False,
            },
            "required_conversation_resolution": {"enabled": True},
        }
        enforced = load_enforced_review_policy(payload)
        self.assertEqual(enforced["required_approving_review_count"], 2)
        self.assertTrue(enforced["dismiss_stale_reviews"])
        self.assertTrue(enforced["required_conversation_resolution"])

    def test_load_enforced_review_policy_when_unset(self) -> None:
        enforced = load_enforced_review_policy({})
        self.assertIsNone(enforced["required_approving_review_count"])
        self.assertIsNone(enforced["dismiss_stale_reviews"])
        self.assertIsNone(enforced["required_conversation_resolution"])

    def test_review_policy_drift_detects_missing_reviews(self) -> None:
        expected = {"required_approving_review_count": 1}
        enforced = {"required_approving_review_count": None}
        drift = compute_review_policy_drift(expected, enforced)
        self.assertEqual(len(drift), 1)
        self.assertIn("expected >=1 but enforced None", drift[0])

    def test_review_policy_drift_detects_disabled_conversation_resolution(self) -> None:
        # Regression for PR #1365 -> #1375: merge before review-thread fixes.
        expected = {"required_conversation_resolution": True}
        enforced = {"required_conversation_resolution": False}
        drift = compute_review_policy_drift(expected, enforced)
        self.assertEqual(len(drift), 1)
        self.assertIn("required_conversation_resolution", drift[0])
        self.assertIn("enforced False", drift[0])

    def test_review_policy_no_drift_when_compliant(self) -> None:
        expected = {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "required_conversation_resolution": True,
        }
        enforced = dict(expected)
        self.assertEqual(compute_review_policy_drift(expected, enforced), [])


if __name__ == "__main__":
    unittest.main()
