"""Activity feed service for recent congressional activity."""

import logging
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import select, union_all, literal, func
from sqlalchemy.orm import Session

from app.models import Vote, Bill, StockTrade, CampaignFinance, Politician

logger = logging.getLogger(__name__)

ActivityType = Literal["vote", "trade", "bill", "finance"]


@dataclass
class ActivityItem:
    """A single item in the activity feed."""

    id: UUID
    activity_type: ActivityType
    title: str
    description: str
    politician_id: UUID | None
    politician_name: str | None
    party: str | None
    state: str | None
    timestamp: datetime
    metadata: dict


def get_recent_activity(
    db: Session,
    limit: int = 50,
    days: int = 7,
    activity_types: list[ActivityType] | None = None,
    state: str | None = None,
    party: str | None = None,
) -> list[ActivityItem]:
    """
    Get recent activity across all activity types.

    Args:
        db: Database session
        limit: Maximum number of items to return
        days: Number of days to look back
        activity_types: Filter to specific types (vote, trade, bill, finance)
        state: Filter to specific state
        party: Filter to specific party

    Returns:
        List of ActivityItem objects sorted by timestamp (newest first)
    """
    if activity_types is None:
        activity_types = ["vote", "trade", "bill"]

    cutoff_date = datetime.utcnow() - timedelta(days=days)
    activities = []

    # Get recent votes
    if "vote" in activity_types:
        votes = _get_recent_votes(db, cutoff_date, limit, state, party)
        activities.extend(votes)

    # Get recent stock trades
    if "trade" in activity_types:
        trades = _get_recent_trades(db, cutoff_date, limit, state, party)
        activities.extend(trades)

    # Get recent bills
    if "bill" in activity_types:
        bills = _get_recent_bills(db, cutoff_date, limit)
        activities.extend(bills)

    # Sort by timestamp and limit
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    return activities[:limit]


def _get_recent_votes(
    db: Session,
    cutoff_date: datetime,
    limit: int,
    state: str | None = None,
    party: str | None = None,
) -> list[ActivityItem]:
    """Get recent vote activity."""
    query = (
        select(Vote, Politician)
        .join(Politician)
        .where(Vote.vote_date >= cutoff_date.date())
        .order_by(Vote.vote_date.desc())
        .limit(limit)
    )

    if state:
        query = query.where(Politician.state == state)
    if party:
        query = query.where(Politician.party == party)

    results = db.execute(query).all()

    activities = []
    for vote, politician in results:
        bill_title = vote.bill.title[:100] if vote.bill else vote.question or "Unknown bill"
        activities.append(
            ActivityItem(
                id=vote.id,
                activity_type="vote",
                title=f"{politician.full_name} voted {vote.vote_position.upper()}",
                description=bill_title,
                politician_id=politician.id,
                politician_name=politician.full_name,
                party=politician.party,
                state=politician.state,
                timestamp=datetime.combine(vote.vote_date, datetime.min.time()),
                metadata={
                    "vote_position": vote.vote_position,
                    "result": vote.result,
                    "chamber": vote.chamber,
                    "bill_id": str(vote.bill_id) if vote.bill_id else None,
                },
            )
        )

    return activities


def _get_recent_trades(
    db: Session,
    cutoff_date: datetime,
    limit: int,
    state: str | None = None,
    party: str | None = None,
) -> list[ActivityItem]:
    """Get recent stock trade activity."""
    query = (
        select(StockTrade, Politician)
        .join(Politician)
        .where(StockTrade.disclosure_date >= cutoff_date.date())
        .order_by(StockTrade.disclosure_date.desc())
        .limit(limit)
    )

    if state:
        query = query.where(Politician.state == state)
    if party:
        query = query.where(Politician.party == party)

    results = db.execute(query).all()

    activities = []
    for trade, politician in results:
        action = "purchased" if trade.transaction_type == "purchase" else "sold"
        ticker_display = trade.ticker or trade.asset_description or "Unknown asset"

        activities.append(
            ActivityItem(
                id=trade.id,
                activity_type="trade",
                title=f"{politician.full_name} {action} {ticker_display}",
                description=f"{trade.amount_range or 'Undisclosed amount'} - Disclosed {trade.disclosure_delay_days or 0} days after transaction",
                politician_id=politician.id,
                politician_name=politician.full_name,
                party=politician.party,
                state=politician.state,
                timestamp=datetime.combine(trade.disclosure_date, datetime.min.time()) if trade.disclosure_date else trade.created_at,
                metadata={
                    "ticker": trade.ticker,
                    "transaction_type": trade.transaction_type,
                    "amount_range": trade.amount_range,
                    "disclosure_delay_days": trade.disclosure_delay_days,
                },
            )
        )

    return activities


def _get_recent_bills(
    db: Session,
    cutoff_date: datetime,
    limit: int,
) -> list[ActivityItem]:
    """Get recent bill activity."""
    query = (
        select(Bill, Politician)
        .outerjoin(Politician, Bill.sponsor_id == Politician.id)
        .where(Bill.latest_action_date >= cutoff_date.date())
        .order_by(Bill.latest_action_date.desc())
        .limit(limit)
    )

    results = db.execute(query).all()

    activities = []
    for bill, sponsor in results:
        sponsor_text = f"Sponsored by {sponsor.full_name}" if sponsor else "No sponsor"

        activities.append(
            ActivityItem(
                id=bill.id,
                activity_type="bill",
                title=bill.title[:100] if bill.title else bill.bill_id,
                description=f"{sponsor_text} - {bill.latest_action or 'No recent action'}",
                politician_id=sponsor.id if sponsor else None,
                politician_name=sponsor.full_name if sponsor else None,
                party=sponsor.party if sponsor else None,
                state=sponsor.state if sponsor else None,
                timestamp=datetime.combine(bill.latest_action_date, datetime.min.time()) if bill.latest_action_date else bill.created_at,
                metadata={
                    "bill_id": bill.bill_id,
                    "congress": bill.congress,
                    "latest_action": bill.latest_action,
                },
            )
        )

    return activities


def get_politician_activity(
    db: Session,
    politician_id: UUID,
    limit: int = 20,
    days: int = 30,
) -> list[ActivityItem]:
    """Get recent activity for a specific politician."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    activities = []

    # Recent votes
    votes = db.execute(
        select(Vote)
        .where(
            Vote.politician_id == politician_id,
            Vote.vote_date >= cutoff_date.date(),
        )
        .order_by(Vote.vote_date.desc())
        .limit(limit)
    ).scalars().all()

    politician = db.get(Politician, politician_id)
    if not politician:
        return []

    for vote in votes:
        bill_title = vote.bill.title[:100] if vote.bill else vote.question or "Unknown"
        activities.append(
            ActivityItem(
                id=vote.id,
                activity_type="vote",
                title=f"Voted {vote.vote_position.upper()}",
                description=bill_title,
                politician_id=politician_id,
                politician_name=politician.full_name,
                party=politician.party,
                state=politician.state,
                timestamp=datetime.combine(vote.vote_date, datetime.min.time()),
                metadata={"vote_position": vote.vote_position, "result": vote.result},
            )
        )

    # Recent trades
    trades = db.execute(
        select(StockTrade)
        .where(
            StockTrade.politician_id == politician_id,
            StockTrade.disclosure_date >= cutoff_date.date(),
        )
        .order_by(StockTrade.disclosure_date.desc())
        .limit(limit)
    ).scalars().all()

    for trade in trades:
        action = "Purchased" if trade.transaction_type == "purchase" else "Sold"
        activities.append(
            ActivityItem(
                id=trade.id,
                activity_type="trade",
                title=f"{action} {trade.ticker or 'asset'}",
                description=trade.amount_range or "Undisclosed amount",
                politician_id=politician_id,
                politician_name=politician.full_name,
                party=politician.party,
                state=politician.state,
                timestamp=datetime.combine(trade.disclosure_date, datetime.min.time()) if trade.disclosure_date else trade.created_at,
                metadata={"ticker": trade.ticker, "amount_range": trade.amount_range},
            )
        )

    # Sort and limit
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    return activities[:limit]
