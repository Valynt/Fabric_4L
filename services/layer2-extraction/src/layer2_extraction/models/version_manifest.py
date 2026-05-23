"""Version manifest models for extraction runs."""

from pydantic import BaseModel, ConfigDict, Field


class VersionManifest(BaseModel):
    """Active version set for an extraction run."""

    model_config = ConfigDict(extra="forbid")

    prompt_version: str = Field(..., min_length=1)
    schema_version: str = Field(..., min_length=1)
    model_version: str = Field(..., min_length=1)
    extraction_version: str = Field(..., min_length=1)
    value_pack_version: str = Field(..., min_length=1)


DEFAULT_VERSION_MANIFEST = VersionManifest(
    prompt_version="v1",
    schema_version="v1",
    model_version="gpt-4o",
    extraction_version="v1",
    value_pack_version="v1",
)
