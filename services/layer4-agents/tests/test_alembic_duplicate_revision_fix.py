"""P0-011: L4 Alembic migrations must have a linear chain with unique revision IDs.

Verifies that the duplicate 035 revision has been resolved into a linear
035 -> 036 -> 037 -> 038 chain.
"""

from __future__ import annotations

import re
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def _load_revisions():
    revisions = {}
    seen_files = {}
    for f in sorted(_MIGRATIONS_DIR.glob("*.py")):
        rev = None
        down_rev = None
        for line in f.read_text().splitlines():
            if line.startswith("revision"):
                m = re.search(r'=\s*["\']([^"\']+)["\']', line)
                if m:
                    rev = m.group(1)
            if line.startswith("down_revision"):
                m = re.search(r'=\s*["\']([^"\']+)["\']', line)
                if m:
                    down_rev = m.group(1)
                else:
                    m = re.search(r'=\s*\(([^)]+)\)', line)
                    if m:
                        down_rev = tuple(
                            x.strip().strip('"').strip("'")
                            for x in m.group(1).split(',')
                        )
        if rev:
            revisions[rev] = {"file": f.name, "down_revision": down_rev}
            seen_files.setdefault(rev, []).append(f.name)
    return revisions, seen_files


class TestAlembicRevisionChain:
    """Alembic revision graph must be linear with no duplicates."""

    def test_no_duplicate_revision_ids(self):
        _, seen_files = _load_revisions()
        duplicates = {rev: files for rev, files in seen_files.items() if len(files) > 1}
        assert not duplicates, f"Duplicate revision IDs found: {duplicates}"

    def test_single_head(self):
        revisions, _ = _load_revisions()
        children = {}
        for rev, info in revisions.items():
            down = info["down_revision"]
            if down:
                if isinstance(down, tuple):
                    for d in down:
                        children.setdefault(d, []).append(rev)
                else:
                    children.setdefault(down, []).append(rev)

        heads = [rev for rev in revisions if rev not in children]
        assert len(heads) == 1, f"Expected exactly 1 head, found {len(heads)}: {heads}"

    def test_linear_chain_035_to_038(self):
        """The 035 branch must resolve linearly through 038."""
        revisions, _ = _load_revisions()

        assert "035_add_billing_plan_versions" in revisions
        assert revisions["035_add_billing_plan_versions"]["down_revision"] == "034"

        assert "036_add_billing_customer_sync_state" in revisions
        assert revisions["036_add_billing_customer_sync_state"]["down_revision"] == "035_add_billing_plan_versions"

        assert "037_tenant_scoped_billing_customer_keys" in revisions
        assert revisions["037_tenant_scoped_billing_customer_keys"]["down_revision"] == "036_add_billing_customer_sync_state"

        assert "038_add_billing_webhook_inbox_fields" in revisions
        assert revisions["038_add_billing_webhook_inbox_fields"]["down_revision"] == "037_tenant_scoped_billing_customer_keys"

    def test_no_merge_migrations(self):
        """Merge migrations (tuple down_revision) should not exist after linearization."""
        revisions, _ = _load_revisions()
        merges = [
            rev for rev, info in revisions.items()
            if isinstance(info["down_revision"], tuple)
        ]
        assert not merges, f"Unexpected merge migrations: {merges}"
