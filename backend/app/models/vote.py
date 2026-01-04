"""Vote model for voting records."""

import uuid
from datetime import date, datetime
from sqlalchemy import String, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Vote(Base):
    """Model representing a politician's vote on a bill or resolution."""

    __tablename__ = "votes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vote_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    bill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id")
    )
    politician_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=False
    )
    vote_position: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'yes', 'no', 'not_voting', 'present'
    vote_date: Mapped[date] = mapped_column(Date, nullable=False)
    chamber: Mapped[str] = mapped_column(String(10), nullable=False)
    question: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    bill: Mapped["Bill"] = relationship("Bill", back_populates="votes")
    politician: Mapped["Politician"] = relationship("Politician", back_populates="votes")

    __table_args__ = (
        Index("idx_votes_politician", "politician_id"),
        Index("idx_votes_date", "vote_date"),
        Index("idx_votes_bill", "bill_id"),
    )

    def __repr__(self) -> str:
        return f"<Vote {self.vote_id}: {self.vote_position}>"
