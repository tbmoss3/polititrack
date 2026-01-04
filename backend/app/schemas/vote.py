"""Pydantic schemas for vote endpoints."""

from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field


class VoteBase(BaseModel):
    """Base schema for vote data."""

    vote_id: str
    vote_position: str = Field(..., description="'yes', 'no', 'not_voting', or 'present'")
    vote_date: date
    chamber: str
    question: str | None = None
    result: str | None = None


class VoteCreate(VoteBase):
    """Schema for creating a vote record."""

    bill_id: UUID | None = None
    politician_id: UUID


class VoteResponse(VoteBase):
    """Schema for vote response."""

    id: UUID
    bill_id: UUID | None = None
    politician_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class VoteBillInfo(BaseModel):
    """Embedded bill information for vote detail."""

    id: UUID
    bill_id: str
    title: str
    summary_ai: str | None = None

    class Config:
        from_attributes = True


class VoteDetailResponse(VoteResponse):
    """Extended vote response with bill details."""

    bill: VoteBillInfo | None = None

    class Config:
        from_attributes = True


class VoteListResponse(BaseModel):
    """Schema for paginated vote list."""

    items: list[VoteDetailResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VotingSummary(BaseModel):
    """Summary of politician's voting record."""

    total_votes: int
    yes_votes: int
    no_votes: int
    not_voting: int
    present: int
    participation_rate: float = Field(..., description="Percentage of votes where politician voted yes/no")
