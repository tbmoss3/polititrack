"""Politician model for Congress members."""

import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, Integer, Numeric, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Politician(Base):
    """Model representing a Congress member (Senator or Representative)."""

    __tablename__ = "politicians"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bioguide_id: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    party: Mapped[str | None] = mapped_column(String(50))
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    district: Mapped[int | None] = mapped_column(Integer)  # NULL for Senators
    chamber: Mapped[str] = mapped_column(String(10), nullable=False)  # 'house' or 'senate'
    in_office: Mapped[bool] = mapped_column(Boolean, default=True)
    twitter_handle: Mapped[str | None] = mapped_column(String(50))
    website_url: Mapped[str | None] = mapped_column(String(255))
    photo_url: Mapped[str | None] = mapped_column(String(255))
    transparency_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    sponsored_bills: Mapped[list["Bill"]] = relationship(
        "Bill", back_populates="sponsor", lazy="dynamic"
    )
    votes: Mapped[list["Vote"]] = relationship(
        "Vote", back_populates="politician", lazy="dynamic"
    )
    campaign_finances: Mapped[list["CampaignFinance"]] = relationship(
        "CampaignFinance", back_populates="politician", lazy="dynamic"
    )
    stock_trades: Mapped[list["StockTrade"]] = relationship(
        "StockTrade", back_populates="politician", lazy="dynamic"
    )
    top_donors: Mapped[list["TopDonor"]] = relationship(
        "TopDonor", back_populates="politician", lazy="dynamic"
    )

    __table_args__ = (
        Index("idx_politicians_state", "state"),
        Index("idx_politicians_chamber", "chamber"),
        Index("idx_politicians_party", "party"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def title(self) -> str:
        if self.chamber == "senate":
            return "Senator"
        return "Representative"

    def __repr__(self) -> str:
        return f"<Politician {self.full_name} ({self.party}-{self.state})>"
