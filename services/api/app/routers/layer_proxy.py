from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Request
from value_fabric.shared.models import JSONDict

from app.clients.layer1_client import Layer1Client
from app.clients.layer2_client import Layer2Client
from app.clients.layer3_client import Layer3Client
from app.clients.layer4_client import Layer4Client
from app.clients.layer5_client import Layer5Client
from app.core.tenant_context import tenant_required

router = APIRouter(tags=["Layer Proxy"])

# Singleton clients
_layer1_client: Layer1Client | None = None
_layer2_client: Layer2Client | None = None
_layer3_client: Layer3Client | None = None
_layer4_client: Layer4Client | None = None
_layer5_client: Layer5Client | None = None


def get_layer1_client() -> Layer1Client:
    global _layer1_client
    if _layer1_client is None:
        _layer1_client = Layer1Client()
    return _layer1_client


def get_layer2_client() -> Layer2Client:
    global _layer2_client
    if _layer2_client is None:
        _layer2_client = Layer2Client()
    return _layer2_client


def get_layer3_client() -> Layer3Client:
    global _layer3_client
    if _layer3_client is None:
        _layer3_client = Layer3Client()
    return _layer3_client


def get_layer4_client() -> Layer4Client:
    global _layer4_client
    if _layer4_client is None:
        _layer4_client = Layer4Client()
    return _layer4_client


def get_layer5_client() -> Layer5Client:
    global _layer5_client
    if _layer5_client is None:
        _layer5_client = Layer5Client()
    return _layer5_client


# =============================================================================
# Layer 1 — Ingestion
# =============================================================================

@router.post("/ingestion/sources", tags=["L1-Ingestion"])
async def create_source(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer1Client = Depends(get_layer1_client),
):
    """Create a new source in Layer 1 catalog."""
    body: JSONDict = await request.json()
    return await client.create_source(
        tenant_id=tenant_id,
        url=body.get("url"),
        name=body.get("name"),
        config=body.get("config"),
    )


@router.post("/ingestion/sources/{source_id}/versions", tags=["L1-Ingestion"])
async def create_source_version(
    request: Request,
    source_id: str = Path(description="Unique identifier of the source to version"),
    tenant_id: str = Depends(tenant_required),
    client: Layer1Client = Depends(get_layer1_client),
):
    """Create a new source version."""
    body: JSONDict = await request.json()
    return await client.create_source_version(
        tenant_id=tenant_id,
        source_id=source_id,
        content=body.get("content"),
        metadata=body.get("metadata"),
    )


@router.post("/ingestion/runs", tags=["L1-Ingestion"])
async def create_ingestion_run(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer1Client = Depends(get_layer1_client),
):
    """Trigger an ingestion run."""
    body: JSONDict = await request.json()
    return await client.create_ingestion_run(
        tenant_id=tenant_id,
        source_version_id=body.get("source_version_id"),
        config=body.get("config"),
    )


@router.get("/ingestion/runs/{run_id}", tags=["L1-Ingestion"])
async def get_ingestion_run(
    run_id: str = Path(description="Unique identifier of the ingestion run"),
    tenant_id: str = Depends(tenant_required),
    client: Layer1Client = Depends(get_layer1_client),
):
    """Get ingestion run status."""
    return await client.get_ingestion_run(tenant_id=tenant_id, run_id=run_id)


@router.get("/ingestion/sources", tags=["L1-Ingestion"])
async def list_sources(
    limit: int = Query(default=50, description="Maximum number of sources to return"),
    offset: int = Query(default=0, description="Number of sources to skip for pagination"),
    tenant_id: str = Depends(tenant_required),
    client: Layer1Client = Depends(get_layer1_client),
):
    """List sources in the catalog."""
    return await client.list_sources(tenant_id=tenant_id, limit=limit, offset=offset)


# =============================================================================
# Layer 2 — Extraction
# =============================================================================

@router.post("/extract", tags=["L2-Extraction"])
async def extract(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer2Client = Depends(get_layer2_client),
):
    """Extract entities from content (extraction only).

    Body follows the canonical ``ExtractRequest`` contract
    (``content_id``, ``source_url``, ``markdown_content``, optional
    ``extraction_config``).
    """
    body: JSONDict = await request.json()
    return await client.extract(
        tenant_id=tenant_id,
        content_id=body.get("content_id", ""),
        source_url=body.get("source_url", ""),
        markdown_content=body.get("markdown_content", ""),
        extraction_config=body.get("extraction_config"),
    )


@router.post("/extract-and-ingest", tags=["L2-Extraction"])
async def extract_and_ingest(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer2Client = Depends(get_layer2_client),
):
    """Extract and ingest into Layer 3 knowledge graph."""
    body: JSONDict = await request.json()
    return await client.extract_and_ingest(
        tenant_id=tenant_id,
        content_id=body.get("content_id", ""),
        source_url=body.get("source_url", ""),
        markdown_content=body.get("markdown_content", ""),
        extraction_config=body.get("extraction_config"),
    )


@router.get("/extractions/{job_id}", tags=["L2-Extraction"])
async def get_extraction_status(
    job_id: str = Path(description="Unique identifier of the extraction job"),
    tenant_id: str = Depends(tenant_required),
    client: Layer2Client = Depends(get_layer2_client),
):
    """Get extraction job status."""
    return await client.get_job_status(tenant_id=tenant_id, job_id=job_id)


# =============================================================================
# Layer 3 — Knowledge Graph
# =============================================================================

@router.get("/query/entities", tags=["L3-Knowledge"])
async def query_entities(
    entity_type: str | None = Query(default=None, description="Filter entities by type"),
    limit: int = Query(default=50, description="Maximum number of entities to return"),
    offset: int = Query(default=0, description="Number of entities to skip for pagination"),
    tenant_id: str = Depends(tenant_required),
    client: Layer3Client = Depends(get_layer3_client),
):
    """Query entities from the knowledge graph."""
    return await client.query_entities(
        tenant_id=tenant_id,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )


@router.post("/search", tags=["L3-Knowledge"])
async def search_knowledge_graph(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer3Client = Depends(get_layer3_client),
):
    """Hybrid search in the knowledge graph."""
    body: JSONDict = await request.json()
    return await client.search(
        tenant_id=tenant_id,
        query=body.get("query", ""),
        limit=body.get("limit", 10),
    )


@router.get("/value-trees/{tree_id}", tags=["L3-Knowledge"])
async def get_value_tree(
    tree_id: str = Path(description="Unique identifier of the value tree"),
    tenant_id: str = Depends(tenant_required),
    client: Layer3Client = Depends(get_layer3_client),
):
    """Get a value tree by ID."""
    return await client.get_value_tree(tenant_id=tenant_id, tree_id=tree_id)


@router.post("/ingest", tags=["L3-Knowledge"])
async def ingest_rdf(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer3Client = Depends(get_layer3_client),
):
    """Ingest RDF data into the knowledge graph."""
    body: JSONDict = await request.json()
    return await client.ingest_rdf(
        tenant_id=tenant_id,
        rdf_data=body.get("rdf", ""),
        source_version_id=body.get("source_version_id", ""),
    )


@router.post("/query/graphrag", tags=["L3-Knowledge"])
async def query_graphrag(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer3Client = Depends(get_layer3_client),
):
    """Query the knowledge graph using GraphRAG retrieval."""
    body: JSONDict = await request.json()
    return await client.query_graphrag(
        tenant_id=tenant_id,
        question=body.get("question", ""),
        context=body.get("context"),
    )


# =============================================================================
# Layer 4 — Agent Workflows
# =============================================================================

@router.post("/workflows", tags=["L4-Agents"])
async def submit_workflow(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer4Client = Depends(get_layer4_client),
):
    """Submit a workflow to Layer 4."""
    body: JSONDict = await request.json()
    return await client.submit_workflow(
        tenant_id=tenant_id,
        workflow_type=body.get("workflow_type", ""),
        inputs=body.get("inputs", {}),
    )


@router.get("/workflows/{workflow_id}", tags=["L4-Agents"])
async def get_workflow(
    workflow_id: str = Path(description="Unique identifier of the workflow"),
    tenant_id: str = Depends(tenant_required),
    client: Layer4Client = Depends(get_layer4_client),
):
    """Retrieve the current status of a workflow."""
    return await client.get_workflow(tenant_id=tenant_id, workflow_id=workflow_id)


@router.get("/workflows/{workflow_id}/result", tags=["L4-Agents"])
async def get_workflow_result(
    workflow_id: str = Path(description="Unique identifier of the workflow"),
    tenant_id: str = Depends(tenant_required),
    client: Layer4Client = Depends(get_layer4_client),
):
    """Retrieve the final result of a workflow."""
    return await client.get_workflow_result(tenant_id=tenant_id, workflow_id=workflow_id)


@router.post("/hypotheses/generate", tags=["L4-Agents"])
async def generate_hypotheses(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer4Client = Depends(get_layer4_client),
):
    """Generate hypotheses via Layer 4."""
    body: JSONDict = await request.json()
    return await client.generate_hypotheses(tenant_id=tenant_id, payload=body)


@router.post("/analysis/roi", tags=["L4-Agents"])
async def run_roi_analysis(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer4Client = Depends(get_layer4_client),
):
    """Run ROI analysis via Layer 4."""
    body: JSONDict = await request.json()
    return await client.run_roi_analysis(tenant_id=tenant_id, payload=body)


@router.post("/narratives/generate", tags=["L4-Agents"])
async def generate_narrative(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer4Client = Depends(get_layer4_client),
):
    """Generate narrative via Layer 4."""
    body: JSONDict = await request.json()
    return await client.generate_narrative(tenant_id=tenant_id, payload=body)


# =============================================================================
# Layer 5 — Ground Truth
# =============================================================================

@router.get("/truths", tags=["L5-Ground-Truth"])
async def list_truths(
    status: str | None = Query(default=None, description="Filter truths by validation status"),
    claim_type: str | None = Query(default=None, description="Filter truths by claim type"),
    limit: int = Query(default=50, description="Maximum number of truths to return"),
    offset: int = Query(default=0, description="Number of truths to skip for pagination"),
    tenant_id: str = Depends(tenant_required),
    client: Layer5Client = Depends(get_layer5_client),
):
    """List TruthObjects with optional filters."""
    return await client.list_truths(
        tenant_id=tenant_id,
        status=status,
        claim_type=claim_type,
        limit=limit,
        offset=offset,
    )


@router.get("/truths/{truth_id}", tags=["L5-Ground-Truth"])
async def get_truth(
    truth_id: str = Path(description="Unique identifier of the TruthObject"),
    tenant_id: str = Depends(tenant_required),
    client: Layer5Client = Depends(get_layer5_client),
):
    """Get a single TruthObject by ID."""
    return await client.get_truth(tenant_id=tenant_id, truth_id=truth_id)


@router.post("/truths", tags=["L5-Ground-Truth"])
async def submit_truth(
    request: Request,
    tenant_id: str = Depends(tenant_required),
    client: Layer5Client = Depends(get_layer5_client),
):
    """Submit a new TruthObject."""
    body: JSONDict = await request.json()
    return await client.submit_truth(
        tenant_id=tenant_id,
        claim=body.get("claim", ""),
        claim_type=body.get("claim_type", "other"),
        confidence=body.get("confidence", 0.0),
        value=body.get("value"),
        applies_to=body.get("applies_to"),
        sources=body.get("sources"),
        extraction_job_id=body.get("extraction_job_id"),
        extraction_model=body.get("extraction_model"),
        raw_extraction_data=body.get("raw_extraction_data"),
    )


@router.post("/truths/{truth_id}/validate", tags=["L5-Ground-Truth"])
async def validate_truth(
    request: Request,
    truth_id: str = Path(description="Unique identifier of the TruthObject to validate"),
    tenant_id: str = Depends(tenant_required),
    client: Layer5Client = Depends(get_layer5_client),
):
    """Validate or transition a TruthObject."""
    body: JSONDict = await request.json()
    return await client.validate_truth(
        tenant_id=tenant_id,
        truth_id=truth_id,
        action=body.get("action", ""),
        actor=body.get("actor", ""),
        actor_type=body.get("actor_type", "system"),
        notes=body.get("notes"),
    )


@router.post("/truths/sync-kg", tags=["L5-Ground-Truth"])
async def sync_knowledge_graph(
    tenant_id: str = Depends(tenant_required),
    client: Layer5Client = Depends(get_layer5_client),
):
    """Sync validated TruthObjects to Layer 3 knowledge graph."""
    return await client.sync_kg(tenant_id=tenant_id)


@router.get("/truths/freshness-summary", tags=["L5-Ground-Truth"])
async def get_freshness_summary(
    tenant_id: str = Depends(tenant_required),
    client: Layer5Client = Depends(get_layer5_client),
):
    """Get freshness summary of TruthObjects."""
    return await client.get_freshness_summary(tenant_id=tenant_id)


@router.get("/maturity-ladder", tags=["L5-Ground-Truth"])
async def get_maturity_ladder(
    tenant_id: str = Depends(tenant_required),
    client: Layer5Client = Depends(get_layer5_client),
):
    """Get maturity ladder reference."""
    return await client.get_maturity_ladder(tenant_id=tenant_id)
