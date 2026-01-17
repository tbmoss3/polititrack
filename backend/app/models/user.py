"""User models for tracking, alerts, and preferences."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Index, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class User(Base):
    """Model representing a user of the platform."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_frequency: Mapped[str] = mapped_column(
        String(20), default="weekly"
    )  # 'immediate', 'daily', 'weekly', 'none'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    followed_politicians: Mapped[list["UserFollowPolitician"]] = relationship(
        "UserFollowPolitician", back_populates="user", lazy="dynamic"
    )
    followed_bills: Mapped[list["UserFollowBill"]] = relationship(
        "UserFollowBill", back_populates="user", lazy="dynamic"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="user", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserFollowPolitician(Base):
    """Model for tracking which politicians a user follows."""

    __tablename__ = "user_follow_politicians"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    politician_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("politicians.id"), nullable=False
    )
    notify_votes: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_trades: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_finance: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="followed_politicians")
    politician: Mapped["Politician"] = relationship("Politician")

    __table_args__ = (
        Index("idx_user_follow_politicians_user", "user_id"),
        Index("idx_user_follow_politicians_politician", "politician_id"),
    )


class UserFollowBill(Base):
    """Model for tracking which bills a user follows."""

    __tablename__ = "user_follow_bills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id"), nullable=False
    )
    notify_votes: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="followed_bills")
    bill: Mapped["Bill"] = relationship("Bill")

    __table_args__ = (
        Index("idx_user_follow_bills_user", "user_id"),
        Index("idx_user_follow_bills_bill", "bill_id"),
    )


class Alert(Base):
    """Model for storing user alerts/notifications."""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    alert_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'vote', 'trade', 'bill_status', 'conflict'
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50))  # 'politician', 'bill', 'vote'
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_emailed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="alerts")

    __table_args__ = (
        Index("idx_alerts_user", "user_id"),
        Index("idx_alerts_created", "created_at"),
        Index("idx_alerts_unread", "user_id", "is_read"),
    )

    def __repr__(self) -> str:
        return f"<Alert {self.alert_type}: {self.title[:30]}>"
