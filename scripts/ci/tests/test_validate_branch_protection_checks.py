from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.validate_branch_protection_checks import (
    compute_diff,
    compute_gap_drift,
    compute_review_policy_drift,
    load_conditional_checks,
    load_enforced_checks,
    load_enforced_review_policy,
    load_expected_checks,
    load_expected_review_policy,
    load_gap_file,
    split_policy_drift,
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

    def test_load_conditional_checks_reads_contexts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "required-checks.json"
            config_path.write_text(
                json.dumps(
                    {
                        "conditional_status_checks": [
                            {"context": "Security Gates Required", "reason": "PR-only"},
                            {"context": "SDK Release Validation", "reason": "path-scoped"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                load_conditional_checks(config_path),
                ["Security Gates Required", "SDK Release Validation"],
            )

    def test_load_conditional_checks_absent_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "required-checks.json"
            config_path.write_text(json.dumps({"required_status_checks": ["a"]}), encoding="utf-8")
            self.assertEqual(load_conditional_checks(config_path), [])

    def test_load_gap_file_missing_returns_strict_empty(self) -> None:
        # No --gap-file on the scheduled run: strict mode, nothing is tolerated.
        self.assertEqual(
            load_gap_file(None), {"gaps": [], "conditional_contexts": [], "review_policy_gaps": []}
        )

    def test_load_gap_file_reads_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gap_path = Path(tmp) / "gap.json"
            gap_path.write_text(
                json.dumps(
                    {
                        "gaps": [{"context": "01-repository-integrity", "status": "pending"}],
                        "conditional_contexts": [{"context": "Security Gates Required"}],
                    }
                ),
                encoding="utf-8",
            )
            parsed = load_gap_file(gap_path)
            self.assertEqual(parsed["gaps"][0]["context"], "01-repository-integrity")
            self.assertEqual(parsed["conditional_contexts"][0]["context"], "Security Gates Required")

    def test_load_gap_file_missing_path_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gap_path = Path(tmp) / "nope.json"
            with self.assertRaises(ValueError):
                load_gap_file(gap_path)

    def test_compute_gap_drift_tracked_missing_is_warning_only(self) -> None:
        expected = ["01-repository-integrity", "already-enforced"]
        enforced = ["already-enforced"]
        gap = {"gaps": [{"context": "01-repository-integrity", "status": "pending"}]}
        fatal, warnings = compute_gap_drift(expected, enforced, [], gap)
        self.assertEqual(fatal, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("tracked in gap ledger", warnings[0])

    def test_compute_gap_drift_unrepresented_missing_is_fatal(self) -> None:
        expected = ["01-repository-integrity"]
        enforced: list[str] = []
        fatal, warnings = compute_gap_drift(expected, enforced, [], {"gaps": []})
        self.assertEqual(warnings, [])
        self.assertEqual(len(fatal), 1)
        self.assertIn("not represented in gap ledger", fatal[0])

    def test_compute_gap_drift_strict_mode_any_missing_is_fatal(self) -> None:
        # Scheduled run: gap file absent => empty ledger => missing must be fatal.
        expected = ["01-repository-integrity"]
        enforced: list[str] = []
        fatal, _ = compute_gap_drift(expected, enforced, [], {"gaps": []})
        self.assertEqual(len(fatal), 1)

    def test_compute_gap_drift_unexpected_enforced_is_fatal(self) -> None:
        fatal, warnings = compute_gap_drift(
            ["a"], ["a", "rogue-check"], [], {"gaps": []}
        )
        self.assertEqual(warnings, [])
        self.assertEqual(len(fatal), 1)
        self.assertIn("not declared universal", fatal[0])

    def test_compute_gap_drift_stale_ledger_entry_is_fatal(self) -> None:
        # Ledger references a context that is no longer declared universal.
        gap = {"gaps": [{"context": "removed-check", "status": "pending"}]}
        fatal, _ = compute_gap_drift(["a"], ["a"], [], gap)
        self.assertEqual(len(fatal), 1)
        self.assertIn("no longer declared universal", fatal[0])

    def test_compute_gap_drift_conditional_leak_into_required_is_fatal(self) -> None:
        # A conditional context must never be a universal required check.
        conditional = ["SDK Release Validation"]
        fatal, _ = compute_gap_drift(
            ["SDK Release Validation"], [], conditional, {"gaps": []}
        )
        self.assertGreaterEqual(len(fatal), 1)
        self.assertTrue(
            any("must not be a universal required check" in line for line in fatal)
        )

    def test_compute_gap_drift_conditional_enforced_is_fatal(self) -> None:
        # A conditional context must not be enforced by branch protection.
        conditional = ["Security Gates Required"]
        fatal, _ = compute_gap_drift([], ["Security Gates Required"], conditional, {"gaps": []})
        self.assertGreaterEqual(len(fatal), 1)
        self.assertTrue(
            any("must not be enforced by branch protection" in line for line in fatal)
        )

    def test_compute_gap_drift_full_reconciliation_passes(self) -> None:
        expected = ["a", "b"]
        enforced = ["a", "b"]
        fatal, warnings = compute_gap_drift(expected, enforced, [], {"gaps": []})
        self.assertEqual(fatal, [])
        self.assertEqual(warnings, [])

    def test_split_policy_drift_documented_gap_is_warning(self) -> None:
        gap = {"review_policy_gaps": [{"policy": "required_conversation_resolution"}]}
        fatal, warnings = split_policy_drift(
            ["required_conversation_resolution: expected True but enforced False"], gap
        )
        self.assertEqual(fatal, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("tracked in gap ledger", warnings[0])

    def test_split_policy_drift_undocumented_is_fatal(self) -> None:
        fatal, warnings = split_policy_drift(
            ["required_conversation_resolution: expected True but enforced False"], {"gaps": []}
        )
        self.assertEqual(warnings, [])
        self.assertEqual(len(fatal), 1)

    def test_split_policy_drift_strict_mode_all_fatal(self) -> None:
        # No --gap-file on the scheduled run: the empty ledger documents nothing,
        # so every policy drift message remains fatal.
        fatal, warnings = split_policy_drift(
            ["required_conversation_resolution: expected True but enforced False"],
            {"gaps": [], "conditional_contexts": [], "review_policy_gaps": []},
        )
        self.assertEqual(warnings, [])
        self.assertEqual(len(fatal), 1)

    def test_review_policy_absent_enforcement_satisfies_false_expectation(self) -> None:
        # require_code_owner_reviews is False in config; branch protection absent
        # the setting entirely (rpr: null). Absence satisfies a False intent,
        # so it must not be reported as drift.
        expected = {"require_code_owner_reviews": False}
        enforced = {}
        self.assertEqual(compute_review_policy_drift(expected, enforced), [])

    def test_review_policy_drift_detects_true_expectation_absent_enforcement(self) -> None:
        expected = {"dismiss_stale_reviews": True}
        enforced = {}
        drift = compute_review_policy_drift(expected, enforced)
        self.assertEqual(len(drift), 1)
        self.assertIn("dismiss_stale_reviews", drift[0])


if __name__ == "__main__":
    unittest.main()
