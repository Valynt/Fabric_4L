from __future__ import annotations

"""Triple store implementations for provenance storage.

Supports:
- In-memory storage (for testing/single-node)
- Triple store backend (Apache Jena, RDF4J, etc.)
- Neo4j with RDF extension
"""


import logging
from abc import ABC, abstractmethod
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel

from .models import PROVGraph


class InMemoryTripleStore_get_lineageResult(TypedDictModel):
    depth: Any
    downstream: Any
    entity_id: Any
    upstream: Any

class JenaTripleStore_get_lineageResult(TypedDictModel):
    downstream: Any
    entity_id: Any
    upstream: Any

logger = logging.getLogger(__name__)


class TripleStore(ABC):
    """Abstract base class for triple store implementations."""

    @abstractmethod
    async def store_graph(self, graph: PROVGraph) -> str:
        """Store a provenance graph.

        Args:
            graph: PROV graph to store

        Returns:
            graph_id: ID of stored graph
        """
        pass

    @abstractmethod
    async def query(self, sparql_query: str) -> list[dict[str, Any]]:
        """Execute SPARQL query.

        Args:
            sparql_query: SPARQL query string

        Returns:
            Query results
        """
        pass

    @abstractmethod
    async def get_lineage(
        self,
        entity_id: str,
        direction: str = "both",
        depth: int = 3,
    ) -> dict[str, Any]:
        """Get data lineage for an entity.

        Args:
            entity_id: Entity to trace
            direction: "upstream", "downstream", or "both"
            depth: Maximum traversal depth

        Returns:
            Lineage information
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close store connection."""
        pass


class InMemoryTripleStore(TripleStore):
    """In-memory triple store implementation.

    Suitable for testing and single-node deployments.
    Stores triples as (subject, predicate, object) tuples.
    """

    def __init__(self):
        """Initialize in-memory store."""
        # subject -> {predicate -> [objects]}
        self._triples: dict[str, dict[str, list[Any]]] = {}
        # graph_id -> triples
        self._graphs: dict[str, list[tuple[str, str, Any]]] = {}
        # RDF* annotations: (s, p, o) -> {annotation_predicate -> value}
        self._annotations: dict[tuple[str, str, str], dict[str, Any]] = {}

    async def store_graph(self, graph: PROVGraph) -> str:
        """Store a provenance graph."""
        graph_id = graph.graph_id
        triples = graph.to_triples()

        # Store triples
        self._graphs[graph_id] = triples

        # Index triples
        for subject, predicate, object_ in triples:
            if subject not in self._triples:
                self._triples[subject] = {}
            if predicate not in self._triples[subject]:
                self._triples[subject][predicate] = []
            self._triples[subject][predicate].append(object_)

        # Store RDF* annotations
        for triple in graph.rdf_star_triples:
            key = (triple.subject, triple.predicate, str(triple.object_))
            self._annotations[key] = triple.annotations

        logger.info(f"Stored graph {graph_id} with {len(triples)} triples")
        return graph_id

    async def query(self, sparql_query: str) -> list[dict[str, Any]]:
        """Execute simple SPARQL-like query.

        Note: This is a simplified implementation supporting basic patterns.
        For full SPARQL support, use a proper triple store.

        Args:
            sparql_query: Query string (simplified)

        Returns:
            Matching results
        """
        # Very simple pattern matching
        results = []

        # Parse basic SELECT ?s ?p ?o WHERE pattern
        # This is a minimal implementation
        for subject, predicates in self._triples.items():
            for predicate, objects in predicates.items():
                for object_ in objects:
                    results.append(
                        {
                            "s": subject,
                            "p": predicate,
                            "o": object_,
                        }
                    )

        return results

    async def get_lineage(
        self,
        entity_id: str,
        direction: str = "both",
        depth: int = 3,
    ) -> dict[str, Any]:
        """Get data lineage."""
        upstream = []
        downstream = []

        if direction in ["upstream", "both"]:
            upstream = self._get_upstream(entity_id, depth)

        if direction in ["downstream", "both"]:
            downstream = self._get_downstream(entity_id, depth)

        return InMemoryTripleStore_get_lineageResult.model_validate({
            "entity_id": entity_id,
            "upstream": upstream,
            "downstream": downstream,
            "depth": depth,
        })


    def _get_upstream(
        self,
        entity_id: str,
        depth: int,
        visited: set | None = None,
    ) -> list[dict[str, Any]]:
        """Get upstream lineage (what this entity was derived from)."""
        if visited is None:
            visited = set()

        if entity_id in visited or depth <= 0:
            return []

        visited.add(entity_id)
        results = []

        # Find what generated this entity
        # Look for prov:wasGeneratedBy
        entity_data = self._triples.get(entity_id, {})
        generated_by = entity_data.get("prov:wasGeneratedBy", [])

        for activity_id in generated_by:
            # Find what entities were used by this activity
            activity_data = self._triples.get(activity_id, {})
            used = activity_data.get("prov:used", [])

            for used_entity in used:
                results.append(
                    {
                        "entity": used_entity,
                        "via_activity": activity_id,
                    }
                )
                # Recurse
                results.extend(self._get_upstream(used_entity, depth - 1, visited))

        return results

    def _get_downstream(
        self,
        entity_id: str,
        depth: int,
        visited: set | None = None,
    ) -> list[dict[str, Any]]:
        """Get downstream lineage (what was derived from this entity)."""
        if visited is None:
            visited = set()

        if entity_id in visited or depth <= 0:
            return []

        visited.add(entity_id)
        results = []

        # Find activities that used this entity
        for subject, predicates in self._triples.items():
            if "prov:used" in predicates:
                if entity_id in predicates["prov:used"]:
                    # This activity used the entity
                    activity_id = subject

                    # Find what was generated by this activity
                    activity_data = self._triples.get(activity_id, {})
                    activity_data.get("prov:wasGeneratedBy", [])

                    # Find entities generated by this activity
                    for potential_entity, entity_preds in self._triples.items():
                        if "prov:wasGeneratedBy" in entity_preds:
                            if activity_id in entity_preds["prov:wasGeneratedBy"]:
                                results.append(
                                    {
                                        "entity": potential_entity,
                                        "via_activity": activity_id,
                                    }
                                )
                                # Recurse
                                results.extend(
                                    self._get_downstream(potential_entity, depth - 1, visited)
                                )

        return results

    async def get_rdf_star_annotation(
        self,
        subject: str,
        predicate: str,
        object_: str,
    ) -> dict[str, Any] | None:
        """Get RDF* annotation for a triple.

        Args:
            subject: Triple subject
            predicate: Triple predicate
            object_: Triple object

        Returns:
            Annotations or None
        """
        key = (subject, predicate, object_)
        return self._annotations.get(key)

    async def close(self) -> None:
        """Clear in-memory store."""
        self._triples.clear()
        self._graphs.clear()
        self._annotations.clear()


class JenaTripleStore(TripleStore):
    """Apache Jena Fuseki triple store client.

    Connects to a remote Jena Fuseki SPARQL endpoint.
    """

    def __init__(
        self,
        endpoint_url: str = "http://localhost:3030/ds",
        dataset: str = "valuefabric",
    ):
        """Initialize Jena client.

        Args:
            endpoint_url: Fuseki endpoint URL
            dataset: Dataset name
        """
        self.endpoint_url = endpoint_url.rstrip("/")
        self.dataset = dataset
        self.query_url = f"{self.endpoint_url}/{dataset}/sparql"
        self.update_url = f"{self.endpoint_url}/{dataset}/update"
        self.graph_store_url = f"{self.endpoint_url}/{dataset}/data"

    async def store_graph(self, graph: PROVGraph) -> str:
        """Store graph via HTTP."""
        import httpx

        # Serialize to Turtle
        turtle_data = graph.to_turtle()

        # POST to graph store
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.graph_store_url,
                content=turtle_data,
                headers={"Content-Type": "text/turtle"},
            )
            response.raise_for_status()

        return graph.graph_id

    async def query(self, sparql_query: str) -> list[dict[str, Any]]:
        """Execute SPARQL query."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.query_url,
                data={"query": sparql_query},
                headers={"Accept": "application/sparql-results+json"},
            )
            response.raise_for_status()

            data = response.json()

            # Parse results
            results = []
            for binding in data.get("results", {}).get("bindings", []):
                row = {}
                for var_name, var_data in binding.items():
                    row[var_name] = var_data.get("value")
                results.append(row)

            return results

    async def get_lineage(
        self,
        entity_id: str,
        direction: str = "both",
        depth: int = 3,
    ) -> dict[str, Any]:
        """Get lineage via SPARQL."""
        # Build SPARQL query for lineage
        if direction == "upstream":
            query = self._build_upstream_query(entity_id, depth)
        elif direction == "downstream":
            query = self._build_downstream_query(entity_id, depth)
        else:
            query = self._build_both_query(entity_id, depth)

        results = await self.query(query)

        upstream: list[dict] = []
        downstream: list[dict] = []
        for r in results:
            direction_val = r.get("direction")
            if direction_val == "upstream":
                upstream.append(r)
            elif direction_val == "downstream":
                downstream.append(r)

        return JenaTripleStore_get_lineageResult.model_validate({
            "entity_id": entity_id,
            "upstream": upstream,
            "downstream": downstream,
        })


    def _build_upstream_query(self, entity_id: str, depth: int) -> str:
        """Build SPARQL query for upstream lineage."""
        return f"""
        PREFIX prov: <http://www.w3.org/ns/prov#>
        SELECT ?entity ?activity WHERE {{
            <{entity_id}> prov:wasGeneratedBy ?activity .
            ?activity prov:used ?entity .
        }}
        """

    def _build_downstream_query(self, entity_id: str, depth: int) -> str:
        """Build SPARQL query for downstream lineage."""
        return f"""
        PREFIX prov: <http://www.w3.org/ns/prov#>
        SELECT ?entity ?activity WHERE {{
            ?activity prov:used <{entity_id}> .
            ?entity prov:wasGeneratedBy ?activity .
        }}
        """

    def _build_both_query(self, entity_id: str, depth: int) -> str:
        """Build SPARQL query for both directions."""
        return f"""
        PREFIX prov: <http://www.w3.org/ns/prov#>
        SELECT ?entity ?activity ?direction WHERE {{
            {{
                <{entity_id}> prov:wasGeneratedBy ?activity .
                ?activity prov:used ?entity .
                BIND("upstream" AS ?direction)
            }} UNION {{
                ?activity prov:used <{entity_id}> .
                ?entity prov:wasGeneratedBy ?activity .
                BIND("downstream" AS ?direction)
            }}
        }}
        """

    async def close(self) -> None:
        """Close (no-op for HTTP client)."""
        pass


async def create_triple_store(
    backend: str = "memory",
    **kwargs,
) -> TripleStore:
    """Factory function to create triple store.

    Args:
        backend: "memory", "jena", etc.
        **kwargs: Backend-specific configuration

    Returns:
        Configured TripleStore
    """
    if backend == "memory":
        return InMemoryTripleStore()
    elif backend == "jena":
        return JenaTripleStore(
            endpoint_url=kwargs.get("endpoint_url", "http://localhost:3030"),
            dataset=kwargs.get("dataset", "valuefabric"),
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")
