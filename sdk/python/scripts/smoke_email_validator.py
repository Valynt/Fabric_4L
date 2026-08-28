"""Smoke test against the built SDK artifact in CI's isolated release env.

CI installs the freshly built wheel (release dependencies only) into a clean
virtual environment and runs this script. Importing ``valuefabric.generated.l4``
requires the ``email-validator`` package at runtime, so a package whose metadata
omits it fails here at import time - catching a missing transitive/optional
dependency that a source-tree check would miss.
"""

from __future__ import annotations

import re

from valuefabric.generated.l4 import (
    Layer4AgentsTenantsApiRoutesRegistrationRegisterTenantRequest,
)


def main() -> None:
    req = Layer4AgentsTenantsApiRoutesRegistrationRegisterTenantRequest(
        name="Acme",
        slug="acme",
        admin_email="ops@acme.example",
    )
    assert req.admin_email == "ops@acme.example"
    assert re.match(r"^[^@]+@[^@]+$", req.admin_email)
    assert req.model_dump()["admin_email"] == "ops@acme.example"
    print("OK: EmailStr field validated on the built SDK artifact")


if __name__ == "__main__":
    main()
