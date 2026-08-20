#!/usr/bin/env python3
"""Collection-evidence compatibility name delegated to static governance."""
from test_debt_governance_delegate import delegate

if __name__ == "__main__":
    raise SystemExit(delegate(collection_mode=True))
