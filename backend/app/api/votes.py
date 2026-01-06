"""Votes API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Vote, Bill, Politician
from app.schemas.vote import (
    VoteResponse,
    VoteDetailResponse,
    VoteListResponse,
    VoteBillInfo,
    VotingSummary,
)

router = APIRouter()


@router.get("/by-politician/{politician_id}", response_model=VoteListResponse)
async def get_politician_votes(
    politician_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get voting history for a specific politician."""
    # Verify politician exists
    politician = db.get(Politician, politician_id)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    query = select(Vote).where(Vote.politician_id == politician_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Vote.vote_date.desc())

    votes = db.execute(query).scalars().all()

    # Enrich with bill info
    items = []
    for vote in votes:
        bill_info = None
        if vote.bill_id:
            bill = db.get(Bill, vote.bill_id)
            if bill:
                bill_info = VoteBillInfo(
                    id=bill.id,
                    bill_id=bill.bill_id,
                    title=bill.title,
                    summary_ai=bill.summary_official or bill.summary_ai,
                )

        items.append(
            VoteDetailResponse(
                id=vote.id,
                vote_id=vote.vote_id,
                vote_position=vote.vote_position,
                vote_date=vote.vote_date,
                chamber=vote.chamber,
                question=vote.question,
                result=vote.result,
                bill_id=vote.bill_id,
                politician_id=vote.politician_id,
                created_at=vote.created_at,
                bill=bill_info,
            )
        )

    return VoteListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/summary/{politician_id}", response_model=VotingSummary)
async def get_voting_summary(
    politician_id: UUID,
    db: Session = Depends(get_db),
):
    """Get voting summary for a specific politician."""
    politician = db.get(Politician, politician_id)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    # Get vote counts by position
    total_votes = db.execute(
        select(func.count()).where(Vote.politician_id == politician_id)
    ).scalar() or 0

    yes_votes = db.execute(
        select(func.count())
        .where(Vote.politician_id == politician_id)
        .where(Vote.vote_position == "yes")
    ).scalar() or 0

    no_votes = db.execute(
        select(func.count())
        .where(Vote.politician_id == politician_id)
        .where(Vote.vote_position == "no")
    ).scalar() or 0

    not_voting = db.execute(
        select(func.count())
        .where(Vote.politician_id == politician_id)
        .where(Vote.vote_position == "not_voting")
    ).scalar() or 0

    present = db.execute(
        select(func.count())
        .where(Vote.politician_id == politician_id)
        .where(Vote.vote_position == "present")
    ).scalar() or 0

    participation_rate = ((yes_votes + no_votes) / total_votes * 100) if total_votes > 0 else 0.0

    return VotingSummary(
        total_votes=total_votes,
        yes_votes=yes_votes,
        no_votes=no_votes,
        not_voting=not_voting,
        present=present,
        participation_rate=participation_rate,
    )


@router.get("/{vote_id}", response_model=VoteDetailResponse)
async def get_vote(
    vote_id: UUID,
    db: Session = Depends(get_db),
):
    """Get details about a specific vote."""
    vote = db.get(Vote, vote_id)
    if not vote:
        raise HTTPException(status_code=404, detail="Vote not found")

    bill_info = None
    if vote.bill_id:
        bill = db.get(Bill, vote.bill_id)
        if bill:
            bill_info = VoteBillInfo(
                id=bill.id,
                bill_id=bill.bill_id,
                title=bill.title,
                summary_ai=bill.summary_official or bill.summary_ai,
            )

    return VoteDetailResponse(
        id=vote.id,
        vote_id=vote.vote_id,
        vote_position=vote.vote_position,
        vote_date=vote.vote_date,
        chamber=vote.chamber,
        question=vote.question,
        result=vote.result,
        bill_id=vote.bill_id,
        politician_id=vote.politician_id,
        created_at=vote.created_at,
        bill=bill_info,
    )
