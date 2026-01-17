"""Conflict of interest model for detecting potential conflicts."""

import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, DateTime, Date, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ConflictOfInterest(Base):
    """Model representing a potential conflict of interest.

    Detected when a politician votes on bills that may affect
    companies they hold stock in.
    """

    __tablename__ = "conflicts_of_interest"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    politician_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=False
    )
    stock_trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stock_trades.id"), nullable=False
    )
    vote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("votes.id")
    )
    bill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id")
    )

    # Conflict details
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(100))

    # Timing
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    vote_date: Mapped[date | None] = mapped_column(Date)
    days_between: Mapped[int | None] = mapped_column()  # Days between trade and vote

    # Severity scoring
    severity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # 0-100
    reason: Mapped[str] = mapped_column(Text, nullable=False)  # Why this is flagged

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="detected"
    )  # 'detected', 'reviewed', 'dismissed', 'confirmed'

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    politician: Mapped["Politician"] = relationship("Politician")
    stock_trade: Mapped["StockTrade"] = relationship("StockTrade")
    vote: Mapped["Vote"] = relationship("Vote")
    bill: Mapped["Bill"] = relationship("Bill")

    __table_args__ = (
        Index("idx_conflicts_politician", "politician_id"),
        Index("idx_conflicts_ticker", "ticker"),
        Index("idx_conflicts_severity", "severity_score"),
        Index("idx_conflicts_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ConflictOfInterest {self.ticker} - {self.politician_id}>"


# Mapping of stock tickers to sectors for conflict detection
SECTOR_KEYWORDS = {
    "healthcare": ["health", "medical", "pharmaceutical", "drug", "medicare", "medicaid", "hospital"],
    "technology": ["tech", "software", "data", "cyber", "internet", "digital", "ai", "artificial intelligence"],
    "energy": ["energy", "oil", "gas", "petroleum", "renewable", "solar", "wind", "nuclear", "coal"],
    "defense": ["defense", "military", "armed forces", "pentagon", "weapons", "security"],
    "finance": ["bank", "financial", "wall street", "securities", "insurance", "mortgage"],
    "agriculture": ["farm", "agriculture", "food", "crop", "livestock"],
    "telecommunications": ["telecom", "broadband", "5g", "wireless", "spectrum"],
    "transportation": ["transport", "airline", "railroad", "highway", "infrastructure"],
    "real_estate": ["housing", "real estate", "construction", "property"],
    "retail": ["retail", "consumer", "commerce", "trade"],
}

# Common ticker to sector mappings
TICKER_SECTORS = {
    # Healthcare
    "JNJ": "healthcare", "PFE": "healthcare", "UNH": "healthcare", "ABBV": "healthcare",
    "MRK": "healthcare", "LLY": "healthcare", "TMO": "healthcare", "ABT": "healthcare",
    # Technology
    "AAPL": "technology", "MSFT": "technology", "GOOGL": "technology", "AMZN": "technology",
    "META": "technology", "NVDA": "technology", "TSLA": "technology", "AMD": "technology",
    # Energy
    "XOM": "energy", "CVX": "energy", "COP": "energy", "SLB": "energy",
    "NEE": "energy", "DUK": "energy", "SO": "energy",
    # Defense
    "LMT": "defense", "RTX": "defense", "NOC": "defense", "GD": "defense", "BA": "defense",
    # Finance
    "JPM": "finance", "BAC": "finance", "WFC": "finance", "GS": "finance",
    "MS": "finance", "C": "finance", "BLK": "finance",
    # Telecommunications
    "VZ": "telecommunications", "T": "telecommunications", "TMUS": "telecommunications",
}
