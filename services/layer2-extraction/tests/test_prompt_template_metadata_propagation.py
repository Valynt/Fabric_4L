from __future__ import annotations

from layer2_extraction.api.main import (
    ExtractionArtifacts,
    _deserialize_artifacts,
    _serialize_artifacts,
)
from layer2_extraction.models import ExtractionResult


def test_prompt_template_metadata_persists_through_artifact_serialize_deserialize() -> None:
    result = ExtractionResult(
        job_id="job-1",
        source_url="https://example.com",
        tenant_id="tenant-a",
        schema_version="v1",
        prompt_version="prompt-v1",
        prompt_template_version="entity_extraction_v1+relationship_extraction_v1",
        prompt_template_hash="sha256:abc123",
        model_version="gpt-4o",
    )

    result_json, relationships_json = _serialize_artifacts(ExtractionArtifacts(result=result, relationships=[]))
    restored = _deserialize_artifacts(result_json, relationships_json)

    assert restored.result.prompt_template_version == "entity_extraction_v1+relationship_extraction_v1"
    assert restored.result.prompt_template_hash == "sha256:abc123"


def test_prompt_template_metadata_stable_across_replay_roundtrip() -> None:
    original = ExtractionResult(
        job_id="job-2",
        source_url="https://example.com/retry",
        tenant_id="tenant-a",
        schema_version="v1",
        prompt_version="prompt-v1",
        prompt_template_version="entity_extraction_v1+relationship_extraction_v1",
        model_version="gpt-4o",
    )

    first_json, rel_json = _serialize_artifacts(ExtractionArtifacts(result=original, relationships=[]))
    first_restore = _deserialize_artifacts(first_json, rel_json)
    second_json, _ = _serialize_artifacts(first_restore)
    second_restore = _deserialize_artifacts(second_json, rel_json)

    assert second_restore.result.prompt_template_version == original.prompt_template_version
    assert second_restore.result.prompt_template_hash == original.prompt_template_hash
