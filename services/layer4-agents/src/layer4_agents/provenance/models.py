from __future__ import annotations

"""PROV-O and RDF* data models for provenance tracking.

Implements W3C PROV-O specification with RDF* extensions for
annotating statements (statements about statements).

References:
- PROV-O: https://www.w3.org/TR/prov-o/
- RDF*: https://w3c.github.io/rdf-star/
"""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from value_fabric.shared.models.typed_dict import TypedDictModel


class PROVNamespace_get_prefixesResult(TypedDictModel):
    prov: Any
    rdf: Any
    rdfs: Any
    vf: Any
    xsd: Any

class PROVEntity_to_dictResult(TypedDictModel):
    id_: Any
    type_: Any
    attributes: Any
    generatedAt: Any  # noqa: N815
    generatedBy: Any  # noqa: N815
    label: Any

class PROVActivity_to_dictResult(TypedDictModel):
    id_: Any
    type_: Any
    associatedWith: Any  # noqa: N815
    attributes: Any
    endedAt: Any  # noqa: N815
    generated: Any
    label: Any
    startedAt: Any  # noqa: N815
    used: Any

class PROVAgent_to_dictResult(TypedDictModel):
    id_: Any
    type_: Any
    actedOnBehalfOf: Any  # noqa: N815
    attributes: Any
    label: Any

class RDFStarTriple_to_dictResult(TypedDictModel):
    annotations: Any
    object: Any
    predicate: Any
    subject: Any

class PROVGraph_to_dictResult(TypedDictModel):
    context_: dict[str, Any]
    id_: Any
    activities: Any
    agents: Any
    annotations: Any
    entities: Any


class PROVNamespace:
    """PROV-O namespace constants."""

    # Core namespaces
    PROV = "http://www.w3.org/ns/prov#"
    RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    RDFS = "http://www.w3.org/2000/01/rdf-schema#"
    XSD = "http://www.w3.org/2001/XMLSchema#"

    # Value Fabric namespace
    VF = "http://valuefabric.io/ns/prov#"

    # Common prefixes
    @classmethod
    def get_prefixes(cls) -> dict[str, str]:
        return PROVNamespace_get_prefixesResult.model_validate({
            "prov": cls.PROV,
            "rdf": cls.RDF,
            "rdfs": cls.RDFS,
            "xsd": cls.XSD,
            "vf": cls.VF,
        })


class PROVType(str, Enum):
    """PROV-O entity/activity/agent types."""

    # Entities
    ENTITY = "prov:Entity"
    COLLECTION = "prov:Collection"
    BUNDLE = "prov:Bundle"
    PLAN = "prov:Plan"

    # Activities
    ACTIVITY = "prov:Activity"

    # Agents
    AGENT = "prov:Agent"
    PERSON = "prov:Person"
    ORGANIZATION = "prov:Organization"
    SOFTWARE_AGENT = "prov:SoftwareAgent"

    # Value Fabric specific
    LLM_MODEL = "vf:LLMModel"
    AI_AGENT = "vf:AIAgent"
    CALCULATION = "vf:Calculation"
    EXTRACTION = "vf:Extraction"
    SYNTHESIS = "vf:Synthesis"


@dataclass
class PROVEntity:
    """PROV-O Entity representation.

    An entity is a physical, digital, conceptual, or other kind of thing
    with some fixed aspects; entities may be real or imaginary.

    Attributes:
        entity_id: Unique identifier (URI)
        entity_type: Type of entity
        label: Human-readable label
        generated_at: When entity was generated
        attributes: Additional entity attributes
    """

    entity_id: str
    entity_type: PROVType = PROVType.ENTITY
    label: str | None = None
    generated_at: datetime | None = None
    generated_by: str | None = None  # Activity ID
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.entity_id.startswith(("http://", "https://", "urn:")):
            # Generate URN if not a full URI
            self.entity_id = f"urn:uuid:{self.entity_id}"

    def to_triples(self) -> list[tuple[str, str, str | Any]]:
        """Convert to RDF triples.

        Returns:
            List of (subject, predicate, object) triples
        """
        triples = [
            (self.entity_id, "rdf:type", self.entity_type.value),
        ]

        if self.label:
            triples.append((self.entity_id, "rdfs:label", self.label))

        if self.generated_at:
            triples.append((self.entity_id, "prov:generatedAtTime", self.generated_at.isoformat()))

        if self.generated_by:
            triples.append((self.entity_id, "prov:wasGeneratedBy", self.generated_by))

        # Add custom attributes
        for key, value in self.attributes.items():
            triples.append((self.entity_id, f"vf:{key}", value))

        return triples

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return PROVEntity_to_dictResult.model_validate({
            "id_": self.entity_id,
            "type_": self.entity_type.value,
            "label": self.label,
            "generatedAt": self.generated_at.isoformat() if self.generated_at else None,
            "generatedBy": self.generated_by,
            "attributes": self.attributes,
        })


@dataclass
class PROVActivity:
    """PROV-O Activity representation.

    An activity is something that occurs over a period of time and acts upon
    or with entities; it may include consuming, processing, transforming,
    modifying, relocating, using, or generating entities.

    Attributes:
        activity_id: Unique identifier (URI)
        activity_type: Type of activity
        label: Human-readable label
        started_at: When activity started
        ended_at: When activity ended
        used_entities: Entities used by activity
        generated_entities: Entities generated by activity
        was_associated_with: Agents associated with activity
        attributes: Additional activity attributes
    """

    activity_id: str
    activity_type: PROVType = PROVType.ACTIVITY
    label: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    used_entities: list[str] = field(default_factory=list)  # Entity IDs
    generated_entities: list[str] = field(default_factory=list)  # Entity IDs
    was_associated_with: list[str] = field(default_factory=list)  # Agent IDs
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.activity_id.startswith(("http://", "https://", "urn:")):
            self.activity_id = f"urn:uuid:{self.activity_id}"

    def to_triples(self) -> list[tuple[str, str, str | Any]]:
        """Convert to RDF triples."""
        triples = [
            (self.activity_id, "rdf:type", self.activity_type.value),
        ]

        if self.label:
            triples.append((self.activity_id, "rdfs:label", self.label))

        if self.started_at:
            triples.append((self.activity_id, "prov:startedAtTime", self.started_at.isoformat()))

        if self.ended_at:
            triples.append((self.activity_id, "prov:endedAtTime", self.ended_at.isoformat()))

        for entity_id in self.used_entities:
            triples.append((self.activity_id, "prov:used", entity_id))

        for entity_id in self.generated_entities:
            triples.append((entity_id, "prov:wasGeneratedBy", self.activity_id))

        for agent_id in self.was_associated_with:
            triples.append((self.activity_id, "prov:wasAssociatedWith", agent_id))

        # Add custom attributes
        for key, value in self.attributes.items():
            triples.append((self.activity_id, f"vf:{key}", value))

        return triples

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return PROVActivity_to_dictResult.model_validate({
            "id_": self.activity_id,
            "type_": self.activity_type.value,
            "label": self.label,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "endedAt": self.ended_at.isoformat() if self.ended_at else None,
            "used": self.used_entities,
            "generated": self.generated_entities,
            "associatedWith": self.was_associated_with,
            "attributes": self.attributes,
        })


@dataclass
class PROVAgent:
    """PROV-O Agent representation.

    An agent is something that bears some form of responsibility for an activity
    taking place, for the existence of an entity, or for another agent's activity.

    Attributes:
        agent_id: Unique identifier (URI)
        agent_type: Type of agent
        label: Human-readable label
        acted_on_behalf_of: Agent this agent acts for
        attributes: Additional agent attributes
    """

    agent_id: str
    agent_type: PROVType = PROVType.AGENT
    label: str | None = None
    acted_on_behalf_of: str | None = None  # Agent ID
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.agent_id.startswith(("http://", "https://", "urn:")):
            self.agent_id = f"urn:uuid:{self.agent_id}"

    def to_triples(self) -> list[tuple[str, str, str | Any]]:
        """Convert to RDF triples."""
        triples = [
            (self.agent_id, "rdf:type", self.agent_type.value),
        ]

        if self.label:
            triples.append((self.agent_id, "rdfs:label", self.label))

        if self.acted_on_behalf_of:
            triples.append((self.agent_id, "prov:actedOnBehalfOf", self.acted_on_behalf_of))

        # Add custom attributes
        for key, value in self.attributes.items():
            triples.append((self.agent_id, f"vf:{key}", value))

        return triples

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return PROVAgent_to_dictResult.model_validate({
            "id_": self.agent_id,
            "type_": self.agent_type.value,
            "label": self.label,
            "actedOnBehalfOf": self.acted_on_behalf_of,
            "attributes": self.attributes,
        })


@dataclass
class RDFStarTriple:
    """RDF* triple for annotating statements.

    RDF* allows making statements about statements:
    <<(subject predicate object)>> annotation_predicate annotation_value

    Example:
        <<(:calculation123 :produces :roi_value_456)>>
            vf:executionTrace "trace_data";
            vf:algorithmVersion "2.1.0".

    Attributes:
        subject: Triple subject
        predicate: Triple predicate
        object_: Triple object
        annotations: Annotations on the statement
    """

    subject: str
    predicate: str
    object_: str | Any
    annotations: dict[str, Any] = field(default_factory=dict)

    def to_rdf_star(self) -> str:
        """Convert to RDF* Turtle syntax.

        Returns:
            RDF* Turtle representation
        """
        # Escape quotes in object
        obj_str = str(self.object_).replace('"', '\\"')

        lines = [f'<<({self.subject} {self.predicate} "{obj_str}")>>']

        for pred, value in self.annotations.items():
            value_str = str(value).replace('"', '\\"')
            lines.append(f'    {pred} "{value_str}";')

        lines[-1] = lines[-1].rstrip(";") + "."

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return RDFStarTriple_to_dictResult.model_validate({
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object_,
            "annotations": self.annotations,
        })


class PROVGraph:
    """Collection of PROV-O entities, activities, and agents.

    Represents a provenance graph that can be serialized to various formats.
    """

    def __init__(self, graph_id: str | None = None):
        """Initialize provenance graph.

        Args:
            graph_id: Unique graph identifier
        """
        self.graph_id = graph_id or f"urn:uuid:{uuid4()}"
        self.entities: dict[str, PROVEntity] = {}
        self.activities: dict[str, PROVActivity] = {}
        self.agents: dict[str, PROVAgent] = {}
        self.rdf_star_triples: list[RDFStarTriple] = []

    def add_entity(self, entity: PROVEntity) -> None:
        """Add entity to graph."""
        self.entities[entity.entity_id] = entity

    def add_activity(self, activity: PROVActivity) -> None:
        """Add activity to graph."""
        self.activities[activity.activity_id] = activity

    def add_agent(self, agent: PROVAgent) -> None:
        """Add agent to graph."""
        self.agents[agent.agent_id] = agent

    def add_rdf_star(self, triple: RDFStarTriple) -> None:
        """Add RDF* annotated triple."""
        self.rdf_star_triples.append(triple)

    def to_triples(self) -> list[tuple[str, str, str | Any]]:
        """Convert entire graph to RDF triples."""
        triples = []

        for entity in self.entities.values():
            triples.extend(entity.to_triples())

        for activity in self.activities.values():
            triples.extend(activity.to_triples())

        for agent in self.agents.values():
            triples.extend(agent.to_triples())

        return triples

    def to_turtle(self) -> str:
        """Serialize graph to Turtle format.

        Returns:
            Turtle serialization
        """
        lines = [
            "@prefix prov: <http://www.w3.org/ns/prov#> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix vf: <http://valuefabric.io/ns/prov#> .",
            "",
        ]

        # Add RDF* triples first
        if self.rdf_star_triples:
            lines.append("# RDF* Annotations")
            for triple in self.rdf_star_triples:
                lines.append(triple.to_rdf_star())
            lines.append("")

        # Add entities
        if self.entities:
            lines.append("# Entities")
            for entity in self.entities.values():
                for triple in entity.to_triples():
                    obj = f'"{triple[2]}"' if isinstance(triple[2], str) else str(triple[2])
                    lines.append(f"{triple[0]} {triple[1]} {obj} .")
            lines.append("")

        # Add activities
        if self.activities:
            lines.append("# Activities")
            for activity in self.activities.values():
                for triple in activity.to_triples():
                    obj = f'"{triple[2]}"' if isinstance(triple[2], str) else str(triple[2])
                    lines.append(f"{triple[0]} {triple[1]} {obj} .")
            lines.append("")

        # Add agents
        if self.agents:
            lines.append("# Agents")
            for agent in self.agents.values():
                for triple in agent.to_triples():
                    obj = f'"{triple[2]}"' if isinstance(triple[2], str) else str(triple[2])
                    lines.append(f"{triple[0]} {triple[1]} {obj} .")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return PROVGraph_to_dictResult.model_validate({
            "id_": self.graph_id,
            "context_": {
                "prov": "http://www.w3.org/ns/prov#",
                "vf": "http://valuefabric.io/ns/prov#",
            },
            "entities": [e.to_dict() for e in self.entities.values()],
            "activities": [a.to_dict() for a in self.activities.values()],
            "agents": [a.to_dict() for a in self.agents.values()],
            "annotations": [t.to_dict() for t in self.rdf_star_triples],
        })


def create_prov_graph(
    workflow_id: str,
    agent_id: str,
    inputs: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    started_at: datetime,
    ended_at: datetime,
) -> PROVGraph:
    """Create a PROV-O graph for workflow execution.

    Args:
        workflow_id: Workflow instance ID
        agent_id: Agent that executed workflow
        inputs: Input entities
        outputs: Output entities
        started_at: When workflow started
        ended_at: When workflow ended

    Returns:
        PROVGraph with workflow provenance
    """
    graph = PROVGraph(graph_id=f"prov:{workflow_id}")

    # Create agent
    agent = PROVAgent(
        agent_id=f"agent:{agent_id}",
        agent_type=PROVType.AI_AGENT,
        label=f"Agent {agent_id}",
    )
    graph.add_agent(agent)

    # Create workflow activity
    activity = PROVActivity(
        activity_id=f"activity:{workflow_id}",
        activity_type=PROVType.ACTIVITY,
        label=f"Workflow {workflow_id}",
        started_at=started_at,
        ended_at=ended_at,
        was_associated_with=[agent.agent_id],
    )

    # Add input entities
    for inp in inputs:
        entity = PROVEntity(
            entity_id=f"entity:{inp.get('id', uuid4())}",
            label=inp.get("name", "Input"),
            attributes=inp.get("attributes", {}),
        )
        graph.add_entity(entity)
        activity.used_entities.append(entity.entity_id)

    # Add output entities
    for out in outputs:
        entity = PROVEntity(
            entity_id=f"entity:{out.get('id', uuid4())}",
            label=out.get("name", "Output"),
            generated_at=ended_at,
            generated_by=activity.activity_id,
            attributes=out.get("attributes", {}),
        )
        graph.add_entity(entity)
        activity.generated_entities.append(entity.entity_id)

    graph.add_activity(activity)

    return graph
