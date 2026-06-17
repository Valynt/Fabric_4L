from __future__ import annotations

"""
Account Enrichment Orchestrator — Data Intelligence Layer Phase 1.

Coordinates multi-source enrichment for account records:
1. SEC EDGAR → Financial data (revenue, margins, growth)
2. Web crawl  → Tech stack detection via HTML meta/script analysis
3. Domain     → Executive mapping from LinkedIn/public sources
4. Signals    → Pain signal detection from news/filings

The orchestrator is idempotent: re-running enrichment for an already-enriched
account updates stale fields without duplicating data.

Architecture:
- L4 Postgres = system of record (Account model with enrichment JSONB columns)
- L1 adapters = data fetchers (SEC EDGAR, web crawlers)
- L3 graph    = downstream projection (deferred — orchestrator writes to L4 only)
"""
import asyncio
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.security.dil_auth import SSRFBlockedError, validate_url_safe

from ..models.account import Account


class EnrichmentOrchestrator_enrich_accountResult(TypedDictModel):
    account_id: Any | None = None
    enriched_at: Any | None = None
    errors: Any | None = None
    message: str = ""
    results: Any | None = None
    sources_used: Any | None = None
    status: str

class EnrichmentOrchestrator_enrich_batchResult(TypedDictModel):
    failed: Any | None = None
    message: str
    results: Any | None = None
    status: str
    success: Any | None = None
    total: Any | None = None

class EnrichmentOrchestrator_get_enrichment_statusResult(TypedDictModel):
    coverage_pct: Any
    enriched: Any
    failed: Any
    in_progress: Any
    pending: Any
    stale: Any
    total_accounts: Any

class EnrichmentOrchestrator__enrich_from_domainResult(TypedDictModel):
    domain: Any | None = None
    error: str
    executives_found: int | None = None
    note: str | None = None
    source: str | None = None
    success: bool

class EnrichmentOrchestrator__enrich_from_newsResult(TypedDictModel):
    company_name: Any | None = None
    error: str
    note: str | None = None
    signals_found: int | None = None
    source: str | None = None
    success: bool

class EnrichmentOrchestrator__enrich_from_sourceResult(TypedDictModel):
    error: str
    success: bool

class EnrichmentOrchestrator__enrich_from_sec_edgarResult(TypedDictModel):
    entity_name: Any | None = None
    error: str
    filing_date: Any | None = None
    source: str | None = None
    success: bool

class EnrichmentOrchestrator__enrich_from_web_crawlResult(TypedDictModel):
    error: str | None = None
    source: str | None = None
    success: bool
    tech_stack: Any | None = None
    technologies_found: Any | None = None
    url: Any | None = None

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Enrichment Status Enum
# ---------------------------------------------------------------------------

class EnrichmentStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ENRICHED = "enriched"
    FAILED = "failed"
    STALE = "stale"


class EnrichmentSource(str, Enum):
    SEC_EDGAR = "sec_edgar"
    WEB_CRAWL = "web_crawl"
    DOMAIN_LOOKUP = "domain_lookup"
    NEWS_SCAN = "news_scan"


# ---------------------------------------------------------------------------
# Tech Stack Detection Patterns
# ---------------------------------------------------------------------------

# Maps HTML/script patterns to technology categories
TECH_STACK_SIGNATURES: dict[str, dict[str, list[str]]] = {
    "analytics": {
        "Google Analytics": ["google-analytics.com", "gtag/js", "ga.js"],
        "Mixpanel": ["cdn.mxpnl.com", "mixpanel"],
        "Segment": ["cdn.segment.com", "analytics.js"],
        "Heap": ["heap-analytics", "heapanalytics.com"],
        "Amplitude": ["amplitude.com", "amplitude.min.js"],
        "Hotjar": ["hotjar.com", "static.hotjar.com"],
    },
    "crm": {
        "Salesforce": ["force.com", "salesforce.com", "pardot.com"],
        "HubSpot": ["hubspot.com", "hs-scripts.com", "hbspt"],
        "Marketo": ["marketo.net", "munchkin.marketo.net"],
        "Intercom": ["intercom.io", "widget.intercom.io"],
        "Drift": ["drift.com", "js.driftt.com"],
        "Zendesk": ["zendesk.com", "zdassets.com"],
    },
    "infrastructure": {
        "AWS": ["amazonaws.com", "aws-sdk", "cloudfront.net"],
        "Azure": ["azure.com", "azureedge.net", "msecnd.net"],
        "Google Cloud": ["googleapis.com", "gstatic.com"],
        "Cloudflare": ["cloudflare.com", "cdnjs.cloudflare.com"],
        "Fastly": ["fastly.net", "fastly.com"],
    },
    "frontend": {
        "React": ["react.production.min", "reactDOM", "_reactRootContainer"],
        "Angular": ["ng-version", "angular.min.js", "ng-app"],
        "Vue.js": ["vue.min.js", "vue.runtime", "__vue__"],
        "Next.js": ["_next/static", "__NEXT_DATA__"],
        "jQuery": ["jquery.min.js", "jquery-"],
    },
    "ecommerce": {
        "Shopify": ["cdn.shopify.com", "shopify.com"],
        "Magento": ["mage/", "magento"],
        "WooCommerce": ["woocommerce", "wc-"],
        "Stripe": ["js.stripe.com", "stripe.com"],
    },
    "security": {
        "reCAPTCHA": ["recaptcha", "google.com/recaptcha"],
        "Okta": ["okta.com", "oktacdn.com"],
        "Auth0": ["auth0.com", "cdn.auth0.com"],
    },
}


# ---------------------------------------------------------------------------
# Enrichment Orchestrator
# ---------------------------------------------------------------------------

class EnrichmentOrchestrator:
    """Coordinates multi-source account enrichment.

    Usage:
        orchestrator = EnrichmentOrchestrator(db_session)
        result = await orchestrator.enrich_account(account_id)
        result = await orchestrator.enrich_batch(tenant_id, limit=50)
    """

    def __init__(
        self,
        db: AsyncSession,
        sec_edgar_base_url: str = "https://efts.sec.gov/LATEST",
        http_timeout: float = 30.0,
    ):
        self.db = db
        self.sec_edgar_base_url = sec_edgar_base_url
        self.http_timeout = http_timeout
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Lazy-init HTTP client with proper headers."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self.http_timeout,
                headers={
                    "User-Agent": "ValueFabric/1.0 (contact@valuefabric.io)",
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return self._http_client

    async def close(self) -> None:
        """Clean up HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    async def enrich_account(
        self,
        account_id: UUID,
        sources: list[EnrichmentSource] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Enrich a single account from multiple sources.

        Args:
            account_id: The account UUID to enrich.
            sources: Specific sources to use (default: all applicable).
            force: Re-enrich even if already enriched.

        Returns:
            Dict with enrichment results and status per source.
        """
        account = await self.db.get(Account, account_id)
        if account is None:
            return EnrichmentOrchestrator_enrich_accountResult.model_validate({"status": "error", "message": f"Account {account_id} not found"})

        if account.enrichment_status == EnrichmentStatus.ENRICHED and not force:
            return EnrichmentOrchestrator_enrich_accountResult.model_validate({
                "status": "skipped",
                "message": "Already enriched. Use force=True to re-enrich.",
                "enriched_at": account.enriched_at.isoformat() if account.enriched_at else None,
            })


        # Mark as in-progress
        account.enrichment_status = EnrichmentStatus.IN_PROGRESS
        await self.db.flush()

        results: dict[str, Any] = {}
        sources_used: list[str] = []
        errors: list[str] = []

        # Determine applicable sources
        if sources is None:
            sources = self._determine_sources(account)

        # Execute enrichment from each source
        for source in sources:
            try:
                source_result = await self._enrich_from_source(account, source)
                if source_result.get("success"):
                    sources_used.append(source.value)
                results[source.value] = source_result
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.error(
                    "enrichment_source_failed",
                    account_id=str(account_id),
                    source=source.value,
                    error_code="ENRICHMENT_ERROR",
                )
                errors.append(f"{source.value}: ENRICHMENT_ERROR")
                results[source.value] = {"success": False, "error": "ENRICHMENT_ERROR"}

        # Update account status
        if sources_used:
            account.enrichment_status = EnrichmentStatus.ENRICHED
            account.enriched_at = datetime.now(UTC)
            account.enrichment_sources = list(
                set((account.enrichment_sources or []) + sources_used)
            )
        elif errors:
            account.enrichment_status = EnrichmentStatus.FAILED
        else:
            account.enrichment_status = EnrichmentStatus.PENDING

        await self.db.commit()

        logger.info(
            "account_enriched",
            account_id=str(account_id),
            account_name=account.name,
            sources_used=sources_used,
            errors=errors,
        )

        return EnrichmentOrchestrator_enrich_accountResult.model_validate({
            "status": account.enrichment_status,
            "account_id": str(account_id),
            "sources_used": sources_used,
            "errors": errors,
            "results": results,
        })


    async def enrich_batch(
        self,
        tenant_id: str,
        limit: int = 50,
        force: bool = False,
    ) -> dict[str, Any]:
        """Enrich a batch of accounts for a tenant.

        Selects accounts with enrichment_status = 'pending' or 'stale'.
        """
        query = (
            select(Account.id)
            .where(Account.tenant_id == tenant_id)
            .order_by(Account.updated_at.desc())
            .limit(limit)
        )
        if not force:
            query = query.where(
                Account.enrichment_status.in_([
                    EnrichmentStatus.PENDING,
                    EnrichmentStatus.STALE,
                    EnrichmentStatus.FAILED,
                ])
            )

        result = await self.db.execute(query)
        account_ids = [row[0] for row in result.fetchall()]

        if not account_ids:
            return EnrichmentOrchestrator_enrich_batchResult.model_validate({"status": "no_accounts", "message": "No accounts need enrichment"})

        batch_results = []
        success_count = 0
        fail_count = 0

        for account_id in account_ids:
            try:
                enrichment_result = await self.enrich_account(account_id, force=force)
                batch_results.append(enrichment_result)
                if enrichment_result.get("status") == EnrichmentStatus.ENRICHED:
                    success_count += 1
                else:
                    fail_count += 1
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.error("batch_enrichment_error", account_id=str(account_id), error_code="BATCH_ENRICHMENT_ERROR")
                fail_count += 1
                batch_results.append({"account_id": str(account_id), "status": "error", "error": "BATCH_ENRICHMENT_ERROR"})

        return EnrichmentOrchestrator_enrich_batchResult.model_validate({
            "total": len(account_ids),
            "success": success_count,
            "failed": fail_count,
            "results": batch_results,
        })


    async def get_enrichment_status(self, tenant_id: str) -> dict[str, Any]:
        """Get enrichment coverage statistics for a tenant."""
        from sqlalchemy import func

        query = (
            select(
                Account.enrichment_status,
                func.count(Account.id).label("count"),
            )
            .where(Account.tenant_id == tenant_id)
            .group_by(Account.enrichment_status)
        )
        result = await self.db.execute(query)
        status_counts = {row[0]: row[1] for row in result.fetchall()}

        total = sum(status_counts.values())
        enriched = status_counts.get(EnrichmentStatus.ENRICHED, 0)

        return EnrichmentOrchestrator_get_enrichment_statusResult.model_validate({
            "total_accounts": total,
            "enriched": enriched,
            "pending": status_counts.get(EnrichmentStatus.PENDING, 0),
            "in_progress": status_counts.get(EnrichmentStatus.IN_PROGRESS, 0),
            "failed": status_counts.get(EnrichmentStatus.FAILED, 0),
            "stale": status_counts.get(EnrichmentStatus.STALE, 0),
            "coverage_pct": round((enriched / total * 100), 1) if total > 0 else 0.0,
        })


    # -------------------------------------------------------------------
    # Source Determination
    # -------------------------------------------------------------------

    def _determine_sources(self, account: Account) -> list[EnrichmentSource]:
        """Determine which enrichment sources are applicable for an account."""
        sources = []

        # SEC EDGAR: applicable for public companies (have a domain or are large enough)
        if account.annual_revenue and account.annual_revenue > 10_000_000:
            sources.append(EnrichmentSource.SEC_EDGAR)

        # Web crawl: applicable if we have a website/domain
        if account.website or account.domain:
            sources.append(EnrichmentSource.WEB_CRAWL)

        # Domain lookup: applicable if we have a domain
        if account.domain:
            sources.append(EnrichmentSource.DOMAIN_LOOKUP)

        # News scan: always applicable if we have a company name
        if account.name:
            sources.append(EnrichmentSource.NEWS_SCAN)

        # Fallback: at least try web crawl if we have any URL
        if not sources and (account.website or account.domain):
            sources.append(EnrichmentSource.WEB_CRAWL)

        return sources

    # -------------------------------------------------------------------
    # Source-Specific Enrichment
    # -------------------------------------------------------------------

    async def _enrich_from_source(
        self, account: Account, source: EnrichmentSource
    ) -> dict[str, Any]:
        """Dispatch enrichment to the appropriate source handler."""
        handlers = {
            EnrichmentSource.SEC_EDGAR: self._enrich_from_sec_edgar,
            EnrichmentSource.WEB_CRAWL: self._enrich_from_web_crawl,
            EnrichmentSource.DOMAIN_LOOKUP: self._enrich_from_domain,
            EnrichmentSource.NEWS_SCAN: self._enrich_from_news,
        }
        handler = handlers.get(source)
        if handler is None:
            return EnrichmentOrchestrator__enrich_from_sourceResult.model_validate({"success": False, "error": f"Unknown source: {source}"})
        return await handler(account)

    async def _enrich_from_sec_edgar(self, account: Account) -> dict[str, Any]:
        """Enrich account with SEC EDGAR financial data.

        Searches by company name or ticker, fetches latest 10-K filing,
        and extracts financial metrics.
        """
        client = await self._get_http_client()
        search_term = account.name.replace(",", "").replace(".", "").strip()

        try:
            # Search for company in EDGAR
            resp = await client.get(
                f"{self.sec_edgar_base_url}/search-index",
                params={
                    "q": f'"{search_term}"',
                    "dateRange": "custom",
                    "startdt": "2023-01-01",
                    "forms": "10-K",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                return EnrichmentOrchestrator__enrich_from_sec_edgarResult.model_validate({"success": False, "error": "No SEC filings found"})

            # Extract financial summary from the first hit
            filing = hits[0].get("_source", {})
            filing_date = filing.get("file_date")
            entity_name = filing.get("entity_name", "")

            # Build financial data structure
            financials = {
                "source": "sec_edgar",
                "entity_name": entity_name,
                "latest_filing_date": filing_date,
                "filing_type": "10-K",
                "fiscal_year": filing.get("period_of_report", ""),
                "retrieved_at": datetime.now(UTC).isoformat(),
            }

            # Update account
            account.financials = {
                **(account.financials or {}),
                **financials,
            }

            logger.info(
                "sec_edgar_enrichment_success",
                account_name=account.name,
                entity_name=entity_name,
                filing_date=filing_date,
            )

            return EnrichmentOrchestrator__enrich_from_sec_edgarResult.model_validate({
                "success": True,
                "source": "sec_edgar",
                "entity_name": entity_name,
                "filing_date": filing_date,
            })


        except httpx.HTTPStatusError as e:
            return EnrichmentOrchestrator__enrich_from_sec_edgarResult.model_validate({"success": False, "error": f"SEC API error: {e.response.status_code}"})
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("SEC enrichment failed", exc_info=e, extra={"entity_name": entity_name, "filing_date": filing_date})
            return EnrichmentOrchestrator__enrich_from_sec_edgarResult.model_validate({"success": False, "error": "SEC enrichment failed due to internal error"})

    async def _enrich_from_web_crawl(self, account: Account) -> dict[str, Any]:
        """Enrich account with tech stack detection via website crawl.

        Fetches the company homepage and analyzes HTML/scripts for
        technology signatures.
        """
        url = account.website or (f"https://{account.domain}" if account.domain else None)
        if not url:
            return EnrichmentOrchestrator__enrich_from_web_crawlResult.model_validate({"success": False, "error": "No website or domain available"})

        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # V-005: SSRF protection — validate URL before making outbound request
        try:
            validate_url_safe(url)
        except SSRFBlockedError as e:
            logger.warning(
                "ssrf_blocked_web_crawl",
                account_id=str(account.id),
                url=url,
                reason=repr(e),  # ban-str-e-allow: structured-log
            )
            return EnrichmentOrchestrator__enrich_from_web_crawlResult.model_validate({"success": False, "error": f"URL blocked by security policy: {e.reason}"})

        client = await self._get_http_client()

        try:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text

            # Detect tech stack from HTML content
            detected_stack = self._detect_tech_stack(html)

            if detected_stack:
                # Merge with existing tech stack (don't overwrite)
                existing = account.tech_stack or {}
                for category, techs in detected_stack.items():
                    existing_techs = existing.get(category, [])
                    merged = list(set(existing_techs + techs))
                    existing[category] = merged
                account.tech_stack = existing

            logger.info(
                "web_crawl_enrichment_success",
                account_name=account.name,
                url=url,
                technologies_found=sum(len(v) for v in detected_stack.values()),
            )

            return EnrichmentOrchestrator__enrich_from_web_crawlResult.model_validate({
                "success": True,
                "source": "web_crawl",
                "url": url,
                "tech_stack": detected_stack,
                "technologies_found": sum(len(v) for v in detected_stack.values()),
            })


        except httpx.HTTPStatusError as e:
            return EnrichmentOrchestrator__enrich_from_web_crawlResult.model_validate({"success": False, "error": f"HTTP {e.response.status_code} for {url}"})
        except httpx.ConnectError:
            return EnrichmentOrchestrator__enrich_from_web_crawlResult.model_validate({"success": False, "error": f"Connection failed for {url}"})
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Web crawl failed", exc_info=e, extra={"account_id": str(account.id), "url": url})
            return EnrichmentOrchestrator__enrich_from_web_crawlResult.model_validate({"success": False, "error": "Web crawl failed due to internal error"})

    async def _enrich_from_domain(self, account: Account) -> dict[str, Any]:
        """Enrich account with executive/leadership data from domain lookup.

        Production integration requires an Apollo/Clearbit API key.
        Fails closed unless ENRICHMENT_MOCK_MODE=true is explicitly set.
        In mock mode, returns placeholder data tagged with mock=true.
        """
        import os

        domain = account.domain
        if not domain:
            return EnrichmentOrchestrator__enrich_from_domainResult.model_validate({"success": False, "error": "No domain available"})

        mock_mode = os.environ.get("ENRICHMENT_MOCK_MODE", "").lower() == "true"

        if not mock_mode:
            logger.info(
                "domain_enrichment_not_configured",
                account_name=account.name,
                domain=domain,
                note="Set ENRICHMENT_MOCK_MODE=true for placeholder data in non-production environments",
            )
            return EnrichmentOrchestrator__enrich_from_domainResult.model_validate({
                "success": False,
                "error": "domain_enrichment_not_configured",
                "note": "Apollo/Clearbit API key required; set ENRICHMENT_MOCK_MODE=true for mock data",
            })

        # Mock mode: return placeholder data clearly tagged as mock.
        logger.info(
            "domain_enrichment_mock",
            account_name=account.name,
            domain=domain,
        )
        return EnrichmentOrchestrator__enrich_from_domainResult.model_validate({
            "success": True,
            "source": "mock",
            "mock": True,
            "domain": domain,
            "note": "Mock data — ENRICHMENT_MOCK_MODE=true",
            "executives_found": 0,
        })


    async def _enrich_from_news(self, account: Account) -> dict[str, Any]:
        """Enrich account with pain signals from news/public sources.

        Production integration requires a NewsAPI/GDELT API key.
        Fails closed unless ENRICHMENT_MOCK_MODE=true is explicitly set.
        In mock mode, returns placeholder data tagged with mock=true.
        """
        import os

        company_name = account.name
        if not company_name:
            return EnrichmentOrchestrator__enrich_from_newsResult.model_validate({"success": False, "error": "No company name available"})

        mock_mode = os.environ.get("ENRICHMENT_MOCK_MODE", "").lower() == "true"

        if not mock_mode:
            logger.info(
                "news_enrichment_not_configured",
                account_name=company_name,
                note="Set ENRICHMENT_MOCK_MODE=true for placeholder data in non-production environments",
            )
            return EnrichmentOrchestrator__enrich_from_newsResult.model_validate({
                "success": False,
                "error": "news_enrichment_not_configured",
                "note": "NewsAPI/GDELT API key required; set ENRICHMENT_MOCK_MODE=true for mock data",
            })

        # Mock mode: return placeholder data clearly tagged as mock.
        logger.info(
            "news_enrichment_mock",
            account_name=company_name,
        )
        return EnrichmentOrchestrator__enrich_from_newsResult.model_validate({
            "success": True,
            "source": "mock",
            "mock": True,
            "company_name": company_name,
            "note": "Mock data — ENRICHMENT_MOCK_MODE=true",
            "signals_found": 0,
        })


    # -------------------------------------------------------------------
    # Tech Stack Detection
    # -------------------------------------------------------------------

    def _detect_tech_stack(self, html: str) -> dict[str, list[str]]:
        """Detect technologies from HTML content using signature matching.

        Scans the HTML source for known patterns (script URLs, meta tags,
        global variables) that indicate specific technologies.

        Returns:
            Dict mapping category → list of detected technology names.
        """
        detected: dict[str, list[str]] = {}
        html_lower = html.lower()

        for category, techs in TECH_STACK_SIGNATURES.items():
            for tech_name, signatures in techs.items():
                for sig in signatures:
                    if sig.lower() in html_lower:
                        if category not in detected:
                            detected[category] = []
                        if tech_name not in detected[category]:
                            detected[category].append(tech_name)
                        break  # One match is enough for this tech

        return detected


# ---------------------------------------------------------------------------
# FastAPI Dependency
# ---------------------------------------------------------------------------

async def get_enrichment_orchestrator(db: AsyncSession) -> EnrichmentOrchestrator:
    """FastAPI dependency for enrichment orchestrator."""
    return EnrichmentOrchestrator(db)
