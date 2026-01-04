"""Pydantic schemas for politician endpoints."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class PoliticianBase(BaseModel):
    """Base schema for politician data."""

    bioguide_id: str = Field(..., description="Official Congress bioguide ID")
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    party: str | None = Field(None, description="Party affiliation: D, R, or I")
    state: str = Field(..., min_length=2, max_length=2, description="Two-letter state code")
    district: int | None = Field(None, description="Congressional district (null for Senators)")
    chamber: str = Field(..., description="'house' or 'senate'")
    in_office: bool = True
    twitter_handle: str | None = None
    website_url: str | None = None
    photo_url: str | None = None


class PoliticianCreate(PoliticianBase):
    """Schema for creating a politician."""
    pass


class PoliticianUpdate(BaseModel):
    """Schema for updating a politician (all fields optional)."""

    first_name: str | None = None
    last_name: str | None = None
    party: str | None = None
    in_office: bool | None = None
    twitter_handle: str | None = None
    website_url: str | None = None
    photo_url: str | None = None
    transparency_score: Decimal | None = None


class PoliticianResponse(PoliticianBase):
    """Schema for politician response."""

    id: UUID
    transparency_score: Decimal | None = None
    created_at: datetime
    updated_at: datetime

    # Computed properties
    full_name: str
    title: str

    class Config:
        from_attributes = True


class PoliticianListResponse(BaseModel):
    """Schema for paginated politician list."""

    items: list[PoliticianResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransparencyBreakdown(BaseModel):
    """Schema for transparency score breakdown."""

    financial_disclosure: float = Field(..., description="Points from financial disclosure timeliness (0-30)")
    stock_disclosure: float = Field(..., description="Points from stock trade disclosure speed (0-30)")
    vote_participation: float = Field(..., description="Points from voting participation rate (0-20)")
    campaign_finance: float = Field(..., description="Points from campaign finance compliance (0-20)")
    total_score: float = Field(..., description="Total transparency score (0-100)")


class PoliticianDetailResponse(PoliticianResponse):
    """Extended politician response with aggregated stats."""

    transparency_breakdown: TransparencyBreakdown | None = None
    total_votes: int = 0
    total_bills_sponsored: int = 0
    vote_participation_rate: float | None = None
    latest_stock_trade_date: datetime | None = None
    total_stock_trades: int = 0

    class Config:
        from_attributes = True
