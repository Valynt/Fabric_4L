from __future__ import annotations

"""Service layer for Company Knowledge Onboarding.

Business logic and data access for company knowledge profiles, sources,
extraction records, and ICP profiles.
"""
import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..integration.layer1_client import Layer1IngestionClient
from ..integration.layer2_client import Layer2ExtractionClient
from ..integration.layer3_client import Layer3Client
from ..models.company_knowledge import (
    CompanyKnowledgeProfile,
    CrawlStatus,
    ICPProfile,
    KnowledgeSource,
    ProfileStatus,
    ReviewStatus,
    SourceType,
    ValueExtractionRecord,
)

logger = logging.getLogger(__name__)

# Environment-based client configuration
LAYER1_BASE_URL = os.getenv("LAYER4_LAYER1_API_URL", "http://layer1-ingestion:8000")
LAYER2_BASE_URL = os.getenv("LAYER4_LAYER2_API_URL", "http://layer2-extraction:8000")
LAYER3_BASE_URL = os.getenv("LAYER4_LAYER3_API_URL", "http://layer3-knowledge:8000")


class Layer3IngestRequest(BaseModel):
    rdf_data: str
    source_id: str
    extraction_job_id: str
    content_hash: str | None = None
    tenant_id: str | None = None


class Layer3IngestResponse(BaseModel):
    status: str
    source_id: str
    entities_loaded: int
    relationships_loaded: int
    triples_processed: int
    duration_seconds: float | None = None
    error: str | None = None
    warnings: list[str] = []


class CompanyKnowledgeService:
    """Service for company knowledge onboarding operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._layer1_client: Layer1IngestionClient | None = None
        self._layer2_client: Layer2ExtractionClient | None = None
        self._layer3_client: Layer3Client | None = None

    def _get_layer1_client(self, tenant_id: str) -> Layer1IngestionClient:
        """Get or create Layer 1 client for tenant."""
        if self._layer1_client is None:
            self._layer1_client = Layer1IngestionClient(
                base_url=LAYER1_BASE_URL,
                tenant_id=tenant_id,
            )
        return self._layer1_client

    def _get_layer2_client(self, tenant_id: str) -> Layer2ExtractionClient:
        """Get or create Layer 2 client for tenant."""
        if self._layer2_client is None:
            self._layer2_client = Layer2ExtractionClient(
                base_url=LAYER2_BASE_URL,
                tenant_id=tenant_id,
            )
        return self._layer2_client

    def _get_layer3_client(self, tenant_id: str) -> Layer3Client:
        """Get or create Layer 3 client for tenant."""
        if self._layer3_client is None:
            self._layer3_client = Layer3Client(
                base_url=LAYER3_BASE_URL,
                tenant_id=tenant_id,
            )
        return self._layer3_client

    # ========================================================================
    # Company Knowledge Profile
    # ========================================================================

    async def create_profile(
        self,
        tenant_id: str,
        company_name: str,
        website: str | None = None,
    ) -> CompanyKnowledgeProfile:
        """Create a new draft company knowledge profile."""
        profile = CompanyKnowledgeProfile(
            tenant_id=tenant_id,
            company_name=company_name,
            website=website,
            status=ProfileStatus.DRAFT.value,
            version=1,
            active_source_ids=[],
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        logger.info("Created company knowledge profile %s for tenant %s", profile.id, tenant_id)
        return profile

    async def get_profile(self, profile_id: UUID, tenant_id: str) -> CompanyKnowledgeProfile | None:
        """Get a profile by ID with tenant isolation."""
        result = await self.db.execute(
            select(CompanyKnowledgeProfile)
            .where(
                and_(
                    CompanyKnowledgeProfile.id == profile_id,
                    CompanyKnowledgeProfile.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active_profile(self, tenant_id: str) -> CompanyKnowledgeProfile | None:
        """Get the approved profile for a tenant, or the latest draft if none approved."""
        # Try approved first
        result = await self.db.execute(
            select(CompanyKnowledgeProfile)
            .where(
                and_(
                    CompanyKnowledgeProfile.tenant_id == tenant_id,
                    CompanyKnowledgeProfile.status == ProfileStatus.APPROVED.value,
                )
            )
            .order_by(CompanyKnowledgeProfile.version.desc())
            .limit(1)
        )
        profile = result.scalar_one_or_none()
        if profile:
            return profile

        # Fallback to latest draft
        result = await self.db.execute(
            select(CompanyKnowledgeProfile)
            .where(CompanyKnowledgeProfile.tenant_id == tenant_id)
            .order_by(CompanyKnowledgeProfile.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_profiles(
        self,
        tenant_id: str,
        status: ProfileStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CompanyKnowledgeProfile], int]:
        """List profiles for a tenant with optional status filter."""
        query = select(CompanyKnowledgeProfile).where(
            CompanyKnowledgeProfile.tenant_id == tenant_id
        )
        count_query = select(func.count(CompanyKnowledgeProfile.id)).where(
            CompanyKnowledgeProfile.tenant_id == tenant_id
        )

        if status:
            query = query.where(CompanyKnowledgeProfile.status == status.value)
            count_query = count_query.where(CompanyKnowledgeProfile.status == status.value)

        query = query.order_by(CompanyKnowledgeProfile.updated_at.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        profiles = result.scalars().all()

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        return list(profiles), total or 0

    async def update_profile(
        self,
        profile_id: UUID,
        tenant_id: str,
        updates: dict[str, Any],
    ) -> CompanyKnowledgeProfile | None:
        """Update profile fields."""
        profile = await self.get_profile(profile_id, tenant_id)
        if not profile:
            return None

        allowed_fields = {
            "company_name",
            "website",
            "identity",
            "product_catalog",
            "target_customer",
            "personas",
            "use_cases",
            "value_drivers",
            "proof_points",
            "trust_commercial",
            "review_status",
            "confidence_score",
        }

        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                setattr(profile, key, value)

        profile.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def approve_profile(
        self,
        profile_id: UUID,
        tenant_id: str,
        approved_by: UUID,
    ) -> CompanyKnowledgeProfile | None:
        """Approve a draft profile, incrementing version."""
        profile = await self.get_profile(profile_id, tenant_id)
        if not profile:
            return None

        if profile.status == ProfileStatus.APPROVED.value:
            logger.warning("Profile %s is already approved", profile_id)
            return profile

        profile.status = ProfileStatus.APPROVED.value
        profile.version += 1
        profile.approved_at = datetime.now(UTC)
        profile.approved_by = approved_by
        profile.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(profile)
        logger.info("Approved company knowledge profile %s version %s", profile_id, profile.version)
        return profile

    async def archive_profile(
        self,
        profile_id: UUID,
        tenant_id: str,
    ) -> CompanyKnowledgeProfile | None:
        """Archive an approved profile."""
        profile = await self.get_profile(profile_id, tenant_id)
        if not profile:
            return None

        profile.status = ProfileStatus.ARCHIVED.value
        profile.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    # ========================================================================
    # Knowledge Source
    # ========================================================================

    async def add_knowledge_source(
        self,
        tenant_id: str,
        profile_id: UUID,
        source_type: SourceType,
        source_url: str | None = None,
        document_name: str | None = None,
        content_hash: str | None = None,
        raw_storage_path: str | None = None,
        authority_weight: str = "medium",
        page_type: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> KnowledgeSource:
        """Add a knowledge source to a profile."""
        source = KnowledgeSource(
            tenant_id=tenant_id,
            profile_id=profile_id,
            source_type=source_type.value,
            source_url=source_url,
            document_name=document_name,
            content_hash=content_hash,
            raw_storage_path=raw_storage_path,
            crawl_status=CrawlStatus.PENDING.value
            if source_type == SourceType.WEBSITE
            else CrawlStatus.COMPLETE.value,
            authority_weight=authority_weight,
            page_type=page_type,
            extra_metadata=extra_metadata or {},
        )
        self.db.add(source)

        # Link source to profile
        profile = await self.get_profile(profile_id, tenant_id)
        if profile:
            current_sources = list(profile.active_source_ids)
            current_sources.append(str(source.id))
            profile.active_source_ids = current_sources
            profile.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(source)
        logger.info("Added knowledge source %s to profile %s", source.id, profile_id)
        return source

    async def get_knowledge_source(
        self, source_id: UUID, tenant_id: str
    ) -> KnowledgeSource | None:
        """Get a knowledge source by ID with tenant isolation."""
        result = await self.db.execute(
            select(KnowledgeSource)
            .where(
                and_(
                    KnowledgeSource.id == source_id,
                    KnowledgeSource.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_knowledge_sources(
        self,
        tenant_id: str,
        profile_id: UUID | None = None,
        source_type: SourceType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[KnowledgeSource], int]:
        """List knowledge sources for a tenant."""
        query = select(KnowledgeSource).where(KnowledgeSource.tenant_id == tenant_id)
        count_query = select(func.count(KnowledgeSource.id)).where(
            KnowledgeSource.tenant_id == tenant_id
        )

        if profile_id:
            query = query.where(KnowledgeSource.profile_id == profile_id)
            count_query = count_query.where(KnowledgeSource.profile_id == profile_id)
        if source_type:
            query = query.where(KnowledgeSource.source_type == source_type.value)
            count_query = count_query.where(KnowledgeSource.source_type == source_type.value)

        query = query.order_by(KnowledgeSource.created_at.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        sources = result.scalars().all()

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        return list(sources), total or 0

    async def update_crawl_status(
        self,
        source_id: UUID,
        tenant_id: str,
        crawl_status: CrawlStatus,
        metadata_updates: dict[str, Any] | None = None,
    ) -> KnowledgeSource | None:
        """Update crawl status and optional metadata for a website source."""
        source = await self.get_knowledge_source(source_id, tenant_id)
        if not source:
            return None

        source.crawl_status = crawl_status.value
        if metadata_updates:
            current_meta = dict(source.extra_metadata)
            current_meta.update(metadata_updates)
            source.extra_metadata = current_meta
        source.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(source)
        return source

    # ========================================================================
    # Value Extraction Record
    # ========================================================================

    async def create_extraction_record(
        self,
        tenant_id: str,
        profile_id: UUID,
        source_id: UUID,
        extracted: dict[str, Any],
        confidence: float | None = None,
        requires_review: bool = False,
        page_type: str | None = None,
        extraction_version: str | None = None,
        llm_model: str | None = None,
        trace_span_id: str | None = None,
    ) -> ValueExtractionRecord:
        """Create a value extraction record from upstream extraction."""
        record = ValueExtractionRecord(
            tenant_id=tenant_id,
            profile_id=profile_id,
            source_id=source_id,
            extracted=extracted,
            confidence=confidence,
            requires_review=requires_review,
            page_type=page_type,
            extraction_version=extraction_version,
            llm_model=llm_model,
            trace_span_id=trace_span_id,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        logger.info(
            "Created extraction record %s for source %s (confidence=%s, review=%s)",
            record.id, source_id, confidence, requires_review
        )
        return record

    async def get_extraction_record(
        self, record_id: UUID, tenant_id: str
    ) -> ValueExtractionRecord | None:
        """Get an extraction record by ID with tenant isolation."""
        result = await self.db.execute(
            select(ValueExtractionRecord)
            .where(
                and_(
                    ValueExtractionRecord.id == record_id,
                    ValueExtractionRecord.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_extraction_records(
        self,
        tenant_id: str,
        profile_id: UUID | None = None,
        source_id: UUID | None = None,
        min_confidence: float | None = None,
        requires_review: bool | None = None,
        review_status: ReviewStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ValueExtractionRecord], int]:
        """List extraction records with filters."""
        query = select(ValueExtractionRecord).where(
            ValueExtractionRecord.tenant_id == tenant_id
        )
        count_query = select(func.count(ValueExtractionRecord.id)).where(
            ValueExtractionRecord.tenant_id == tenant_id
        )

        if profile_id:
            query = query.where(ValueExtractionRecord.profile_id == profile_id)
            count_query = count_query.where(ValueExtractionRecord.profile_id == profile_id)
        if source_id:
            query = query.where(ValueExtractionRecord.source_id == source_id)
            count_query = count_query.where(ValueExtractionRecord.source_id == source_id)
        if min_confidence is not None:
            query = query.where(ValueExtractionRecord.confidence >= min_confidence)
            count_query = count_query.where(ValueExtractionRecord.confidence >= min_confidence)
        if requires_review is not None:
            query = query.where(ValueExtractionRecord.requires_review == requires_review)
            count_query = count_query.where(
                ValueExtractionRecord.requires_review == requires_review
            )
        if review_status:
            query = query.where(ValueExtractionRecord.review_status == review_status.value)
            count_query = count_query.where(
                ValueExtractionRecord.review_status == review_status.value
            )

        query = query.order_by(ValueExtractionRecord.created_at.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(query)
        records = result.scalars().all()

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        return list(records), total or 0

    async def review_extraction_record(
        self,
        record_id: UUID,
        tenant_id: str,
        action: ReviewStatus,
        reviewed_by: UUID,
        user_edits: dict[str, Any] | None = None,
    ) -> ValueExtractionRecord | None:
        """Review an extraction record: accept, reject, or modify."""
        record = await self.get_extraction_record(record_id, tenant_id)
        if not record:
            return None

        record.review_status = action.value
        record.reviewed_by = reviewed_by
        record.reviewed_at = datetime.now(UTC)
        record.updated_at = datetime.now(UTC)

        if action == ReviewStatus.MODIFIED and user_edits:
            current = dict(record.extracted)
            current.update(user_edits)
            record.extracted = current

        if action in (ReviewStatus.ACCEPTED, ReviewStatus.MODIFIED):
            record.requires_review = False

        await self.db.commit()
        await self.db.refresh(record)
        logger.info("Reviewed extraction record %s as %s by %s", record_id, action.value, reviewed_by)
        return record

    # ========================================================================
    # ICP Profile
    # ========================================================================

    async def create_icp_profile(
        self,
        tenant_id: str,
        profile_id: UUID,
        industries: list[str],
        company_size: list[str],
        buyer_personas: list[dict[str, Any]],
        user_personas: list[dict[str, Any]],
        pain_points: list[str],
        trigger_events: list[str],
        qualification_criteria: list[str],
        disqualification_criteria: list[str],
        competitive_context: dict[str, Any] | None = None,
        buying_committee_structure: dict[str, Any] | None = None,
        typical_sales_motion: str | None = None,
        confidence: float | None = None,
        source_type: str = "manual",
    ) -> ICPProfile:
        """Create an ICP profile linked to a company knowledge profile."""
        icp = ICPProfile(
            tenant_id=tenant_id,
            profile_id=profile_id,
            industries=industries,
            company_size=company_size,
            buyer_personas=buyer_personas,
            user_personas=user_personas,
            pain_points=pain_points,
            trigger_events=trigger_events,
            qualification_criteria=qualification_criteria,
            disqualification_criteria=disqualification_criteria,
            competitive_context=competitive_context,
            buying_committee_structure=buying_committee_structure,
            typical_sales_motion=typical_sales_motion,
            confidence=confidence,
            source_type=source_type,
        )
        self.db.add(icp)
        await self.db.commit()
        await self.db.refresh(icp)
        logger.info("Created ICP profile %s for knowledge profile %s", icp.id, profile_id)
        return icp

    async def get_icp_profile(
        self, icp_id: UUID, tenant_id: str
    ) -> ICPProfile | None:
        """Get an ICP profile by ID with tenant isolation."""
        result = await self.db.execute(
            select(ICPProfile)
            .where(
                and_(
                    ICPProfile.id == icp_id,
                    ICPProfile.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_icp_for_profile(
        self, profile_id: UUID, tenant_id: str
    ) -> ICPProfile | None:
        """Get the ICP profile linked to a company knowledge profile."""
        result = await self.db.execute(
            select(ICPProfile)
            .where(
                and_(
                    ICPProfile.profile_id == profile_id,
                    ICPProfile.tenant_id == tenant_id,
                )
            )
            .order_by(ICPProfile.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_icp_profile(
        self,
        icp_id: UUID,
        tenant_id: str,
        updates: dict[str, Any],
    ) -> ICPProfile | None:
        """Update an ICP profile."""
        icp = await self.get_icp_profile(icp_id, tenant_id)
        if not icp:
            return None

        allowed_fields = {
            "industries",
            "company_size",
            "buyer_personas",
            "user_personas",
            "pain_points",
            "trigger_events",
            "qualification_criteria",
            "disqualification_criteria",
            "competitive_context",
            "buying_committee_structure",
            "typical_sales_motion",
            "confidence",
            "source_type",
        }

        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                setattr(icp, key, value)

        icp.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(icp)
        return icp

    # ========================================================================
    # Onboarding Status
    # ========================================================================

    async def get_onboarding_status(self, tenant_id: str) -> dict[str, Any]:
        """Aggregate onboarding progress for a tenant."""
        profile = await self.get_active_profile(tenant_id)

        # Source counts
        sources_query = select(func.count(KnowledgeSource.id)).where(
            KnowledgeSource.tenant_id == tenant_id
        )
        if profile:
            sources_query = sources_query.where(KnowledgeSource.profile_id == profile.id)
        sources_result = await self.db.execute(sources_query)
        sources_count = sources_result.scalar() or 0

        # Extraction aggregates
        extractions_query = select(func.count(ValueExtractionRecord.id)).where(
            ValueExtractionRecord.tenant_id == tenant_id
        )
        if profile:
            extractions_query = extractions_query.where(
                ValueExtractionRecord.profile_id == profile.id
            )
        extractions_result = await self.db.execute(extractions_query)
        extractions_count = extractions_result.scalar() or 0

        pending_review_query = select(func.count(ValueExtractionRecord.id)).where(
            and_(
                ValueExtractionRecord.tenant_id == tenant_id,
                ValueExtractionRecord.requires_review == True,  # noqa: E712
            )
        )
        if profile:
            pending_review_query = pending_review_query.where(
                ValueExtractionRecord.profile_id == profile.id
            )
        pending_result = await self.db.execute(pending_review_query)
        extractions_pending_review = pending_result.scalar() or 0

        accepted_query = select(func.count(ValueExtractionRecord.id)).where(
            and_(
                ValueExtractionRecord.tenant_id == tenant_id,
                ValueExtractionRecord.review_status == ReviewStatus.ACCEPTED.value,
            )
        )
        if profile:
            accepted_query = accepted_query.where(
                ValueExtractionRecord.profile_id == profile.id
            )
        accepted_result = await self.db.execute(accepted_query)
        extractions_accepted = accepted_result.scalar() or 0

        rejected_query = select(func.count(ValueExtractionRecord.id)).where(
            and_(
                ValueExtractionRecord.tenant_id == tenant_id,
                ValueExtractionRecord.review_status == ReviewStatus.REJECTED.value,
            )
        )
        if profile:
            rejected_query = rejected_query.where(
                ValueExtractionRecord.profile_id == profile.id
            )
        rejected_result = await self.db.execute(rejected_query)
        extractions_rejected = rejected_result.scalar() or 0

        # Average confidence
        avg_conf_query = select(func.avg(ValueExtractionRecord.confidence)).where(
            ValueExtractionRecord.tenant_id == tenant_id
        )
        if profile:
            avg_conf_query = avg_conf_query.where(
                ValueExtractionRecord.profile_id == profile.id
            )
        avg_conf_result = await self.db.execute(avg_conf_query)
        average_confidence = avg_conf_result.scalar()

        # ICP presence
        icp_present = False
        if profile:
            icp_result = await self.db.execute(
                select(func.count(ICPProfile.id)).where(
                    and_(
                        ICPProfile.tenant_id == tenant_id,
                        ICPProfile.profile_id == profile.id,
                    )
                )
            )
            icp_present = (icp_result.scalar() or 0) > 0

        # Determine next step
        next_step = self._determine_next_step(
            profile=profile,
            sources_count=sources_count,
            extractions_pending_review=extractions_pending_review,
            icp_present=icp_present,
        )

        return {
            "tenant_id": tenant_id,
            "profile_id": profile.id if profile else None,
            "profile_status": profile.status if profile else None,
            "company_name": profile.company_name if profile else None,
            "website": profile.website if profile else None,
            "sources_count": sources_count,
            "extractions_count": extractions_count,
            "extractions_pending_review": extractions_pending_review,
            "extractions_accepted": extractions_accepted,
            "extractions_rejected": extractions_rejected,
            "average_confidence": float(average_confidence) if average_confidence is not None else None,
            "icp_present": icp_present,
            "has_approved_profile": profile.status == ProfileStatus.APPROVED.value if profile else False,
            "next_step": next_step,
        }

    def _determine_next_step(
        self,
        profile: CompanyKnowledgeProfile | None,
        sources_count: int,
        extractions_pending_review: int,
        icp_present: bool,
    ) -> str:
        """Determine the next onboarding action based on current state."""
        if not profile:
            return "Enter your company website to begin."

        if profile.status == ProfileStatus.APPROVED.value:
            return "Your company profile is approved. You can now generate value hypotheses."

        if sources_count == 0:
            return "Add your company website or upload materials to extract knowledge."

        if extractions_pending_review > 0:
            return f"Review {extractions_pending_review} low-confidence extraction{'s' if extractions_pending_review > 1 else ''}."

        if not icp_present:
            return "Add your ideal customer profile (ICP) to tailor value models."

        if profile.status == ProfileStatus.DRAFT.value:
            return "Review your draft profile and approve when ready."

        return "Continue refining your company knowledge profile."

    # ========================================================================
    # Pipeline Integration (Layer 1 → 2 → 3)
    # ========================================================================

    async def trigger_layer1_crawl(
        self,
        source_id: UUID,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Trigger Layer 1 website crawl for a knowledge source.

        Args:
            source_id: Knowledge source ID
            tenant_id: Tenant context

        Returns:
            Crawl execution result with target_id and job_id
        """
        source = await self.get_knowledge_source(source_id, tenant_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        if not source.source_url:
            raise ValueError(f"Source {source_id} has no URL")

        client = self._get_layer1_client(tenant_id)
        try:
            result = await client.crawl_website(
                url=source.source_url,
                tenant_id=tenant_id,
                name=f"Company knowledge crawl: {source.source_url}",
            )
            # Update source with crawl tracking
            await self.update_crawl_status(
                source_id=source_id,
                tenant_id=tenant_id,
                crawl_status=CrawlStatus.IN_PROGRESS,
                metadata_updates={
                    "layer1_target_id": result.get("target_id"),
                    "layer1_job_id": result.get("job_id"),
                },
            )
            logger.info(
                "Triggered Layer 1 crawl for source %s: target=%s",
                source_id,
                result.get("target_id"),
            )
            return result
        except asyncio.CancelledError:
            raise
        except Exception as e:
            await self.update_crawl_status(
                source_id=source_id,
                tenant_id=tenant_id,
                crawl_status=CrawlStatus.FAILED,
                metadata_updates={"error_code": "CRAWL_ERROR"},
            )
            logger.error("Layer 1 crawl failed for source %s: %s", source_id, e)
            raise

    async def trigger_layer2_extraction(
        self,
        source_id: UUID,
        tenant_id: str,
        content_id: str,
        markdown_content: str,
    ) -> dict[str, Any]:
        """Trigger Layer 2 value attribute extraction.

        Args:
            source_id: Knowledge source ID
            tenant_id: Tenant context
            content_id: Layer 1 content identifier
            markdown_content: Crawled markdown content

        Returns:
            Extraction result
        """
        source = await self.get_knowledge_source(source_id, tenant_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")

        client = self._get_layer2_client(tenant_id)
        try:
            result = await client.extract_value_attributes(
                content_id=content_id,
                source_url=source.source_url or "",
                markdown_content=markdown_content,
                tenant_id=tenant_id,
            )

            # Store extraction as a ValueExtractionRecord
            extracted = result.get("extracted_entities", {})
            confidence = result.get("confidence", 0.0)
            requires_review = confidence < 0.75

            record = await self.create_extraction_record(
                tenant_id=tenant_id,
                profile_id=source.profile_id,
                source_id=source_id,
                extracted=extracted,
                confidence=confidence,
                requires_review=requires_review,
                page_type=source.page_type,
                extraction_version=result.get("extraction_version", "1.0"),
                llm_model=result.get("model_version", "unknown"),
                trace_span_id=result.get("job_id"),
            )

            # Update source status
            await self.update_crawl_status(
                source_id=source_id,
                tenant_id=tenant_id,
                crawl_status=CrawlStatus.COMPLETE,
                metadata_updates={
                    "layer2_job_id": result.get("job_id"),
                    "extraction_record_id": str(record.id),
                },
            )

            logger.info(
                "Layer 2 extraction completed for source %s: record=%s",
                source_id,
                record.id,
            )
            return result
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Layer 2 extraction failed for source %s: %s", source_id, e)
            raise

    async def sync_profile_to_layer3(
        self,
        profile_id: UUID,
        tenant_id: str,
        auth_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Sync approved company knowledge profile to Layer 3 Knowledge Graph.

        Args:
            profile_id: Company knowledge profile ID
            tenant_id: Tenant context

        Returns:
            Sync result from Layer 3
        """
        profile = await self.get_profile(profile_id, tenant_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")
        if profile.status != ProfileStatus.APPROVED.value:
            raise ValueError("Only approved profiles can be synced to Layer 3")

        client = self._get_layer3_client(tenant_id)

        # Build entity payload from profile sections
        entities: list[dict[str, Any]] = []
        if profile.identity:
            entities.append({
                "type": "Company",
                "name": profile.company_name,
                "properties": profile.identity,
            })
        if profile.product_catalog:
            for product in profile.product_catalog.get("products", []):
                entities.append({
                    "type": "Product",
                    "name": product.get("name", "Unknown"),
                    "properties": product,
                })
        if profile.personas:
            for persona in profile.personas.get("personas", []):
                entities.append({
                    "type": "Persona",
                    "name": persona.get("name", "Unknown"),
                    "properties": persona,
                })
        if profile.use_cases:
            for use_case in profile.use_cases.get("use_cases", []):
                entities.append({
                    "type": "UseCase",
                    "name": use_case.get("name", "Unknown"),
                    "properties": use_case,
                })
        if profile.value_drivers:
            for driver in profile.value_drivers.get("drivers", []):
                entities.append({
                    "type": "ValueDriver",
                    "name": driver.get("name", "Unknown"),
                    "properties": driver,
                })

        rdf_lines = []
        for entity in entities:
            entity_type = entity["type"]
            entity_name = str(entity["name"]).replace('"', '\\"')
            rdf_lines.append(f'_:{entity_type}_{entity_name.replace(" ", "_")} a <urn:value-fabric:{entity_type}> .')
            rdf_lines.append(f'_:{entity_type}_{entity_name.replace(" ", "_")} <urn:value-fabric:name> "{entity_name}" .')
        ingest_request = Layer3IngestRequest(
            rdf_data="\n".join(rdf_lines),
            source_id=f"company-profile:{profile_id}",
            extraction_job_id=f"layer4-company-knowledge:{profile_id}",
            content_hash=None,
            tenant_id=tenant_id,
        )
        ingest_result = await client.ingest(
            ingestion_payload=ingest_request.model_dump(),
            tenant_id=tenant_id,
            passthrough_headers=auth_headers,
        )
        try:
            validated_result = Layer3IngestResponse.model_validate(ingest_result)
        except ValidationError as e:
            raise ValueError(f"Layer 3 ingest contract mismatch: {e}") from e

        logger.info(
            "Synced profile %s to Layer 3 via /v1/ingest: %s entities",
            profile_id,
            validated_result.entities_loaded,
        )
        return {
            "profile_id": str(profile_id),
            "ingest_status": validated_result.status,
            "source_id": validated_result.source_id,
            "entities_loaded": validated_result.entities_loaded,
            "relationships_loaded": validated_result.relationships_loaded,
            "triples_processed": validated_result.triples_processed,
        }
