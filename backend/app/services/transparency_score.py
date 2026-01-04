"""Transparency Score calculation service."""

from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Politician, Vote, StockTrade, CampaignFinance


class TransparencyScoreCalculator:
    """
    Calculate transparency scores for politicians.

    Score breakdown (0-100):
    - Financial disclosure timeliness: 30 points
    - Stock trade disclosure speed: 30 points
    - Voting participation: 20 points
    - Campaign finance reporting: 20 points
    """

    def __init__(self, db: Session):
        self.db = db

    def calculate_score(self, politician_id: str) -> dict:
        """
        Calculate full transparency score with breakdown.

        Args:
            politician_id: UUID of the politician

        Returns:
            Dictionary with score breakdown and total
        """
        financial_score = self._calculate_financial_disclosure_score(politician_id)
        stock_score = self._calculate_stock_disclosure_score(politician_id)
        vote_score = self._calculate_vote_participation_score(politician_id)
        campaign_score = self._calculate_campaign_finance_score(politician_id)

        total = financial_score + stock_score + vote_score + campaign_score

        return {
            "financial_disclosure": round(financial_score, 2),
            "stock_disclosure": round(stock_score, 2),
            "vote_participation": round(vote_score, 2),
            "campaign_finance": round(campaign_score, 2),
            "total_score": round(total, 2),
        }

    def _calculate_financial_disclosure_score(self, politician_id: str) -> float:
        """
        Calculate score based on financial disclosure timeliness.
        Max: 30 points
        Full points if filed within deadline, -5 per month late.
        """
        # Get most recent campaign finance record
        query = (
            select(CampaignFinance)
            .where(CampaignFinance.politician_id == politician_id)
            .order_by(CampaignFinance.last_filed.desc())
            .limit(1)
        )
        finance = self.db.execute(query).scalar_one_or_none()

        if not finance or not finance.last_filed:
            return 15.0  # Default middle score if no data

        # Calculate months since last filing
        today = date.today()
        days_since_filing = (today - finance.last_filed).days

        # FEC requires quarterly reports - check if more than 4 months old
        months_late = max(0, (days_since_filing - 120) // 30)

        score = max(0, 30 - (months_late * 5))
        return float(score)

    def _calculate_stock_disclosure_score(self, politician_id: str) -> float:
        """
        Calculate score based on stock trade disclosure speed.
        Max: 30 points
        Law requires 45 days. Full points if avg < 30 days.
        """
        # Get recent stock trades (last year)
        one_year_ago = date.today() - timedelta(days=365)
        query = (
            select(StockTrade)
            .where(StockTrade.politician_id == politician_id)
            .where(StockTrade.transaction_date >= one_year_ago)
        )
        trades = self.db.execute(query).scalars().all()

        if not trades:
            return 30.0  # Full points if no trades (nothing to disclose)

        # Calculate average disclosure delay
        total_delay = sum(t.disclosure_delay_days for t in trades)
        avg_delay = total_delay / len(trades)

        if avg_delay <= 30:
            return 30.0
        elif avg_delay <= 45:
            return 20.0
        elif avg_delay <= 60:
            return 10.0
        elif avg_delay <= 90:
            return 5.0
        else:
            return 0.0

    def _calculate_vote_participation_score(self, politician_id: str) -> float:
        """
        Calculate score based on voting participation rate.
        Max: 20 points
        Score = participation_rate * 20
        """
        # Get votes from current session (last 2 years)
        two_years_ago = date.today() - timedelta(days=730)

        total_votes = self.db.execute(
            select(func.count())
            .where(Vote.politician_id == politician_id)
            .where(Vote.vote_date >= two_years_ago)
        ).scalar() or 0

        if total_votes == 0:
            return 10.0  # Default if no vote data

        participated_votes = self.db.execute(
            select(func.count())
            .where(Vote.politician_id == politician_id)
            .where(Vote.vote_date >= two_years_ago)
            .where(Vote.vote_position.in_(["yes", "no"]))
        ).scalar() or 0

        participation_rate = participated_votes / total_votes
        return participation_rate * 20

    def _calculate_campaign_finance_score(self, politician_id: str) -> float:
        """
        Calculate score based on campaign finance reporting completeness.
        Max: 20 points
        Based on having complete, recent data.
        """
        current_cycle = (date.today().year // 2) * 2  # Current election cycle

        query = (
            select(CampaignFinance)
            .where(CampaignFinance.politician_id == politician_id)
            .where(CampaignFinance.cycle == current_cycle)
        )
        finance = self.db.execute(query).scalar_one_or_none()

        if not finance:
            return 5.0  # Low score if no current cycle data

        score = 0.0

        # Points for having data
        if finance.total_raised is not None:
            score += 5.0
        if finance.total_spent is not None:
            score += 5.0
        if finance.total_from_pacs is not None:
            score += 5.0
        if finance.total_from_individuals is not None:
            score += 5.0

        return score


async def update_all_transparency_scores(db: Session) -> int:
    """
    Update transparency scores for all politicians.

    Args:
        db: Database session

    Returns:
        Number of politicians updated
    """
    calculator = TransparencyScoreCalculator(db)

    politicians = db.execute(select(Politician)).scalars().all()
    updated_count = 0

    for politician in politicians:
        try:
            score_breakdown = calculator.calculate_score(str(politician.id))
            politician.transparency_score = Decimal(str(score_breakdown["total_score"]))
            updated_count += 1
        except Exception:
            continue

    db.commit()
    return updated_count
