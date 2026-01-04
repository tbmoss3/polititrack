"""Pydantic schemas for bill endpoints."""

from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field


class BillBase(BaseModel):
    """Base schema for bill data."""

    bill_id: str = Field(..., description="Bill identifier, e.g., 'hr1234-118'")
    congress: int = Field(..., description="Congress number, e.g., 118")
    title: str
    summary_official: str | None = None
    introduced_date: date | None = None
    latest_action: str | None = None
    latest_action_date: date | None = None
    subjects: list[str] | None = None


class BillCreate(BillBase):
    """Schema for creating a bill."""

    sponsor_id: UUID | None = None


class BillResponse(BillBase):
    """Schema for bill response."""

    id: UUID
    sponsor_id: UUID | None = None
    summary_ai: str | None = Field(None, description="2-sentence AI-generated plain English summary")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BillSponsorInfo(BaseModel):
    """Embedded sponsor information for bill detail."""

    id: UUID
    full_name: str
    party: str | None
    state: str
    chamber: str

    class Config:
        from_attributes = True


class BillDetailResponse(BillResponse):
    """Extended bill response with sponsor details."""

    sponsor: BillSponsorInfo | None = None
    total_votes: int = 0
    vote_result: str | None = None

    class Config:
        from_attributes = True


class BillListResponse(BaseModel):
    """Schema for paginated bill list."""

    items: list[BillResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
