"""Cypher query validator for tenant isolation enforcement.

Scans Cypher queries to detect unscoped reads that could lead to
cross-tenant data leakage. Enforces mandatory tenant_id filtering
on all MATCH clauses that access entity nodes.

Security Model:
- All MATCH (n:Entity) clauses must include {tenant_id: ...} predicate
- Queries without explicit tenant scoping are rejected
- Composite constraints on (id, tenant_id) provide defense-in-depth

Usage:
    >>> from security.query_validator import QueryValidator, ValidationError
    >>> 
    >>> validator = QueryValidator()
    >>> 
    >>> # Valid query - has tenant_id predicate
    >>> validator.validate('MATCH (e:Entity {id: $id, tenant_id: $tenant_id}) RETURN e')
    []
    
    >>> # Invalid query - missing tenant_id
    >>> try:
    ...     validator.validate('MATCH (e:Entity {id: $id}) RETURN e')
    ... except UnscopedQueryError:
    ...     print("Query rejected - missing tenant_id")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal, TypedDict


class ValidationFindingPayload(TypedDict):
    severity: Literal["error", "warning", "info"]
    message: str
    line_number: int | None
    pattern: str | None
    suggestion: str | None

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Base exception for query validation errors."""
    pass


class UnscopedQueryError(ValidationError):
    """Raised when a query lacks mandatory tenant_id filtering."""
    pass


class UnsafePatternError(ValidationError):
    """Raised when a query contains unsafe patterns (e.g., DETACH DELETE without tenant)."""
    pass


class ValidationSeverity(str, Enum):
    """Severity levels for validation findings."""
    ERROR = "error"      # Blocks query execution
    WARNING = "warning"    # Logs but allows execution
    INFO = "info"          # Informational only


class QueryRisk(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass
class ValidationFinding:
    """A single validation finding.
    
    Attributes:
        severity: ERROR, WARNING, or INFO
        message: Human-readable description
        line_number: Line where issue was found (if known)
        pattern: The problematic pattern detected
        suggestion: Recommended fix
    """
    severity: ValidationSeverity
    message: str
    line_number: int | None = None
    pattern: str | None = None
    suggestion: str | None = None
    
    def to_dict(self) -> ValidationFindingPayload:
        """Convert finding to dictionary."""
        return ValidationFindingPayload(
            severity=self.severity.value,
            message=self.message,
            line_number=self.line_number,
            pattern=self.pattern,
            suggestion=self.suggestion,
        )


class QueryValidator:
    """Validate Cypher queries for tenant isolation compliance.
    
    Scans queries for:
    1. Unscoped Entity MATCH clauses (missing tenant_id)
    2. Unsafe patterns (DELETE without tenant filter)
    3. Required patterns (tenant_id in all entity predicates)
    
    Example:
        >>> validator = QueryValidator()
        >>> 
        >>> # This query is safe - has tenant_id
        >>> validator.validate('MATCH (e:Entity {id: $id, tenant_id: $tenant_id}) RETURN e')
        []
        
        >>> # This query is unsafe - missing tenant_id
        >>> try:
        ...     validator.validate('MATCH (e:Entity {id: $id}) RETURN e')
        ... except UnscopedQueryError:
        ...     print("Query rejected - missing tenant_id")
    """
    
    # Pattern to match MATCH clauses for domain nodes
    # Captures: MATCH (e:NodeType ...) -> groups: (node_var, node_type, properties)
    _ENTITY_MATCH_PATTERN = re.compile(
        r'MATCH\s*\(\s*(\w+)\s*:\s*(Entity|UseCase|ValueDriver|Capability|Persona|Formula|Outcome|PROVEntity|DecisionTrace|DecisionStep)\s*(?:\{([^}]*)\})?\s*\)',
        re.IGNORECASE | re.DOTALL
    )
    
    # Pattern to find tenant_id in property map
    _TENANT_ID_PATTERN = re.compile(
        r'tenant_id\s*:\s*(\$tenant_id|"[^"]*"|\'[^\']*\')',
        re.IGNORECASE
    )
    
    # Pattern to detect DETACH DELETE
    _DETACH_DELETE_PATTERN = re.compile(
        r'DETACH\s+DELETE',
        re.IGNORECASE
    )
    
    # Pattern to detect unscoped MATCH with WHERE
    _UNSCOPED_WHERE_PATTERN = re.compile(
        r'MATCH\s*\(\s*\w+\s*:\s*(?:Entity|UseCase|ValueDriver|Capability|Persona|Formula|Outcome|PROVEntity|DecisionTrace|DecisionStep)\s*\)\s*WHERE',
        re.IGNORECASE
    )

    _DOMAIN_LABEL_PATTERN = r"(Entity|UseCase|ValueDriver|Capability|Persona|Formula|Outcome|PROVEntity|DecisionTrace|DecisionStep)"
    _NODE_TOKEN_PATTERN = re.compile(r"\(\s*(\w+)\s*:\s*" + _DOMAIN_LABEL_PATTERN + r"(?:\s*:[^)]+)?\s*(?:\{([^}]*)\})?\s*\)", re.IGNORECASE | re.DOTALL)
    _WHERE_TENANT_PATTERN = re.compile(r"\b(\w+)\.tenant_id\s*=\s*(?:\$tenant_id|\"[^\"]*\"|'[^']*')", re.IGNORECASE)
    _ADMIN_PATTERN = re.compile(r"\b(CREATE|DROP)\s+(CONSTRAINT|INDEX|DATABASE|USER|ROLE)\b|\bCALL\s+db\.", re.IGNORECASE)
    _WRITE_PATTERN = re.compile(r"\b(CREATE|MERGE|SET|DELETE|DETACH\s+DELETE|REMOVE)\b", re.IGNORECASE)
    
    def __init__(self, fail_closed: bool = True):
        """Initialize validator.
        
        Args:
            fail_closed: If True (default), unscoped queries raise exceptions.
                        If False, log warnings but don't block.
        """
        self.fail_closed = fail_closed
        self._findings: list[ValidationFinding] = []
    
    def validate(self, query: str, query_name: str | None = None) -> list[ValidationFinding]:
        """Validate a Cypher query for tenant isolation.
        
        Args:
            query: Cypher query string
            query_name: Optional name for error messages (e.g., "get_entity_by_id")
            
        Returns:
            List of validation findings (empty if query is valid)
            
        Raises:
            UnscopedQueryError: If query has unscoped Entity MATCH and fail_closed=True
            UnsafePatternError: If query has unsafe patterns and fail_closed=True
        """
        self._findings = []
        name = query_name or "query"
        
        # Check 1: All Entity MATCH clauses must have tenant_id
        self._check_entity_tenant_scoping(query, name)
        
        # Check 2: DETACH DELETE must have tenant verification
        self._check_delete_safety(query, name)
        
        # Check 3: Unscoped WHERE patterns
        self._check_where_clause_scoping(query, name)
        
        # If fail_closed and we have errors, raise
        if self.fail_closed:
            errors = [f for f in self._findings if f.severity == ValidationSeverity.ERROR]
            if errors:
                raise UnscopedQueryError(
                    f"Query '{name}' failed tenant isolation validation: " +
                    "; ".join(e.message for e in errors)
                )
        
        return self._findings

    @classmethod
    def classify_risk(cls, query: str) -> QueryRisk:
        if cls._ADMIN_PATTERN.search(query):
            return QueryRisk.ADMIN
        if cls._WRITE_PATTERN.search(query):
            return QueryRisk.WRITE
        return QueryRisk.READ

    def validate_structural_tenant_scope(self, query: str, query_name: str | None = None) -> list[ValidationFinding]:
        """AST-like structural validation supporting multiline/aliases/subqueries.

        This is intentionally parser-like (token + clause analysis) so we can
        handle aliased variables and nested CALL blocks during migration.
        """
        findings: list[ValidationFinding] = []
        where_scoped_aliases = {
            m.group(1).lower()
            for m in self._WHERE_TENANT_PATTERN.finditer(query)
        }
        for match in self._NODE_TOKEN_PATTERN.finditer(query):
            alias = match.group(1)
            props = match.group(3) or ""
            has_tenant_in_props = bool(self._TENANT_ID_PATTERN.search(props))
            has_tenant_in_where = alias.lower() in where_scoped_aliases
            if not has_tenant_in_props and not has_tenant_in_where:
                findings.append(
                    ValidationFinding(
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Domain node alias '{alias}' is not tenant-scoped in "
                            "properties or WHERE predicate"
                        ),
                        line_number=self._estimate_line(query, alias),
                        pattern=match.group(0),
                        suggestion=f"Add {{tenant_id: $tenant_id}} or WHERE {alias}.tenant_id = $tenant_id",
                    )
                )
        if self.fail_closed and any(f.severity == ValidationSeverity.ERROR for f in findings):
            name = query_name or "query"
            raise UnscopedQueryError(
                f"Query '{name}' failed structural tenant validation: "
                + "; ".join(f.message for f in findings if f.severity == ValidationSeverity.ERROR)
            )
        return findings
    
    def _check_entity_tenant_scoping(self, query: str, query_name: str) -> None:
        """Check that all domain MATCH clauses include tenant_id.
        
        Args:
            query: Cypher query
            query_name: Query identifier for messages
        """
        matches = self._ENTITY_MATCH_PATTERN.findall(query)
        
        # Collect aliases that have tenant_id scoped in a WHERE clause
        where_scoped_aliases = {
            m.group(1).lower()
            for m in self._WHERE_TENANT_PATTERN.finditer(query)
        }
        
        for node_var, node_type, properties in matches:
            # Check if the alias is tenant-scoped via WHERE
            if node_var.lower() in where_scoped_aliases:
                continue
            
            # Check if properties include tenant_id
            if not properties:
                # No properties at all - definitely unscoped
                self._findings.append(ValidationFinding(
                    severity=ValidationSeverity.ERROR,
                    message=f"Domain MATCH (line ~{self._estimate_line(query, 'MATCH')}): "
                           f"Missing property map - must include {{tenant_id: $tenant_id}}",
                    line_number=self._estimate_line(query, 'MATCH'),
                    pattern=f"MATCH ({node_var}:{node_type})",
                    suggestion=f"Change to: MATCH ({node_var}:{node_type} {{id: $id, tenant_id: $tenant_id}})"
                ))
            elif not self._TENANT_ID_PATTERN.search(properties):
                # Has properties but no tenant_id
                self._findings.append(ValidationFinding(
                    severity=ValidationSeverity.ERROR,
                    message=f"Domain MATCH (line ~{self._estimate_line(query, 'MATCH')}): "
                           f"Missing tenant_id in property map",
                    line_number=self._estimate_line(query, 'MATCH'),
                    pattern=f"MATCH ({node_var}:{node_type} {{{properties}}})",
                    suggestion=f"Add tenant_id: {node_var}:{node_type} {{{properties}, tenant_id: $tenant_id}}"
                ))
    
    def _check_delete_safety(self, query: str, query_name: str) -> None:
        """Check that DELETE operations have tenant verification.
        
        Args:
            query: Cypher query
            query_name: Query identifier for messages
        """
        # Look for DETACH DELETE
        if self._DETACH_DELETE_PATTERN.search(query):
            # Check if the query has a preceding MATCH with tenant_id
            # This is a simplified check - production should parse the AST
            if 'tenant_id' not in query.lower():
                self._findings.append(ValidationFinding(
                    severity=ValidationSeverity.ERROR,
                    message="DETACH DELETE without tenant_id filtering detected",
                    line_number=self._estimate_line(query, 'DETACH DELETE'),
                    pattern="DETACH DELETE",
                    suggestion="Add MATCH with {tenant_id: $tenant_id} before DELETE"
                ))
    
    def _check_where_clause_scoping(self, query: str, query_name: str) -> None:
        """Check WHERE clauses for tenant scoping.
        
        Args:
            query: Cypher query
            query_name: Query identifier for messages
        """
        # Pattern: MATCH (n:Entity) WHERE ... without tenant in initial match
        unscoped_where = self._UNSCOPED_WHERE_PATTERN.search(query)
        if unscoped_where:
            # Check if WHERE clause includes tenant_id
            where_start = unscoped_where.end()
            # Find next clause (RETURN, WITH, etc.)
            next_clause_match = re.search(
                r'\s+(RETURN|WITH|MATCH|CREATE|DELETE|SET|REMOVE)\s+',
                query[where_start:],
                re.IGNORECASE
            )
            if next_clause_match:
                where_clause = query[where_start:where_start + next_clause_match.start()]
            else:
                where_clause = query[where_start:]
            
            if 'tenant_id' not in where_clause.lower():
                self._findings.append(ValidationFinding(
                    severity=ValidationSeverity.WARNING,
                    message="WHERE clause may be missing tenant_id filter",
                    line_number=self._estimate_line(query, 'WHERE'),
                    pattern="MATCH (n:NodeType) WHERE ...",
                    suggestion="Add AND n.tenant_id = $tenant_id to WHERE clause"
                ))
    
    def _estimate_line(self, query: str, pattern: str) -> int | None:
        """Estimate line number for a pattern in query.
        
        Args:
            query: Full query string
            pattern: Pattern to find
            
        Returns:
            Estimated line number or None
        """
        try:
            idx = query.upper().index(pattern.upper())
            return query[:idx].count('\n') + 1
        except ValueError:
            return None
    
    def is_valid(self, query: str) -> bool:
        """Quick check if query passes validation.
        
        Args:
            query: Cypher query
            
        Returns:
            True if no errors found
        """
        try:
            findings = self.validate(query)
            errors = [f for f in findings if f.severity == ValidationSeverity.ERROR]
            return len(errors) == 0
        except ValidationError:
            return False


class ValidatedNeo4jSession:
    """Neo4j session wrapper with query validation.
    
    Wraps a Neo4j session and validates all queries before execution,
    blocking unscoped reads that could leak cross-tenant data.
    
    Example:
        >>> from security.query_validator import ValidatedNeo4jSession
        >>> 
        >>> async with driver.session() as raw_session:
        ...     session = ValidatedNeo4jSession(raw_session, tenant_id="tenant-123")
        ...     
        ...     # This will execute - has tenant_id
        ...     result = await session.run(
        ...         "MATCH (e:Entity {id: $id, tenant_id: $tenant_id}) RETURN e",
        ...         id="abc", tenant_id="tenant-123"
        ...     )
        ...     
        ...     # This will raise UnscopedQueryError
        ...     result = await session.run(
        ...         "MATCH (e:Entity {id: $id}) RETURN e",  # Missing tenant_id!
        ...         id="abc"
        ...     )
    """
    
    def __init__(self, session, tenant_id: str | None, strict: bool = True):
        """Initialize validated session wrapper.
        
        Args:
            session: Underlying Neo4j async session
            tenant_id: Tenant ID for scoping (required for strict mode)
            strict: If True, reject all unscoped queries
        """
        self._session = session
        self._tenant_id = tenant_id
        self._strict = strict
        self._validator = QueryValidator(fail_closed=strict)
    
    async def run(self, query: str, parameters: dict | None = None, **kwargs) -> object:
        """Run query with validation.
        
        Args:
            query: Cypher query
            parameters: Query parameters
            **kwargs: Additional parameters
            
        Returns:
            Query result
            
        Raises:
            UnscopedQueryError: If query fails tenant isolation validation
        """
        # Validate query
        if self._strict:
            self._validator.validate(query, query_name="neo4j_session.run")
        
        # Inject tenant_id if not present
        params = parameters or {}
        params.update(kwargs)
        
        if self._tenant_id and 'tenant_id' not in params:
            params['tenant_id'] = self._tenant_id
        
        return await self._session.run(query, params)
    
    async def close(self) -> None:
        """Close underlying session."""
        await self._session.close()


def create_validated_session(
    driver,
    tenant_id: str,
    strict: bool = True
) -> ValidatedNeo4jSession:
    """Factory function to create a validated Neo4j session.
    
    Args:
        driver: Neo4j async driver
        tenant_id: Tenant ID for query scoping
        strict: If True, reject unscoped queries
        
    Returns:
        ValidatedNeo4jSession wrapper
    """
    raw_session = driver.session()
    return ValidatedNeo4jSession(raw_session, tenant_id, strict)
