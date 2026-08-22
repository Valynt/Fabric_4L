from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
)

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Provides endpoints for Value Model CRUD and management.

All Cypher queries are tenant-scoped via `create_neo4j_tenant_session`.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_context

from src.logging_config import get_logger

from ...api.dependencies_tenant_secured import create_neo4j_tenant_session
from ...api.exceptions import DatabaseError, ValidationError

logger = get_logger(__name__)
router = APIRouter()


# ───────────────────────────────────────────────────────────────────────────────
# Enums and Constants
# ───────────────────────────────────────────────────────────────────────────────


class ModelStatus(str, Enum):
    """Lifecycle states for a value model."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


FOLDER_ALL = "all"
FOLDER_MY_MODELS = "my-models"
FOLDER_SHARED = "shared"
FOLDER_FAVORITES = "favorites"

VALID_FOLDERS = {FOLDER_ALL, FOLDER_MY_MODELS, FOLDER_SHARED, FOLDER_FAVORITES}
ALLOWED_SORT_FIELD_MAP = {
    "name": "m.name",
    "updated_at": "m.updated_at",
    "created_at": "m.created_at",
}
VALID_SORT_DIRS = {"asc", "desc"}


# ───────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ───────────────────────────────────────────────────────────────────────────────


class ModelSummary(BaseModel):
    """Summary view of a Value Model for list displays."""

    model_id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="Brief description")
    industry: str = Field(..., description="Industry vertical")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    status: ModelStatus = Field(..., description="Lifecycle status")
    folder: str = Field(default=FOLDER_MY_MODELS, description="Organization folder")
    formula_count: int = Field(default=0, ge=0, description="Number of formulas")
    entity_count: int = Field(default=0, ge=0, description="Number of entities")
    driver_count: int = Field(default=0, ge=0, description="Number of value drivers")
    created_at: str = Field(..., description="ISO timestamp of creation")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    owner: str = Field(..., description="User ID of owner")
    is_shared: bool = Field(default=False, description="Whether shared with others")


class ModelDetail(ModelSummary):
    """Detailed view of a Value Model including relationships."""

    formula_ids: list[str] = Field(
        default_factory=list, description="Associated formula IDs"
    )
    entity_ids: list[str] = Field(
        default_factory=list, description="Associated entity IDs"
    )
    pack_ids: list[str] = Field(
        default_factory=list, description="Referenced value pack IDs"
    )


class ModelCreateRequest(BaseModel):
    """Request body for creating a new Value Model."""

    name: str = Field(..., min_length=1, max_length=200, description="Model name")
    description: str = Field(
        default="", max_length=2000, description="Model description"
    )
    industry: str = Field(
        ..., min_length=1, max_length=100, description="Industry vertical"
    )
    tags: list[str] = Field(default_factory=list, max_length=20, description="Tags")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Ensure no tag exceeds 50 characters."""
        for tag in v:
            if len(tag) > 50:
                raise ValueError(f"Tag exceeds 50 characters: {tag}")
        return v


class ModelListResponse(BaseModel):
    """Paginated list of models with metadata."""

    models: list[ModelSummary] = Field(..., description="Model summaries")
    total: int = Field(..., ge=0, description="Total matching models")
    offset: int = Field(..., ge=0, description="Current offset")
    limit: int = Field(..., ge=1, description="Page size")
    filters_applied: dict[str, Any] = Field(
        default_factory=dict, description="Echo of filters"
    )


class ModelFolderSummary(BaseModel):
    """Folder entry for sidebar navigation."""

    folder_id: str = Field(..., description="Folder identifier")
    name: str = Field(..., description="Display name")
    count: int = Field(..., ge=0, description="Model count in folder")


class FoldersResponse(BaseModel):
    """Response for folder listing endpoint."""

    folders: list[ModelFolderSummary] = Field(..., description="Available folders")


class CreateResponse(BaseModel):
    """Response after successful model creation."""

    model_id: str = Field(..., description="ID of created model")
    message: str = Field(default="Model created successfully")


class DeleteResponse(BaseModel):
    """Response after successful model deletion."""

    model_id: str = Field(..., description="ID of deleted model")
    message: str = Field(default="Model deleted successfully")


# ───────────────────────────────────────────────────────────────────────────────
# Database Operations
# ───────────────────────────────────────────────────────────────────────────────


def _model_node_to_summary(record: dict[str, Any]) -> ModelSummary:
    """Transform Neo4j node record to ModelSummary."""
    node = record.get("m", {})
    return ModelSummary(
        model_id=node.get("model_id", ""),
        name=node.get("name", ""),
        description=node.get("description", ""),
        industry=node.get("industry", ""),
        tags=node.get("tags", []),
        status=ModelStatus(node.get("status", "draft")),
        folder=node.get("folder", FOLDER_MY_MODELS),
        formula_count=node.get("formula_count", 0),
        entity_count=node.get("entity_count", 0),
        driver_count=node.get("driver_count", 0),
        created_at=node.get("created_at", datetime.now(UTC).isoformat()),
        updated_at=node.get("updated_at", datetime.now(UTC).isoformat()),
        owner=node.get("owner", "unknown"),
        is_shared=node.get("is_shared", False),
    )


async def _ensure_constraints(neo4j: Any) -> None:
    """Ensure required Neo4j constraints exist.

    Idempotent - safe to call multiple times.
    """
    try:
        # Check if constraint exists (Neo4j Community compatible)
        records = await neo4j.execute_query(
            "SHOW CONSTRAINTS YIELD name WHERE name = 'model_id_unique' RETURN count(*) as cnt"
        )
        count = records[0].get("cnt", 0) if records else 0

        if count == 0:
            await neo4j.execute_query(
                "CREATE CONSTRAINT model_id_unique IF NOT EXISTS "
                "FOR (m:ValueModel) REQUIRE m.model_id IS UNIQUE"
            )
            logger.info("Created ValueModel constraint: model_id_unique")
    except (ValidationError, DatabaseError):
        context = {
            "tenant": "unknown",
            "endpoint": "/models",
            "operation": "ensure_constraints",
        }
        logger.warning(
            "Constraint check mapped exception",
            extra={"context": context},
            exc_info=True,
        )
    except Exception:
        context = {
            "tenant": "unknown",
            "endpoint": "/models",
            "operation": "ensure_constraints",
        }
        logger.warning(
            "Constraint check/creation skipped",
            extra={"context": context},
            exc_info=True,
        )


def _validate_list_models_params(folder: str, sort_by: str, sort_dir: str) -> None:
    """Validate query parameters for list_models."""
    if folder not in VALID_FOLDERS:
        raise ValidationError(message=f"Invalid folder: {folder}")
    if sort_by not in ALLOWED_SORT_FIELD_MAP:
        raise ValidationError(message=f"Invalid sort_by: {sort_by}")
    if sort_dir not in VALID_SORT_DIRS:
        raise ValidationError(message=f"Invalid sort_dir: {sort_dir}")


def _build_list_models_query_and_params(
    current_tenant: str,
    current_user: str,
    folder: str,
    status: str,
    industry: str | None,
    search: str | None,
    sort_by: str,
    sort_dir: str,
    limit: int,
    offset: int,
) -> tuple[str, str, dict[str, object]]:
    """Build count query, data query, and parameter dictionary for list_models."""
    where_clauses = ["m.tenant_id = $tenant_id"]
    params: dict[str, object] = {
        "user_id": current_user,
        "limit": limit,
        "offset": offset,
        "tenant_id": current_tenant,
    }

    # Folder filtering
    if folder == FOLDER_MY_MODELS:
        where_clauses.append("m.owner = $user_id")
        where_clauses.append("m.folder = $folder")
        params["folder"] = FOLDER_MY_MODELS
    elif folder == FOLDER_SHARED:
        where_clauses.append("m.is_shared = true")
        where_clauses.append("m.owner <> $user_id")
    elif folder == FOLDER_FAVORITES:
        where_clauses.append("m.folder = $folder")
        params["folder"] = FOLDER_FAVORITES

    # Status filtering
    if status != "all" and status in [s.value for s in ModelStatus]:
        where_clauses.append("m.status = $status")
        params["status"] = status

    # Industry filtering
    if industry:
        where_clauses.append("m.industry = $industry")
        params["industry"] = industry

    # Search
    if search:
        where_clauses.append(
            "(m.name CONTAINS $search OR m.description CONTAINS $search OR ANY(tag IN m.tags WHERE tag CONTAINS $search))"
        )
        params["search"] = search.lower()

    extra_clauses = where_clauses[1:]
    extra_where = f"AND {' AND '.join(extra_clauses)}" if extra_clauses else ""

    sort_field = ALLOWED_SORT_FIELD_MAP[sort_by]
    sort_direction = "DESC" if sort_dir == "desc" else "ASC"

    count_query = f"""
    MATCH (m:ValueModel)
    WHERE m.tenant_id = $tenant_id
    {extra_where}
    RETURN count(m) as total
    """

    data_query = f"""
    MATCH (m:ValueModel)
    WHERE m.tenant_id = $tenant_id
    {extra_where}
    RETURN m
    ORDER BY {sort_field} {sort_direction}
    SKIP $offset
    LIMIT $limit
    """

    return count_query, data_query, params


# ───────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ───────────────────────────────────────────────────────────────────────────────


@router.get(
    "/models",
    response_model=ModelListResponse,
    tags=["Models"],
    summary="List Value Models",
    description="Returns a paginated list of value models with optional filtering, sorting, and search.",
    responses={
        200: {"description": "Models retrieved successfully"},
        400: {"description": "Invalid filter or sort parameters"},
        500: {"description": "Database error"},
    },
)
async def list_models(
    ctx: RequestContext = Depends(require_tenant_context),
    search: str | None = Query(None, description="Search in name, description, tags"),
    folder: str = Query(FOLDER_ALL, description="Filter by folder"),
    industry: str | None = Query(None, description="Filter by industry"),
    status: str = Query(
        "all", description="Filter by status: draft, active, archived, all"
    ),
    sort_by: str = Query(
        "updated_at", description="Sort field: name, updated_at, created_at"
    ),
    sort_dir: str = Query("desc", description="Sort direction: asc, desc"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Results to skip"),
) -> ModelListResponse:
    """List value models with filtering and pagination."""
    current_tenant = str(ctx.tenant_id)

    async with await create_neo4j_tenant_session(current_tenant) as neo4j:
        await _ensure_constraints(neo4j)
        current_user = str(ctx.user_id or "")

        # Validate parameters
        _validate_list_models_params(folder, sort_by, sort_dir)

        count_query, data_query, params = _build_list_models_query_and_params(
            current_tenant=current_tenant,
            current_user=current_user,
            folder=folder,
            status=status,
            industry=industry,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )

        try:
            # Execute count
            count_records = await neo4j.execute_query(count_query, params)
            total = count_records[0].get("total", 0) if count_records else 0

            # Execute data query
            data_records = await neo4j.execute_query(data_query, params)
            models = (
                [_model_node_to_summary(record) for record in data_records]
                if data_records
                else []
            )

            return ModelListResponse(
                models=models,
                total=total,
                offset=offset,
                limit=limit,
                filters_applied={
                    "search": search,
                    "folder": folder,
                    "industry": industry,
                    "status": status,
                    "sort_by": sort_by,
                    "sort_dir": sort_dir,
                },
            )
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise ServiceUnavailableError(message="Database error") from e


@router.get(
    "/models/folders",
    response_model=FoldersResponse,
    tags=["Models"],
    summary="Get Model Folder Counts",
    description="Returns folder counts for the sidebar navigation.",
)
async def get_folder_counts(
    ctx: RequestContext = Depends(require_tenant_context),
) -> FoldersResponse:
    """Get folder counts for sidebar navigation."""
    current_user = str(ctx.user_id or "")
    current_tenant = str(ctx.tenant_id)

    async with await create_neo4j_tenant_session(current_tenant) as neo4j:
        await _ensure_constraints(neo4j)

        query = """
        MATCH (m:ValueModel)
        WHERE m.tenant_id = $tenant_id
        WITH 
            count(m) as all_count,
            count(CASE WHEN m.owner = $user_id AND m.folder = 'my-models' THEN 1 END) as my_models_count,
            count(CASE WHEN m.is_shared = true AND m.owner <> $user_id THEN 1 END) as shared_count,
            count(CASE WHEN m.folder = 'favorites' THEN 1 END) as favorites_count
        RETURN all_count, my_models_count, shared_count, favorites_count
        """
        try:
            records = await neo4j.execute_query(
                query, {"user_id": current_user, "tenant_id": current_tenant}
            )
            if records:
                record = records[0]
                folders = [
                    ModelFolderSummary(
                        folder_id=FOLDER_ALL,
                        name="All Models",
                        count=record.get("all_count", 0),
                    ),
                    ModelFolderSummary(
                        folder_id=FOLDER_MY_MODELS,
                        name="My Models",
                        count=record.get("my_models_count", 0),
                    ),
                    ModelFolderSummary(
                        folder_id=FOLDER_SHARED,
                        name="Shared With Me",
                        count=record.get("shared_count", 0),
                    ),
                    ModelFolderSummary(
                        folder_id=FOLDER_FAVORITES,
                        name="Favorites",
                        count=record.get("favorites_count", 0),
                    ),
                ]
            else:
                folders = [
                    ModelFolderSummary(
                        folder_id=FOLDER_ALL, name="All Models", count=0
                    ),
                    ModelFolderSummary(
                        folder_id=FOLDER_MY_MODELS, name="My Models", count=0
                    ),
                    ModelFolderSummary(
                        folder_id=FOLDER_SHARED, name="Shared With Me", count=0
                    ),
                    ModelFolderSummary(
                        folder_id=FOLDER_FAVORITES, name="Favorites", count=0
                    ),
                ]

            return FoldersResponse(folders=folders)
        except Exception as e:
            logger.error(f"Failed to get folder counts: {e}")
            raise ServiceUnavailableError(message="Database error") from e


@router.get(
    "/models/{model_id}",
    response_model=ModelDetail,
    tags=["Models"],
    summary="Get Model Detail",
    description="Returns detailed information about a specific value model.",
    responses={
        200: {"description": "Model retrieved successfully"},
        404: {"description": "Model not found"},
        500: {"description": "Database error"},
    },
)
async def get_model_detail(
    model_id: str,
    ctx: RequestContext = Depends(require_tenant_context),
) -> ModelDetail:
    """Get detailed information about a specific model."""
    current_tenant = str(ctx.tenant_id)

    query = """
    MATCH (m:ValueModel {model_id: $model_id})
    WHERE m.tenant_id = $tenant_id
    OPTIONAL MATCH (m)-[:HAS_FORMULA]->(f)
    OPTIONAL MATCH (m)-[:HAS_ENTITY]->(e)
    OPTIONAL MATCH (m)-[:USES_PACK]->(p)
    WITH m,
         collect(DISTINCT f.formula_id) as formula_ids,
         collect(DISTINCT e.id) as entity_ids,
         collect(DISTINCT p.pack_id) as pack_ids
    RETURN m, formula_ids, entity_ids, pack_ids
    """

    async with await create_neo4j_tenant_session(current_tenant) as neo4j:
        try:
            records = await neo4j.execute_query(
                query, {"model_id": model_id, "tenant_id": current_tenant}
            )
            if not records:
                raise NotFoundError(message=str(f"Model {model_id} not found"))

            record = records[0]
            summary = _model_node_to_summary(record)

            return ModelDetail(
                **summary.model_dump(),
                formula_ids=record.get("formula_ids", []),
                entity_ids=record.get("entity_ids", []),
                pack_ids=record.get("pack_ids", []),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get model detail: {e}")
            raise ServiceUnavailableError(message="Database error") from e


@router.post(
    "/models",
    response_model=CreateResponse,
    status_code=201,
    tags=["Models"],
    summary="Create Value Model",
    description="Creates a new value model with the specified properties.",
    responses={
        201: {"description": "Model created successfully"},
    },
)
async def create_model(
    data: ModelCreateRequest,
    ctx: RequestContext = Depends(require_tenant_context),
) -> CreateResponse:
    """Create a new value model."""
    current_user = str(ctx.user_id or "")
    current_tenant = str(ctx.tenant_id)
    model_id = f"mdl_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')[:-3]}"

    now = datetime.now(UTC).isoformat()

    query = """
    CREATE (m:ValueModel {
        model_id: $model_id,
        name: $name,
        description: $description,
        industry: $industry,
        tags: $tags,
        status: $status,
        folder: $folder,
        formula_count: 0,
        entity_count: 0,
        driver_count: 0,
        created_at: $created_at,
        updated_at: $updated_at,
        owner: $owner,
        is_shared: false,
        tenant_id: $tenant_id
    })
    RETURN m.model_id as model_id
    """

    params = {
        "model_id": model_id,
        "name": data.name,
        "description": data.description,
        "industry": data.industry,
        "tags": data.tags,
        "status": ModelStatus.DRAFT.value,
        "folder": FOLDER_MY_MODELS,
        "created_at": now,
        "updated_at": now,
        "owner": current_user,
        "tenant_id": current_tenant,
    }

    async with await create_neo4j_tenant_session(current_tenant) as neo4j:
        await _ensure_constraints(neo4j)
        try:
            records = await neo4j.execute_query(query, params)
            if records:
                return CreateResponse(model_id=model_id)
            else:
                raise ServiceUnavailableError(message="Failed to create model")
        except Exception as e:
            logger.error(f"Failed to create model: {e}")
            raise ServiceUnavailableError(message="Database error") from e


@router.delete(
    "/models/{model_id}",
    response_model=DeleteResponse,
    tags=["Models"],
    summary="Delete Value Model",
    description="Deletes a value model and its relationships.",
    responses={
        200: {"description": "Model deleted successfully"},
        404: {"description": "Model not found"},
        403: {"description": "Not authorized to delete this model"},
        500: {"description": "Database error"},
    },
)
async def delete_model(
    model_id: str,
    ctx: RequestContext = Depends(require_tenant_context),
) -> DeleteResponse:
    """Delete a value model (owner only)."""
    current_user = str(ctx.user_id or "")
    current_tenant = str(ctx.tenant_id)

    async with await create_neo4j_tenant_session(current_tenant) as neo4j:
        # Check ownership
        check_query = """
        MATCH (m:ValueModel {model_id: $model_id})
        WHERE m.tenant_id = $tenant_id
        RETURN m.owner as owner
        """

        try:
            check_records = await neo4j.execute_query(
                check_query, {"model_id": model_id, "tenant_id": current_tenant}
            )
            if not check_records:
                raise NotFoundError(message=str(f"Model {model_id} not found"))

            owner = check_records[0].get("owner")
            if owner != current_user:
                # In production, also check admin/superuser roles
                raise AuthorizationError(message="Not authorized to delete this model")

            # Delete with relationships
            delete_query = """
            MATCH (m:ValueModel {model_id: $model_id})
            WHERE m.tenant_id = $tenant_id
            OPTIONAL MATCH (m)-[r]-()
            DELETE r, m
            """

            await neo4j.execute_query(
                delete_query, {"model_id": model_id, "tenant_id": current_tenant}
            )
            return DeleteResponse(model_id=model_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            raise ServiceUnavailableError(message="Database error") from e
