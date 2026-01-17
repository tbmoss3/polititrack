"""Voting alignment calculation service."""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import Session

from app.models import Vote, Politician

logger = logging.getLogger(__name__)


@dataclass
class AlignmentResult:
    """Result of voting alignment calculation."""

    politician1_id: UUID
    politician1_name: str
    politician2_id: UUID
    politician2_name: str
    total_common_votes: int
    aligned_votes: int
    alignment_percentage: float
    opposed_votes: int
    one_not_voting: int


@dataclass
class PartyAlignmentResult:
    """Result of party alignment calculation."""

    politician_id: UUID
    politician_name: str
    party: str
    total_party_votes: int
    aligned_with_party: int
    party_alignment_percentage: float
    against_party: int


def calculate_voting_alignment(
    db: Session,
    politician1_id: UUID,
    politician2_id: UUID,
) -> AlignmentResult | None:
    """
    Calculate voting alignment between two politicians.

    Compares how often two politicians vote the same way on common votes.

    Args:
        db: Database session
        politician1_id: First politician's UUID
        politician2_id: Second politician's UUID

    Returns:
        AlignmentResult with voting statistics, or None if insufficient data
    """
    # Get politician names
    p1 = db.get(Politician, politician1_id)
    p2 = db.get(Politician, politician2_id)

    if not p1 or not p2:
        return None

    # Find common votes (same vote_date and chamber, similar vote context)
    # We match on vote_date + chamber + question as a proxy for "same vote"
    p1_votes = (
        select(
            Vote.vote_date,
            Vote.chamber,
            Vote.question,
            Vote.vote_position.label("p1_position"),
        )
        .where(Vote.politician_id == politician1_id)
        .subquery()
    )

    p2_votes = (
        select(
            Vote.vote_date,
            Vote.chamber,
            Vote.question,
            Vote.vote_position.label("p2_position"),
        )
        .where(Vote.politician_id == politician2_id)
        .subquery()
    )

    # Join on matching votes
    common_votes_query = (
        select(
            p1_votes.c.p1_position,
            p2_votes.c.p2_position,
        )
        .select_from(p1_votes)
        .join(
            p2_votes,
            and_(
                p1_votes.c.vote_date == p2_votes.c.vote_date,
                p1_votes.c.chamber == p2_votes.c.chamber,
                p1_votes.c.question == p2_votes.c.question,
            ),
        )
    )

    common_votes = db.execute(common_votes_query).all()

    if not common_votes:
        return AlignmentResult(
            politician1_id=politician1_id,
            politician1_name=p1.full_name,
            politician2_id=politician2_id,
            politician2_name=p2.full_name,
            total_common_votes=0,
            aligned_votes=0,
            alignment_percentage=0.0,
            opposed_votes=0,
            one_not_voting=0,
        )

    # Calculate alignment
    aligned = 0
    opposed = 0
    one_not_voting = 0

    for p1_pos, p2_pos in common_votes:
        # Both voted yes or both voted no
        if p1_pos == p2_pos and p1_pos in ("yes", "no"):
            aligned += 1
        # One voted yes, other voted no
        elif p1_pos in ("yes", "no") and p2_pos in ("yes", "no") and p1_pos != p2_pos:
            opposed += 1
        # One or both didn't vote
        else:
            one_not_voting += 1

    total = len(common_votes)
    # Only count yes/no votes for percentage
    voted_total = aligned + opposed
    alignment_pct = (aligned / voted_total * 100) if voted_total > 0 else 0.0

    return AlignmentResult(
        politician1_id=politician1_id,
        politician1_name=p1.full_name,
        politician2_id=politician2_id,
        politician2_name=p2.full_name,
        total_common_votes=total,
        aligned_votes=aligned,
        alignment_percentage=round(alignment_pct, 1),
        opposed_votes=opposed,
        one_not_voting=one_not_voting,
    )


def calculate_party_alignment(
    db: Session,
    politician_id: UUID,
) -> PartyAlignmentResult | None:
    """
    Calculate how often a politician votes with their party.

    Compares the politician's votes to the majority position of their party.

    Args:
        db: Database session
        politician_id: Politician's UUID

    Returns:
        PartyAlignmentResult with party voting statistics
    """
    politician = db.get(Politician, politician_id)
    if not politician:
        return None

    party = politician.party
    if not party:
        return None

    # Get all votes by this politician
    politician_votes = db.execute(
        select(Vote.vote_date, Vote.chamber, Vote.question, Vote.vote_position)
        .where(Vote.politician_id == politician_id)
        .where(Vote.vote_position.in_(["yes", "no"]))
    ).all()

    if not politician_votes:
        return PartyAlignmentResult(
            politician_id=politician_id,
            politician_name=politician.full_name,
            party=party,
            total_party_votes=0,
            aligned_with_party=0,
            party_alignment_percentage=0.0,
            against_party=0,
        )

    aligned = 0
    against = 0

    for vote_date, chamber, question, position in politician_votes:
        # Find party majority for this vote
        party_votes = db.execute(
            select(
                Vote.vote_position,
                func.count().label("cnt"),
            )
            .join(Politician)
            .where(
                Vote.vote_date == vote_date,
                Vote.chamber == chamber,
                Vote.question == question,
                Politician.party == party,
                Vote.vote_position.in_(["yes", "no"]),
            )
            .group_by(Vote.vote_position)
            .order_by(func.count().desc())
        ).first()

        if party_votes:
            party_majority = party_votes[0]
            if position == party_majority:
                aligned += 1
            else:
                against += 1

    total = aligned + against
    alignment_pct = (aligned / total * 100) if total > 0 else 0.0

    return PartyAlignmentResult(
        politician_id=politician_id,
        politician_name=politician.full_name,
        party=party,
        total_party_votes=total,
        aligned_with_party=aligned,
        party_alignment_percentage=round(alignment_pct, 1),
        against_party=against,
    )


def get_most_aligned_politicians(
    db: Session,
    politician_id: UUID,
    limit: int = 10,
    same_party_only: bool = False,
) -> list[AlignmentResult]:
    """
    Find politicians who vote most similarly to the given politician.

    Args:
        db: Database session
        politician_id: The politician to compare against
        limit: Maximum number of results
        same_party_only: Only compare within same party

    Returns:
        List of AlignmentResult sorted by alignment percentage
    """
    politician = db.get(Politician, politician_id)
    if not politician:
        return []

    # Get other politicians in same chamber
    query = select(Politician).where(
        Politician.id != politician_id,
        Politician.chamber == politician.chamber,
        Politician.in_office == True,
    )

    if same_party_only and politician.party:
        query = query.where(Politician.party == politician.party)

    other_politicians = db.execute(query.limit(50)).scalars().all()

    results = []
    for other in other_politicians:
        alignment = calculate_voting_alignment(db, politician_id, other.id)
        if alignment and alignment.total_common_votes >= 10:  # Minimum votes threshold
            results.append(alignment)

    # Sort by alignment percentage descending
    results.sort(key=lambda x: x.alignment_percentage, reverse=True)
    return results[:limit]


def get_most_opposed_politicians(
    db: Session,
    politician_id: UUID,
    limit: int = 10,
) -> list[AlignmentResult]:
    """
    Find politicians who vote most differently from the given politician.

    Args:
        db: Database session
        politician_id: The politician to compare against
        limit: Maximum number of results

    Returns:
        List of AlignmentResult sorted by alignment percentage (ascending)
    """
    politician = db.get(Politician, politician_id)
    if not politician:
        return []

    # Get other politicians in same chamber
    other_politicians = db.execute(
        select(Politician).where(
            Politician.id != politician_id,
            Politician.chamber == politician.chamber,
            Politician.in_office == True,
        ).limit(50)
    ).scalars().all()

    results = []
    for other in other_politicians:
        alignment = calculate_voting_alignment(db, politician_id, other.id)
        if alignment and alignment.total_common_votes >= 10:
            results.append(alignment)

    # Sort by alignment percentage ascending (lowest = most opposed)
    results.sort(key=lambda x: x.alignment_percentage)
    return results[:limit]
