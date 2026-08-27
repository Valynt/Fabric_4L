"""TOMBSTONE: this module is retired and must not be imported.

The canonical Layer 1 SQLAlchemy models live at:

    layer1_ingestion.shared.models

This file (``services/layer1-ingestion/src/shared/models.py``) was a legacy
duplicate of the installed package module. As of 2026-08-26 it had zero
runtime importers, and it is not part of any installed distribution
(``pyproject.toml`` ``packages.find`` only picks up ``layer1_ingestion*``).
Its legacy body defined a second ``declarative_base()`` ``Base`` with an
incomplete table set, which is exactly the "dual Base" hazard this
remediation removes. The legacy body has been deleted; only this tombstone
remains so that any accidental import fails loudly instead of silently
binding to a stale metadata registry.

CI migration drift tooling (``scripts/ci/check_migration_drift.py`` and
``scripts/ci/migration_status_report.py``) and the layer1 mypy overrides now
reference the canonical path.

Regression guard: ``services/layer1-ingestion/tests/test_canonical_models_path.py``

Remediation: brooks-remediation task-1 (2026-08-26)
"""

raise ImportError(
    "services/layer1-ingestion/src/shared/models.py is tombstoned. "
    "Use 'layer1_ingestion.shared.models' instead."
)
