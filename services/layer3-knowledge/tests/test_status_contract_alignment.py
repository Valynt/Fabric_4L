import json
from pathlib import Path

from value_fabric.shared.contracts.layer3_statuses import (
    ENTITY_STATUSES,
    HEALTH_STATUSES,
    INGEST_STATUSES,
    SYNC_STATUSES,
)


def _openapi_schemas() -> dict:
    path = Path(__file__).resolve().parents[3] / 'contracts' / 'openapi' / 'layer3-knowledge.json'
    return json.loads(path.read_text())['components']['schemas']


def test_status_constants_align_with_openapi_contract() -> None:
    schemas = _openapi_schemas()
    assert tuple(schemas['DependencyStatus']['properties']['status']['enum']) == HEALTH_STATUSES
    assert tuple(schemas['IngestResponse']['properties']['status']['enum']) == INGEST_STATUSES
    assert tuple(schemas['SyncStatusResponse']['properties']['status']['anyOf'][0]['enum']) == SYNC_STATUSES
    assert tuple(schemas['EntitySummary']['properties']['status']['enum']) == ENTITY_STATUSES
    assert tuple(schemas['EntityDetail']['properties']['status']['enum']) == ENTITY_STATUSES
