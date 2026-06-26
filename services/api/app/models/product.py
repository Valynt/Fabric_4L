from __future__ import annotations

from pydantic import BaseModel, Field


class ValueDriversMapRequest(BaseModel):
    account_id: str | None = Field(None, description="Optional account context")
    context: str = Field(..., min_length=1, description="Business context to map drivers from")
    industry: str | None = Field(None, description="Industry segment")


class ValueModelGenerateRequest(BaseModel):
    account_id: str | None = Field(None, description="Optional account context")
    drivers: list[str] = Field(default_factory=list, description="Value drivers to model")
    assumptions: dict | None = Field(None, description="Key assumptions")


class ValueModelValidateRequest(BaseModel):
    account_id: str | None = Field(None, description="Optional account context")
    value_model: dict = Field(..., description="Value model to validate")


class ValueModelQARequest(BaseModel):
    account_id: str | None = Field(None, description="Optional account context")
    value_model: dict = Field(..., description="Value model to question/answer")
    question: str = Field(..., min_length=1, description="Question about the model")


class AssumptionScoreRequest(BaseModel):
    account_id: str | None = Field(None, description="Optional account context")
    assumption: str = Field(..., min_length=1, description="Assumption text")
    evidence: list[str] = Field(default_factory=list, description="Supporting evidence")


class EvidenceExtractRequest(BaseModel):
    account_id: str | None = Field(None, description="Optional account context")
    source_text: str = Field(..., min_length=1, description="Text to extract value signals from")


class CFONarrativeGenerateRequest(BaseModel):
    account_id: str | None = Field(None, description="Optional account context")
    value_model: dict = Field(..., description="Value model to narrate")
    audience: str = Field(default="cfo", description="Target audience")


class RealizationCompareRequest(BaseModel):
    account_id: str | None = Field(None, description="Optional account context")
    plan_id: str | None = Field(None, description="Realization plan identifier")
    actuals: dict | None = Field(None, description="Actual outcome data")


class ProductJobResponse(BaseModel):
    job_id: str
    product_code: str
    status: str = "accepted"
    result: dict | None = None
