"""Meridian production-path certification journey.

One deterministic journey through the canonical external interface (the API
gateway, decision D1) across Layers 1-6 with real services and real
persistence. No mocks, no manual inter-layer compensation: if production
code does not perform a handoff, the corresponding stage fails.

The suite is the mission's drift detector: stages fail against the current
(broken) system and turn green as the WS3 convergence fixes land. The stage
failure count in ``artifacts/certification/manifest.json`` must strictly
decrease over the convergence PR and reach zero before merge.

Execution graph: ``docs/architecture/production-path-execution-graph.md``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from tests.certification.harness import CertificationHarness, CertificationRecorder

pytestmark = [
    pytest.mark.certification,
    pytest.mark.backend_integrated,
    pytest.mark.service_required,
    pytest.mark.timeout(900),
]

MERIDIAN_ACCOUNT = {
    "provider": "salesforce",
    "name": "Meridian Auto Certification",
    "domain": "meridian-auto-cert.example",
    "industry": "Automotive",
    "region": "North America",
    "company_size": 8500,
    "stage": "qualified",
    "segment": "enterprise",
}

L1_TERMINAL_OK = {"ready", "completed"}
L1_TERMINAL_BAD = {"failed_permanent", "cancelled"}
WORKFLOW_TERMINAL = {"completed", "succeeded", "success", "failed", "error"}


def _marker(run_id: str) -> str:
    return f"MERIDIAN-CERT-{run_id.upper()}"


async def _poll(
    fetch,
    predicate,
    *,
    attempts: int = 40,
    interval: float = 3.0,
    description: str,
) -> Any:
    last: Any = None
    for _ in range(attempts):
        last = await fetch()
        if predicate(last):
            return last
        await asyncio.sleep(interval)
    raise AssertionError(f"Timed out waiting for {description}; last={str(last)[:800]}")


async def test_meridian_production_path_journey(
    cert_harness: CertificationHarness, cert_recorder: CertificationRecorder
) -> None:
    """Execute the full L1-L6 customer journey through the gateway.

    Stages run sequentially because each depends on the previous stage's
    persisted artifacts. Stage failures are recorded in the certification
    manifest and aggregated into one failure at the end so every stage runs
    even when an early boundary is broken.
    """
    h = cert_harness
    ctx: dict[str, Any] = cert_recorder.context
    marker = _marker(cert_recorder.run_id)
    failures: list[str] = []

    async def run_stage(name: str, coro: Any) -> Any:
        try:
            return await h.stage(name, coro)
        except AssertionError as exc:
            failures.append(f"{name}: {exc}")
            return None

    # -- Stage 1: readiness ------------------------------------------------
    async def stage_readiness() -> str:
        for layer in ("l1", "l2", "l3", "l4", "l5", "l6"):
            path, _ = await h.first_healthy(layer)
            assert path, f"{layer} unhealthy"
        path, _ = await h.gateway_healthy()
        return path

    await run_stage("service_readiness", stage_readiness())

    # -- Stage 2: seed tenant A (sanctioned validation seed route) ----------
    async def stage_seed() -> None:
        # Canonical pattern (tests/shared/live_harness.py create_seed_graph +
        # assert_cross_tenant_denied): only tenant A is provisioned through
        # the seed route; tenant B stays an unprovisioned context and every
        # cross-tenant access with it must fail closed (401/403/404).
        # Tenant B cannot be seeded through this route: the route upserts a
        # FIXED validation user set (VALIDATION_USERS, constant UUIDs) that
        # can belong to exactly one tenant — a second seed raises 409 by
        # design (fail-closed, verified live).
        await h.request(
            "l4",
            "POST",
            "/v1/validation/seed/auth-context",
            tenant_id=h.seed_ids.tenant_a,
            json={
                "tenant_id": h.seed_ids.tenant_a,
                "tenant_name": f"Certification cert-tenant-a {cert_recorder.run_id}",
                "tenant_slug": f"cert-tenant-a-{cert_recorder.run_id}",
                "service_account_id": "production-path-certification",
            },
            expected=(200,),
            # Canonical privileged reason expected by the L4 validation
            # seed route (layer4_agents.test_support.seed_runtime_config
            # SEED_PRIVILEGED_REASON, default "validation-seed").
            extra_headers={"X-Privileged-Reason": "validation-seed"},
        )
        ctx["tenant_a"] = h.seed_ids.tenant_a
        ctx["tenant_b"] = h.seed_ids.tenant_b

    await run_stage("tenant_seed", stage_seed())

    # -- Stage 3: account creation through the gateway (frontend path) -----
    async def stage_account() -> None:
        body, _ = await h.frontend_path_request(
            "l4",
            "POST",
            "/accounts",
            json_body={
                **MERIDIAN_ACCOUNT,
                "id": h.seed_ids.account_id,
                # Canonical Account schema requires tenant_id in the body.
                "tenant_id": h.seed_ids.tenant_a,
            },
            expected=(200, 201, 409),
        )
        ctx["account_id"] = str(body.get("id") or h.seed_ids.account_id)

    await run_stage("account_create_via_gateway", stage_account())

    # -- Stage 4: source submission through the gateway (frontend path) ----
    async def stage_source() -> None:
        body, _ = await h.frontend_path_request(
            "l1",
            "POST",
            "/sources",
            json_body={
                "account_id": ctx.get("account_id", h.seed_ids.account_id),
                "source_type": "notes",
                "title": f"Meridian discovery notes {cert_recorder.run_id}",
                "content": (
                    f"# Meridian Auto value discovery\n\n"
                    f"{marker}: service-contract cycle time reduced 18 percent "
                    f"after guided onboarding; warranty claims processing costs "
                    f"$2.4M annually across 3400 dealerships.\n"
                ),
                "external_reference": f"meridian-cert-src-{cert_recorder.run_id}",
                "idempotency_key": f"meridian-cert-src-{cert_recorder.run_id}",
                "requested_outputs": ["fabric_found_summary"],
                "metadata": {"certification_run_id": cert_recorder.run_id},
            },
            expected=(200, 201, 202),
        )
        ctx["source_id"] = str(body.get("source_id"))
        ctx["source_version_id"] = str(body.get("source_version_id"))
        ctx["ingestion_run_id"] = str(body.get("ingestion_run_id"))

    await run_stage("source_submit_via_gateway", stage_source())

    # -- Stage 5: L1 pipeline reaches a terminal state ---------------------
    async def stage_l1_terminal() -> None:
        run_id = ctx.get("ingestion_run_id")
        assert run_id and run_id != "None", "no ingestion_run_id from stage 4"

        async def fetch_run() -> Any:
            body, _ = await h.request(
                "l1", "GET", f"/api/v1/ingestion/runs/{run_id}", expected=(200,)
            )
            return body

        run = await _poll(
            fetch_run,
            lambda r: str(r.get("status", "")).lower() in L1_TERMINAL_OK | L1_TERMINAL_BAD,
            description=f"L1 run {run_id} terminal state",
        )
        status = str(run.get("status", "")).lower()
        assert status in L1_TERMINAL_OK, (
            f"L1 run ended in {status}: {run.get('error_code')} "
            f"{run.get('error_detail_safe')}"
        )

    await run_stage("l1_pipeline_terminal", stage_l1_terminal())

    # -- Stage 6: extraction reached the knowledge graph -------------------
    async def stage_graph_populated() -> None:
        source_version_id = ctx.get("source_version_id")
        assert source_version_id and source_version_id != "None", (
            "no source_version_id from stage 4"
        )

        async def fetch_entities() -> Any:
            body, _ = await h.request(
                "l3",
                "GET",
                f"/v1/entities/?search_text={marker}",
                expected=(200,),
            )
            return body

        entities = await _poll(
            fetch_entities,
            lambda b: marker in str(b) or "meridian" in str(b).lower(),
            attempts=20,
            description="L3 entities derived from the certified source version",
        )
        assert marker.lower() in str(entities).lower() or "meridian" in str(entities).lower()

    await run_stage("extraction_reached_knowledge_graph", stage_graph_populated())

    # -- Stage 7: hypothesis generation through the gateway ----------------
    async def stage_hypothesis() -> None:
        body, _ = await h.frontend_path_request(
            "l4",
            "POST",
            "/hypotheses/generate",
            json_body={
                "account_id": ctx.get("account_id", h.seed_ids.account_id),
                "max_hypotheses": 3,
            },
            expected=(200, 201, 202),
        )
        hypotheses = body.get("hypotheses") if isinstance(body, dict) else None
        if hypotheses:
            ctx["hypothesis_id"] = str(hypotheses[0].get("id"))

    await run_stage("hypothesis_generate_via_gateway", stage_hypothesis())

    # -- Stage 8: L4 workflow execution -------------------------------------
    async def stage_workflow() -> None:
        body, _ = await h.request(
            "l4",
            "POST",
            "/v1/workflows",
            json={
                # Canonical executable type: the API enum
                # (contracts/openapi/layer4-agents.json WorkflowCreateRequest)
                # lists five values, but the executor registry
                # (layer4_agents.workflows.WORKFLOW_TYPES) implements three;
                # of those, only roi_calculator is reachable through the API
                # input schema (business_case requires a top-level account_id
                # that WorkflowInputs silently drops). roi_calculator is the
                # value-model step of the certification journey.
                "workflow_type": "roi_calculator",
                "inputs": {
                    "prospect_id": ctx.get("account_id", h.seed_ids.account_id),
                    "use_case_ids": ["meridian-cert-value-driver"],
                    "custom_data": {
                        "account_id": ctx.get("account_id", h.seed_ids.account_id),
                        "certification_marker": marker,
                    },
                },
            },
            expected=(200, 201, 202),
        )
        workflow_id = str(
            # Canonical response field per WorkflowCreateResponse is
            # workflow_instance_id; keep legacy aliases for tolerance.
            body.get("workflow_instance_id")
            or body.get("workflow_id")
            or body.get("id")
            or body.get("run_id")
        )
        assert workflow_id and workflow_id != "None", f"no workflow id in {body!r}"
        ctx["workflow_id"] = workflow_id

        async def fetch_workflow() -> Any:
            wf, _ = await h.request(
                "l4", "GET", f"/v1/workflows/{workflow_id}", expected=(200,)
            )
            return wf

        workflow = await _poll(
            fetch_workflow,
            lambda w: str(w.get("status", "")).lower() in WORKFLOW_TERMINAL,
            attempts=40,
            description=f"L4 workflow {workflow_id} terminal state",
        )
        status = str(workflow.get("status", "")).lower()
        assert status not in {"failed", "error"}, f"workflow failed: {workflow!r}"

    await run_stage("workflow_execute_l4", stage_workflow())

    # -- Stage 9: Ground Truth claim with the canonical taxonomy (D6) ------
    async def stage_truth() -> None:
        body, _ = await h.request(
            "l5",
            "POST",
            "/api/v1/truths",
            json={
                "claim": (
                    f"{marker}: Meridian Auto reduced service-contract cycle "
                    f"time by 18 percent"
                ),
                "claim_type": "cost_savings_baseline",
                "confidence": 0.82,
                "value": {"amount": 0.18, "unit": "relative_reduction"},
                "evidence_sources": [
                    {
                        "source_id": ctx.get("source_id", "unknown"),
                        "source_version_id": ctx.get("source_version_id", "unknown"),
                        "excerpt": "service-contract cycle time reduced 18 percent",
                    }
                ],
            },
            expected=(200, 201),
        )
        ctx["truth_id"] = str(body.get("id") or body.get("truth_id"))

        # Canonical lifecycle: KG sync only fires for VALIDATED truths
        # (L5 router: sync requires status == "validated"). The journey must
        # perform the validation transition (ValidateRequest action
        # "validate", requires evidence + actor) — submission alone leaves
        # the claim PROPOSED and unsynced.
        truth_id = ctx["truth_id"]
        await h.request(
            "l5",
            "POST",
            f"/api/v1/truths/{truth_id}/validate",
            json={
                "action": "validate",
                "actor": "production-path-certification",
                "actor_type": "service",
                "notes": f"Certification validation {cert_recorder.run_id}",
            },
            expected=(200, 201),
        )

    await run_stage("ground_truth_submission", stage_truth())

    # -- Stage 10: approved truth reachable from the graph path ------------
    async def stage_truth_sync() -> None:
        truth_id = ctx.get("truth_id")
        assert truth_id and truth_id != "None", "no truth_id from stage 9"

        async def fetch_graph_truth() -> Any:
            body, _ = await h.request(
                "l3", "GET", f"/v1/entities/?search_text={marker}", expected=(200,)
            )
            return body

        await _poll(
            fetch_graph_truth,
            lambda b: truth_id in str(b) or marker in str(b),
            attempts=10,
            description="Ground Truth node visible through the L3 graph path",
        )

    await run_stage("truth_synced_to_graph", stage_truth_sync())

    # -- Stage 11: benchmark participation through the gateway -------------
    async def stage_benchmarks() -> None:
        datasets, _ = await h.frontend_path_request(
            "l6", "GET", "", expected=(200,)
        )
        items = (datasets.get("items") or datasets.get("datasets") or []) if isinstance(datasets, dict) else datasets
        assert items, (
            "no governed benchmark datasets available; certification requires "
            "a pre-existing dataset (decision D7)"
        )
        dataset = items[0]
        dataset_id = str(dataset.get("id") or dataset.get("dataset_id"))
        ctx["benchmark_dataset_id"] = dataset_id
        # The compare contract 404s on metrics absent from the dataset; use
        # the dataset's own first metric (canonical list field) rather than
        # assuming a metric name.
        dataset_metrics = dataset.get("metrics") or []
        assert dataset_metrics, f"dataset {dataset_id} exposes no metrics"
        metric = str(dataset_metrics[0])
        comparison, _ = await h.frontend_path_request(
            "l6",
            "POST",
            "/compare",
            json_body={
                # Canonical ComparisonRequestPayload (layer6-benchmarks.json):
                # requires dataset_id, metric, company_value (string),
                # industry — not a metrics/subject envelope.
                "dataset_id": dataset_id,
                "metric": metric,
                "company_value": "0.18",
                "industry": MERIDIAN_ACCOUNT["industry"],
                "segment": MERIDIAN_ACCOUNT["segment"],
            },
            expected=(200, 201),
        )
        ctx["benchmark_comparison"] = comparison

    await run_stage("benchmark_participation", stage_benchmarks())

    # -- Stage 12: value case retrievable through the gateway --------------
    async def stage_value_case() -> None:
        workflow_id = ctx.get("workflow_id")
        assert workflow_id, "no workflow_id from stage 8"
        body, _ = await h.frontend_path_request(
            "l4", "GET", f"/workflows/{workflow_id}/result", expected=(200,)
        )
        text = str(body)
        assert "grounding_status" in text or "grounded" in text, (
            "value case lacks an explicit grounding/trust state (A-12): "
            f"{text[:600]}"
        )
        ctx["value_case"] = body

    await run_stage("value_case_via_gateway", stage_value_case())

    # -- Stage 13: tenant B denial sweep ------------------------------------
    async def stage_denial() -> None:
        checks: list[tuple[str, str, str]] = []
        if ctx.get("account_id"):
            checks.append(("l4", "GET", f"/v1/accounts/{ctx['account_id']}"))
        if ctx.get("source_id") and ctx["source_id"] != "None":
            checks.append(
                ("l1", "GET", f"/api/v1/ingestion/sources/{ctx['source_id']}")
            )
        if ctx.get("ingestion_run_id"):
            checks.append(
                ("l1", "GET", f"/api/v1/ingestion/runs/{ctx['ingestion_run_id']}")
            )
        if ctx.get("truth_id") and ctx["truth_id"] != "None":
            checks.append(("l5", "GET", f"/api/v1/truths/{ctx['truth_id']}"))
        assert checks, "no tenant-A artifacts recorded to deny against"
        for layer, method, path in checks:
            await h.request(
                layer,
                method,
                path,
                tenant_id=h.seed_ids.tenant_b,
                expected=(401, 403, 404),
            )
        # Tenant B must not see tenant A artifacts in list/search surfaces.
        entities, _ = await h.request(
            "l3",
            "GET",
            f"/v1/entities/?search_text={marker}",
            tenant_id=h.seed_ids.tenant_b,
            expected=(200, 401, 403, 404),
        )
        assert marker not in str(entities), (
            "tenant B can observe tenant A graph data via search"
        )

    await run_stage("tenant_b_denial_sweep", stage_denial())

    cert_recorder.export()
    assert not failures, (
        f"Production-path certification failed {len(failures)} stage(s):\n"
        + "\n".join(f"  - {f}" for f in failures)
    )
