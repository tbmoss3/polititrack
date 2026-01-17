"""API endpoints for new features."""

import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Politician, Committee, CommitteeAssignment
from app.api.dependencies import get_politician_or_404
from app.services.district_finder import find_district_by_address, find_district_by_zip, DistrictResult
from app.services.voting_alignment import (
    calculate_voting_alignment,
    calculate_party_alignment,
    get_most_aligned_politicians,
    AlignmentResult,
    PartyAlignmentResult,
)
from app.services.conflict_detector import (
    detect_conflicts_for_politician,
    get_conflicts_by_politician,
    get_high_severity_conflicts,
)
from app.services.activity_feed import (
    get_recent_activity,
    get_politician_activity,
    ActivityItem,
)
from app.services.search import search_all, search_suggestions, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ Schemas ============

class DistrictRequest(BaseModel):
    """Request for district lookup by address."""
    street: str = Field(..., min_length=5, description="Street address")
    city: str = Field(..., min_length=2, description="City name")
    state: str = Field(..., min_length=2, max_length=2, description="State abbreviation")
    zip_code: str | None = Field(None, description="Optional ZIP code")


class DistrictResponse(BaseModel):
    """Response for district lookup."""
    state: str
    state_name: str
    district: int | None
    formatted_address: str | None
    representatives: list[dict] = []


class AlignmentResponse(BaseModel):
    """Response for voting alignment."""
    politician1_id: str
    politician1_name: str
    politician2_id: str
    politician2_name: str
    total_common_votes: int
    aligned_votes: int
    alignment_percentage: float
    opposed_votes: int
    one_not_voting: int


class PartyAlignmentResponse(BaseModel):
    """Response for party alignment."""
    politician_id: str
    politician_name: str
    party: str
    total_party_votes: int
    aligned_with_party: int
    party_alignment_percentage: float
    against_party: int


class ComparisonRequest(BaseModel):
    """Request for politician comparison."""
    politician_ids: list[str] = Field(..., min_length=2, max_length=4)


class ComparisonResponse(BaseModel):
    """Response for politician comparison."""
    politicians: list[dict]
    voting_alignments: list[AlignmentResponse]


class ActivityResponse(BaseModel):
    """Response for activity feed."""
    id: str
    activity_type: str
    title: str
    description: str
    politician_id: str | None
    politician_name: str | None
    party: str | None
    state: str | None
    timestamp: str
    metadata: dict


class ConflictResponse(BaseModel):
    """Response for conflict of interest."""
    id: str
    politician_id: str
    politician_name: str | None
    ticker: str
    company_name: str | None
    sector: str | None
    trade_date: str
    vote_date: str | None
    days_between: int | None
    severity_score: float | None
    reason: str
    status: str


class CommitteeResponse(BaseModel):
    """Response for committee."""
    id: str
    committee_code: str
    name: str
    chamber: str
    committee_type: str
    url: str | None


class CommitteeAssignmentResponse(BaseModel):
    """Response for committee assignment."""
    id: str
    committee: CommitteeResponse
    role: str
    is_subcommittee: bool
    subcommittee_name: str | None


# ============ Feature 1: District Finder ============

@router.post("/district/find", response_model=DistrictResponse)
async def find_district(
    request: DistrictRequest,
    db: Session = Depends(get_db),
):
    """
    Find congressional district from a street address.

    Returns the district number and representatives for that location.
    """
    result = await find_district_by_address(
        street=request.street,
        city=request.city,
        state=request.state,
        zip_code=request.zip_code,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Could not find district for this address. Please verify the address is correct.",
        )

    # Find representatives for this district
    representatives = []

    # Get House representative (if has a district)
    if result.district is not None:
        rep = db.query(Politician).filter(
            Politician.state == result.state,
            Politician.chamber == "house",
            Politician.district == result.district,
            Politician.in_office == True,
        ).first()

        if rep:
            representatives.append({
                "id": str(rep.id),
                "name": rep.full_name,
                "party": rep.party,
                "chamber": "house",
                "district": rep.district,
            })

    # Get Senators
    senators = db.query(Politician).filter(
        Politician.state == result.state,
        Politician.chamber == "senate",
        Politician.in_office == True,
    ).all()

    for sen in senators:
        representatives.append({
            "id": str(sen.id),
            "name": sen.full_name,
            "party": sen.party,
            "chamber": "senate",
        })

    return DistrictResponse(
        state=result.state,
        state_name=result.state_name,
        district=result.district,
        formatted_address=result.formatted_address,
        representatives=representatives,
    )


@router.get("/district/by-zip/{zip_code}", response_model=list[DistrictResponse])
async def find_district_by_zip_code(
    zip_code: str,
    db: Session = Depends(get_db),
):
    """Find congressional district(s) from a ZIP code."""
    if len(zip_code) != 5 or not zip_code.isdigit():
        raise HTTPException(status_code=400, detail="ZIP code must be 5 digits")

    results = await find_district_by_zip(zip_code)

    if not results:
        raise HTTPException(status_code=404, detail="Could not find district for this ZIP code")

    responses = []
    for result in results:
        # Find representatives
        representatives = []

        if result.district is not None:
            rep = db.query(Politician).filter(
                Politician.state == result.state,
                Politician.chamber == "house",
                Politician.district == result.district,
                Politician.in_office == True,
            ).first()

            if rep:
                representatives.append({
                    "id": str(rep.id),
                    "name": rep.full_name,
                    "party": rep.party,
                    "chamber": "house",
                    "district": rep.district,
                })

        senators = db.query(Politician).filter(
            Politician.state == result.state,
            Politician.chamber == "senate",
            Politician.in_office == True,
        ).all()

        for sen in senators:
            representatives.append({
                "id": str(sen.id),
                "name": sen.full_name,
                "party": sen.party,
                "chamber": "senate",
            })

        responses.append(DistrictResponse(
            state=result.state,
            state_name=result.state_name,
            district=result.district,
            formatted_address=result.formatted_address,
            representatives=representatives,
        ))

    return responses


# ============ Feature 2: Voting Alignment ============

@router.get("/alignment/{politician1_id}/{politician2_id}", response_model=AlignmentResponse)
async def get_voting_alignment(
    politician1_id: UUID,
    politician2_id: UUID,
    db: Session = Depends(get_db),
):
    """Calculate voting alignment between two politicians."""
    result = calculate_voting_alignment(db, politician1_id, politician2_id)

    if not result:
        raise HTTPException(status_code=404, detail="One or both politicians not found")

    return AlignmentResponse(
        politician1_id=str(result.politician1_id),
        politician1_name=result.politician1_name,
        politician2_id=str(result.politician2_id),
        politician2_name=result.politician2_name,
        total_common_votes=result.total_common_votes,
        aligned_votes=result.aligned_votes,
        alignment_percentage=result.alignment_percentage,
        opposed_votes=result.opposed_votes,
        one_not_voting=result.one_not_voting,
    )


@router.get("/alignment/party/{politician_id}", response_model=PartyAlignmentResponse)
async def get_party_alignment(
    politician_id: UUID,
    db: Session = Depends(get_db),
):
    """Calculate how often a politician votes with their party."""
    result = calculate_party_alignment(db, politician_id)

    if not result:
        raise HTTPException(status_code=404, detail="Politician not found or no party affiliation")

    return PartyAlignmentResponse(
        politician_id=str(result.politician_id),
        politician_name=result.politician_name,
        party=result.party,
        total_party_votes=result.total_party_votes,
        aligned_with_party=result.aligned_with_party,
        party_alignment_percentage=result.party_alignment_percentage,
        against_party=result.against_party,
    )


@router.get("/alignment/most-aligned/{politician_id}", response_model=list[AlignmentResponse])
async def get_most_aligned(
    politician_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    same_party_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Get politicians who vote most similarly to the given politician."""
    results = get_most_aligned_politicians(db, politician_id, limit, same_party_only)

    return [
        AlignmentResponse(
            politician1_id=str(r.politician1_id),
            politician1_name=r.politician1_name,
            politician2_id=str(r.politician2_id),
            politician2_name=r.politician2_name,
            total_common_votes=r.total_common_votes,
            aligned_votes=r.aligned_votes,
            alignment_percentage=r.alignment_percentage,
            opposed_votes=r.opposed_votes,
            one_not_voting=r.one_not_voting,
        )
        for r in results
    ]


# ============ Feature 3: Politician Comparison ============

@router.post("/compare", response_model=ComparisonResponse)
async def compare_politicians(
    request: ComparisonRequest,
    db: Session = Depends(get_db),
):
    """Compare 2-4 politicians side by side."""
    politician_ids = [UUID(pid) for pid in request.politician_ids]

    # Get politician details
    politicians = []
    for pid in politician_ids:
        p = db.get(Politician, pid)
        if not p:
            raise HTTPException(status_code=404, detail=f"Politician {pid} not found")

        politicians.append({
            "id": str(p.id),
            "name": p.full_name,
            "party": p.party,
            "state": p.state,
            "chamber": p.chamber,
            "district": p.district,
            "transparency_score": float(p.transparency_score) if p.transparency_score else None,
            "in_office": p.in_office,
        })

    # Calculate pairwise voting alignments
    alignments = []
    for i, pid1 in enumerate(politician_ids):
        for pid2 in politician_ids[i + 1 :]:
            result = calculate_voting_alignment(db, pid1, pid2)
            if result:
                alignments.append(
                    AlignmentResponse(
                        politician1_id=str(result.politician1_id),
                        politician1_name=result.politician1_name,
                        politician2_id=str(result.politician2_id),
                        politician2_name=result.politician2_name,
                        total_common_votes=result.total_common_votes,
                        aligned_votes=result.aligned_votes,
                        alignment_percentage=result.alignment_percentage,
                        opposed_votes=result.opposed_votes,
                        one_not_voting=result.one_not_voting,
                    )
                )

    return ComparisonResponse(
        politicians=politicians,
        voting_alignments=alignments,
    )


# ============ Feature 4: Activity Feed ============

@router.get("/activity/recent", response_model=list[ActivityResponse])
async def get_recent_activity_feed(
    limit: int = Query(50, ge=1, le=100),
    days: int = Query(7, ge=1, le=30),
    activity_type: str | None = Query(None, description="Filter by type: vote, trade, bill"),
    state: str | None = Query(None, description="Filter by state"),
    party: str | None = Query(None, description="Filter by party"),
    db: Session = Depends(get_db),
):
    """Get recent activity feed across all politicians."""
    types = [activity_type] if activity_type else None

    activities = get_recent_activity(
        db=db,
        limit=limit,
        days=days,
        activity_types=types,
        state=state,
        party=party,
    )

    return [
        ActivityResponse(
            id=str(a.id),
            activity_type=a.activity_type,
            title=a.title,
            description=a.description,
            politician_id=str(a.politician_id) if a.politician_id else None,
            politician_name=a.politician_name,
            party=a.party,
            state=a.state,
            timestamp=a.timestamp.isoformat(),
            metadata=a.metadata,
        )
        for a in activities
    ]


@router.get("/activity/politician/{politician_id}", response_model=list[ActivityResponse])
async def get_politician_activity_feed(
    politician_id: UUID,
    limit: int = Query(20, ge=1, le=50),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get recent activity for a specific politician."""
    activities = get_politician_activity(db, politician_id, limit, days)

    return [
        ActivityResponse(
            id=str(a.id),
            activity_type=a.activity_type,
            title=a.title,
            description=a.description,
            politician_id=str(a.politician_id) if a.politician_id else None,
            politician_name=a.politician_name,
            party=a.party,
            state=a.state,
            timestamp=a.timestamp.isoformat(),
            metadata=a.metadata,
        )
        for a in activities
    ]


# ============ Feature 5: Conflict of Interest ============

@router.get("/conflicts/politician/{politician_id}", response_model=list[ConflictResponse])
async def get_politician_conflicts(
    politician_id: UUID,
    status: str | None = Query(None, description="Filter by status"),
    min_severity: float | None = Query(None, ge=0, le=100),
    db: Session = Depends(get_db),
):
    """Get potential conflicts of interest for a politician."""
    conflicts = get_conflicts_by_politician(db, politician_id, status, min_severity)

    politician = db.get(Politician, politician_id)

    return [
        ConflictResponse(
            id=str(c.id),
            politician_id=str(c.politician_id),
            politician_name=politician.full_name if politician else None,
            ticker=c.ticker,
            company_name=c.company_name,
            sector=c.sector,
            trade_date=str(c.trade_date),
            vote_date=str(c.vote_date) if c.vote_date else None,
            days_between=c.days_between,
            severity_score=float(c.severity_score) if c.severity_score else None,
            reason=c.reason,
            status=c.status,
        )
        for c in conflicts
    ]


@router.post("/conflicts/detect/{politician_id}")
async def detect_politician_conflicts(
    politician_id: UUID,
    db: Session = Depends(get_db),
):
    """Run conflict detection for a specific politician."""
    conflicts = detect_conflicts_for_politician(db, politician_id)

    return {
        "status": "complete",
        "conflicts_detected": len(conflicts),
        "politician_id": str(politician_id),
    }


@router.get("/conflicts/high-severity", response_model=list[ConflictResponse])
async def get_high_severity_conflicts_list(
    min_severity: float = Query(70.0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get high severity conflicts across all politicians."""
    conflicts = get_high_severity_conflicts(db, min_severity, limit)

    responses = []
    for c in conflicts:
        politician = db.get(Politician, c.politician_id)
        responses.append(
            ConflictResponse(
                id=str(c.id),
                politician_id=str(c.politician_id),
                politician_name=politician.full_name if politician else None,
                ticker=c.ticker,
                company_name=c.company_name,
                sector=c.sector,
                trade_date=str(c.trade_date),
                vote_date=str(c.vote_date) if c.vote_date else None,
                days_between=c.days_between,
                severity_score=float(c.severity_score) if c.severity_score else None,
                reason=c.reason,
                status=c.status,
            )
        )

    return responses


# ============ Feature 6: Search ============

@router.get("/search")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    type: str = Query("all", description="Search type: all, politicians, bills, donors"),
    limit: int = Query(50, ge=1, le=100),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    """Full-text search across politicians, bills, and donors."""
    result = search_all(db, q, type, limit, page)

    return {
        "query": result.query,
        "total_results": result.total_results,
        "results": [
            {
                "id": str(r.id),
                "type": r.result_type,
                "title": r.title,
                "subtitle": r.subtitle,
                "relevance_score": r.relevance_score,
                "metadata": r.metadata,
            }
            for r in result.results
        ],
        "counts": {
            "politicians": result.politicians_count,
            "bills": result.bills_count,
            "donors": result.donors_count,
        },
    }


@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Get autocomplete suggestions for search."""
    suggestions = search_suggestions(db, q, limit)
    return {"suggestions": suggestions}


# ============ Feature 8: Committee Assignments ============

@router.get("/committees", response_model=list[CommitteeResponse])
async def list_committees(
    chamber: str | None = Query(None, description="Filter by chamber: house, senate"),
    db: Session = Depends(get_db),
):
    """List all congressional committees."""
    query = db.query(Committee)

    if chamber:
        query = query.filter(Committee.chamber == chamber.lower())

    committees = query.order_by(Committee.name).all()

    return [
        CommitteeResponse(
            id=str(c.id),
            committee_code=c.committee_code,
            name=c.name,
            chamber=c.chamber,
            committee_type=c.committee_type,
            url=c.url,
        )
        for c in committees
    ]


@router.get("/committees/politician/{politician_id}", response_model=list[CommitteeAssignmentResponse])
async def get_politician_committees(
    politician_id: UUID,
    db: Session = Depends(get_db),
):
    """Get committee assignments for a politician."""
    assignments = db.query(CommitteeAssignment).filter(
        CommitteeAssignment.politician_id == politician_id
    ).all()

    return [
        CommitteeAssignmentResponse(
            id=str(a.id),
            committee=CommitteeResponse(
                id=str(a.committee.id),
                committee_code=a.committee.committee_code,
                name=a.committee.name,
                chamber=a.committee.chamber,
                committee_type=a.committee.committee_type,
                url=a.committee.url,
            ),
            role=a.role,
            is_subcommittee=a.is_subcommittee,
            subcommittee_name=a.subcommittee_name,
        )
        for a in assignments
    ]


@router.get("/committees/{committee_id}/members")
async def get_committee_members(
    committee_id: UUID,
    db: Session = Depends(get_db),
):
    """Get all members of a committee."""
    committee = db.get(Committee, committee_id)
    if not committee:
        raise HTTPException(status_code=404, detail="Committee not found")

    assignments = db.query(CommitteeAssignment).filter(
        CommitteeAssignment.committee_id == committee_id
    ).all()

    members = []
    for a in assignments:
        p = a.politician
        members.append({
            "id": str(p.id),
            "name": p.full_name,
            "party": p.party,
            "state": p.state,
            "role": a.role,
            "is_subcommittee": a.is_subcommittee,
            "subcommittee_name": a.subcommittee_name,
        })

    return {
        "committee": {
            "id": str(committee.id),
            "name": committee.name,
            "chamber": committee.chamber,
        },
        "members": members,
    }
