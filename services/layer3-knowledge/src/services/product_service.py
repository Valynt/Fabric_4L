"""Product Portfolio Service for Knowledge Graph operations.

Manages Product, Feature, and Capability nodes and their relationships
in Neo4j. Provides product-to-capability mapping, signal-to-product
matching, and portfolio analytics.

Architecture:
    - Products are top-level nodes representing sellable offerings
    - Features are child nodes linked via HAS_FEATURE
    - Capabilities are linked via ENABLES_CAPABILITY
    - PainSignals are matched to Products via ADDRESSES_PAIN
    - All queries are tenant-scoped via tenant_id property
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from neo4j import AsyncDriver
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..db.audited_mutation import AuditedGraphMutation
from ..db.query_execution import run_validated_query
from ..security.query_validator import ValidatedNeo4jSession
from .cypher_scope_guard import (
    validate_tenant_scoped_cypher,
)


class ProductService_create_productResult(TypedDictModel):
    id: Any

class ProductService_get_productResult(TypedDictModel):
    capabilities: Any
    features: Any

class ProductService_list_productsResult(TypedDictModel):
    limit: Any
    products: Any
    skip: Any
    total: Any

class ProductService_add_featureResult(TypedDictModel):
    id: Any

class ProductService_link_capabilityResult(TypedDictModel):
    capability: Any
    strength: Any

class ProductService_get_portfolio_summaryResult(TypedDictModel):
    avg_capabilities_per_product: Any | None = None
    avg_features_per_product: Any | None = None
    categories: list[Any]
    total_capabilities: int
    total_features: int
    total_products: int

try:
    from value_fabric.shared.identity.context import require_context
except ImportError:
    require_context = None

logger = structlog.get_logger()
_TENANT_OWNED_LABELS = {"Product", "Feature", "Capability", "PainSignal"}


def _get_tenant_id() -> str:
    """Safely retrieve tenant ID from request context.

    Returns "default" if context is not available (e.g., in tests or background tasks).
    """
    if not require_context:
        raise RuntimeError("tenant_id is required in request context")
    try:
        return str(require_context().tenant_id)
    except RuntimeError:
        raise RuntimeError("tenant_id is required in request context")


# ---------------------------------------------------------------------------
# Data Transfer Objects
# ---------------------------------------------------------------------------

class ProductCreate:
    """Input for creating a product node."""

    def __init__(
        self,
        name: str,
        description: str,
        category: str | None = None,
        sku: str | None = None,
        pricing_model: str | None = None,
        target_personas: list[str] | None = None,
        industries: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.sku = sku
        self.pricing_model = pricing_model
        self.target_personas = target_personas or []
        self.industries = industries or []
        self.metadata = metadata or {}


class FeatureCreate:
    """Input for creating a feature node linked to a product."""

    def __init__(
        self,
        name: str,
        description: str,
        feature_type: str = "core",
        maturity: str = "ga",
        metadata: dict[str, Any] | None = None,
    ):
        self.name = name
        self.description = description
        self.feature_type = feature_type  # core, addon, premium
        self.maturity = maturity  # beta, ga, deprecated
        self.metadata = metadata or {}


class ProductService:
    """Service for product portfolio graph operations."""

    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    @staticmethod
    def _validate_query_scope(query: str) -> None:
        validate_tenant_scoped_cypher(
            query,
            tenant_owned_labels=_TENANT_OWNED_LABELS,
            query_name="ProductService",
        )

    async def _run_cypher(
        self,
        session: Any,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> Any:
        """Execute Cypher through mandatory validation gateway."""
        params = parameters or {}
        tenant_id = params.get("tenant_id", None)
        if not tenant_id:
            raise RuntimeError("tenant_id is required for ProductService cypher execution")
        self._validate_query_scope(query)
        validated_session = ValidatedNeo4jSession(session, tenant_id=str(tenant_id), strict=True)
        return await run_validated_query(
            validated_session,
            query,
            params,
            tenant_id=str(tenant_id),
            require_explicit_tenant_id=True,
            query_name="product_service.run_cypher",
        )

    # ------------------------------------------------------------------
    # Product CRUD
    # ------------------------------------------------------------------

    async def create_product(
        self,
        tenant_id: str,
        product: ProductCreate,
    ) -> dict[str, Any]:
        """Create a Product node in the knowledge graph."""
        product_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        product_props = {
            "id": product_id,
            "tenant_id": tenant_id,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "sku": product.sku,
            "pricing_model": product.pricing_model,
            "target_personas": product.target_personas,
            "industries": product.industries,
            "entity_type": "Product",
            "created_at": now,
            "updated_at": now,
        }
        async with self._driver.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="product_service.create_product",
            )
            await mutation.write_node("Product", product_id, product_props)
            logger.info(
                "product_created",
                product_id=product_id,
                tenant_id=tenant_id,
                name=product.name,
            )
            return ProductService_create_productResult.model_validate(product_props)

    async def get_product(
        self,
        tenant_id: str,
        product_id: str,
    ) -> dict[str, Any] | None:
        """Get a single product by ID, scoped to tenant."""
        query = """
        MATCH (p:Product {id: $product_id, tenant_id: $tenant_id})
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature {tenant_id: $tenant_id})
        OPTIONAL MATCH (p)-[:ENABLES_CAPABILITY]->(c:Capability {tenant_id: $tenant_id})
        RETURN p {.id, .name, .description, .category, .sku,
                   .pricing_model, .target_personas, .industries,
                   .created_at, .updated_at} AS product,
               collect(DISTINCT f {.id, .name, .feature_type, .maturity}) AS features,
               collect(DISTINCT c {.id, .name}) AS capabilities
        """
        self._validate_query_scope(query)
        async with self._driver.session() as session:
            result = await self._run_cypher(session,
                query,
                {"product_id": product_id, "tenant_id": tenant_id},
            )
            record = await result.single()
            if not record or not record["product"]:
                return None
            return ProductService_get_productResult.model_validate({
                **record["product"],
                "features": record["features"],
                "capabilities": record["capabilities"],
            })


    async def list_products(
        self,
        tenant_id: str,
        category: str | None = None,
        industry: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List products with optional filtering."""
        where_clauses = ["p.tenant_id = $tenant_id"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "skip": skip,
            "limit": limit,
        }

        if category:
            where_clauses.append("p.category = $category")
            params["category"] = category
        if industry:
            where_clauses.append("$industry IN p.industries")
            params["industry"] = industry

        where = " AND ".join(where_clauses)

        count_query = f"""
        // strict-scoped-query-execution: where includes p.tenant_id = $tenant_id
        MATCH (p:Product) WHERE {where}
        RETURN count(p) AS total
        """
        list_query = f"""
        // strict-scoped-query-execution: where includes p.tenant_id = $tenant_id
        MATCH (p:Product) WHERE {where}
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature {{tenant_id: $tenant_id}})
        OPTIONAL MATCH (p)-[:ENABLES_CAPABILITY]->(c:Capability {{tenant_id: $tenant_id}})
        RETURN p {{.id, .name, .description, .category, .sku,
                    .pricing_model, .industries, .created_at}} AS product,
               count(DISTINCT f) AS feature_count,
               count(DISTINCT c) AS capability_count
        ORDER BY p.name
        SKIP $skip LIMIT $limit
        """

        self._validate_query_scope(count_query)
        self._validate_query_scope(list_query)

        async with self._driver.session() as session:
            # strict-scoped-query-execution: dynamic query parameters include tenant_id
            count_result = await self._run_cypher(session, count_query, params)
            count_record = await count_result.single()
            total = count_record["total"] if count_record else 0

            # strict-scoped-query-execution: dynamic query parameters include tenant_id
            list_result = await self._run_cypher(session, list_query, params)
            records = [record async for record in list_result]

            products = []
            for record in records:
                products.append({
                    **record["product"],
                    "feature_count": record["feature_count"],
                    "capability_count": record["capability_count"],
                })

            return ProductService_list_productsResult.model_validate({"products": products, "total": total, "skip": skip, "limit": limit})

    async def update_product(
        self,
        tenant_id: str,
        product_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update a product's properties."""
        # Only allow safe property updates
        allowed_fields = {
            "name", "description", "category", "sku",
            "pricing_model", "target_personas", "industries",
        }
        safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        if not safe_updates:
            return await self.get_product(tenant_id, product_id)

        set_clauses = ", ".join(f"p.{k} = ${k}" for k in safe_updates)
        query = f"""
        MATCH (p:Product {{id: $product_id, tenant_id: $tenant_id}})
        SET {set_clauses}, p.updated_at = datetime($now)
        RETURN p {{.id, .name, .description, .category}} AS product
        """
        params = {
            "product_id": product_id,
            "tenant_id": tenant_id,
            "now": datetime.now(UTC).isoformat(),
            **safe_updates,
        }

        async with self._driver.session() as session:
            # strict-scoped-query-execution: query parameters include tenant_id
            result = await self._run_cypher(session, query, params)
            record = await result.single()
            if not record:
                return None
            logger.info("product_updated", product_id=product_id, fields=list(safe_updates))
            return record["product"]

    async def delete_product(self, tenant_id: str, product_id: str) -> bool:
        """Delete a product and its orphaned features."""
        exists_query = """
        MATCH (p:Product {id: $product_id, tenant_id: $tenant_id})
        RETURN count(p) AS found
        """
        orphan_features_query = """
        MATCH (p:Product {id: $product_id, tenant_id: $tenant_id})-[:HAS_FEATURE]->(f:Feature {tenant_id: $tenant_id})
        WHERE NOT exists {
            (f)<-[:HAS_FEATURE]-(other:Product {tenant_id: $tenant_id})
            WHERE other.id <> p.id
        }
        RETURN collect(f.id) AS feature_ids
        """
        async with self._driver.session() as session:
            exists_result = await self._run_cypher(
                session,
                exists_query,
                {"product_id": product_id, "tenant_id": tenant_id},
            )
            exists_record = await exists_result.single()
            found_count = 0
            if exists_record:
                try:
                    found_count = exists_record["found"]
                except KeyError:
                    found_count = exists_record["deleted"]
            if found_count <= 0:
                return False

            orphan_result = await self._run_cypher(
                session,
                orphan_features_query,
                {"product_id": product_id, "tenant_id": tenant_id},
            )
            orphan_record = await orphan_result.single()
            orphan_feature_ids = []
            if orphan_record:
                try:
                    orphan_feature_ids = orphan_record["feature_ids"]
                except KeyError:
                    orphan_feature_ids = []

            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="product_service.delete_product",
            )
            await mutation.delete_node("Product", product_id)
            for feature_id in orphan_feature_ids:
                await mutation.delete_node("Feature", feature_id)

            logger.info("product_deleted", product_id=product_id, tenant_id=tenant_id)
            return True

    # ------------------------------------------------------------------
    # Feature Management
    # ------------------------------------------------------------------

    async def add_feature(
        self, tenant_id: str, product_id: str, feature: FeatureCreate
    ) -> dict[str, Any] | None:
        """Add a feature to a product."""
        feature_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        product_query = """
        MATCH (p:Product {id: $product_id, tenant_id: $tenant_id})
        RETURN p.id AS product_id
        """
        feature_props = {
            "id": feature_id,
            "tenant_id": tenant_id,
            "name": feature.name,
            "description": feature.description,
            "feature_type": feature.feature_type,
            "maturity": feature.maturity,
            "entity_type": "Feature",
            "created_at": now,
            "updated_at": now,
        }
        async with self._driver.session() as session:
            product_result = await self._run_cypher(
                session,
                product_query,
                {"product_id": product_id, "tenant_id": tenant_id},
            )
            product_record = await product_result.single()
            if not product_record:
                return None  # Product not found

            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="product_service.add_feature",
            )
            await mutation.write_node("Feature", feature_id, feature_props)
            await mutation.write_relationship(
                product_id,
                "HAS_FEATURE",
                feature_id,
                {"created_at": now},
                versioned=False,
            )
            logger.info(
                "feature_added",
                feature_id=feature_id,
                product_id=product_id,
            )
            return ProductService_add_featureResult.model_validate(feature_props)

    async def remove_feature(
        self, tenant_id: str, product_id: str, feature_id: str
    ) -> bool:
        """Remove a feature from a product."""
        query = """
        MATCH (p:Product {id: $product_id, tenant_id: $tenant_id})
              -[r:HAS_FEATURE]->(f:Feature {id: $feature_id})
        WHERE f.tenant_id = $tenant_id
        DELETE r
        WITH f
        WHERE NOT exists { (f)<-[:HAS_FEATURE]-(:Product) }
        DETACH DELETE f
        RETURN true AS removed
        """
        async with self._driver.session() as session:
            result = await self._run_cypher(session,
                query,
                {
                    "product_id": product_id,
                    "tenant_id": tenant_id,
                    "feature_id": feature_id,
                },
            )
            record = await result.single()
            return bool(record)

    # ------------------------------------------------------------------
    # Capability Linking
    # ------------------------------------------------------------------

    async def link_capability(
        self,
        tenant_id: str,
        product_id: str,
        capability_id: str,
        strength: float = 1.0,
    ) -> dict[str, Any] | None:
        """Link a product to an existing capability node.

        Phase 1 hardening: Uses AuditedGraphMutation for audit trail.
        """
        async with self._driver.session() as session:
            # Phase 1 hardening: Use AuditedGraphMutation for relationship writes
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="product_service.link_capability",
            )

            await mutation.write_relationship(product_id, "ENABLES_CAPABILITY", capability_id, {"strength": strength})

            # Query to return capability info
            query = """
            MATCH (c:Capability {id: $capability_id, tenant_id: $tenant_id})
            RETURN c {.id, .name} AS capability
            """
            result = await self._run_cypher(session, query, {
                "capability_id": capability_id,
                "tenant_id": tenant_id,
            })
            record = await result.single()
            if not record:
                return None
            return ProductService_link_capabilityResult.model_validate({
                "capability": record["capability"],
                "strength": strength,
            })


    async def unlink_capability(
        self, tenant_id: str, product_id: str, capability_id: str
    ) -> bool:
        """Remove the ENABLES_CAPABILITY relationship.

        Phase 1 hardening: Uses AuditedGraphMutation for audit trail.
        """
        async with self._driver.session() as session:
            # Phase 1 hardening: Use AuditedGraphMutation for relationship deletion
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="product_service.unlink_capability",
            )

            await mutation.delete_relationship(product_id, "ENABLES_CAPABILITY", capability_id)
            return True

    # ------------------------------------------------------------------
    # Signal-to-Product Matching
    # ------------------------------------------------------------------

    async def match_signals_to_products(
        self, tenant_id: str, account_id: str | None = None, min_confidence: float = 0.5
    ) -> list[dict[str, Any]]:
        """Match PainSignals to Products via shared Capabilities.

        The matching logic:
        1. PainSignal -[:INDICATES_NEED_FOR]-> Capability
        2. Product -[:ENABLES_CAPABILITY]-> Capability
        3. Score = sum(signal.confidence * relationship.strength)
        """
        where_clauses = ["ps.tenant_id = $tenant_id", "ps.confidence_score >= $min_confidence"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "min_confidence": min_confidence,
        }

        if account_id:
            where_clauses.append("ps.account_id = $account_id")
            params["account_id"] = account_id

        where = " AND ".join(where_clauses)

        query = f"""
        // strict-scoped-query-execution: where includes ps.tenant_id = $tenant_id
        MATCH (ps:PainSignal)-[:INDICATES_NEED_FOR]->(c:Capability)<-[ec:ENABLES_CAPABILITY]-(p:Product)
        WHERE {where} AND p.tenant_id = $tenant_id AND c.tenant_id = $tenant_id
        WITH p, ps, c,
             ps.confidence_score * COALESCE(ec.strength, 1.0) AS match_score
        ORDER BY match_score DESC
        WITH p,
             collect(DISTINCT {{
                 signal_id: ps.id,
                 signal_name: ps.name,
                 capability_id: c.id,
                 capability_name: c.name,
                 score: match_score
             }}) AS matches,
             sum(match_score) AS total_score,
             count(DISTINCT ps) AS signal_count
        RETURN p {{.id, .name, .category}} AS product,
               total_score,
               signal_count,
               matches[0..5] AS top_matches
        ORDER BY total_score DESC
        """

        self._validate_query_scope(query)
        async with self._driver.session() as session:
            # strict-scoped-query-execution: query parameters include tenant_id
            result = await self._run_cypher(session, query, params)
            records = [record async for record in result]
            return [
                {
                    "product": record["product"],
                    "total_score": record["total_score"],
                    "signal_count": record["signal_count"],
                    "top_matches": record["top_matches"],
                }
                for record in records
            ]

    # ------------------------------------------------------------------
    # Portfolio Analytics
    # ------------------------------------------------------------------

    async def get_portfolio_summary(self, tenant_id: str) -> dict[str, Any]:
        """Get a summary of the product portfolio for a tenant."""
        query = """
        MATCH (p:Product {tenant_id: $tenant_id})
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature {tenant_id: $tenant_id})
        OPTIONAL MATCH (p)-[:ENABLES_CAPABILITY]->(c:Capability {tenant_id: $tenant_id})
        WITH p, count(DISTINCT f) AS features, count(DISTINCT c) AS capabilities
        RETURN count(p) AS total_products,
               sum(features) AS total_features,
               sum(capabilities) AS total_capabilities,
               collect(DISTINCT p.category) AS categories,
               avg(features) AS avg_features_per_product,
               avg(capabilities) AS avg_capabilities_per_product
        """
        self._validate_query_scope(query)
        async with self._driver.session() as session:
            result = await self._run_cypher(session, query, {"tenant_id": tenant_id})
            record = await result.single()
            if not record:
                return ProductService_get_portfolio_summaryResult.model_validate({
                    "total_products": 0,
                    "total_features": 0,
                    "total_capabilities": 0,
                    "categories": [],
                })


            return ProductService_get_portfolio_summaryResult.model_validate({
                "total_products": record["total_products"],
                "total_features": record["total_features"],
                "total_capabilities": record["total_capabilities"],
                "categories": [c for c in record["categories"] if c],
                "avg_features_per_product": round(record["avg_features_per_product"] or 0, 1),
                "avg_capabilities_per_product": round(record["avg_capabilities_per_product"] or 0, 1),
            })


    async def get_capability_coverage(self, tenant_id: str) -> list[dict[str, Any]]:
        """Show which capabilities are covered by products and which are gaps."""
        query = """
        MATCH (c:Capability {tenant_id: $tenant_id})
        OPTIONAL MATCH (p:Product {tenant_id: $tenant_id})-[ec:ENABLES_CAPABILITY]->(c)
        OPTIONAL MATCH (ps:PainSignal {tenant_id: $tenant_id})-[:INDICATES_NEED_FOR]->(c)
        RETURN c {.id, .name} AS capability,
               collect(DISTINCT p {.id, .name}) AS products,
               count(DISTINCT ps) AS signal_demand,
               CASE WHEN count(p) > 0 THEN 'covered' ELSE 'gap' END AS status
        ORDER BY signal_demand DESC
        """
        self._validate_query_scope(query)
        async with self._driver.session() as session:
            result = await self._run_cypher(session, query, {"tenant_id": tenant_id})
            records = [record async for record in result]
            return [
                {
                    "capability": record["capability"],
                    "products": record["products"],
                    "signal_demand": record["signal_demand"],
                    "status": record["status"],
                }
                for record in records
            ]
