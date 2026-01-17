"""Conflict of interest detection service."""

import logging
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from app.models import (
    Politician,
    Vote,
    Bill,
    StockTrade,
    ConflictOfInterest,
    SECTOR_KEYWORDS,
    TICKER_SECTORS,
)

logger = logging.getLogger(__name__)

# Time window for detecting conflicts (days before/after trade)
CONFLICT_WINDOW_DAYS = 90


def detect_conflicts_for_politician(
    db: Session,
    politician_id: UUID,
    window_days: int = CONFLICT_WINDOW_DAYS,
) -> list[ConflictOfInterest]:
    """
    Detect potential conflicts of interest for a politician.

    Looks for votes on bills that may affect companies the politician
    holds stock in, within a time window around the trade date.

    Args:
        db: Database session
        politician_id: Politician's UUID
        window_days: Number of days before/after trade to check for related votes

    Returns:
        List of detected ConflictOfInterest objects
    """
    politician = db.get(Politician, politician_id)
    if not politician:
        return []

    # Get all stock trades for this politician
    trades = db.execute(
        select(StockTrade)
        .where(StockTrade.politician_id == politician_id)
        .order_by(StockTrade.transaction_date.desc())
    ).scalars().all()

    conflicts = []

    for trade in trades:
        if not trade.ticker:
            continue

        # Get sector for this ticker
        sector = TICKER_SECTORS.get(trade.ticker.upper())
        if not sector:
            continue

        # Get keywords for this sector
        keywords = SECTOR_KEYWORDS.get(sector, [])
        if not keywords:
            continue

        # Find votes within the time window
        start_date = trade.transaction_date - timedelta(days=window_days)
        end_date = trade.transaction_date + timedelta(days=window_days)

        # Get votes by this politician in the window
        votes = db.execute(
            select(Vote)
            .where(
                Vote.politician_id == politician_id,
                Vote.vote_date >= start_date,
                Vote.vote_date <= end_date,
                Vote.bill_id.isnot(None),
            )
        ).scalars().all()

        for vote in votes:
            if not vote.bill:
                continue

            # Check if bill relates to the sector
            bill = vote.bill
            is_related = _check_bill_sector_relation(bill, keywords)

            if is_related:
                # Calculate days between trade and vote
                days_between = abs((vote.vote_date - trade.transaction_date).days)

                # Calculate severity score
                severity = _calculate_severity(trade, vote, days_between)

                # Create conflict record
                conflict = ConflictOfInterest(
                    politician_id=politician_id,
                    stock_trade_id=trade.id,
                    vote_id=vote.id,
                    bill_id=bill.id,
                    ticker=trade.ticker,
                    company_name=trade.asset_description,
                    sector=sector,
                    trade_date=trade.transaction_date,
                    vote_date=vote.vote_date,
                    days_between=days_between,
                    severity_score=Decimal(str(severity)),
                    reason=_generate_conflict_reason(trade, vote, bill, sector, days_between),
                    status="detected",
                )

                # Check if this conflict already exists
                existing = db.execute(
                    select(ConflictOfInterest).where(
                        ConflictOfInterest.stock_trade_id == trade.id,
                        ConflictOfInterest.vote_id == vote.id,
                    )
                ).scalar_one_or_none()

                if not existing:
                    db.add(conflict)
                    conflicts.append(conflict)

    if conflicts:
        db.commit()
        logger.info(f"Detected {len(conflicts)} potential conflicts for politician {politician_id}")

    return conflicts


def _check_bill_sector_relation(bill: Bill, keywords: list[str]) -> bool:
    """Check if a bill relates to a sector based on keywords."""
    # Check bill title
    title_lower = bill.title.lower() if bill.title else ""
    for keyword in keywords:
        if keyword in title_lower:
            return True

    # Check bill subjects
    if bill.subjects:
        subjects_text = " ".join(bill.subjects).lower()
        for keyword in keywords:
            if keyword in subjects_text:
                return True

    # Check official summary
    if bill.summary_official:
        summary_lower = bill.summary_official.lower()
        for keyword in keywords:
            if keyword in summary_lower:
                return True

    return False


def _calculate_severity(trade: StockTrade, vote: Vote, days_between: int) -> float:
    """
    Calculate severity score for a conflict (0-100).

    Higher scores indicate more concerning conflicts.
    """
    score = 50.0  # Base score

    # Timing factor: closer in time = higher severity
    if days_between <= 7:
        score += 30
    elif days_between <= 30:
        score += 20
    elif days_between <= 60:
        score += 10

    # Trade size factor
    if trade.amount_max:
        if trade.amount_max >= 1000000:
            score += 15
        elif trade.amount_max >= 250000:
            score += 10
        elif trade.amount_max >= 50000:
            score += 5

    # Vote position factor (voting in favor of industry could be more concerning)
    if vote.vote_position == "yes":
        score += 5

    return min(100.0, score)


def _generate_conflict_reason(
    trade: StockTrade,
    vote: Vote,
    bill: Bill,
    sector: str,
    days_between: int,
) -> str:
    """Generate human-readable reason for the conflict flag."""
    action = "purchased" if trade.transaction_type == "purchase" else "sold"
    timing = "before" if trade.transaction_date < vote.vote_date else "after"

    return (
        f"Politician {action} {trade.ticker} ({sector} sector) stock "
        f"{days_between} days {timing} voting '{vote.vote_position}' on "
        f"'{bill.title[:100]}...' which relates to the {sector} industry."
    )


def get_conflicts_by_politician(
    db: Session,
    politician_id: UUID,
    status: str | None = None,
    min_severity: float | None = None,
) -> list[ConflictOfInterest]:
    """
    Get all conflicts of interest for a politician.

    Args:
        db: Database session
        politician_id: Politician's UUID
        status: Filter by status ('detected', 'reviewed', 'dismissed', 'confirmed')
        min_severity: Minimum severity score to include

    Returns:
        List of ConflictOfInterest objects
    """
    query = select(ConflictOfInterest).where(
        ConflictOfInterest.politician_id == politician_id
    )

    if status:
        query = query.where(ConflictOfInterest.status == status)

    if min_severity:
        query = query.where(ConflictOfInterest.severity_score >= min_severity)

    query = query.order_by(ConflictOfInterest.severity_score.desc())

    return db.execute(query).scalars().all()


def get_conflicts_by_ticker(
    db: Session,
    ticker: str,
    status: str | None = None,
) -> list[ConflictOfInterest]:
    """Get all conflicts related to a specific stock ticker."""
    query = select(ConflictOfInterest).where(
        ConflictOfInterest.ticker == ticker.upper()
    )

    if status:
        query = query.where(ConflictOfInterest.status == status)

    return db.execute(query.order_by(ConflictOfInterest.created_at.desc())).scalars().all()


def get_high_severity_conflicts(
    db: Session,
    min_severity: float = 70.0,
    limit: int = 50,
) -> list[ConflictOfInterest]:
    """Get the highest severity conflicts across all politicians."""
    return db.execute(
        select(ConflictOfInterest)
        .where(
            ConflictOfInterest.severity_score >= min_severity,
            ConflictOfInterest.status == "detected",
        )
        .order_by(ConflictOfInterest.severity_score.desc())
        .limit(limit)
    ).scalars().all()
