"""Politicians API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Politician, Vote, Bill, CampaignFinance, StockTrade
from app.schemas.politician import (
    PoliticianResponse,
    PoliticianListResponse,
    PoliticianDetailResponse,
    TransparencyBreakdown,
    OfficialDisclosureLinks,
)
from app.services.official_disclosures import get_disclosure_links

router = APIRouter()


@router.get("", response_model=PoliticianListResponse)
async def list_politicians(
    state: str | None = Query(None, min_length=2, max_length=2),
    party: str | None = Query(None),
    chamber: str | None = Query(None),
    in_office: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all politicians with optional filters."""
    query = select(Politician)

    if state:
        query = query.where(Politician.state == state.upper())
    if party:
        query = query.where(Politician.party == party.upper())
    if chamber:
        query = query.where(Politician.chamber == chamber.lower())
    if in_office is not None:
        query = query.where(Politician.in_office == in_office)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Politician.last_name)

    politicians = db.execute(query).scalars().all()

    return PoliticianListResponse(
        items=[_to_politician_response(p) for p in politicians],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/by-state/{state}", response_model=list[PoliticianResponse])
async def get_politicians_by_state(
    state: str,
    db: Session = Depends(get_db),
):
    """Get all politicians from a specific state."""
    query = (
        select(Politician)
        .where(Politician.state == state.upper())
        .where(Politician.in_office == True)
        .order_by(Politician.chamber, Politician.last_name)
    )
    politicians = db.execute(query).scalars().all()
    return [_to_politician_response(p) for p in politicians]


@router.get("/{politician_id}", response_model=PoliticianDetailResponse)
async def get_politician(
    politician_id: UUID,
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific politician."""
    politician = db.get(Politician, politician_id)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    # Get vote stats
    vote_count = db.execute(
        select(func.count()).where(Vote.politician_id == politician_id)
    ).scalar() or 0

    yes_votes = db.execute(
        select(func.count())
        .where(Vote.politician_id == politician_id)
        .where(Vote.vote_position.in_(["yes", "no"]))
    ).scalar() or 0

    # Get sponsored bills count
    bills_sponsored = db.execute(
        select(func.count()).where(Bill.sponsor_id == politician_id)
    ).scalar() or 0

    participation_rate = (yes_votes / vote_count * 100) if vote_count > 0 else None

    return PoliticianDetailResponse(
        **_to_politician_response(politician).model_dump(),
        total_votes=vote_count,
        total_bills_sponsored=bills_sponsored,
        vote_participation_rate=participation_rate,
        transparency_breakdown=_calculate_transparency_breakdown(politician, db),
    )


def _to_politician_response(politician: Politician) -> PoliticianResponse:
    """Convert Politician model to response schema."""
    # Get official disclosure links based on chamber
    disclosure_links = get_disclosure_links(
        chamber=politician.chamber,
        last_name=politician.last_name,
        first_name=politician.first_name,
        state=politician.state,
    )

    return PoliticianResponse(
        id=politician.id,
        bioguide_id=politician.bioguide_id,
        first_name=politician.first_name,
        last_name=politician.last_name,
        party=politician.party,
        state=politician.state,
        district=politician.district,
        chamber=politician.chamber,
        in_office=politician.in_office,
        twitter_handle=politician.twitter_handle,
        website_url=politician.website_url,
        photo_url=politician.photo_url,
        transparency_score=politician.transparency_score,
        created_at=politician.created_at,
        updated_at=politician.updated_at,
        full_name=politician.full_name,
        title=politician.title,
        official_disclosures=OfficialDisclosureLinks(**disclosure_links),
    )


def _calculate_transparency_breakdown(politician: Politician, db: Session) -> TransparencyBreakdown | None:
    """Calculate transparency score breakdown for a politician based on actual data."""
    from datetime import datetime

    if politician.transparency_score is None:
        return None

    # 1. Stock trade disclosure speed (30 pts max)
    stock_trades = db.execute(
        select(StockTrade).where(StockTrade.politician_id == politician.id)
    ).scalars().all()

    stock_score = 15.0  # Default if no trades
    if stock_trades:
        delays = []
        for trade in stock_trades:
            if trade.transaction_date and trade.disclosure_date:
                try:
                    trans_date = datetime.fromisoformat(str(trade.transaction_date))
                    disc_date = datetime.fromisoformat(str(trade.disclosure_date))
                    delays.append((disc_date - trans_date).days)
                except:
                    pass
        if delays:
            avg_delay = sum(delays) / len(delays)
            if avg_delay <= 30:
                stock_score = 30.0
            elif avg_delay <= 45:
                stock_score = 20.0
            elif avg_delay <= 60:
                stock_score = 10.0
            else:
                stock_score = 5.0

    # 2. Voting participation (30 pts max)
    vote_count = db.execute(
        select(func.count()).where(Vote.politician_id == politician.id)
    ).scalar() or 0

    yes_no_count = db.execute(
        select(func.count())
        .where(Vote.politician_id == politician.id)
        .where(Vote.vote_position.in_(["yes", "no"]))
    ).scalar() or 0

    vote_score = 15.0  # Default if no data
    if vote_count > 0:
        participation_rate = yes_no_count / vote_count
        vote_score = participation_rate * 30.0

    # 3. Campaign finance reporting (20 pts max)
    has_finance = db.execute(
        select(func.count()).where(CampaignFinance.politician_id == politician.id)
    ).scalar() or 0

    finance_score = 20.0 if has_finance > 0 else 10.0

    # 4. General disclosure compliance (20 pts max)
    disclosure_score = 5.0  # Base points
    if politician.website_url:
        disclosure_score += 5.0
    if stock_trades or has_finance:
        disclosure_score += 10.0

    total = stock_score + vote_score + finance_score + disclosure_score

    return TransparencyBreakdown(
        stock_disclosure=round(stock_score, 2),
        vote_participation=round(vote_score, 2),
        campaign_finance=round(finance_score, 2),
        financial_disclosure=round(disclosure_score, 2),
        total_score=round(total, 2),
    )
