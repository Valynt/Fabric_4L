from __future__ import annotations

"""Skill-specific ingestion job route registrations."""

from fastapi import APIRouter

from . import main

router = APIRouter()
router.add_api_route(
    "/jobs/licensing-company-intake",
    main.create_licensing_company_intake_job,
    methods=["POST"],
    response_model=main.SkillJobResponse,
    status_code=202,
)
router.add_api_route(
    "/jobs/prospect-research",
    main.create_prospect_research_job,
    methods=["POST"],
    response_model=main.SkillJobResponse,
    status_code=202,
)
router.add_api_route(
    "/corpuses/{corpus_id}",
    main.get_source_corpus,
    methods=["GET"],
    response_model=main.SourceCorpusResponse,
)
router.add_api_route(
    "/intelligence-packets/{packet_id}",
    main.get_account_intelligence_packet,
    methods=["GET"],
    response_model=main.AccountIntelligencePacketResponse,
)
router.add_api_route(
    "/jobs/{job_id}/skill-output", main.get_job_skill_output, methods=["GET"]
)
router.add_api_route(
    "/source-corpora",
    main.list_source_corpora,
    methods=["GET"],
    response_model=main.SourceCorpusListResponse,
)
router.add_api_route(
    "/source-corpora/{corpus_id}",
    main.get_source_corpus_detail,
    methods=["GET"],
    response_model=main.SourceCorpusResponse,
)
router.add_api_route(
    "/account-intelligence-packets",
    main.list_account_intelligence_packets,
    methods=["GET"],
    response_model=main.AccountIntelligencePacketListResponse,
)
router.add_api_route(
    "/account-intelligence-packets/{packet_id}",
    main.get_account_intelligence_packet_detail,
    methods=["GET"],
    response_model=main.AccountIntelligencePacketResponse,
)
