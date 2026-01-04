"""Pydantic schemas for stock trade endpoints."""

from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field


class StockTradeBase(BaseModel):
    """Base schema for stock trade data."""

    transaction_date: date
    disclosure_date: date
    ticker: str | None = None
    asset_description: str | None = None
    transaction_type: str | None = Field(None, description="'purchase', 'sale', or 'exchange'")
    amount_range: str | None = Field(None, description="e.g., '$1,001 - $15,000'")
    amount_min: int | None = None
    amount_max: int | None = None
    filing_url: str | None = None


class StockTradeCreate(StockTradeBase):
    """Schema for creating a stock trade record."""

    politician_id: UUID


class StockTradeResponse(StockTradeBase):
    """Schema for stock trade response."""

    id: UUID
    politician_id: UUID
    disclosure_delay_days: int = Field(..., description="Days between transaction and disclosure")
    amount_midpoint: int | None = Field(None, description="Estimated midpoint of amount range")
    created_at: datetime

    class Config:
        from_attributes = True


class StockTradeListResponse(BaseModel):
    """Schema for paginated stock trade list."""

    items: list[StockTradeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class StockTradeSummary(BaseModel):
    """Summary of politician's stock trading activity."""

    total_trades: int
    total_purchases: int
    total_sales: int
    avg_disclosure_delay_days: float
    most_traded_tickers: list[str]
    estimated_total_value_min: int | None = None
    estimated_total_value_max: int | None = None


class NetWorthTrend(BaseModel):
    """Data point for net worth trend visualization."""

    date: date
    estimated_min: int
    estimated_max: int
    cumulative_trades: int


class StockTradeAnalysis(BaseModel):
    """Full stock trade analysis for a politician."""

    summary: StockTradeSummary
    net_worth_trend: list[NetWorthTrend]
    recent_trades: list[StockTradeResponse]
    disclosure_compliance_score: float = Field(..., description="0-100 score based on disclosure timeliness")
