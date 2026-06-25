from __future__ import annotations

"""Skill-specific ingestion job route registrations."""

from fastapi import APIRouter

from . import skill_handlers
from .schemas.content_schemas import (
    AccountIntelligencePacketListResponse,
    AccountIntelligencePacketResponse,
    SourceCorpusListResponse,
    SourceCorpusResponse,
)
from .schemas.job_schemas import SkillJobResponse

router = APIRouter()

# NOTE: Static /jobs/* routes must be registered BEFORE parameterized routes
# like /jobs/{job_id}/skill-output. FastAPI resolves routes in declaration order;
# placing the catch-all route first would shadow the static skill-job endpoints.

# Static skill job creation endpoints
router.add_api_route(
    "/jobs/licensing-company-intake",
    skill_handlers.create_licensing_company_intake_job,
    methods=["POST"],
    response_model=SkillJobResponse,
    status_code=202,
)
router.add_api_route(
    "/jobs/prospect-research",
    skill_handlers.create_prospect_research_job,
    methods=["POST"],
    response_model=SkillJobResponse,
    status_code=202,
)

# Parameterized skill job output endpoint (must follow static /jobs/* routes)
router.add_api_route(
    "/jobs/{job_id}/skill-output",
    skill_handlers.get_job_skill_output,
    methods=["GET"],
)

# Source corpora endpoints
router.add_api_route(
    "/corpuses/{corpus_id}",
    skill_handlers.get_source_corpus,
    methods=["GET"],
    response_model=SourceCorpusResponse,
)
router.add_api_route(
    "/source-corpora",
    skill_handlers.list_source_corpora,
    methods=["GET"],
    response_model=SourceCorpusListResponse,
)
router.add_api_route(
    "/source-corpora/{corpus_id}",
    skill_handlers.get_source_corpus_detail,
    methods=["GET"],
    response_model=SourceCorpusResponse,
)

# Account intelligence packet endpoints
router.add_api_route(
    "/intelligence-packets/{packet_id}",
    skill_handlers.get_account_intelligence_packet,
    methods=["GET"],
    response_model=AccountIntelligencePacketResponse,
)
router.add_api_route(
    "/account-intelligence-packets",
    skill_handlers.list_account_intelligence_packets,
    methods=["GET"],
    response_model=AccountIntelligencePacketListResponse,
)
router.add_api_route(
    "/account-intelligence-packets/{packet_id}",
    skill_handlers.get_account_intelligence_packet_detail,
    methods=["GET"],
    response_model=AccountIntelligencePacketResponse,
)
