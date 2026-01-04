"""Finance API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Politician, CampaignFinance, TopDonor
from app.schemas.finance import (
    CampaignFinanceResponse,
    CampaignFinanceListResponse,
    TopDonorResponse,
    TopDonorListResponse,
    FinanceSummary,
)

router = APIRouter()


@router.get("/by-politician/{politician_id}", response_model=CampaignFinanceListResponse)
async def get_politician_finance(
    politician_id: UUID,
    db: Session = Depends(get_db),
):
    """Get campaign finance history for a politician."""
    politician = db.get(Politician, politician_id)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    query = (
        select(CampaignFinance)
        .where(CampaignFinance.politician_id == politician_id)
        .order_by(CampaignFinance.cycle.desc())
    )
    finances = db.execute(query).scalars().all()

    items = [_to_campaign_finance_response(f) for f in finances]

    total_raised = sum(f.total_raised or 0 for f in finances)
    total_spent = sum(f.total_spent or 0 for f in finances)

    return CampaignFinanceListResponse(
        items=items,
        total_raised_all_cycles=total_raised if total_raised > 0 else None,
        total_spent_all_cycles=total_spent if total_spent > 0 else None,
    )


@router.get("/donors/{politician_id}", response_model=TopDonorListResponse)
async def get_top_donors(
    politician_id: UUID,
    cycle: int | None = Query(None, description="Election cycle year"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get top donors for a politician."""
    politician = db.get(Politician, politician_id)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    query = select(TopDonor).where(TopDonor.politician_id == politician_id)

    if cycle:
        query = query.where(TopDonor.cycle == cycle)

    query = query.order_by(TopDonor.total_amount.desc()).limit(limit)
    donors = db.execute(query).scalars().all()

    # Determine the cycle for the response
    response_cycle = cycle
    if not response_cycle and donors:
        response_cycle = donors[0].cycle

    return TopDonorListResponse(
        items=[_to_top_donor_response(d) for d in donors],
        cycle=response_cycle or 0,
        total=len(donors),
    )


@router.get("/summary/{politician_id}", response_model=FinanceSummary)
async def get_finance_summary(
    politician_id: UUID,
    db: Session = Depends(get_db),
):
    """Get comprehensive financial summary for a politician."""
    politician = db.get(Politician, politician_id)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    # Get all campaign finance records
    finance_query = (
        select(CampaignFinance)
        .where(CampaignFinance.politician_id == politician_id)
        .order_by(CampaignFinance.cycle.desc())
    )
    finances = db.execute(finance_query).scalars().all()

    # Get current cycle data (most recent)
    current_finance = finances[0] if finances else None
    current_cycle = current_finance.cycle if current_finance else 2024

    # Get top donors for current cycle
    donor_query = (
        select(TopDonor)
        .where(TopDonor.politician_id == politician_id)
        .where(TopDonor.cycle == current_cycle)
        .order_by(TopDonor.total_amount.desc())
        .limit(10)
    )
    donors = db.execute(donor_query).scalars().all()

    return FinanceSummary(
        current_cycle=current_cycle,
        total_raised=current_finance.total_raised if current_finance else None,
        total_spent=current_finance.total_spent if current_finance else None,
        cash_on_hand=current_finance.cash_on_hand if current_finance else None,
        pac_percentage=current_finance.pac_percentage if current_finance else None,
        individual_percentage=(
            float(current_finance.total_from_individuals / current_finance.total_raised * 100)
            if current_finance and current_finance.total_raised and current_finance.total_from_individuals
            else None
        ),
        top_donors=[_to_top_donor_response(d) for d in donors],
        historical_fundraising=[_to_campaign_finance_response(f) for f in finances],
    )


def _to_campaign_finance_response(finance: CampaignFinance) -> CampaignFinanceResponse:
    """Convert CampaignFinance model to response schema."""
    return CampaignFinanceResponse(
        id=finance.id,
        politician_id=finance.politician_id,
        cycle=finance.cycle,
        total_raised=finance.total_raised,
        total_spent=finance.total_spent,
        cash_on_hand=finance.cash_on_hand,
        total_from_pacs=finance.total_from_pacs,
        total_from_individuals=finance.total_from_individuals,
        last_filed=finance.last_filed,
        pac_percentage=finance.pac_percentage,
        created_at=finance.created_at,
        updated_at=finance.updated_at,
    )


def _to_top_donor_response(donor: TopDonor) -> TopDonorResponse:
    """Convert TopDonor model to response schema."""
    return TopDonorResponse(
        id=donor.id,
        politician_id=donor.politician_id,
        cycle=donor.cycle,
        donor_name=donor.donor_name,
        donor_type=donor.donor_type,
        total_amount=donor.total_amount,
        created_at=donor.created_at,
    )
