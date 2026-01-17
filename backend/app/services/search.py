"""Full-text search service using PostgreSQL."""

import logging
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.orm import Session

from app.models import Politician, Bill, TopDonor

logger = logging.getLogger(__name__)

SearchType = Literal["all", "politicians", "bills", "donors"]


@dataclass
class SearchResult:
    """A single search result."""

    id: UUID
    result_type: str  # 'politician', 'bill', 'donor'
    title: str
    subtitle: str
    relevance_score: float
    metadata: dict


@dataclass
class SearchResponse:
    """Response containing search results."""

    query: str
    total_results: int
    results: list[SearchResult]
    politicians_count: int
    bills_count: int
    donors_count: int


def search_all(
    db: Session,
    query: str,
    search_type: SearchType = "all",
    limit: int = 50,
    page: int = 1,
) -> SearchResponse:
    """
    Perform full-text search across politicians, bills, and donors.

    Args:
        db: Database session
        query: Search query string
        search_type: Type of results to return ('all', 'politicians', 'bills', 'donors')
        limit: Maximum results per type
        page: Page number for pagination

    Returns:
        SearchResponse with results and counts
    """
    if not query or len(query.strip()) < 2:
        return SearchResponse(
            query=query,
            total_results=0,
            results=[],
            politicians_count=0,
            bills_count=0,
            donors_count=0,
        )

    results = []
    politicians_count = 0
    bills_count = 0
    donors_count = 0

    # Clean query for search
    clean_query = query.strip()

    # Search politicians
    if search_type in ("all", "politicians"):
        politician_results, politicians_count = _search_politicians(db, clean_query, limit)
        results.extend(politician_results)

    # Search bills
    if search_type in ("all", "bills"):
        bill_results, bills_count = _search_bills(db, clean_query, limit)
        results.extend(bill_results)

    # Search donors
    if search_type in ("all", "donors"):
        donor_results, donors_count = _search_donors(db, clean_query, limit)
        results.extend(donor_results)

    # Sort by relevance score
    results.sort(key=lambda x: x.relevance_score, reverse=True)

    # Paginate
    offset = (page - 1) * limit
    paginated_results = results[offset : offset + limit]

    return SearchResponse(
        query=query,
        total_results=len(results),
        results=paginated_results,
        politicians_count=politicians_count,
        bills_count=bills_count,
        donors_count=donors_count,
    )


def _search_politicians(
    db: Session,
    query: str,
    limit: int,
) -> tuple[list[SearchResult], int]:
    """Search politicians by name, state, party."""
    query_lower = query.lower()
    query_parts = query_lower.split()

    # Build search conditions
    conditions = []

    # Full name match (highest relevance)
    conditions.append(
        func.lower(Politician.first_name + " " + Politician.last_name).contains(query_lower)
    )

    # First name or last name match
    for part in query_parts:
        conditions.append(func.lower(Politician.first_name).contains(part))
        conditions.append(func.lower(Politician.last_name).contains(part))

    # State match
    if len(query) == 2:
        conditions.append(func.upper(Politician.state) == query.upper())

    # Party match
    party_map = {"democrat": "D", "republican": "R", "independent": "I"}
    for party_name, party_code in party_map.items():
        if party_name.startswith(query_lower):
            conditions.append(Politician.party == party_code)

    politicians = db.execute(
        select(Politician)
        .where(or_(*conditions))
        .where(Politician.in_office == True)
        .limit(limit)
    ).scalars().all()

    results = []
    for p in politicians:
        # Calculate relevance score
        full_name = f"{p.first_name} {p.last_name}".lower()
        if query_lower == full_name:
            score = 1.0
        elif full_name.startswith(query_lower):
            score = 0.9
        elif query_lower in full_name:
            score = 0.8
        else:
            score = 0.6

        results.append(
            SearchResult(
                id=p.id,
                result_type="politician",
                title=p.full_name,
                subtitle=f"{p.party}-{p.state} • {p.title}",
                relevance_score=score,
                metadata={
                    "party": p.party,
                    "state": p.state,
                    "chamber": p.chamber,
                    "bioguide_id": p.bioguide_id,
                },
            )
        )

    return results, len(results)


def _search_bills(
    db: Session,
    query: str,
    limit: int,
) -> tuple[list[SearchResult], int]:
    """Search bills by title, bill_id, or subjects."""
    query_lower = query.lower()

    # Check if searching by bill ID pattern (e.g., "hr 1234" or "s 567")
    is_bill_id_search = any(
        query_lower.startswith(prefix)
        for prefix in ["hr", "s ", "hres", "sres", "hjres", "sjres"]
    )

    conditions = []

    if is_bill_id_search:
        # Normalize bill ID query
        bill_query = query_lower.replace(" ", "").replace(".", "")
        conditions.append(func.lower(Bill.bill_id).contains(bill_query))
    else:
        # Search by title
        conditions.append(func.lower(Bill.title).contains(query_lower))

        # Search by summary
        conditions.append(func.lower(Bill.summary_official).contains(query_lower))

    bills = db.execute(
        select(Bill)
        .where(or_(*conditions))
        .order_by(Bill.latest_action_date.desc().nullslast())
        .limit(limit)
    ).scalars().all()

    results = []
    for b in bills:
        # Calculate relevance score
        title_lower = b.title.lower() if b.title else ""
        if query_lower in b.bill_id.lower():
            score = 1.0
        elif title_lower.startswith(query_lower):
            score = 0.9
        elif query_lower in title_lower:
            score = 0.8
        else:
            score = 0.6

        results.append(
            SearchResult(
                id=b.id,
                result_type="bill",
                title=b.bill_id.upper(),
                subtitle=b.title[:150] if b.title else "No title",
                relevance_score=score,
                metadata={
                    "congress": b.congress,
                    "latest_action": b.latest_action,
                    "introduced_date": str(b.introduced_date) if b.introduced_date else None,
                },
            )
        )

    return results, len(results)


def _search_donors(
    db: Session,
    query: str,
    limit: int,
) -> tuple[list[SearchResult], int]:
    """Search donors by name."""
    query_lower = query.lower()

    donors = db.execute(
        select(TopDonor)
        .where(func.lower(TopDonor.donor_name).contains(query_lower))
        .order_by(TopDonor.total_amount.desc())
        .limit(limit)
    ).scalars().all()

    results = []
    seen_donors = set()  # Deduplicate by donor name

    for d in donors:
        if d.donor_name in seen_donors:
            continue
        seen_donors.add(d.donor_name)

        # Get associated politician
        politician = db.get(Politician, d.politician_id)
        politician_name = politician.full_name if politician else "Unknown"

        # Calculate relevance
        donor_lower = d.donor_name.lower()
        if query_lower == donor_lower:
            score = 1.0
        elif donor_lower.startswith(query_lower):
            score = 0.9
        else:
            score = 0.7

        results.append(
            SearchResult(
                id=d.id,
                result_type="donor",
                title=d.donor_name,
                subtitle=f"${d.total_amount:,.0f} to {politician_name} ({d.cycle})",
                relevance_score=score,
                metadata={
                    "donor_type": d.donor_type,
                    "cycle": d.cycle,
                    "total_amount": float(d.total_amount) if d.total_amount else 0,
                    "politician_id": str(d.politician_id),
                },
            )
        )

    return results, len(results)


def search_suggestions(
    db: Session,
    query: str,
    limit: int = 10,
) -> list[str]:
    """
    Get search suggestions (autocomplete) for a query.

    Returns a list of suggested search terms based on partial matches.
    """
    if not query or len(query) < 2:
        return []

    query_lower = query.lower()
    suggestions = set()

    # Politician name suggestions
    politicians = db.execute(
        select(Politician.first_name, Politician.last_name)
        .where(
            or_(
                func.lower(Politician.first_name).startswith(query_lower),
                func.lower(Politician.last_name).startswith(query_lower),
            )
        )
        .where(Politician.in_office == True)
        .limit(limit)
    ).all()

    for first, last in politicians:
        suggestions.add(f"{first} {last}")

    # State suggestions
    states = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
              "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
              "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
              "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
              "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
              "New Hampshire", "New Jersey", "New Mexico", "New York",
              "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
              "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
              "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
              "West Virginia", "Wisconsin", "Wyoming"]

    for state in states:
        if state.lower().startswith(query_lower):
            suggestions.add(state)

    # Sort and limit
    sorted_suggestions = sorted(suggestions)[:limit]
    return sorted_suggestions
