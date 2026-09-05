"""V1-TENANCY-012 hostile tests: query_graph Cypher tenant-filter bypass.

Adversarial model: the ``cypher_query`` string is attacker-controlled (it can
originate from indirect prompt injection inside a retrieved document or from a
hostile end user). The tool MUST scope every returned node to the authenticated
tenant and fail closed on anything it cannot scope.

Defects covered (RED):
  D1  OR-bypass: injected ``a.tenant_id = $tenant_id AND <orig>`` lets a
      top-level ``OR`` in the original predicate escape the tenant filter.
  D2  UNION: a second, unfiltered query leg returns cross-tenant rows.
  D3  Multi-alias patterns: only the first node alias was filtered, so
      ``MATCH (a)-->(b) RETURN b`` leaks tenant-B neighbours.
  D4  Statement chaining / multi-MATCH re-binding fails open.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from layer4_agents.models.tool_schemas import QueryGraphInput
from layer4_agents.tools.knowledge_tools import QueryGraphTool

TENANT_A_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
NEO4J_CONFIG = {"neo4j_uri": "bolt://localhost:7687", "neo4j_password": "password"}


@pytest.fixture
def captured_query():
    """Run the tool with a mocked driver and capture the executed Cypher."""

    async def _run(cypher: str) -> tuple[str, object]:
        session = AsyncMock()
        result = AsyncMock()
        result.data = AsyncMock(return_value=[])
        session.run = AsyncMock(return_value=result)
        session.__aenter__.return_value = session
        session.__aexit__.return_value = False
        driver = MagicMock()
        driver.session = MagicMock(return_value=session)

        tool = QueryGraphTool(config=NEO4J_CONFIG)
        tool._driver = driver

        ctx = MagicMock()
        ctx.tenant_id = TENANT_A_ID
        ctx.user_id = "user-1"
        ctx.roles = ["analyst"]
        ctx.source = "jwt"
        ctx.assert_valid = MagicMock()

        with patch(
            "layer4_agents.shared.domain.context.get_current_tenant_context",
            return_value=ctx,
        ):
            output = await tool.execute(
                QueryGraphInput(cypher_query=cypher, parameters={})
            )
        executed = (
            session.run.await_args.args[0] if session.run.await_count else None
        )
        return executed, output

    return _run


@pytest.mark.asyncio
async def test_d1_or_bypass_in_where_predicate_is_neutralised(captured_query):
    """Hostile OR in the original predicate must not escape the tenant filter."""
    executed, output = await captured_query(
        "MATCH (n:Account) WHERE n.name = 'x' OR n.tenant_id = '"
        + str(TENANT_A_ID).replace("a", "b")
        + "' RETURN n"
    )
    assert output.error is None
    assert executed is not None
    # The injected tenant predicate must bind tighter than the hostile OR:
    # the original predicate must be parenthesised.
    assert "n.tenant_id = $tenant_id AND (" in executed, (
        f"tenant filter can be bypassed by top-level OR: {executed}"
    )


@pytest.mark.asyncio
async def test_d2_union_leg_is_rejected(captured_query):
    """UNION legs bypass the single-point filter injection; reject them."""
    executed, output = await captured_query(
        "MATCH (n:Account) RETURN n UNION MATCH (b:Account) RETURN b"
    )
    assert executed is None, "UNION query reached the driver unscoped"
    assert output.error is not None
    assert output.row_count == 0


@pytest.mark.asyncio
async def test_d3_all_node_aliases_are_tenant_filtered(captured_query):
    """Every node alias in the pattern must carry a tenant predicate."""
    executed, output = await captured_query(
        "MATCH (a:Account)-[:ENABLES]->(b:UseCase) RETURN b"
    )
    assert output.error is None
    assert executed is not None
    assert "a.tenant_id = $tenant_id" in executed
    assert "b.tenant_id = $tenant_id" in executed, (
        f"second alias unfiltered (cross-tenant neighbour leak): {executed}"
    )


@pytest.mark.asyncio
async def test_d4_statement_chaining_is_rejected(captured_query):
    executed, output = await captured_query(
        "MATCH (n:Account) RETURN n; MATCH (b:Account) RETURN b"
    )
    assert executed is None, "chained statement reached the driver"
    assert output.error is not None


@pytest.mark.asyncio
async def test_d4_second_match_rebinding_fails_closed(captured_query):
    """A second MATCH binding a fresh alias cannot be safely scoped -> reject."""
    executed, output = await captured_query(
        "MATCH (a:Account) WITH a MATCH (b:Account) RETURN b"
    )
    assert executed is None, (
        "second MATCH introduced an unscoped alias and still executed"
    )
    assert output.error is not None


@pytest.mark.asyncio
async def test_legit_single_alias_query_still_scoped(captured_query):
    """Regression guard: plain queries keep working with the tenant filter."""
    executed, output = await captured_query(
        "MATCH (n:Account) WHERE n.name = $name RETURN n LIMIT 10"
    )
    assert output.error is None
    assert "n.tenant_id = $tenant_id AND (" in executed


# ---------------------------------------------------------------------------
# Revision 1 — F1/F2: string-literal / comment awareness (independent review)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f1_clause_keyword_inside_string_literal_not_used_for_injection(
    captured_query,
):
    """'RETURN' inside a string literal must not be treated as a clause."""
    executed, output = await captured_query(
        "MATCH (n {name: 'RETURN'}) RETURN n"
    )
    assert output.error is None
    assert executed is not None
    # Filter must be injected OUTSIDE the literal, before the real RETURN.
    assert "WHERE n.tenant_id = $tenant_id RETURN n" in executed, executed
    # The literal itself must survive intact.
    assert "'RETURN'" in executed


@pytest.mark.asyncio
async def test_f2_literal_clause_keyword_cannot_truncate_predicate(captured_query):
    """'WITH' inside a literal must not end the predicate scan early."""
    executed, output = await captured_query(
        "MATCH (n) WHERE (n.x = 'WITH') OR true RETURN n"
    )
    # Balanced-parens variant: original predicate must be wrapped whole, so
    # the injected tenant predicate ANDs with the entire OR expression.
    assert output.error is None
    assert executed is not None
    assert "n.tenant_id = $tenant_id AND (" in executed
    assert "OR true )" in executed, executed


@pytest.mark.asyncio
async def test_f2_unbalanced_parens_via_literal_fail_closed(captured_query):
    """Predicate whose parens only balance via literal content is rejected."""
    executed, output = await captured_query(
        "MATCH (n) WHERE (n.x = 'WITH')) OR true RETURN n"
    )
    assert executed is None, "unbalanced hostile predicate reached the driver"
    assert output.error is not None


@pytest.mark.asyncio
async def test_union_keyword_inside_string_literal_is_allowed(captured_query):
    """False-positive guard: 'UNION' inside a literal is not a query leg."""
    executed, output = await captured_query(
        "MATCH (n) WHERE n.name = 'UNION' RETURN n"
    )
    assert output.error is None, f"legit literal rejected: {output.error}"
    assert "n.tenant_id = $tenant_id AND (" in executed


@pytest.mark.asyncio
async def test_write_keyword_inside_string_literal_is_allowed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.name = 'DELETE' RETURN n"
    )
    assert output.error is None, f"legit literal rejected: {output.error}"


@pytest.mark.asyncio
async def test_escaped_quote_inside_literal(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.name = 'it\\'s' RETURN n"
    )
    assert output.error is None, f"escaped-quote literal rejected: {output.error}"
    assert "n.tenant_id = $tenant_id AND (" in executed


@pytest.mark.asyncio
async def test_doubled_quote_inside_literal(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.name = 'it''s' RETURN n"
    )
    assert output.error is None, f"doubled-quote literal rejected: {output.error}"


@pytest.mark.asyncio
async def test_semicolon_inside_string_literal_is_allowed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.name = 'a;b' RETURN n"
    )
    assert output.error is None, f"literal semicolon rejected: {output.error}"


@pytest.mark.asyncio
async def test_backtick_identifier_containing_clause_keyword(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.`WHERE x` = 1 RETURN n"
    )
    assert output.error is None, f"backtick identifier rejected: {output.error}"
    assert "n.tenant_id = $tenant_id AND (" in executed


@pytest.mark.asyncio
async def test_line_comment_containing_clause_keyword(captured_query):
    executed, output = await captured_query(
        "MATCH (n) // RETURN everything\nRETURN n"
    )
    assert output.error is None, f"comment broke query: {output.error}"
    assert "WHERE n.tenant_id = $tenant_id RETURN n" in executed, executed


@pytest.mark.asyncio
async def test_block_comment_containing_clause_keyword(captured_query):
    executed, output = await captured_query(
        "MATCH (n) /* UNION MATCH (x) */ RETURN n"
    )
    assert output.error is None, f"block comment broke query: {output.error}"
    assert "WHERE n.tenant_id = $tenant_id RETURN n" in executed, executed


# ---------------------------------------------------------------------------
# Revision 2 — F4: pattern comprehensions / subqueries bypass the filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f4_pattern_comprehension_poc_fails_closed(captured_query):
    """Exact reviewer PoC: m inside the comprehension is unscoped."""
    executed, output = await captured_query(
        "MATCH (n) RETURN [(n)-->(m) | m.name] AS leaked LIMIT 25"
    )
    assert executed is None, "pattern comprehension reached the driver"
    assert output.error is not None
    assert output.row_count == 0


@pytest.mark.asyncio
async def test_f4_multi_hop_pattern_comprehension_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) RETURN [(n)-[*1..3]->(m) | m.name] AS leaked"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f4_path_comprehension_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) RETURN [p = (n)-->(m) | p] AS leaked"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f4_exists_function_subquery_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE exists((n)-->(m)) RETURN n"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f4_exists_block_subquery_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE EXISTS { (n)-->(m) } RETURN n"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f4_count_block_subquery_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) RETURN COUNT { (n)-->(m) } AS c"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f4_list_literal_still_allowed(captured_query):
    """False-positive guard: a plain list literal is not a comprehension."""
    executed, output = await captured_query(
        "MATCH (n) RETURN [1, 2, 3] AS xs LIMIT 1"
    )
    assert output.error is None, f"list literal rejected: {output.error}"
    assert "WHERE n.tenant_id = $tenant_id RETURN" in executed


@pytest.mark.asyncio
async def test_f4_bracket_pattern_inside_string_literal_still_allowed(
    captured_query,
):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.name = '[(a)-->(b) | b.name]' RETURN n"
    )
    assert output.error is None, f"literal rejected: {output.error}"
    assert "n.tenant_id = $tenant_id AND (" in executed


@pytest.mark.asyncio
async def test_f4_map_projection_still_allowed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) RETURN n { .name, .id } AS proj LIMIT 1"
    )
    assert output.error is None, f"map projection rejected: {output.error}"
    assert "WHERE n.tenant_id = $tenant_id RETURN" in executed


@pytest.mark.asyncio
async def test_f4_count_aggregation_still_allowed(captured_query):
    """Plain count(...) aggregation is not a COUNT{} subquery."""
    executed, output = await captured_query(
        "MATCH (n) RETURN count(n) AS c"
    )
    assert output.error is None, f"count() rejected: {output.error}"


# ---------------------------------------------------------------------------
# Revision 3 — F5: anonymous nodes / node-endpoint functions escape the filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f5_anonymous_endpoint_poc_fails_closed(captured_query):
    """Exact reviewer PoC: anonymous () endpoint + endNode(r) leaks."""
    executed, output = await captured_query(
        "MATCH (n)-[r]->() RETURN endNode(r).name AS leaked LIMIT 50"
    )
    assert executed is None, "anonymous-node query reached the driver"
    assert output.error is not None
    assert output.row_count == 0


@pytest.mark.asyncio
async def test_f5_startnode_variant_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH (n)<-[r]-() RETURN startNode(r).name AS leaked"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f5_anonymous_node_on_left_fails_closed(captured_query):
    executed, output = await captured_query("MATCH ()<--(n) RETURN n")
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f5_anonymous_node_second_pattern_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH (n), () RETURN n"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f5_endnode_without_anonymous_node_fails_closed(captured_query):
    """endNode(/startNode( are rejected even when every node is aliased."""
    executed, output = await captured_query(
        "MATCH (n)-[r]->(m) RETURN endNode(r).name AS leaked"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f5_anonymous_relationship_allowed_endpoints_filtered(
    captured_query,
):
    """Anonymous rels expose no properties; aliased endpoints stay filtered."""
    executed, output = await captured_query(
        "MATCH (n)-[]->(m) RETURN m"
    )
    assert output.error is None, f"anonymous rel rejected: {output.error}"
    assert "n.tenant_id = $tenant_id" in executed
    assert "m.tenant_id = $tenant_id" in executed


@pytest.mark.asyncio
async def test_f5_function_call_parens_not_flagged(captured_query):
    """False-positive guard: count(n)/toLower(...) parens are not nodes."""
    executed, output = await captured_query(
        "MATCH (n) WHERE toLower(n.name) = 'x' RETURN count(n) AS c"
    )
    assert output.error is None, f"function call rejected: {output.error}"
    assert "n.tenant_id = $tenant_id AND (" in executed


@pytest.mark.asyncio
async def test_f5_anonymous_pattern_inside_string_literal_allowed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.name = '()-[]->() endNode(' RETURN n"
    )
    assert output.error is None, f"literal rejected: {output.error}"


# ---------------------------------------------------------------------------
# Revision 4 — F6: variable-length paths expose unfiltered intermediate nodes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f6_variable_length_path_poc_fails_closed(captured_query):
    """Exact reviewer PoC: intermediate nodes on p are other tenants'."""
    executed, output = await captured_query(
        "MATCH p = (n)-[*1..3]->(m) RETURN [x IN nodes(p) | x.name] AS leaked LIMIT 25"
    )
    assert executed is None, "variable-length path reached the driver"
    assert output.error is not None
    assert output.row_count == 0


@pytest.mark.asyncio
async def test_f6_fixed_hop_varlength_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH (n)-[*2]->(m) RETURN m"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f6_open_ended_varlength_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH (n)-[*1..]->(m) RETURN m"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f6_relationships_of_path_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH p = (n)-->(m) RETURN relationships(p) AS rs"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f6_nodes_function_fails_closed(captured_query):
    executed, output = await captured_query(
        "MATCH p = (n)-->(m) RETURN nodes(p) AS ns"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f6_path_variable_single_hop_fails_closed(captured_query):
    """Named paths let relationships(p) reach edge properties; reject them."""
    executed, output = await captured_query(
        "MATCH p = (n)-->(m) RETURN p"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f6_varlength_inside_string_literal_allowed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.name = '[*1..3] p = (a)' RETURN n"
    )
    assert output.error is None, f"literal rejected: {output.error}"
    assert "n.tenant_id = $tenant_id AND (" in executed


@pytest.mark.asyncio
async def test_f6_list_comprehension_still_allowed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) RETURN [x IN [1, 2] | x * 2] AS ys LIMIT 1"
    )
    assert output.error is None, f"list comprehension rejected: {output.error}"


@pytest.mark.asyncio
async def test_f6_multiplication_expression_still_allowed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.score * 2 > 10 RETURN n"
    )
    assert output.error is None, f"multiplication rejected: {output.error}"


@pytest.mark.asyncio
async def test_f6_single_hop_aliased_relationship_still_allowed(captured_query):
    """Accepted-risk surface: fully aliased single-hop edge."""
    executed, output = await captured_query(
        "MATCH (n)-[r:ENABLES]->(m) RETURN m.name, r.confidence"
    )
    assert output.error is None, f"single-hop rejected: {output.error}"
    assert "n.tenant_id = $tenant_id" in executed
    assert "m.tenant_id = $tenant_id" in executed


# ---------------------------------------------------------------------------
# Revision 5 — F7: named/typed variable-length relationships bypass rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f7_named_varlength_rel_fails_closed(captured_query):
    """PoC 1: named var-length rel -[r*1..2]-> slips past the '[*' regex."""
    executed, output = await captured_query(
        "MATCH (n)-[r*1..2]->(m) RETURN m"
    )
    assert executed is None, "named var-length rel reached the driver"
    assert output.error is not None
    assert output.row_count == 0


@pytest.mark.asyncio
async def test_f7_typed_named_varlength_rel_fails_closed(captured_query):
    """PoC 2: r is a LIST of rels; x.secret projects cross-tenant edges."""
    executed, output = await captured_query(
        "MATCH (n)-[r:KNOWS*1..3]->(m) RETURN [x IN r | x.secret] AS leaked"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f7_typed_anonymous_varlength_fails_closed(captured_query):
    """PoC 3: typed anonymous fixed-hop var-length."""
    executed, output = await captured_query(
        "MATCH (n)-[:KNOWS*2]->(m) RETURN m"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f7_spaced_named_varlength_fails_closed(captured_query):
    """PoC 4: whitespace inside the bracket -[r *2..]-> must not help."""
    executed, output = await captured_query(
        "MATCH (n)-[r *2..]->(m) RETURN size(r)"
    )
    assert executed is None
    assert output.error is not None


@pytest.mark.asyncio
async def test_f7_multiplication_guard(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.score * 2 > 10 RETURN n"
    )
    assert output.error is None, f"multiplication rejected: {output.error}"


@pytest.mark.asyncio
async def test_f7_star_inside_string_literal_allowed(captured_query):
    executed, output = await captured_query(
        "MATCH (n) WHERE n.name = '[r*1..2]' RETURN n"
    )
    assert output.error is None, f"literal rejected: {output.error}"


@pytest.mark.asyncio
async def test_f7_map_projection_all_props_allowed(captured_query):
    """Cypher map projection n { .* } uses braces, not brackets: allowed."""
    executed, output = await captured_query(
        "MATCH (n) RETURN n { .* } AS proj LIMIT 1"
    )
    assert output.error is None, f"map projection rejected: {output.error}"


@pytest.mark.asyncio
async def test_f7_star_inside_list_literal_fails_closed_documented(captured_query):
    """Documented collateral: a '*' inside ANY bracket is rejected.

    List literals containing multiplication (e.g. [n.score * 2]) are
    indistinguishable from var-length rel brackets without a full parser, so
    they fail closed too. This is an accepted, documented posture.
    """
    executed, output = await captured_query(
        "MATCH (n) RETURN [n.score * 2] AS x LIMIT 1"
    )
    assert executed is None
    assert output.error is not None
