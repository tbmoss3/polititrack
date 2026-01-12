"""FastAPI dependencies for common operations."""

from uuid import UUID
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Politician, Vote, Bill


async def get_politician_or_404(
    politician_id: UUID,
    db: Session = Depends(get_db),
) -> Politician:
    """
    Fetch a politician by ID or raise 404.

    Use as a FastAPI dependency to reduce boilerplate:
        @router.get("/by-politician/{politician_id}")
        async def get_data(politician: Politician = Depends(get_politician_or_404)):
            # politician is guaranteed to exist
    """
    politician = db.get(Politician, politician_id)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")
    return politician


async def get_vote_or_404(
    vote_id: UUID,
    db: Session = Depends(get_db),
) -> Vote:
    """Fetch a vote by ID or raise 404."""
    vote = db.get(Vote, vote_id)
    if not vote:
        raise HTTPException(status_code=404, detail="Vote not found")
    return vote


async def get_bill_or_404(
    bill_id: UUID,
    db: Session = Depends(get_db),
) -> Bill:
    """Fetch a bill by ID or raise 404."""
    bill = db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    return bill
