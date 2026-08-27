"""Regression guard: Layer 1 models canonical path enforcement.

Ensures that:
  1. The canonical runtime models module (layer1_ingestion.shared.models) is
     importable and exposes the expected entities.
  2. The legacy path (services/layer1-ingestion/src/shared/models.py) stays
     dead — either physically absent, or present only as a tombstone that
     raises ImportError and retains no model definitions — so it can never
     accidentally serve as the runtime Base.

These tests prevent the "dual Base" architecture debt from silently
re-emerging after the brooks-remediation/task-1 consolidation.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Repo-relative location of the retired legacy models module. Resolved from this
# test file rather than the process CWD so the assertion is independent of where
# pytest is invoked from and of the active import mode (prepend/importlib).
LEGACY_MODELS_PATH = Path(__file__).resolve().parents[1] / "src" / "shared" / "models.py"


class TestCanonicalModelsPath:
    """The canonical models module must be importable and complete."""

    def test_canonical_module_importable(self):
        """layer1_ingestion.shared.models must be importable without error."""
        mod = importlib.import_module("layer1_ingestion.shared.models")
        assert mod is not None

    def test_canonical_base_is_declarative_base(self):
        """Base must use the modern DeclarativeBase API, not the legacy factory."""
        from sqlalchemy.orm import DeclarativeBase

        from layer1_ingestion.shared.models import Base

        assert issubclass(Base, DeclarativeBase), (
            "layer1_ingestion.shared.models.Base must subclass DeclarativeBase "
            "(not the legacy declarative_base() return value)"
        )

    def test_canonical_module_has_required_tables(self):
        """The canonical Base.metadata must include all expected table names."""
        from layer1_ingestion.shared.models import Base

        registered = set(Base.metadata.tables.keys())
        # Legacy tables (v1/v2 pipeline)
        legacy_tables = {
            "scraping_targets",
            "scraping_jobs",
            "job_stage_details",
            "job_errors",
            "raw_content",
            "extracted_data",
            "compliance_logs",
            "proxy_pools",
            "robots_txt_cache",
            "crawl_queue",
            "crawl_decisions",
            "source_corpuses",
            "account_intelligence_packets",
            "event_outbox",
            "tenant_registry",
        }
        # v3.0 Source Ingestion Layer tables (must NOT be missing from canonical)
        v3_tables = {
            "ingested_sources",
            "source_versions",
            "source_ingestion_runs",
            "ingestion_run_steps",
            "normalized_documents",
            "source_consents",
            "evidence_chunks",
        }
        all_expected = legacy_tables | v3_tables
        missing = all_expected - registered
        assert not missing, (
            f"Canonical Base.metadata is missing expected tables: {sorted(missing)}. "
            "Ensure layer1_ingestion.shared.models defines all legacy + v3.0 tables."
        )

    def test_canonical_module_exposes_v3_enums(self):
        """v3.0 enums must be present in the canonical module."""
        import layer1_ingestion.shared.models as m

        expected_enums = (
            "IngestionRunStatus",
            "CustodyMode",
            "SourceType",
            "SourceConsentStatus",
            "EvidenceChunkStatus",
        )
        for name in expected_enums:
            assert hasattr(m, name), (
                f"Canonical layer1_ingestion.shared.models is missing v3.0 enum: {name}"
            )


class TestLegacyPathTombstoned:
    """The legacy ``src/shared/models.py`` path must be dead.

    "Dead" is satisfied by either of two end states:

    1. The file no longer exists (it was physically deleted), or
    2. The file exists only as a tombstone that raises ``ImportError``.

    Both are accepted so that the eventual physical deletion of the legacy
    file does not turn this regression guard into a false failure.
    """

    def test_legacy_models_path_is_absent_or_tombstoned(self):
        """Legacy models must be unloadable as a runtime module.

        If this test fails it means the legacy models file has been
        un-tombstoned and once again exposes runtime ORM entities —
        re-introducing dual-Base architecture debt.
        """
        if not LEGACY_MODELS_PATH.exists():
            # Strongest form of the guarantee: nothing left to import.
            return

        spec = importlib.util.spec_from_file_location(
            "_legacy_layer1_models_tombstone_probe", LEGACY_MODELS_PATH
        )
        assert spec is not None and spec.loader is not None, (
            f"Could not build an import spec for {LEGACY_MODELS_PATH}"
        )
        module = importlib.util.module_from_spec(spec)

        # Executed off a file-location spec and never registered in sys.modules,
        # so this neither depends on nor pollutes the ambient import state.
        with pytest.raises(ImportError) as excinfo:
            spec.loader.exec_module(module)

        assert "layer1_ingestion.shared.models" in str(excinfo.value), (
            "The legacy models tombstone must point callers at the canonical "
            f"module; got: {excinfo.value!r}"
        )

    def test_legacy_models_file_defines_no_orm_entities(self):
        """A tombstone must not retain an unreachable legacy model body.

        Leaving ~900 lines of dead ORM code below the ``raise`` keeps the
        duplicate definitions in the tree (and trips lint/type baselines),
        so the tombstone is only genuine once the body is gone.
        """
        if not LEGACY_MODELS_PATH.exists():
            return

        tree = ast.parse(LEGACY_MODELS_PATH.read_text(encoding="utf-8"))
        offending = [
            type(node).__name__
            for node in tree.body
            if not isinstance(node, ast.Raise)
            and not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))
        ]
        assert not offending, (
            f"{LEGACY_MODELS_PATH} must contain only a docstring and a raise; "
            f"found top-level statements: {offending}. The legacy model body "
            "must be removed, not merely shadowed by a raise."
        )
        assert any(isinstance(node, ast.Raise) for node in tree.body), (
            f"{LEGACY_MODELS_PATH} exists but does not raise; it must fail closed."
        )
