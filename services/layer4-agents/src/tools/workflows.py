from __future__ import annotations

"""
Workflow tools that chain multiple operations.
"""


import logging
from typing import Any

from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.models.typed_dict import TypedDictModel

from .analytics import compute_metrics
from .knowledge import get_entity, update_entity


class analyze_entityResult(TypedDictModel):
    entity: Any
    metrics: Any

logger = logging.getLogger(__name__)


async def analyze_entity(
    entity_id: str,
    context: RequestContext | None = None
) -> dict | None:
    """Analyze entity by getting data and computing metrics.
    
    Args:
        entity_id: Entity identifier
        context: Request context (optional)
    
    Returns:
        Analysis results or None if entity not found
    """
    # Get entity (maintains tenant context)
    entity_data = await get_entity(entity_id=entity_id, context=context)
    
    if not entity_data:
        logger.warning(f"Entity {entity_id} not found")
        return None
    
    # Compute metrics (maintains tenant context)
    metrics = await compute_metrics(entity_data=entity_data, context=context)
    
    return analyze_entityResult.model_validate({
        "entity": entity_data,
        "metrics": metrics
    })


async def read_and_update(
    entity_id: str,
    context: RequestContext | None = None
) -> dict | None:
    """Read entity and update it (requires write permission).
    
    Args:
        entity_id: Entity identifier
        context: Request context (required for permission check)
    
    Returns:
        Updated entity or None if not found/permission denied
    """
    # Get entity
    entity_data = await get_entity(entity_id=entity_id, context=context)
    
    if not entity_data:
        logger.warning(f"Entity {entity_id} not found")
        return None
    
    # Update entity (permission check happens here)
    updated = await update_entity(
        entity_id=entity_id,
        updates={"analyzed": True},
        context=context
    )
    
    return updated
