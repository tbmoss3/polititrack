"""Bill model for legislation."""

import uuid
from datetime import date, datetime
from sqlalchemy import String, Integer, Text, Date, DateTime, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Bill(Base):
    """Model representing a piece of legislation."""

    __tablename__ = "bills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bill_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )  # e.g., "hr1234-118"
    congress: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary_official: Mapped[str | None] = mapped_column(Text)
    summary_ai: Mapped[str | None] = mapped_column(Text)  # 2-sentence AI summary
    sponsor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("politicians.id")
    )
    introduced_date: Mapped[date | None] = mapped_column(Date)
    latest_action: Mapped[str | None] = mapped_column(Text)
    latest_action_date: Mapped[date | None] = mapped_column(Date)
    subjects: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    sponsor: Mapped["Politician"] = relationship(
        "Politician", back_populates="sponsored_bills"
    )
    votes: Mapped[list["Vote"]] = relationship(
        "Vote", back_populates="bill", lazy="dynamic"
    )

    @property
    def bill_type(self) -> str:
        """Extract bill type (hr, s, hjres, sjres, etc.)."""
        return self.bill_id.split("-")[0].rstrip("0123456789")

    @property
    def bill_number(self) -> str:
        """Extract bill number."""
        parts = self.bill_id.split("-")
        return "".join(filter(str.isdigit, parts[0]))

    def __repr__(self) -> str:
        return f"<Bill {self.bill_id}: {self.title[:50]}...>"
