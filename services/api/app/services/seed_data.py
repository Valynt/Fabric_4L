import json
import os
from typing import Any

import structlog

from app.core.config import get_settings
from app.core.database import db
from app.core.security import hash_password
from app.models.schemas import (
    Account,
    AgentRun,
    BusinessCase,
    Evidence,
    GovernanceGate,
    ROICalculation,
    Scenario,
    Signal,
    Stakeholder,
    Tenant,
    User,
    ValueDriver,
    ValueHypothesis,
    ValueLever,
    ValuePack,
)

PACKS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "packs")

logger = structlog.get_logger(__name__)


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_tenants():
    tenants = [
        Tenant(
            id="tenant-alpha",
            name="Alpha Corp",
            plan="enterprise",
            default_value_pack_id="software-v1",
        ),
        Tenant(
            id="tenant-beta",
            name="Beta Solutions",
            plan="team",
            default_value_pack_id="manufacturing-v1",
        ),
    ]
    for t in tenants:
        db.tenants.insert(t.id, t)
    return tenants


def seed_users(tenant_ids: list[str]):
    # Seed passwords are intentionally weak for demo/dev only.
    # These accounts must never exist in production (F-02, F-14).
    settings = get_settings()
    if settings.is_production_like:
        raise RuntimeError("seed_users is disabled in production-like environments")
    users = [
        User(
            id="user-1",
            tenant_id=tenant_ids[0],
            email="admin@alpha.com",
            name="Admin User",
            role="tenant_admin",
            password_hash=hash_password("SeedAdmin!Dev2024"),
            status="active",
        ),
        User(
            id="user-2",
            tenant_id=tenant_ids[1],
            email="analyst@beta.com",
            name="Analyst User",
            role="analyst",
            password_hash=hash_password("SeedAnalyst!Dev2024"),
            status="active",
        ),
    ]
    for u in users:
        db.users.insert(u.id, u)
    return users


def seed_value_packs() -> list[ValuePack]:
    manifest_path = os.path.join(PACKS_DIR, "pack-manifest.json")
    if not os.path.exists(manifest_path):
        return []
    manifest = load_json(manifest_path)
    packs: list[ValuePack] = []
    for p in manifest.get("packs", []):
        pack = ValuePack(
            id=p["pack_id"],
            name=p["name"],
            industry=p["industry"],
            description=p.get("description"),
            status=p.get("status", "published"),
            version=p.get("version", "1.0.0"),
            formula_count=p.get("formula_count", 0),
            variable_count=p.get("variable_count", 0),
            entity_count=p.get("entity_count", 0),
            tags=p.get("tags", []),
            path=p.get("path"),
        )
        db.value_packs.insert(pack.id, pack)
        packs.append(pack)
    return packs


def seed_accounts(tenant_ids: list[str], pack_ids: list[str]) -> list[Account]:
    accounts_data = [
        {
            "id": "acc-allego",
            "name": "Allegro Dynamics",
            "industry": "Software",
            "segment": "B2B SaaS",
            "website": "https://allegrodynamics.example.com",
            "annual_revenue": 45_000_000,
            "employee_count": 320,
            "crm_stage": "opportunity",
            "value_pack_id": pack_ids[2] if len(pack_ids) > 2 else None,
            "summary": "Sales enablement platform evaluating ROI of AI-powered coaching.",
            "tenant_id": tenant_ids[0],
        },
        {
            "id": "acc-vertex",
            "name": "Vertex Manufacturing",
            "industry": "Manufacturing",
            "segment": "Industrial Equipment",
            "website": "https://vertexmfg.example.com",
            "annual_revenue": 120_000_000,
            "employee_count": 850,
            "crm_stage": "qualification",
            "value_pack_id": pack_ids[1] if len(pack_ids) > 1 else None,
            "summary": "Predictive maintenance and OEE optimization initiative.",
            "tenant_id": tenant_ids[0],
        },
        {
            "id": "acc-healthix",
            "name": "HealthiX Systems",
            "industry": "Healthcare",
            "segment": "MedTech",
            "website": "https://healthix.example.com",
            "annual_revenue": 78_000_000,
            "employee_count": 410,
            "crm_stage": "proposal",
            "value_pack_id": pack_ids[0] if len(pack_ids) > 0 else None,
            "summary": "Clinical workflow automation and regulatory compliance platform.",
            "tenant_id": tenant_ids[0],
        },
        {
            "id": "acc-finova",
            "name": "Finova Analytics",
            "industry": "Financial Services",
            "segment": "Fintech",
            "website": "https://finova.example.com",
            "annual_revenue": 200_000_000,
            "employee_count": 600,
            "crm_stage": "negotiation",
            "value_pack_id": pack_ids[3] if len(pack_ids) > 3 else None,
            "summary": "Real-time fraud detection and digital onboarding acceleration.",
            "tenant_id": tenant_ids[1],
        },
        {
            "id": "acc-pubtech",
            "name": "PubTech Solutions",
            "industry": "Public Sector",
            "segment": "Government Software",
            "website": "https://pubtech.example.gov",
            "annual_revenue": 30_000_000,
            "employee_count": 150,
            "crm_stage": "opportunity",
            "value_pack_id": pack_ids[2] if len(pack_ids) > 2 else None,
            "summary": "Citizen service platform modernization and case management.",
            "tenant_id": tenant_ids[1],
        },
    ]
    accounts: list[Account] = []
    for a in accounts_data:
        acc = Account(**a)
        db.accounts.insert(acc.id, acc)
        accounts.append(acc)
    return accounts


def seed_stakeholders(accounts: list[Account]) -> list[Stakeholder]:
    stakeholders_data = [
        {
            "id": "sh-1",
            "account_id": "acc-allego",
            "tenant_id": accounts[0].tenant_id,
            "name": "Sarah Chen",
            "title": "VP of Sales",
            "persona_id": "persona-vp-sales",
            "department": "Sales",
            "priorities": ["quota attainment", "ramp time"],
            "pains": ["low conversion rates", "long onboarding"],
            "influence_level": "high",
            "decision_role": "economic",
        },
        {
            "id": "sh-2",
            "account_id": "acc-allego",
            "tenant_id": accounts[0].tenant_id,
            "name": "Marcus Johnson",
            "title": "CRO",
            "persona_id": "persona-cro",
            "department": "Revenue",
            "priorities": ["pipeline velocity", "forecast accuracy"],
            "pains": ["unpredictable revenue"],
            "influence_level": "high",
            "decision_role": "economic",
        },
        {
            "id": "sh-3",
            "account_id": "acc-vertex",
            "tenant_id": accounts[1].tenant_id,
            "name": "Diana Ross",
            "title": "Plant Manager",
            "persona_id": "persona-plant-manager",
            "department": "Operations",
            "priorities": ["OEE", "safety"],
            "pains": ["unplanned downtime"],
            "influence_level": "high",
            "decision_role": "user",
        },
        {
            "id": "sh-4",
            "account_id": "acc-healthix",
            "tenant_id": accounts[2].tenant_id,
            "name": "Dr. Alan Grant",
            "title": "CMO",
            "persona_id": "persona-cmo",
            "department": "Medical",
            "priorities": ["patient outcomes", "compliance"],
            "pains": ["documentation burden"],
            "influence_level": "high",
            "decision_role": "economic",
        },
        {
            "id": "sh-5",
            "account_id": "acc-finova",
            "tenant_id": accounts[3].tenant_id,
            "name": "Rachel Green",
            "title": "CFO",
            "persona_id": "persona-cfo",
            "department": "Finance",
            "priorities": ["cost control", "risk reduction"],
            "pains": ["fraud losses"],
            "influence_level": "high",
            "decision_role": "economic",
        },
    ]
    result: list[Stakeholder] = []
    for s in stakeholders_data:
        st = Stakeholder(**s)
        db.stakeholders.insert(st.id, st)
        result.append(st)
    return result


def seed_signals(accounts: list[Account]) -> list[Signal]:
    signals_data = [
        {
            "id": "sig-1",
            "account_id": "acc-allego",
            "tenant_id": accounts[0].tenant_id,
            "signal_type": "pain",
            "title": "Low onboarding completion",
            "description": "Only 42% of new hires complete full onboarding track.",
            "severity": "high",
            "confidence": 0.85,
        },
        {
            "id": "sig-2",
            "account_id": "acc-allego",
            "tenant_id": accounts[0].tenant_id,
            "signal_type": "pain",
            "title": "Quota attainment declining",
            "description": "Q1 attainment down 12% YoY.",
            "severity": "critical",
            "confidence": 0.92,
        },
        {
            "id": "sig-3",
            "account_id": "acc-vertex",
            "tenant_id": accounts[1].tenant_id,
            "signal_type": "pain",
            "title": "Unplanned downtime spikes",
            "description": "Downtime increased 18% in Q2.",
            "severity": "high",
            "confidence": 0.88,
        },
        {
            "id": "sig-4",
            "account_id": "acc-healthix",
            "tenant_id": accounts[2].tenant_id,
            "signal_type": "opportunity",
            "title": "AI documentation assistant",
            "description": "Physicians spend 2.5h/day on notes; AI could reduce by 60%.",
            "severity": "medium",
            "confidence": 0.78,
        },
        {
            "id": "sig-5",
            "account_id": "acc-finova",
            "tenant_id": accounts[3].tenant_id,
            "signal_type": "risk",
            "title": "Fraud rate above benchmark",
            "description": "Fraud rate at 1.8% vs industry 0.9%.",
            "severity": "critical",
            "confidence": 0.95,
        },
    ]
    result: list[Signal] = []
    for s in signals_data:
        sig = Signal(**s)
        db.signals.insert(sig.id, sig)
        result.append(sig)
    return result


def seed_evidence(accounts: list[Account]) -> list[Evidence]:
    evidence_data = [
        {
            "id": "ev-1",
            "account_id": "acc-allego",
            "tenant_id": accounts[0].tenant_id,
            "title": "Q1 Sales Performance Deck",
            "excerpt": "Quota attainment declined 12% year-over-year.",
            "source_type": "pdf",
            "confidence": 0.92,
        },
        {
            "id": "ev-2",
            "account_id": "acc-vertex",
            "tenant_id": accounts[1].tenant_id,
            "title": "Maintenance Log 2026",
            "excerpt": "Unplanned downtime increased 18% in Q2 due to bearing failures.",
            "source_type": "spreadsheet",
            "confidence": 0.88,
        },
        {
            "id": "ev-3",
            "account_id": "acc-healthix",
            "tenant_id": accounts[2].tenant_id,
            "title": "Physician Time Study",
            "excerpt": "Clinicians spend 2.5 hours per day on documentation tasks.",
            "source_type": "case_study",
            "confidence": 0.85,
        },
        {
            "id": "ev-4",
            "account_id": "acc-finova",
            "tenant_id": accounts[3].tenant_id,
            "title": "Fraud Benchmark Report",
            "excerpt": "Industry average fraud rate is 0.9%; Finova measured 1.8%.",
            "source_type": "api",
            "confidence": 0.95,
        },
    ]
    result: list[Evidence] = []
    for e in evidence_data:
        ev = Evidence(**e)
        db.evidence.insert(ev.id, ev)
        result.append(ev)
    return result


def seed_hypotheses(accounts: list[Account]) -> list[ValueHypothesis]:
    hypotheses_data = [
        {
            "id": "hyp-1",
            "account_id": "acc-allego",
            "tenant_id": accounts[0].tenant_id,
            "title": "AI coaching reduces ramp time by 30%",
            "claim": "Implementing AI role-play coaching will reduce new hire ramp time from 6 to 4 months.",
            "expected_outcome": "$1.2M additional ARR from faster quota attainment",
            "confidence": 0.75,
        },
        {
            "id": "hyp-2",
            "account_id": "acc-vertex",
            "tenant_id": accounts[1].tenant_id,
            "title": "Predictive maintenance cuts downtime 25%",
            "claim": "IoT sensor + ML model will predict bearing failures 2 weeks early.",
            "expected_outcome": "Save $890K annually in avoided downtime",
            "confidence": 0.82,
        },
        {
            "id": "hyp-3",
            "account_id": "acc-healthix",
            "tenant_id": accounts[2].tenant_id,
            "title": "Clinical AI reduces documentation time 60%",
            "claim": "Ambient clinical voice AI will cut documentation burden by 60%.",
            "expected_outcome": "Reclaim 1.5h/day per physician, improving capacity and satisfaction",
            "confidence": 0.68,
        },
        {
            "id": "hyp-4",
            "account_id": "acc-finova",
            "tenant_id": accounts[3].tenant_id,
            "title": "Real-time fraud detection halves losses",
            "claim": "Sub-100ms fraud scoring will reduce fraud rate from 1.8% to 0.9%.",
            "expected_outcome": "$4.5M annual loss reduction",
            "confidence": 0.85,
        },
    ]
    result: list[ValueHypothesis] = []
    for h in hypotheses_data:
        hyp = ValueHypothesis(**h)
        db.hypotheses.insert(hyp.id, hyp)
        result.append(hyp)
    return result


def seed_drivers_and_levers(accounts: list[Account]) -> list[ValueDriver]:
    drivers_data = [
        {
            "id": "drv-1",
            "account_id": "acc-allego",
            "tenant_id": accounts[0].tenant_id,
            "name": "Revenue per Rep",
            "category": "revenue_uplift",
            "description": "Increase average quota attainment and deal size.",
            "levers": [
                {
                    "id": "lev-1",
                    "driver_id": "drv-1",
                    "name": "Faster ramp time",
                    "description": "Reduce onboarding from 6 to 4 months",
                    "baseline_metric": 6.0,
                    "target_metric": 4.0,
                    "unit": "months",
                    "confidence": 0.75,
                },
                {
                    "id": "lev-2",
                    "driver_id": "drv-1",
                    "name": "Higher win rate",
                    "description": "Improve win rate via AI coaching",
                    "baseline_metric": 18.0,
                    "target_metric": 24.0,
                    "unit": "%",
                    "confidence": 0.70,
                },
            ],
        },
        {
            "id": "drv-2",
            "account_id": "acc-vertex",
            "tenant_id": accounts[1].tenant_id,
            "name": "Maintenance Cost Avoidance",
            "category": "cost_savings",
            "description": "Avoid unplanned downtime and emergency repairs.",
            "levers": [
                {
                    "id": "lev-3",
                    "driver_id": "drv-2",
                    "name": "Downtime reduction",
                    "description": "Predict failures before they occur",
                    "baseline_metric": 18.0,
                    "target_metric": 12.0,
                    "unit": "%",
                    "confidence": 0.82,
                },
            ],
        },
        {
            "id": "drv-3",
            "account_id": "acc-finova",
            "tenant_id": accounts[3].tenant_id,
            "name": "Fraud Loss Reduction",
            "category": "risk_reduction",
            "description": "Reduce fraud rate and associated charge-offs.",
            "levers": [
                {
                    "id": "lev-4",
                    "driver_id": "drv-3",
                    "name": "Fraud rate improvement",
                    "description": "Cut fraud rate in half",
                    "baseline_metric": 1.8,
                    "target_metric": 0.9,
                    "unit": "%",
                    "confidence": 0.85,
                },
            ],
        },
    ]
    result: list[ValueDriver] = []
    for d in drivers_data:
        levers = [ValueLever(**lever_data) for lever_data in d.pop("levers", [])]
        drv = ValueDriver(**d, levers=levers)
        db.drivers.insert(drv.id, drv)
        result.append(drv)
    return result


def seed_scenarios(accounts: list[Account]) -> list[Scenario]:
    scenarios = [
        Scenario(
            id="sc-1",
            account_id="acc-allego",
            tenant_id=accounts[0].tenant_id,
            name="conservative",
            assumptions={"ramp_reduction": 0.15, "cost": 400_000},
            confidence=0.6,
        ),
        Scenario(
            id="sc-2",
            account_id="acc-allego",
            tenant_id=accounts[0].tenant_id,
            name="expected",
            assumptions={"ramp_reduction": 0.30, "cost": 350_000},
            confidence=0.75,
        ),
        Scenario(
            id="sc-3",
            account_id="acc-allego",
            tenant_id=accounts[0].tenant_id,
            name="optimistic",
            assumptions={"ramp_reduction": 0.45, "cost": 300_000},
            confidence=0.5,
        ),
    ]
    for s in scenarios:
        db.scenarios.insert(s.id, s)
    return scenarios


def seed_roi_calculations(accounts: list[Account]) -> list[ROICalculation]:
    # Deterministic seeded ROI calculations
    calcs = [
        ROICalculation(
            id="roi-1",
            account_id="acc-allego",
            tenant_id=accounts[0].tenant_id,
            scenario_id="sc-2",
            revenue_uplift=1_200_000,
            cost_savings=0,
            risk_reduction=0,
            solution_cost=350_000,
            total_benefit=1_200_000,
            net_benefit=850_000,
            roi_percent=242.86,
            payback_months=3.5,
            calculation_trace=[
                {
                    "step": "revenue_uplift",
                    "value": 1_200_000,
                    "note": "50 reps x 2 months faster x $12K/mo",
                },
                {"step": "total_benefit", "value": 1_200_000},
                {"step": "net_benefit", "value": 850_000},
                {"step": "roi_percent", "value": 242.86},
                {"step": "payback_months", "value": 3.5},
            ],
        ),
    ]
    for c in calcs:
        db.roi_calculations.insert(c.id, c)
    return calcs


def seed_business_cases(accounts: list[Account]) -> list[BusinessCase]:
    cases = [
        BusinessCase(
            id="bc-1",
            account_id="acc-allego",
            tenant_id=accounts[0].tenant_id,
            title="Allegro Dynamics AI Coaching Business Case",
            executive_summary="AI-powered coaching is projected to improve ramp time by 30%, yielding $1.2M incremental ARR with a 3.5-month payback.",
            value_narrative="Current-state onboarding is manual and inconsistent. AI coaching delivers personalized role-play at scale, reducing time-to-productivity and improving quota attainment.",
            roi_calculation_ids=["roi-1"],
            assumptions=[
                "30% ramp time improvement",
                "50 affected reps",
                "$12K monthly quota value",
            ],
            risks=["Adoption resistance", "Integration timeline"],
            recommendation="Proceed with phased rollout beginning Q3.",
            status="draft",
        ),
    ]
    for c in cases:
        db.business_cases.insert(c.id, c)
    return cases


def seed_governance(tenant_ids: list[str]) -> list[GovernanceGate]:
    gates = [
        GovernanceGate(
            id="gate-1",
            tenant_id=tenant_ids[0],
            name="Architecture",
            category="architecture",
            status="passed",
        ),
        GovernanceGate(
            id="gate-2",
            tenant_id=tenant_ids[0],
            name="Security",
            category="security",
            status="passed",
        ),
        GovernanceGate(
            id="gate-3",
            tenant_id=tenant_ids[0],
            name="Tenant Isolation",
            category="tenant_isolation",
            status="passed",
        ),
        GovernanceGate(
            id="gate-4",
            tenant_id=tenant_ids[0],
            name="Contract Drift",
            category="contract_drift",
            status="pending",
        ),
        GovernanceGate(
            id="gate-5",
            tenant_id=tenant_ids[0],
            name="Observability",
            category="observability",
            status="passed",
        ),
        GovernanceGate(
            id="gate-6",
            tenant_id=tenant_ids[0],
            name="Agent Safety",
            category="agent_safety",
            status="pending",
        ),
    ]
    for g in gates:
        db.governance_gates.insert(g.id, g)
    return gates


def seed_agent_runs(tenant_ids: list[str]) -> list[AgentRun]:
    runs = [
        AgentRun(
            id="run-1",
            tenant_id=tenant_ids[0],
            account_id="acc-allego",
            workflow_type="hypothesis_generation",
            status="completed",
            current_step="generate",
            output={"hypotheses_count": 4},
            review_required=False,
        ),
        AgentRun(
            id="run-2",
            tenant_id=tenant_ids[0],
            account_id="acc-allego",
            workflow_type="roi_modeling",
            status="completed",
            current_step="calculate",
            output={"roi_percent": 242.86},
            review_required=True,
        ),
    ]
    for r in runs:
        db.agent_runs.insert(r.id, r)
    return runs


def seed_all():
    tenants = seed_tenants()
    tenant_ids = [t.id for t in tenants]
    seed_users(tenant_ids)
    packs = seed_value_packs()
    pack_ids = [p.id for p in packs]
    accounts = seed_accounts(tenant_ids, pack_ids)
    seed_stakeholders(accounts)
    seed_signals(accounts)
    seed_evidence(accounts)
    seed_hypotheses(accounts)
    seed_drivers_and_levers(accounts)
    seed_scenarios(accounts)
    seed_roi_calculations(accounts)
    seed_business_cases(accounts)
    seed_governance(tenant_ids)
    seed_agent_runs(tenant_ids)
    logger.info(
        "[seed] Loaded %d tenants, %d accounts, %d value packs",
        len(tenants),
        len(accounts),
        len(packs),
    )
