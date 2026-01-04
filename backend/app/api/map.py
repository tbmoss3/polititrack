"""Map API endpoints for GeoJSON and aggregated state data."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Politician

router = APIRouter()


class StateAggregation(BaseModel):
    """Aggregated data for a single state."""

    state: str = Field(..., description="Two-letter state code")
    total_politicians: int
    democrats: int
    republicans: int
    independents: int
    avg_transparency_score: float | None
    senators: int
    representatives: int


class StatesMapResponse(BaseModel):
    """Response containing all state aggregations."""

    states: list[StateAggregation]


class DistrictInfo(BaseModel):
    """Information about a congressional district."""

    state: str
    district: int
    representative_id: str | None
    representative_name: str | None
    party: str | None
    transparency_score: float | None


class DistrictsResponse(BaseModel):
    """Response containing district information for a state."""

    state: str
    districts: list[DistrictInfo]
    senators: list[dict]


@router.get("/states", response_model=StatesMapResponse)
async def get_states_aggregation(db: Session = Depends(get_db)):
    """Get aggregated politician data for all states (for map coloring/tooltips)."""
    # Aggregate by state
    query = (
        select(
            Politician.state,
            func.count(Politician.id).label("total"),
            func.sum(case((Politician.party == "D", 1), else_=0)).label("democrats"),
            func.sum(case((Politician.party == "R", 1), else_=0)).label("republicans"),
            func.sum(case((Politician.party.in_(["I", "ID"]), 1), else_=0)).label("independents"),
            func.avg(Politician.transparency_score).label("avg_transparency"),
            func.sum(case((Politician.chamber == "senate", 1), else_=0)).label("senators"),
            func.sum(case((Politician.chamber == "house", 1), else_=0)).label("representatives"),
        )
        .where(Politician.in_office == True)
        .group_by(Politician.state)
    )

    results = db.execute(query).all()

    states = [
        StateAggregation(
            state=row.state,
            total_politicians=row.total,
            democrats=row.democrats or 0,
            republicans=row.republicans or 0,
            independents=row.independents or 0,
            avg_transparency_score=float(row.avg_transparency) if row.avg_transparency else None,
            senators=row.senators or 0,
            representatives=row.representatives or 0,
        )
        for row in results
    ]

    return StatesMapResponse(states=states)


@router.get("/districts/{state}", response_model=DistrictsResponse)
async def get_state_districts(
    state: str,
    db: Session = Depends(get_db),
):
    """Get district-level data for a specific state."""
    state = state.upper()

    # Get representatives (by district)
    reps_query = (
        select(Politician)
        .where(Politician.state == state)
        .where(Politician.chamber == "house")
        .where(Politician.in_office == True)
        .order_by(Politician.district)
    )
    representatives = db.execute(reps_query).scalars().all()

    districts = [
        DistrictInfo(
            state=state,
            district=rep.district or 0,
            representative_id=str(rep.id),
            representative_name=rep.full_name,
            party=rep.party,
            transparency_score=float(rep.transparency_score) if rep.transparency_score else None,
        )
        for rep in representatives
    ]

    # Get senators
    senators_query = (
        select(Politician)
        .where(Politician.state == state)
        .where(Politician.chamber == "senate")
        .where(Politician.in_office == True)
    )
    senators = db.execute(senators_query).scalars().all()

    senators_data = [
        {
            "id": str(s.id),
            "name": s.full_name,
            "party": s.party,
            "transparency_score": float(s.transparency_score) if s.transparency_score else None,
        }
        for s in senators
    ]

    return DistrictsResponse(
        state=state,
        districts=districts,
        senators=senators_data,
    )


@router.get("/party-breakdown")
async def get_party_breakdown(db: Session = Depends(get_db)):
    """Get national party breakdown for overview statistics."""
    query = (
        select(
            Politician.party,
            Politician.chamber,
            func.count(Politician.id).label("count"),
        )
        .where(Politician.in_office == True)
        .group_by(Politician.party, Politician.chamber)
    )

    results = db.execute(query).all()

    breakdown = {
        "house": {"D": 0, "R": 0, "I": 0},
        "senate": {"D": 0, "R": 0, "I": 0},
    }

    for row in results:
        chamber = row.chamber
        party = row.party if row.party in ["D", "R"] else "I"
        if chamber in breakdown:
            breakdown[chamber][party] = row.count

    return {
        "house": breakdown["house"],
        "senate": breakdown["senate"],
        "total": {
            "D": breakdown["house"]["D"] + breakdown["senate"]["D"],
            "R": breakdown["house"]["R"] + breakdown["senate"]["R"],
            "I": breakdown["house"]["I"] + breakdown["senate"]["I"],
        },
    }
