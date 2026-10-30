"""Pydantic schemas used as output_schema for the formatter agents."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class IntentExtractionResult(BaseModel):
    country: Optional[str] = Field(default=None, description="Target country, e.g. 'Thailand'")
    industry: Optional[str] = Field(default=None, description="Target industry, e.g. 'fintech'")
    stage: Literal["pattern_discovery", "lead_generation", "follow_up", "chitchat"] = Field(
        description="What the user wants to do next"
    )
    reasoning: str = Field(description="One short sentence explaining the decision")


class Company(BaseModel):
    company_name: str
    country_of_origin: str
    investment_type: str = Field(description="e.g. new office, acquisition, JV")
    investment_date: str = Field(description="e.g. 2025-Q2")
    source_url: str
    business_description: str


class CompanyList(BaseModel):
    companies: List[Company]


class ValidationResult(BaseModel):
    company_name: str
    is_valid: bool
    reasoning: str


class ResearchFindings(BaseModel):
    summary: str = Field(description="Summary of the signals found")
    sources: List[str] = Field(description="Source URLs backing the summary")


class Lead(BaseModel):
    company_name: str
    country_of_origin: str
    business_description: str


class LeadList(BaseModel):
    leads: List[Lead]
