from __future__ import annotations

"""Variable Registry Service implementation for Layer 4 Agents.

Neo4j-backed implementation of variable definitions and resolution.
"""


from datetime import UTC, datetime
from typing import Any

from neo4j import AsyncDriver

from ..interfaces.variable_registry import (
    IVariableRegistry,
    ResolutionContext,
    Variable,
    VariableDataType,
    VariableSearchCriteria,
    VariableSourceBinding,
    VariableSourceType,
    VariableValidationRule,
    VariableValue,
)


class Neo4jVariableRegistry(IVariableRegistry):
    """Neo4j-backed Variable Registry implementation."""

    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    async def register_variable(self, variable: Variable) -> Variable:
        """Register new variable definition in Neo4j."""
        now = datetime.now(UTC).isoformat()

        # Build source binding properties
        source_props = {}
        if variable.source_binding:
            source_props = {
                "sourceType": variable.source_binding.source_type.value,
                "sourceLocation": variable.source_binding.source_location,
                "extractionQuery": variable.source_binding.extraction_query,
                "transformation": variable.source_binding.transformation,
                "fallbackValue": variable.source_binding.fallback_value,
                "isRequired": variable.source_binding.is_required,
            }

        # Build validation rules
        validation_rules = []
        for rule in variable.validation_rules:
            validation_rules.append(
                {
                    "ruleType": rule.rule_type,
                    "parameters": rule.parameters,
                    "errorMessage": rule.error_message,
                }
            )

        query = """
        CREATE (v:Variable {
            id: $variable_id,
            name: $name,
            description: $description,
            dataType: $data_type,
            industry: $industry,
            applicableFormulas: $applicable_formulas,
            applicablePacks: $applicable_packs,
            validationRules: $validation_rules,
            createdAt: $created_at,
            version: $version,
            isActive: $is_active
        })
        SET v.sourceType = $source_type,
            v.sourceLocation = $source_location,
            v.extractionQuery = $extraction_query,
            v.transformation = $transformation,
            v.fallbackValue = $fallback_value,
            v.isRequired = $is_required
        RETURN v
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                variable_id=variable.variable_id,
                name=variable.name,
                description=variable.description,
                data_type=variable.data_type.value,
                industry=variable.industry,
                applicable_formulas=variable.applicable_formulas,
                applicable_packs=variable.applicable_packs,
                validation_rules=validation_rules,
                created_at=now,
                version=variable.version,
                is_active=variable.is_active,
                source_type=source_props.get("sourceType"),
                source_location=source_props.get("sourceLocation"),
                extraction_query=source_props.get("extractionQuery"),
                transformation=source_props.get("transformation"),
                fallback_value=source_props.get("fallbackValue"),
                is_required=source_props.get("isRequired", True),
            )
            record = await result.single()

            if not record:
                raise ValueError("Failed to register variable")

            v = record["v"]
            variable.created_at = datetime.fromisoformat(v["createdAt"])

            return variable

    async def get_variable(self, variable_id: str) -> Variable | None:
        """Retrieve variable definition from Neo4j."""
        query = """
        MATCH (v:Variable {id: $variable_id})
        RETURN v
        """

        async with self._driver.session() as session:
            result = await session.run(query, variable_id=variable_id)
            record = await result.single()

            if not record:
                return None

            v = record["v"]

            # Reconstruct source binding
            source_binding = None
            if v.get("sourceType"):
                source_binding = VariableSourceBinding(
                    source_type=VariableSourceType(v["sourceType"]),
                    source_location=v.get("sourceLocation", ""),
                    extraction_query=v.get("extractionQuery"),
                    transformation=v.get("transformation"),
                    fallback_value=v.get("fallbackValue"),
                    is_required=v.get("isRequired", True),
                )

            # Reconstruct validation rules with safe key access
            validation_rules = []
            for rule_data in v.get("validationRules", []):
                if not isinstance(rule_data, dict):
                    continue
                validation_rules.append(
                    VariableValidationRule(
                        rule_type=rule_data.get("ruleType", "unknown"),
                        parameters=rule_data.get("parameters", {}),
                        error_message=rule_data.get("errorMessage", "Validation failed"),
                    )
                )

            return Variable(
                variable_id=v["id"],
                name=v["name"],
                description=v.get("description", ""),
                data_type=VariableDataType(v["dataType"]),
                source_binding=source_binding,
                validation_rules=validation_rules,
                industry=v.get("industry"),
                applicable_formulas=v.get("applicableFormulas", []),
                applicable_packs=v.get("applicablePacks", []),
                created_at=datetime.fromisoformat(v["createdAt"])
                if "createdAt" in v
                else datetime.now(UTC),
                updated_at=datetime.fromisoformat(v["updatedAt"]) if "updatedAt" in v else None,
                version=v.get("version", "1.0.0"),
                is_active=v.get("isActive", True),
            )

    async def update_variable(
        self,
        variable_id: str,
        updates: dict[str, Any],
    ) -> Variable:
        """Update variable definition in Neo4j."""
        # Build dynamic update query
        set_clauses = ["v.updatedAt = $updated_at"]
        params = {
            "variable_id": variable_id,
            "updated_at": datetime.now(UTC).isoformat(),
        }

        allowed_fields = [
            "name",
            "description",
            "dataType",
            "industry",
            "applicableFormulas",
            "applicablePacks",
            "isActive",
        ]

        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"v.{field} = ${field}")
                params[field] = updates[field]

        # Handle source binding updates
        if "source_binding" in updates:
            sb = updates["source_binding"]
            set_clauses.extend(
                [
                    "v.sourceType = $source_type",
                    "v.sourceLocation = $source_location",
                ]
            )
            params["source_type"] = sb.source_type.value
            params["source_location"] = sb.source_location

        query = f"""
        MATCH (v:Variable {{id: $variable_id}})
        SET {", ".join(set_clauses)}
        RETURN v
        """

        async with self._driver.session() as session:
            result = await session.run(query, **params)
            record = await result.single()

            if not record:
                raise ValueError(f"Variable {variable_id} not found")

            # Return updated variable
            return await self.get_variable(variable_id)

    async def search_variables(
        self,
        criteria: VariableSearchCriteria,
    ) -> list[Variable]:
        """Search variables by context in Neo4j."""
        # Build dynamic query based on criteria
        where_clauses = []
        params = {}

        if criteria.industry:
            where_clauses.append("v.industry = $industry")
            params["industry"] = criteria.industry

        if criteria.pack_id:
            where_clauses.append("$pack_id IN v.applicablePacks")
            params["pack_id"] = criteria.pack_id

        if criteria.formula_id:
            where_clauses.append("$formula_id IN v.applicableFormulas")
            params["formula_id"] = criteria.formula_id

        if criteria.data_type:
            where_clauses.append("v.dataType = $data_type")
            params["data_type"] = criteria.data_type.value

        if criteria.source_type:
            where_clauses.append("v.sourceType = $source_type")
            params["source_type"] = criteria.source_type.value

        if criteria.is_active is not None:
            where_clauses.append("v.isActive = $is_active")
            params["is_active"] = criteria.is_active

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
        MATCH (v:Variable)
        WHERE {where_clause}
        RETURN v
        ORDER BY v.name
        """

        async with self._driver.session() as session:
            result = await session.run(query, **params)
            records = await result.data()

            variables = []
            for r in records:
                v = r["v"]

                source_binding = None
                if v.get("sourceType"):
                    source_binding = VariableSourceBinding(
                        source_type=VariableSourceType(v["sourceType"]),
                        source_location=v.get("sourceLocation", ""),
                        extraction_query=v.get("extractionQuery"),
                        transformation=v.get("transformation"),
                        fallback_value=v.get("fallbackValue"),
                        is_required=v.get("isRequired", True),
                    )

                variables.append(
                    Variable(
                        variable_id=v["id"],
                        name=v["name"],
                        description=v.get("description", ""),
                        data_type=VariableDataType(v["dataType"]),
                        source_binding=source_binding,
                        industry=v.get("industry"),
                        applicable_formulas=v.get("applicableFormulas", []),
                        applicable_packs=v.get("applicablePacks", []),
                        created_at=datetime.fromisoformat(v["createdAt"])
                        if "createdAt" in v
                        else datetime.now(UTC),
                        version=v.get("version", "1.0.0"),
                        is_active=v.get("isActive", True),
                    )
                )

            return variables

    async def resolve_variable(
        self,
        variable_id: str,
        context: ResolutionContext,
    ) -> VariableValue:
        """Resolve variable value from source."""
        # Get variable definition
        variable = await self.get_variable(variable_id)
        if not variable:
            raise ValueError(f"Variable {variable_id} not found")

        # Default value
        value = None
        source_type = VariableSourceType.USER_INPUT
        source_location = None

        if variable.source_binding:
            source_type = variable.source_binding.source_type
            source_location = variable.source_binding.source_location

            # Resolve from source integration or fail closed.
            # Never return synthetic placeholder strings.
            if source_type == VariableSourceType.USER_INPUT:
                # Look for value in context variables
                value = context.workspace_id
            elif source_type == VariableSourceType.CRM_FIELD:
                raise ValueError(
                    f"CRM integration not configured for variable {variable_id}. "
                    "Set CRM_API_URL and CRM_API_KEY."
                )
            elif source_type == VariableSourceType.BENCHMARK_LOOKUP:
                raise ValueError(
                    f"Benchmark integration not configured for variable {variable_id}. "
                    "Set BENCHMARK_API_URL and BENCHMARK_API_KEY."
                )
            elif source_type == VariableSourceType.FORMULA_CALCULATION:
                raise ValueError(
                    f"Formula calculation service not configured for variable {variable_id}. "
                    "Set FORMULA_SERVICE_URL."
                )
            elif source_type == VariableSourceType.GROUND_TRUTH:
                raise ValueError(
                    f"Ground-truth integration not configured for variable {variable_id}. "
                    "Set LAYER5_BASE_URL."
                )
            else:
                value = variable.source_binding.fallback_value

        # Cast to appropriate type
        typed_value = self._cast_value(value, variable.data_type)

        return VariableValue(
            variable_id=variable_id,
            value=typed_value,
            data_type=variable.data_type,
            source_type=source_type,
            source_location=source_location,
            workspace_id=context.workspace_id,
            entity_id=context.entity_id,
            confidence=1.0,
        )

    async def resolve_variables_batch(
        self,
        variable_ids: list[str],
        context: ResolutionContext,
    ) -> dict[str, VariableValue]:
        """Resolve multiple variables efficiently."""
        results = {}
        for var_id in variable_ids:
            try:
                results[var_id] = await self.resolve_variable(var_id, context)
            except Exception:
                # Log error but continue with other variables
                results[var_id] = VariableValue(
                    variable_id=var_id,
                    value=None,
                    data_type=VariableDataType.STRING,
                    source_type=VariableSourceType.USER_INPUT,
                    source_location=None,
                    workspace_id=context.workspace_id,
                    confidence=0.0,
                )
        return results

    async def validate_value(
        self,
        variable_id: str,
        value: Any,
    ) -> tuple[bool, str | None]:
        """Validate value against variable rules."""
        variable = await self.get_variable(variable_id)
        if not variable:
            return False, f"Variable {variable_id} not found"

        # Check data type
        try:
            self._cast_value(value, variable.data_type)
        except (ValueError, TypeError) as e:
            return False, "INVALID_DATA_TYPE_ERROR"

        # Run validation rules
        for rule in variable.validation_rules:
            is_valid, error = self._apply_rule(value, rule)
            if not is_valid:
                return False, error or f"Validation failed: {rule.rule_type}"

        return True, None

    def _cast_value(self, value: Any, data_type: VariableDataType) -> Any:
        """Cast value to appropriate data type."""
        if value is None:
            return None

        if data_type == VariableDataType.STRING:
            return str(value)
        elif data_type == VariableDataType.INTEGER:
            return int(value)
        elif data_type == VariableDataType.DECIMAL:
            from decimal import Decimal

            return Decimal(str(value))
        elif data_type == VariableDataType.BOOLEAN:
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        elif data_type == VariableDataType.DATE:
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            return value
        elif data_type == VariableDataType.ENUM:
            return str(value)
        elif data_type == VariableDataType.JSON:
            if isinstance(value, str):
                import json

                return json.loads(value)
            return value

        return value

    def _apply_rule(self, value: Any, rule: VariableValidationRule) -> tuple[bool, str | None]:
        """Apply a validation rule to a value."""
        params = rule.parameters

        if rule.rule_type == "range":
            if "min" in params and value < params["min"]:
                return False, rule.error_message
            if "max" in params and value > params["max"]:
                return False, rule.error_message

        elif rule.rule_type == "regex":
            import re

            pattern = params.get("pattern", ".*")
            # Ensure pattern has anchors for complete string matching
            anchored_pattern = pattern
            if not anchored_pattern.startswith('^'):
                anchored_pattern = '^' + anchored_pattern
            if not anchored_pattern.endswith('$'):
                anchored_pattern = anchored_pattern + '$'
            if not re.match(anchored_pattern, str(value)):
                return False, rule.error_message

        elif rule.rule_type == "enum":
            allowed = params.get("values", [])
            if value not in allowed:
                return False, rule.error_message

        return True, None
