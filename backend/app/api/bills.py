"""Bills API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Bill, Politician
from app.schemas.bill import (
    BillResponse,
    BillDetailResponse,
    BillListResponse,
    BillSponsorInfo,
)

router = APIRouter()


@router.get("", response_model=BillListResponse)
async def list_bills(
    congress: int | None = Query(None, description="Filter by Congress number"),
    sponsor_id: UUID | None = Query(None, description="Filter by sponsor"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List bills with optional filters."""
    query = select(Bill)

    if congress:
        query = query.where(Bill.congress == congress)
    if sponsor_id:
        query = query.where(Bill.sponsor_id == sponsor_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Bill.introduced_date.desc())

    bills = db.execute(query).scalars().all()

    return BillListResponse(
        items=[_to_bill_response(b) for b in bills],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{bill_id}", response_model=BillDetailResponse)
async def get_bill(
    bill_id: UUID,
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific bill."""
    bill = db.get(Bill, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    sponsor_info = None
    if bill.sponsor_id:
        sponsor = db.get(Politician, bill.sponsor_id)
        if sponsor:
            sponsor_info = BillSponsorInfo(
                id=sponsor.id,
                full_name=sponsor.full_name,
                party=sponsor.party,
                state=sponsor.state,
                chamber=sponsor.chamber,
            )

    return BillDetailResponse(
        **_to_bill_response(bill).model_dump(),
        sponsor=sponsor_info,
    )


def _to_bill_response(bill: Bill) -> BillResponse:
    """Convert Bill model to response schema."""
    return BillResponse(
        id=bill.id,
        bill_id=bill.bill_id,
        congress=bill.congress,
        title=bill.title,
        summary_official=bill.summary_official,
        summary_ai=bill.summary_ai,
        sponsor_id=bill.sponsor_id,
        introduced_date=bill.introduced_date,
        latest_action=bill.latest_action,
        latest_action_date=bill.latest_action_date,
        subjects=bill.subjects,
        created_at=bill.created_at,
        updated_at=bill.updated_at,
    )
