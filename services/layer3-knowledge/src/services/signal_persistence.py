"""Signal persistence service for Layer 3 Knowledge Graph.

Manages persistence of PainSignal entities and their relationships
to Evidence, ValueDrivers, and Accounts in Neo4j.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from neo4j import AsyncDriver

from ..db.query_execution import run_validated_query

try:
    from value_fabric.shared.identity.context import require_context
except ImportError:
    require_context = None

logger = logging.getLogger(__name__)


def _get_tenant_id() -> str:
    """Safely retrieve tenant ID from request context.

    Returns "default" if context is not available (e.g., in tests or background tasks).
    """
    if not require_context:
        return "default"
    try:
        return str(require_context().tenant_id)
    except RuntimeError:
        return "default"


class SignalPersistenceService:
    """Service for persisting and retrieving pain signals.

    Handles:
    - PainSignal node creation/update
    - Evidence relationship linking
    - Account signal associations
    - Value driver mappings
    - Tenant-scoped queries
    """

    def __init__(self, driver: AsyncDriver):
        """Initialize with Neo4j driver.

        Args:
            driver: Neo4j async driver instance
        """
        self._driver = driver

    async def persist_signal(
        self,
        tenant_id: str,
        signal_data: dict[str, Any],
    ) -> str:
        """Persist a pain signal to the knowledge graph.

        Creates or updates a PainSignal node linked to an Account.

        Args:
            signal_data: Signal data dictionary (matches PainSignal model)

        Returns:
            Signal ID of the persisted signal
        """
        signal_id = signal_data.get("id")
        account_id = signal_data.get("account_id")

        # Build properties dictionary
        properties = {
            "id": signal_id,
            "tenant_id": tenant_id,
            "name": signal_data.get("name"),
            "category": signal_data.get("category", "Operational"),
            "description": signal_data.get("description"),
            "confidence_score": signal_data.get("confidence_score", 0.0),
            "confidence_explanation": signal_data.get("confidence_explanation", ""),
            "trend_direction": signal_data.get("trend_direction", "new"),
            "trend_explanation": signal_data.get("trend_explanation", ""),
            "executive_hypothesis": signal_data.get("executive_hypothesis", ""),
            "source_prompt_id": signal_data.get("source_prompt_id", ""),
            "extraction_trace_id": signal_data.get("extraction_trace_id", ""),
            "created_at": signal_data.get("created_at", datetime.now(UTC).isoformat()),
            "updated_at": signal_data.get("updated_at", datetime.now(UTC).isoformat()),
        }

        # Handle optional impact fields
        if "impact_value" in signal_data and signal_data["impact_value"] is not None:
            properties["impact_value"] = float(signal_data["impact_value"])
        if "impact_unit" in signal_data and signal_data["impact_unit"]:
            properties["impact_unit"] = signal_data["impact_unit"]
        if "impact_formula_id" in signal_data:
            properties["impact_formula_id"] = signal_data["impact_formula_id"]

        async with self._driver.session() as session:
            # Create/merge PainSignal node
            query = """
            MERGE (s:PainSignal {id: $id, tenant_id: $tenant_id})
            SET s += $properties
            WITH s
            MATCH (a:Account {id: $account_id, tenant_id: $tenant_id})
            MERGE (a)-[r:exhibits]->(s)
            SET r.discovered_at = datetime()
            RETURN s.id as signal_id
            """

            result = await run_validated_query(session,
                query,
                {
                    "id": signal_id,
                    "tenant_id": tenant_id,
                    "account_id": account_id,
                    "properties": properties,
                },
            )
            record = await result.single()
            return record["signal_id"] if record else signal_id

    async def link_evidence(
        self,
        tenant_id: str,
        signal_id: str,
        evidence_matches: list[dict[str, Any]],
    ) -> int:
        """Link evidence to a pain signal.

        Creates Evidence nodes and links them to the signal.

        Args:
            signal_id: Target signal ID
            evidence_matches: List of evidence match data

        Returns:
            Number of evidence links created
        """
        links_created = 0

        async with self._driver.session() as session:
            for match in evidence_matches:
                evidence_id = match.get("evidence_id")

                query = """
                MATCH (s:PainSignal {id: $signal_id, tenant_id: $tenant_id})
                MERGE (e:Evidence {id: $evidence_id, tenant_id: $tenant_id})
                SET e.title = $title,
                    e.evidence_type = $evidence_type
                MERGE (s)-[r:supportedBy]->(e)
                SET r.match_score = $match_score,
                    r.match_reasoning = $match_reasoning,
                    r.relevance_quote = $relevance_quote,
                    r.linked_at = datetime()
                RETURN count(r) as created
                """

                result = await run_validated_query(session,
                    query,
                    {
                        "signal_id": signal_id,
                        "evidence_id": evidence_id,
                        "tenant_id": tenant_id,
                        "title": match.get("title", ""),
                        "evidence_type": match.get("evidence_type", "case_study"),
                        "match_score": match.get("match_score", 0),
                        "match_reasoning": match.get("match_reasoning", ""),
                        "relevance_quote": match.get("relevance_quote", ""),
                    },
                )
                record = await result.single()
                if record and record["created"] > 0:
                    links_created += 1

        return links_created

    async def map_to_value_driver(
        self,
        tenant_id: str,
        signal_id: str,
        value_driver_id: str,
    ) -> bool:
        """Map a signal to a value driver.

        Args:
            signal_id: Signal ID
            value_driver_id: Value driver ID

        Returns:
            True if relationship created
        """
        async with self._driver.session() as session:
            query = """
            MATCH (s:PainSignal {id: $signal_id, tenant_id: $tenant_id})
            MATCH (vd:ValueDriver {id: $value_driver_id, tenant_id: $tenant_id})
            MERGE (s)-[r:mapsTo]->(vd)
            SET r.mapped_at = datetime()
            RETURN count(r) > 0 as created
            """

            result = await run_validated_query(session,
                query,
                {
                    "signal_id": signal_id,
                    "value_driver_id": value_driver_id,
                    "tenant_id": tenant_id,
                },
            )
            record = await result.single()
            return record["created"] if record else False

    async def get_signals_for_account(
        self,
        tenant_id: str,
        account_id: str,
        category: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get signals for an account.

        Args:
            account_id: Account identifier
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of signal dictionaries
        """
        async with self._driver.session() as session:
            if category:
                query = """
                MATCH (a:Account {id: $account_id, tenant_id: $tenant_id})
                      -[:exhibits]->(s:PainSignal {category: $category, tenant_id: $tenant_id})
                OPTIONAL MATCH (s)-[r:supportedBy]->(e:Evidence {tenant_id: $tenant_id})
                RETURN s {
                    .*,
                    evidence_matches: collect(e {.*, match_score: r.match_score})
                } as signal
                ORDER BY s.confidence_score DESC
                LIMIT $limit
                """
                params = {
                    "account_id": account_id,
                    "tenant_id": tenant_id,
                    "category": category,
                    "limit": limit,
                }
            else:
                query = """
                MATCH (a:Account {id: $account_id, tenant_id: $tenant_id})
                      -[:exhibits]->(s:PainSignal {tenant_id: $tenant_id})
                OPTIONAL MATCH (s)-[r:supportedBy]->(e:Evidence {tenant_id: $tenant_id})
                RETURN s {
                    .*,
                    evidence_matches: collect(e {.*, match_score: r.match_score})
                } as signal
                ORDER BY s.confidence_score DESC
                LIMIT $limit
                """
                params = {
                    "account_id": account_id,
                    "tenant_id": tenant_id,
                    "limit": limit,
                }

            result = await run_validated_query(session, query, params)
            records = await result.data()
            return [r["signal"] for r in records]

    async def get_signal_by_id(
        self,
        tenant_id: str,
        signal_id: str,
    ) -> dict[str, Any] | None:
        """Get a single signal by ID with full details.

        Args:
            signal_id: Signal identifier

        Returns:
            Signal dictionary or None if not found
        """
        async with self._driver.session() as session:
            query = """
            MATCH (s:PainSignal {id: $signal_id, tenant_id: $tenant_id})
            OPTIONAL MATCH (s)-[r:supportedBy]->(e:Evidence {tenant_id: $tenant_id})
            OPTIONAL MATCH (s)-[:mapsTo]->(vd:ValueDriver {tenant_id: $tenant_id})
            RETURN s {
                .*,
                evidence_matches: collect(DISTINCT e {
                    evidence_id: e.id,
                    evidence_type: e.evidence_type,
                    title: e.title,
                    match_score: r.match_score,
                    match_reasoning: r.match_reasoning,
                    relevance_quote: r.relevance_quote
                }),
                value_drivers: collect(DISTINCT vd {id: vd.id, name: vd.name})
            } as signal
            """

            result = await run_validated_query(session,
                query,
                {"signal_id": signal_id, "tenant_id": tenant_id},
            )
            record = await result.single()
            return record["signal"] if record else None

    async def update_signal_impact(
        self,
        tenant_id: str,
        signal_id: str,
        impact_value: Decimal,
        impact_unit: str,
        formula_id: str,
    ) -> bool:
        """Update signal with quantified impact.

        Args:
            signal_id: Signal identifier
            impact_value: Calculated impact value
            impact_unit: Unit of measurement
            formula_id: Applied formula reference

        Returns:
            True if updated successfully
        """
        async with self._driver.session() as session:
            query = """
            MATCH (s:PainSignal {id: $signal_id, tenant_id: $tenant_id})
            SET s.impact_value = $impact_value,
                s.impact_unit = $impact_unit,
                s.impact_formula_id = $formula_id,
                s.updated_at = datetime()
            WITH s
            MATCH (f:Formula {id: $formula_id, tenant_id: $tenant_id})
            MERGE (s)-[r:quantifiedBy]->(f)
            SET r.quantified_at = datetime()
            RETURN count(s) > 0 as updated
            """

            result = await run_validated_query(session,
                query,
                {
                    "signal_id": signal_id,
                    "impact_value": float(impact_value),
                    "impact_unit": impact_unit,
                    "formula_id": formula_id,
                    "tenant_id": tenant_id,
                },
            )
            record = await result.single()
            return record["updated"] if record else False
