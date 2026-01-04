"""Campaign finance models."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, Date, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class CampaignFinance(Base):
    """Model representing campaign finance data for an election cycle."""

    __tablename__ = "campaign_finance"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    politician_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=False
    )
    cycle: Mapped[int] = mapped_column(Integer, nullable=False)  # Election cycle (e.g., 2024)
    total_raised: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_spent: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    cash_on_hand: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_from_pacs: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_from_individuals: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    last_filed: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    politician: Mapped["Politician"] = relationship(
        "Politician", back_populates="campaign_finances"
    )

    __table_args__ = (
        UniqueConstraint("politician_id", "cycle", name="uq_campaign_finance_politician_cycle"),
        Index("idx_campaign_finance_politician", "politician_id"),
        Index("idx_campaign_finance_cycle", "cycle"),
    )

    @property
    def pac_percentage(self) -> float | None:
        """Calculate percentage of funds from PACs."""
        if self.total_raised and self.total_from_pacs:
            return float(self.total_from_pacs / self.total_raised * 100)
        return None

    def __repr__(self) -> str:
        return f"<CampaignFinance {self.cycle}: ${self.total_raised:,.2f}>"


class TopDonor(Base):
    """Model representing aggregated top donor data."""

    __tablename__ = "top_donors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    politician_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=False
    )
    cycle: Mapped[int] = mapped_column(Integer, nullable=False)
    donor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    donor_type: Mapped[str | None] = mapped_column(
        String(50)
    )  # 'individual', 'pac', 'organization'
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    politician: Mapped["Politician"] = relationship(
        "Politician", back_populates="top_donors"
    )

    __table_args__ = (
        UniqueConstraint(
            "politician_id", "cycle", "donor_name", name="uq_top_donor_politician_cycle_name"
        ),
        Index("idx_top_donors_politician", "politician_id"),
    )

    def __repr__(self) -> str:
        return f"<TopDonor {self.donor_name}: ${self.total_amount:,.2f}>"
