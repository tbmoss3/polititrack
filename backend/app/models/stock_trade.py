"""Stock trade model for financial disclosures."""

import uuid
from datetime import date, datetime
from sqlalchemy import String, Integer, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class StockTrade(Base):
    """Model representing a stock trade disclosure."""

    __tablename__ = "stock_trades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    politician_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=False
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    disclosure_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(10))
    asset_description: Mapped[str | None] = mapped_column(Text)
    transaction_type: Mapped[str | None] = mapped_column(
        String(20)
    )  # 'purchase', 'sale', 'exchange'
    amount_range: Mapped[str | None] = mapped_column(
        String(50)
    )  # e.g., "$1,001 - $15,000"
    amount_min: Mapped[int | None] = mapped_column(Integer)
    amount_max: Mapped[int | None] = mapped_column(Integer)
    filing_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    politician: Mapped["Politician"] = relationship(
        "Politician", back_populates="stock_trades"
    )

    __table_args__ = (
        Index("idx_stock_trades_politician", "politician_id"),
        Index("idx_stock_trades_date", "transaction_date"),
        Index("idx_stock_trades_ticker", "ticker"),
    )

    @property
    def disclosure_delay_days(self) -> int:
        """Calculate days between transaction and disclosure."""
        return (self.disclosure_date - self.transaction_date).days

    @property
    def amount_midpoint(self) -> int | None:
        """Estimate midpoint of amount range."""
        if self.amount_min is not None and self.amount_max is not None:
            return (self.amount_min + self.amount_max) // 2
        return None

    def __repr__(self) -> str:
        return f"<StockTrade {self.ticker or 'N/A'}: {self.transaction_type} {self.amount_range}>"
