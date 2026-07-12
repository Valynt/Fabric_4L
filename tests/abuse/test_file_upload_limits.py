from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_paths_exist, assert_readme_documents_gap

pytestmark = [pytest.mark.abuse, pytest.mark.production_readiness]


def test_file_upload_limit_gap_is_documented() -> None:
    assert_paths_exist(
        (
            "packages/shared/src/value_fabric/shared/storage/client.py",
            "packages/shared/src/value_fabric/shared/storage/tests/test_tenant_scoping.py",
        ),
        label="file storage upload limit references",
    )
    assert_readme_documents_gap("tests/abuse/README.md", "FILE_UPLOAD_RUNTIME_LIMITS")

