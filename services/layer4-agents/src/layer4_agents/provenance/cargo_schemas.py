from __future__ import annotations

"""
Vendor-Specific Schemas (Anti-Corruption Layer) for Cargo.

These models strictly define the payload shape expected from the Cargo API.
Validating against these prevents downstream failures if the vendor changes their contract.
"""

from typing import Any
from pydantic import BaseModel, Field


class CargoRawCompetitor(BaseModel):
    name: str
    domain: str | None = None
    linkedinUrl: str | None = None


class CargoRawEnrichment(BaseModel):
    id: str | None = None
    uuid: str | None = None
    name: str | None = None
    companyDomain: str | None = Field(None, alias="domain")
    industry: str | None = None
    linkedinIndustry: str | None = None
    sub_industry: str | None = None
    employeesCount: int | str | None = None
    employee_count: int | str | None = None
    employee_range: str | None = None
    annual_revenue_usd: float | str | None = None
    revenue: float | str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postalCode: str | None = None
    description: str | None = None
    linkedinUrl: str | None = None
    crunchbaseUrl: str | None = None
    ownership: str | None = None
    foundedYear: int | str | None = None
    founding_year: int | str | None = None
    followersCount: int | str | None = None
    technologies: list[str] | dict[str, list[str]] | None = None
    source: str | None = None
    
    # Funding Signals
    lastFundingRoundAmount: float | str | None = None
    lastFundingRoundDate: str | None = None
    lastFundingRoundType: str | None = None
    
    # Nested lists
    competitors: list[CargoRawCompetitor] | None = None


class CargoRawStakeholder(BaseModel):
    firstName: str | None = None
    first_name: str | None = None
    lastName: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    title: str | None = None
    job_title: str | None = None
    linkedinUrl: str | None = None
    profile_url: str | None = None
    about: str | None = None
    joined_at: str | None = None
    recently_hired: bool | None = False
    tenure_months: int | None = None
    work_email: str | None = None
    email: str | None = None
    companyLinkedinId: str | None = None


class CargoRawSignal(BaseModel):
    id: str | None = None
    category: str | None = None
    signal_category: str | None = None
    type: str | None = None
    signal_type: str | None = None
    headline: str | None = None
    title: str | None = None
    description: str | None = None
    confidence: float | str | None = None
    source: str | None = None
    source_url: str | None = None
    metadata: dict[str, Any] | None = None


class CargoRawStakeholdersResponse(BaseModel):
    stakeholders: list[CargoRawStakeholder]


class CargoRawCompetitorsResponse(BaseModel):
    competitors: list[CargoRawCompetitor]
