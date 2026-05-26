"""Prompt template registry with immutable version IDs.

This module provides a registry for prompt templates with immutable version IDs,
ensuring prompt/template version lineage is first-class persisted extraction metadata.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class PromptVersion:
    """Immutable prompt version identifier and metadata."""
    
    version_id: str
    template_name: str
    template_hash: str
    created_at: datetime
    description: str
    parameters: dict[str, Any]


class PromptRegistry:
    """Registry for prompt templates with immutable version tracking.
    
    This is a simple file-based registry that can be migrated to a database
    later. For now, it provides immutable version IDs based on template content.
    """
    
    def __init__(self) -> None:
        self._versions: dict[str, PromptVersion] = {}
    
    def register_template(
        self,
        template_name: str,
        template_content: str,
        description: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> PromptVersion:
        """Register a prompt template and return its immutable version ID.
        
        Args:
            template_name: Name of the prompt template
            template_content: The prompt template content
            description: Description of the template
            parameters: Template parameters and their defaults
            
        Returns:
            PromptVersion with immutable version_id
        """
        # Compute content hash for versioning
        template_hash = hashlib.sha256(template_content.encode("utf-8")).hexdigest()
        
        # Compute version ID from template name + hash
        version_payload = f"{template_name}|{template_hash}"
        version_id = hashlib.sha256(version_payload.encode("utf-8")).hexdigest()[:16]
        
        version = PromptVersion(
            version_id=version_id,
            template_name=template_name,
            template_hash=template_hash,
            created_at=datetime.now(UTC),
            description=description,
            parameters=parameters or {},
        )
        
        self._versions[version_id] = version
        return version
    
    def get_version(self, version_id: str) -> PromptVersion | None:
        """Get a prompt version by its ID."""
        return self._versions.get(version_id)
    
    def get_latest_version(self, template_name: str) -> PromptVersion | None:
        """Get the latest version of a template by name."""
        matching = [v for v in self._versions.values() if v.template_name == template_name]
        if not matching:
            return None
        return max(matching, key=lambda v: v.created_at)


# Global registry instance
_registry = PromptRegistry()


def get_prompt_registry() -> PromptRegistry:
    """Get the global prompt registry instance."""
    return _registry


def register_prompt_template(
    template_name: str,
    template_content: str,
    description: str = "",
    parameters: dict[str, Any] | None = None,
) -> str:
    """Register a prompt template and return its immutable version ID.
    
    This is a convenience function that registers a template and returns
    just the version_id string for use in telemetry context.
    
    Args:
        template_name: Name of the prompt template
        template_content: The prompt template content
        description: Description of the template
        parameters: Template parameters and their defaults
        
    Returns:
        Immutable version_id string
    """
    registry = get_prompt_registry()
    version = registry.register_template(template_name, template_content, description, parameters)
    return version.version_id
