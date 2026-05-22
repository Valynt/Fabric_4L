"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Provenance Tracking Agent.

Implements PROV-O lineage tracking with RDF-star annotations.
"""

import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from neo4j import AsyncDriver
from value_fabric.shared.models.typed_dict import TypedDictModel

from .base import AgentResult, BaseAgent
from ..db.query_execution import run_validated_query


class ProvenanceTrackingAgent__record_entityResult(TypedDictModel):
    entity_id: Any | None = None
    error: str
    full_id: Any | None = None
    label: Any | None = None
    recorded: bool | None = None
    type: Any | None = None

class ProvenanceTrackingAgent__record_activityResult(TypedDictModel):
    activity_id: Any | None = None
    error: str
    full_id: Any | None = None
    label: Any | None = None
    recorded: bool | None = None
    type: Any | None = None

class ProvenanceTrackingAgent__record_derivationResult(TypedDictModel):
    derivation_type: Any | None = None
    derived_entity: Any | None = None
    error: str
    recorded: bool | None = None
    source_entity: Any | None = None

class ProvenanceTrackingAgent__create_decision_traceResult(TypedDictModel):
    completed_at: Any
    created_at: Any
    output_id: Any
    output_type: Any
    step_count: Any
    steps: Any
    trace_id: Any
    workflow_id: Any
    workflow_instance_id: Any

class ProvenanceTrackingAgent__query_lineageResult(TypedDictModel):
    downstream_lineage: Any | None = None
    entity_id: Any | None = None
    error: str
    full_lineage_depth: Any | None = None
    lineage: list[Any]
    upstream_lineage: Any | None = None

class ProvenanceTrackingAgent_build_provenance_recordResult(TypedDictModel):
    attribution: dict[str, Any]
    entity: dict[str, Any]
    generation: dict[str, Any]
    rdf_triples: list[Any]
    usage: dict[str, Any]

logger = logging.getLogger(__name__)

# SECURITY: Valid ID patterns
_TENANT_SYSTEM = "system"
_TENANT_ADMIN = "admin"
_VALID_ENTITY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_:@#-]{1,256}$")


class PROVEntityType(Enum):
    """PROV-O entity types."""

    DOCUMENT = "prov:Entity:Document"
    SEGMENT = "prov:Entity:Segment"
    PAIN_POINT = "prov:Entity:PainPoint"
    VALUE_NODE = "prov:Entity:ValueNode"
    CALCULATION = "prov:Entity:Calculation"
    NARRATIVE = "prov:Entity:Narrative"
    ACCOUNT_PLAN = "prov:Entity:AccountPlan"
    FORMULA = "prov:Entity:Formula"


class PROVActivityType(Enum):
    """PROV-O activity types."""

    DOCUMENT_INGESTION = "prov:Activity:DocumentIngestion"
    EXTRACTION = "prov:Activity:Extraction"
    PROJECTION = "prov:Activity:Projection"
    TRAVERSAL = "prov:Activity:Traversal"
    CALCULATION = "prov:Activity:Calculation"
    SYNTHESIS = "prov:Activity:Synthesis"
    PLAN_GENERATION = "prov:Activity:PlanGeneration"


class PROVAgentType(Enum):
    """PROV-O agent types."""

    LLM_MODEL = "prov:Agent:LLMModel"
    AI_AGENT = "prov:Agent:AIAgent"
    USER = "prov:Agent:User"
    SYSTEM = "prov:Agent:System"
    EXTERNAL_SERVICE = "prov:Agent:ExternalService"


@dataclass
class RDFStarAnnotation:
    """RDF-star annotation for an edge."""

    annotation_id: str
    subject: str
    predicate: str
    object: str
    annotations: dict[str, Any]
    created_at: datetime


@dataclass
class DecisionStep:
    """Single step in a decision trace."""

    step_id: str
    step_type: str
    step_number: int
    timestamp: datetime
    description: str
    input_refs: list[str]
    output_refs: list[str]
    agent_id: str | None
    llm_model: str | None
    confidence: float | None
    reasoning: str | None
    supporting_evidence: list[dict[str, Any]]
    alternatives_considered: list[dict[str, Any]]


@dataclass
class DecisionTrace:
    """Complete decision trace for an AI-generated output."""

    trace_id: str
    workflow_id: str
    workflow_instance_id: str
    output_type: str
    output_id: str
    created_at: datetime
    completed_at: datetime | None
    steps: list[DecisionStep]
    tenant_id: str = "system"


class ProvenanceTrackingAgent(BaseAgent):
    """Agent for provenance tracking and lineage recording.

    Capabilities:
    - prov_o_generation: Generate PROV-O compliant provenance
    - rdf_star_annotation: Annotate edges with execution metadata
    - lineage_tracking: Track data lineage through workflows
    - decision_trace_construction: Build decision traces for AI outputs

    Storage backend: triple_store (Neo4j with RDF-star support)
    """

    # PROV-O Namespaces
    PROV_NAMESPACES = {
        "prov": "http://www.w3.org/ns/prov#",
        "vf": "http://valuefabric.io/prov/",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "rdf-star": "http://www.w3.org/ns/rdf-star#",
    }

    def __init__(self, driver: AsyncDriver | None = None):
        """Initialize provenance tracking agent.

        Args:
            driver: Neo4j async driver for triple store
        """
        super().__init__("ProvenanceTrackingAgent")
        self._driver = driver

    def _validate_tenant_id(self, tenant_id: str | None) -> str:
        """Validate and normalize tenant ID.

        SECURITY: Strict validation to prevent tenant confusion attacks.
        Accepts UUID format or reserved system/admin identifiers.

        Args:
            tenant_id: Raw tenant identifier from context

        Returns:
            Normalized tenant ID string

        Raises:
            ValueError: If tenant_id is invalid format
        """
        if tenant_id is None:
            return _TENANT_SYSTEM

        normalized = str(tenant_id).strip().lower()

        if not normalized:
            return _TENANT_SYSTEM

        # Allow reserved system identifiers
        if normalized in (_TENANT_SYSTEM, _TENANT_ADMIN):
            return normalized

        # Validate UUID format for tenant isolation
        try:
            UUID(normalized)
            return normalized
        except ValueError as e:
            raise ValueError(f"Invalid tenant_id format: {tenant_id}. Expected UUID.") from e

    def _validate_entity_id(self, entity_id: str | None) -> str:
        """Validate entity ID format to prevent injection.

        SECURITY: Entity IDs must follow PROV-O URI-safe patterns.

        Args:
            entity_id: Entity identifier to validate

        Returns:
            Validated entity ID

        Raises:
            ValueError: If entity_id is invalid or contains unsafe characters
        """
        if not entity_id:
            raise ValueError("entity_id is required")

        if not isinstance(entity_id, str):
            raise ValueError(f"entity_id must be string, got {type(entity_id)}")

        if not _VALID_ENTITY_ID_PATTERN.match(entity_id):
            raise ValueError(
                f"Invalid entity_id format: {entity_id}. "
                "Must be 1-256 characters, alphanumeric with _:@#- only"
            )

        return entity_id

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Execute provenance tracking operation.

        Args:
            context: Must contain:
                - operation: 'record_entity', 'record_activity', 'record_derivation',
                          'create_decision_trace', 'query_lineage'
                - workflow_id: ID of workflow
                - workflow_instance_id: ID of workflow instance

        Returns:
            AgentResult with provenance records
        """
        start_time = time.time()

        try:
            operation = context.get("operation", "record_entity")
            raw_tenant_id = context.get("tenant_id")

            # SECURITY: Validate tenant_id format early (fail-fast)
            try:
                tenant_id = self._validate_tenant_id(raw_tenant_id)
            except ValueError as e:
                return self._create_result(
                    status="failed",
                    output={},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    errors=[f"Invalid tenant_id: {e}"],
                )

            if operation == "record_entity":
                # SECURITY: Validate entity_id
                try:
                    entity_id = self._validate_entity_id(context.get("entity_id"))
                except ValueError as e:
                    return self._create_result(
                        status="failed",
                        output={},
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        errors=[str(e)],
                    )
                result = await self._record_entity(
                    entity_type=context.get("entity_type", "DOCUMENT"),
                    entity_id=entity_id,
                    label=context.get("label"),
                    attributes=context.get("attributes", {}),
                    tenant_id=tenant_id,
                )
            elif operation == "record_activity":
                result = await self._record_activity(
                    activity_type=context.get("activity_type", "EXTRACTION"),
                    activity_id=context.get("activity_id"),
                    label=context.get("label"),
                    attributes=context.get("attributes", {}),
                )
            elif operation == "record_derivation":
                # SECURITY: Validate entity_ids
                try:
                    derived_id = self._validate_entity_id(context.get("derived_entity_id"))
                    source_id = self._validate_entity_id(context.get("source_entity_id"))
                except ValueError as e:
                    return self._create_result(
                        status="failed",
                        output={},
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        errors=[str(e)],
                    )
                result = await self._record_derivation(
                    derived_entity_id=derived_id,
                    source_entity_id=source_id,
                    derivation_type=context.get("derivation_type", "wasDerivedFrom"),
                    tenant_id=tenant_id,
                )
            elif operation == "create_decision_trace":
                result = await self._create_decision_trace(
                    workflow_id=context.get("workflow_id"),
                    workflow_instance_id=context.get("workflow_instance_id"),
                    output_type=context.get("output_type"),
                    output_id=context.get("output_id"),
                    steps=context.get("steps", []),
                    tenant_id=tenant_id,
                )
            elif operation == "query_lineage":
                # SECURITY: Validate entity_id
                try:
                    entity_id = self._validate_entity_id(context.get("entity_id"))
                except ValueError as e:
                    return self._create_result(
                        status="failed",
                        output={},
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        errors=[str(e)],
                    )
                result = await self._query_lineage(
                    entity_id=entity_id,
                    tenant_id=tenant_id,
                )
            else:
                return self._create_result(
                    status="failed",
                    output={},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    errors=[f"Unknown operation: {operation}"],
                )

            return self._create_result(
                status="success",
                output=result,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.error(f"Provenance tracking failed: {e}")
            return self._create_result(
                status="failed",
                output={},
                execution_time_ms=int((time.time() - start_time) * 1000),
                errors=[str(e)],
            )

    async def _record_entity(
        self,
        entity_type: str,
        entity_id: str,
        label: str,
        attributes: dict[str, Any],
        tenant_id: str = "system",
    ) -> dict[str, Any]:
        """Record a PROV-O entity.

        Args:
            entity_type: Entity type from PROVEntityType
            entity_id: Unique entity ID
            label: Human-readable label
            attributes: Additional entity attributes
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with recorded entity info
        """
        if not self._driver:
            return ProvenanceTrackingAgent__record_entityResult.model_validate({"error": "No database driver"})

        full_entity_id = f"{self.PROV_NAMESPACES['vf']}entity/{entity_id}"

        query = """
        CREATE (e:PROVEntity:{{ entity_type }} {
            entity_id: $entity_id,
            full_id: $full_entity_id,
            label: $label,
            entity_type: $entity_type,
            tenant_id: $tenant_id,
            generated_at: datetime(),
            attributes: $attributes
        })
        RETURN e.entity_id as id
        """

        async with self._driver.session() as session:
            result = await run_validated_query(session,
                query,
                {
                    "entity_id": entity_id,
                    "full_entity_id": full_entity_id,
                    "label": label,
                    "entity_type": entity_type,
                    "tenant_id": tenant_id,
                    "attributes": attributes,
                },
            )
            record = await result.single()

        return ProvenanceTrackingAgent__record_entityResult.model_validate({
            "entity_id": entity_id,
            "full_id": full_entity_id,
            "type": entity_type,
            "label": label,
            "recorded": record is not None,
        })


    async def _record_activity(
        self,
        activity_type: str,
        activity_id: str,
        label: str,
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        """Record a PROV-O activity.

        Args:
            activity_type: Activity type from PROVActivityType
            activity_id: Unique activity ID
            label: Human-readable label
            attributes: Additional activity attributes

        Returns:
            Dict with recorded activity info
        """
        if not self._driver:
            return ProvenanceTrackingAgent__record_activityResult.model_validate({"error": "No database driver"})

        full_activity_id = f"{self.PROV_NAMESPACES['vf']}activity/{activity_id}"

        query = """
        CREATE (a:PROVActivity:{{ activity_type }} {
            activity_id: $activity_id,
            full_id: $full_activity_id,
            label: $label,
            activity_type: $activity_type,
            started_at: datetime(),
            attributes: $attributes
        })
        RETURN a.activity_id as id
        """

        async with self._driver.session() as session:
            result = await run_validated_query(session,
                query,
                {
                    "activity_id": activity_id,
                    "full_activity_id": full_activity_id,
                    "label": label,
                    "activity_type": activity_type,
                    "attributes": attributes,
                },
            )
            record = await result.single()

        return ProvenanceTrackingAgent__record_activityResult.model_validate({
            "activity_id": activity_id,
            "full_id": full_activity_id,
            "type": activity_type,
            "label": label,
            "recorded": record is not None,
        })


    async def _record_derivation(
        self,
        derived_entity_id: str,
        source_entity_id: str,
        derivation_type: str = "wasDerivedFrom",
        tenant_id: str = "system",
    ) -> dict[str, Any]:
        """Record a derivation relationship.

        Args:
            derived_entity_id: ID of derived entity
            source_entity_id: ID of source entity
            derivation_type: Type of derivation
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with derivation record
        """
        if not self._driver:
            return ProvenanceTrackingAgent__record_derivationResult.model_validate({"error": "No database driver"})

        query = """
        MATCH (derived:PROVEntity {entity_id: $derived_id, tenant_id: $tenant_id})
        MATCH (source:PROVEntity {entity_id: $source_id, tenant_id: $tenant_id})
        CREATE (derived)-[r:wasDerivedFrom {
            derivation_type: $derivation_type,
            timestamp: datetime()
        }]->(source)
        RETURN r
        """

        async with self._driver.session() as session:
            result = await run_validated_query(session,
                query,
                {
                    "derived_id": derived_entity_id,
                    "source_id": source_entity_id,
                    "derivation_type": derivation_type,
                    "tenant_id": tenant_id,
                },
            )
            record = await result.single()

        return ProvenanceTrackingAgent__record_derivationResult.model_validate({
            "derivation_type": derivation_type,
            "derived_entity": derived_entity_id,
            "source_entity": source_entity_id,
            "recorded": record is not None,
        })


    async def _create_decision_trace(
        self,
        workflow_id: str,
        workflow_instance_id: str,
        output_type: str,
        output_id: str,
        steps: list[dict[str, Any]],
        tenant_id: str = "system",
    ) -> dict[str, Any]:
        """Create a decision trace for AI-generated output.

        Args:
            workflow_id: Workflow definition ID
            workflow_instance_id: Workflow execution ID
            output_type: Type of output generated
            output_id: ID of generated output
            steps: List of decision steps
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with decision trace
        """
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"

        decision_trace = DecisionTrace(
            trace_id=trace_id,
            workflow_id=workflow_id,
            workflow_instance_id=workflow_instance_id,
            output_type=output_type,
            output_id=output_id,
            created_at=datetime.utcnow(),
            completed_at=None,
            steps=[],
            tenant_id=tenant_id,
        )

        # Convert step dicts to DecisionStep objects
        for i, step_data in enumerate(steps):
            step = DecisionStep(
                step_id=step_data.get("step_id", f"step-{i + 1}"),
                step_type=step_data.get("step_type", "processing"),
                step_number=i + 1,
                timestamp=datetime.utcnow(),
                description=step_data.get("description", ""),
                input_refs=step_data.get("input_refs", []),
                output_refs=step_data.get("output_refs", []),
                agent_id=step_data.get("agent_id"),
                llm_model=step_data.get("llm_model"),
                confidence=step_data.get("confidence"),
                reasoning=step_data.get("reasoning"),
                supporting_evidence=step_data.get("supporting_evidence", []),
                alternatives_considered=step_data.get("alternatives_considered", []),
            )
            decision_trace.steps.append(step)

        decision_trace.completed_at = datetime.utcnow()

        # Store in database
        if self._driver:
            await self._store_decision_trace(decision_trace)

        return ProvenanceTrackingAgent__create_decision_traceResult.model_validate({
            "trace_id": trace_id,
            "workflow_id": workflow_id,
            "workflow_instance_id": workflow_instance_id,
            "output_type": output_type,
            "output_id": output_id,
            "step_count": len(decision_trace.steps),
            "steps": [
                {
                    "step_number": s.step_number,
                    "step_type": s.step_type,
                    "description": s.description,
                    "confidence": s.confidence,
                    "agent_id": s.agent_id,
                }
                for s in decision_trace.steps
            ],
            "created_at": decision_trace.created_at.isoformat(),
            "completed_at": decision_trace.completed_at.isoformat()
            if decision_trace.completed_at
            else None,
        })


    async def _store_decision_trace(self, trace: DecisionTrace) -> None:
        """Store decision trace in Neo4j.

        Args:
            trace: DecisionTrace to store
        """
        if not self._driver:
            return

        # Create trace node
        query = """
        CREATE (t:DecisionTrace {
            trace_id: $trace_id,
            workflow_id: $workflow_id,
            workflow_instance_id: $workflow_instance_id,
            output_type: $output_type,
            output_id: $output_id,
            tenant_id: $tenant_id,
            created_at: datetime($created_at),
            completed_at: datetime($completed_at)
        })
        RETURN t
        """

        async with self._driver.session() as session:
            await run_validated_query(session,
                query,
                {
                    "trace_id": trace.trace_id,
                    "workflow_id": trace.workflow_id,
                    "workflow_instance_id": trace.workflow_instance_id,
                    "output_type": trace.output_type,
                    "output_id": trace.output_id,
                    "tenant_id": trace.tenant_id,
                    "created_at": trace.created_at.isoformat(),
                    "completed_at": trace.completed_at.isoformat()
                    if trace.completed_at
                    else None,
                },
            )

            # Create step nodes and link to trace
            for step in trace.steps:
                step_query = """
                MATCH (t:DecisionTrace {trace_id: $trace_id, tenant_id: $tenant_id})
                CREATE (s:DecisionStep {
                    step_id: $step_id,
                    step_type: $step_type,
                    step_number: $step_number,
                    description: $description,
                    confidence: $confidence,
                    agent_id: $agent_id,
                    llm_model: $llm_model,
                    tenant_id: $tenant_id
                })
                CREATE (t)-[:HAS_STEP]->(s)
                """

                await run_validated_query(session,
                    step_query,
                    {
                        "trace_id": trace.trace_id,
                        "step_id": step.step_id,
                        "step_type": step.step_type,
                        "step_number": step.step_number,
                        "description": step.description,
                        "confidence": step.confidence,
                        "agent_id": step.agent_id,
                        "llm_model": step.llm_model,
                        "tenant_id": trace.tenant_id,
                    },
                )

    async def _query_lineage(self, entity_id: str, tenant_id: str = "system") -> dict[str, Any]:
        """Query lineage for an entity.

        Args:
            entity_id: Entity ID to query
            tenant_id: Tenant ID for data isolation

        Returns:
            Dict with lineage information
        """
        if not self._driver:
            return ProvenanceTrackingAgent__query_lineageResult.model_validate({"lineage": [], "error": "No database driver"})

        # Query upstream lineage (what this entity was derived from)
        upstream_query = """
        MATCH path = (e:PROVEntity {entity_id: $entity_id, tenant_id: $tenant_id})-[:wasDerivedFrom|wasGeneratedBy|used*1..10]->(source)
        WHERE source.tenant_id = $tenant_id
        RETURN [node in nodes(path) | {id: node.entity_id, type: node.entity_type, label: node.label}] as lineage
        """

        # Query downstream lineage (what was derived from this entity)
        downstream_query = """
        MATCH path = (e:PROVEntity {entity_id: $entity_id, tenant_id: $tenant_id})<-[:wasDerivedFrom|wasGeneratedBy|used*1..10]-(derived)
        WHERE derived.tenant_id = $tenant_id
        RETURN [node in nodes(path) | {id: node.entity_id, type: node.entity_type, label: node.label}] as lineage
        """

        upstream = []
        downstream = []

        async with self._driver.session() as session:
            # Get upstream
            result = await run_validated_query(session, upstream_query, {"entity_id": entity_id, "tenant_id": tenant_id})
            async for record in result:
                upstream.extend(record.get("lineage", []))

            # Get downstream
            result = await run_validated_query(session, downstream_query, {"entity_id": entity_id, "tenant_id": tenant_id})
            async for record in result:
                downstream.extend(record.get("lineage", []))

        return ProvenanceTrackingAgent__query_lineageResult.model_validate({
            "entity_id": entity_id,
            "upstream_lineage": upstream,
            "downstream_lineage": downstream,
            "full_lineage_depth": len(upstream) + len(downstream),
        })


    def create_rdf_star_annotation(
        self,
        subject: str,
        predicate: str,
        object: str,
        annotations: dict[str, Any],
    ) -> RDFStarAnnotation:
        """Create RDF-star annotation for an edge.

        Args:
            subject: Edge subject
            predicate: Edge predicate
            object: Edge object
            annotations: Annotation attributes

        Returns:
            RDFStarAnnotation
        """
        return RDFStarAnnotation(
            annotation_id=f"anno-{uuid.uuid4().hex[:12]}",
            subject=subject,
            predicate=predicate,
            object=object,
            annotations=annotations,
            created_at=datetime.utcnow(),
        )

    def build_provenance_record(
        self,
        entity_type: str,
        entity_id: str,
        generated_by: str,
        used_entities: list[str],
        attributed_to: str,
    ) -> dict[str, Any]:
        """Build complete provenance record.

        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            generated_by: Activity that generated it
            used_entities: Entities used in generation
            attributed_to: Agent responsible

        Returns:
            Dict with complete provenance
        """
        return ProvenanceTrackingAgent_build_provenance_recordResult.model_validate({
            "entity": {
                "id": entity_id,
                "type": entity_type,
            },
            "generation": {
                "activity": generated_by,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "usage": {
                "used_entities": used_entities,
            },
            "attribution": {
                "agent": attributed_to,
            },
            "rdf_triples": [
                (f"vf:{entity_id}", "prov:wasGeneratedBy", f"vf:{generated_by}"),
                (f"vf:{entity_id}", "prov:wasAttributedTo", f"vf:{attributed_to}"),
                *[
                    (f"vf:{generated_by}", "prov:used", f"vf:{used}")
                    for used in used_entities
                ],
            ],
        })

