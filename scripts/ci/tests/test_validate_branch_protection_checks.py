from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.ci.validate_branch_protection_checks import compute_diff, load_enforced_checks, load_expected_checks


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


if __name__ == "__main__":
    unittest.main()
