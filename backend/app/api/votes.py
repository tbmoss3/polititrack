"""Votes API endpoints."""

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, case
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Vote, Bill, Politician
from app.api.dependencies import get_politician_or_404, get_vote_or_404
from app.schemas.vote import (
    VoteResponse,
    VoteDetailResponse,
    VoteListResponse,
    VoteBillInfo,
    VotingSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_bill_info(bill: Bill | None) -> VoteBillInfo | None:
    """Build VoteBillInfo from a Bill model."""
    if not bill:
        return None
    return VoteBillInfo(
        id=bill.id,
        bill_id=bill.bill_id,
        title=bill.title,
        summary_ai=bill.summary_official or bill.summary_ai,
    )


@router.get("/by-politician/{politician_id}", response_model=VoteListResponse)
async def get_politician_votes(
    politician_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    politician: Politician = Depends(get_politician_or_404),
):
    """Get voting history for a specific politician."""
    # Use joinedload to fetch bills in a single query (fixes N+1)
    query = (
        select(Vote)
        .options(joinedload(Vote.bill))
        .where(Vote.politician_id == politician_id)
    )

    # Count total
    count_query = select(func.count()).select_from(
        select(Vote.id).where(Vote.politician_id == politician_id).subquery()
    )
    total = db.execute(count_query).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Vote.vote_date.desc())

    votes = db.execute(query).scalars().unique().all()

    # Build response items - bill is already loaded via joinedload
    items = [
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
            bill=_build_bill_info(vote.bill),
        )
        for vote in votes
    ]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return VoteListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/summary/{politician_id}", response_model=VotingSummary)
async def get_voting_summary(
    politician_id: UUID,
    db: Session = Depends(get_db),
    politician: Politician = Depends(get_politician_or_404),
):
    """Get voting summary for a specific politician."""
    # Single aggregation query instead of 5 separate count queries
    summary = db.execute(
        select(
            func.count().label("total"),
            func.sum(case((Vote.vote_position == "yes", 1), else_=0)).label("yes"),
            func.sum(case((Vote.vote_position == "no", 1), else_=0)).label("no"),
            func.sum(case((Vote.vote_position == "not_voting", 1), else_=0)).label("not_voting"),
            func.sum(case((Vote.vote_position == "present", 1), else_=0)).label("present"),
        ).where(Vote.politician_id == politician_id)
    ).first()

    total_votes = summary.total or 0
    yes_votes = summary.yes or 0
    no_votes = summary.no or 0
    not_voting = summary.not_voting or 0
    present = summary.present or 0

    participation_rate = (
        ((yes_votes + no_votes) / total_votes * 100) if total_votes > 0 else 0.0
    )

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
    # Use joinedload to fetch bill in single query
    vote = db.execute(
        select(Vote).options(joinedload(Vote.bill)).where(Vote.id == vote_id)
    ).scalar_one_or_none()

    if not vote:
        raise HTTPException(status_code=404, detail="Vote not found")

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
        bill=_build_bill_info(vote.bill),
    )
