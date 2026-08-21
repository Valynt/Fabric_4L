"""Tests for the PR size policy gate.

Covers the fixes from Codex PR review #1393:
- ``extract_field_value`` must parse the ``**Size justification:**`` bold
  format used in the PR template (the original regex only handled single
  asterisks).
- An untouched PR template (HTML-comment instructions) must not pass the
  size gate as a valid justification.
- ``parse_additions`` fallback: when the GitHub event payload lacks
  per-file stats, the gate must use ``git diff --numstat`` against the
  base ref to subtract generated/lockfile additions instead of returning
  the unfiltered aggregate total.
"""
from __future__ import annotations

import unittest
from unittest import mock
from pathlib import Path

from scripts.ci import check_pr_size_policy


class ExtractFieldValueTests(unittest.TestCase):
    def test_parses_bold_field(self) -> None:
        body = "- **Size justification:** Cannot split because the migration is atomic.\n"
        self.assertEqual(
            check_pr_size_policy.extract_field_value(body, "Size justification"),
            "Cannot split because the migration is atomic.",
        )

    def test_parses_italic_field(self) -> None:
        body = "*Size justification:* Cannot split because the migration is atomic.\n"
        self.assertEqual(
            check_pr_size_policy.extract_field_value(body, "Size justification"),
            "Cannot split because the migration is atomic.",
        )

    def test_returns_none_when_field_absent(self) -> None:
        body = "## Summary\nNo size justification here.\n"
        self.assertIsNone(
            check_pr_size_policy.extract_field_value(body, "Size justification"),
        )


class PlaceholderJustificationTests(unittest.TestCase):
    def test_rejects_empty_and_common_placeholders(self) -> None:
        for value in ("", "tbd", "todo", "pending", "?", "n/a", "none"):
            self.assertTrue(
                check_pr_size_policy.is_placeholder_justification(value),
                f"Expected {value!r} to be a placeholder",
            )

    def test_rejects_html_comment_only_value(self) -> None:
        html = "<!-- Required when the PR is large. Replace this comment. -->"
        self.assertTrue(check_pr_size_policy.is_placeholder_justification(html))

    def test_accepts_concrete_rationale(self) -> None:
        value = "Cannot split because the schema migration is atomic and must ship in one PR."
        self.assertFalse(check_pr_size_policy.is_placeholder_justification(value))


class ParseAdditionsFallbackTests(unittest.TestCase):
    def test_uses_payload_files_when_available(self) -> None:
        payload = {
            "pull_request": {
                "additions": 500,
                "files": [
                    {"filename": "services/layer1/src/main.py", "additions": 300},
                    {"filename": "pnpm-lock.yaml", "additions": 200},
                ],
            }
        }
        net, relevant = check_pr_size_policy.parse_additions(payload, "")
        # 500 total - 200 excluded (pnpm-lock.yaml) = 300 net
        self.assertEqual(net, 300)
        self.assertEqual(relevant, {"services/layer1/src/main.py"})

    def test_falls_back_to_git_numstat_when_files_absent(self) -> None:
        payload = {
            "pull_request": {
                "additions": 1500,
                "base": {"ref": "main"},
                # No "files" array — simulates the pull_request event body.
            }
        }
        env_changed = "services/layer1/src/main.py pnpm-lock.yaml"
        numstat = {
            "services/layer1/src/main.py": 20,
            "pnpm-lock.yaml": 1480,
        }
        with mock.patch.object(
            check_pr_size_policy, "_git_numstat", return_value=numstat
        ):
            net, relevant = check_pr_size_policy.parse_additions(
                payload, env_changed
            )
        # 1500 total - 1480 excluded (pnpm-lock.yaml) = 20 net
        self.assertEqual(net, 20)
        self.assertEqual(relevant, {"services/layer1/src/main.py"})

    def test_falls_back_to_membership_when_git_unavailable(self) -> None:
        """When git diff fails, the last-resort fallback over-counts
        (aggregate additions) but never under-counts."""
        payload = {
            "pull_request": {
                "additions": 1500,
                "base": {"ref": "main"},
            }
        }
        env_changed = "services/layer1/src/main.py pnpm-lock.yaml"
        with mock.patch.object(
            check_pr_size_policy, "_git_numstat", return_value={}
        ):
            net, relevant = check_pr_size_policy.parse_additions(
                payload, env_changed
            )
        # Fallback returns aggregate additions (over-counts) and filters
        # relevant files by membership.
        self.assertEqual(net, 1500)
        self.assertEqual(relevant, {"services/layer1/src/main.py"})


class GitNumstatTests(unittest.TestCase):
    def test_parses_numstat_output(self) -> None:
        fake_output = "10\t5\tservices/layer1/src/main.py\n20\t0\tpnpm-lock.yaml\n-\t-\tbinary.png\n"
        result = mock.Mock(stdout=fake_output, returncode=0)
        with mock.patch.object(
            check_pr_size_policy.subprocess, "run", return_value=result
        ):
            stats = check_pr_size_policy._git_numstat("main")
        self.assertEqual(stats, {"services/layer1/src/main.py": 10, "pnpm-lock.yaml": 20})

    def test_returns_empty_on_git_failure(self) -> None:
        result = mock.Mock(stdout="", returncode=1)
        with mock.patch.object(
            check_pr_size_policy.subprocess, "run", return_value=result
        ):
            stats = check_pr_size_policy._git_numstat("nonexistent-ref")
        self.assertEqual(stats, {})


if __name__ == "__main__":
    unittest.main()
