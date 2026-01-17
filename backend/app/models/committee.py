"""Committee model for congressional committees."""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Committee(Base):
    """Model representing a congressional committee."""

    __tablename__ = "committees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    committee_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )  # e.g., "HSAG" for House Agriculture
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    chamber: Mapped[str] = mapped_column(String(10), nullable=False)  # 'house' or 'senate'
    committee_type: Mapped[str] = mapped_column(String(50), default="standing")  # standing, select, joint
    url: Mapped[str | None] = mapped_column(String(255))
    jurisdiction: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    assignments: Mapped[list["CommitteeAssignment"]] = relationship(
        "CommitteeAssignment", back_populates="committee", lazy="dynamic"
    )

    __table_args__ = (
        Index("idx_committees_chamber", "chamber"),
    )

    def __repr__(self) -> str:
        return f"<Committee {self.committee_code}: {self.name}>"


class CommitteeAssignment(Base):
    """Model representing a politician's assignment to a committee."""

    __tablename__ = "committee_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    politician_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=False
    )
    committee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("committees.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), default="member")  # chair, ranking_member, member
    is_subcommittee: Mapped[bool] = mapped_column(Boolean, default=False)
    subcommittee_name: Mapped[str | None] = mapped_column(String(255))
    congress: Mapped[int | None] = mapped_column()  # Which congress session
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    politician: Mapped["Politician"] = relationship("Politician", backref="committee_assignments")
    committee: Mapped["Committee"] = relationship("Committee", back_populates="assignments")

    __table_args__ = (
        Index("idx_committee_assignments_politician", "politician_id"),
        Index("idx_committee_assignments_committee", "committee_id"),
    )

    def __repr__(self) -> str:
        return f"<CommitteeAssignment {self.politician_id} -> {self.committee_id}>"
