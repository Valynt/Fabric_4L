from __future__ import annotations

import unittest

from scripts.ci.check_pr_governance_fields import (
    extract_field_value,
    is_relevant_change,
    validate_pr_body,
)


class CheckPrGovernanceFieldsTests(unittest.TestCase):
    def test_extract_field_value_reads_markdown_label(self) -> None:
        body = "- **Contract shape impact:** Additive\n"
        self.assertEqual(extract_field_value(body, "Contract shape impact"), "Additive")

    def test_validate_pr_body_requires_all_fields(self) -> None:
        body = """
- **Contract shape impact:** None
- **Tenant isolation impact:** Reviewed-no-impact
- **Compatibility shim impact:** None
"""
        self.assertEqual(validate_pr_body(body), [])

    def test_validate_pr_body_rejects_placeholder_values(self) -> None:
        body = """
- **Contract shape impact:** TBD
- **Tenant isolation impact:** None
"""
        failures = validate_pr_body(body)
        self.assertIn("placeholder value for field: Contract shape impact", failures)
        self.assertIn("missing field: Compatibility shim impact", failures)

    def test_is_relevant_change_matches_backend_frontend_and_contract_paths(self) -> None:
        self.assertTrue(is_relevant_change("apps/web/src/App.tsx"))
        self.assertTrue(is_relevant_change("services/layer4-agents/src/layer4_agents/api/routes/foo.py"))
        self.assertTrue(is_relevant_change("contracts/openapi/layer4-agents.json"))
        self.assertFalse(is_relevant_change("docs/governance.md"))


if __name__ == "__main__":
    unittest.main()
