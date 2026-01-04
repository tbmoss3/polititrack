"""Pydantic schemas for finance endpoints."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class CampaignFinanceBase(BaseModel):
    """Base schema for campaign finance data."""

    cycle: int = Field(..., description="Election cycle year, e.g., 2024")
    total_raised: Decimal | None = None
    total_spent: Decimal | None = None
    cash_on_hand: Decimal | None = None
    total_from_pacs: Decimal | None = None
    total_from_individuals: Decimal | None = None
    last_filed: date | None = None


class CampaignFinanceResponse(CampaignFinanceBase):
    """Schema for campaign finance response."""

    id: UUID
    politician_id: UUID
    pac_percentage: float | None = Field(None, description="Percentage of funds from PACs")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignFinanceListResponse(BaseModel):
    """Schema for campaign finance list (multiple cycles)."""

    items: list[CampaignFinanceResponse]
    total_raised_all_cycles: Decimal | None = None
    total_spent_all_cycles: Decimal | None = None


class TopDonorBase(BaseModel):
    """Base schema for top donor data."""

    donor_name: str
    donor_type: str | None = Field(None, description="'individual', 'pac', or 'organization'")
    total_amount: Decimal | None = None


class TopDonorResponse(TopDonorBase):
    """Schema for top donor response."""

    id: UUID
    politician_id: UUID
    cycle: int
    created_at: datetime

    class Config:
        from_attributes = True


class TopDonorListResponse(BaseModel):
    """Schema for top donors list."""

    items: list[TopDonorResponse]
    cycle: int
    total: int


class FinanceSummary(BaseModel):
    """Aggregated financial summary for a politician."""

    current_cycle: int
    total_raised: Decimal | None = None
    total_spent: Decimal | None = None
    cash_on_hand: Decimal | None = None
    pac_percentage: float | None = None
    individual_percentage: float | None = None
    top_donors: list[TopDonorResponse] = []
    historical_fundraising: list[CampaignFinanceResponse] = []
