"""Celery task to refresh voting records from ProPublica."""

import asyncio
import uuid
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Politician, Vote, Bill
from app.services.propublica import ProPublicaClient


@celery_app.task(name="app.tasks.refresh_votes.refresh_all_votes")
def refresh_all_votes():
    """Refresh voting records for all politicians."""
    return asyncio.run(_refresh_all_votes_async())


async def _refresh_all_votes_async():
    """Async implementation of vote refresh."""
    client = ProPublicaClient()
    db = SessionLocal()

    try:
        total_votes = 0
        politicians = db.query(Politician).filter(Politician.in_office == True).all()

        for politician in politicians:
            votes_data = await client.get_member_votes(politician.bioguide_id)

            for vote_data in votes_data[:100]:  # Limit to recent 100 votes per member
                vote_id = f"{politician.bioguide_id}-{vote_data.get('roll_call')}-{vote_data.get('congress')}-{vote_data.get('session')}"

                # Check if vote exists
                existing = db.query(Vote).filter(Vote.vote_id == vote_id).first()
                if existing:
                    continue

                # Find associated bill if any
                bill_id = None
                bill_slug = vote_data.get("bill", {}).get("bill_id")
                if bill_slug:
                    bill = db.query(Bill).filter(Bill.bill_id.ilike(f"%{bill_slug}%")).first()
                    if bill:
                        bill_id = bill.id

                vote = Vote(
                    id=uuid.uuid4(),
                    vote_id=vote_id,
                    bill_id=bill_id,
                    politician_id=politician.id,
                    vote_position=_normalize_position(vote_data.get("position")),
                    vote_date=vote_data.get("date"),
                    chamber=politician.chamber,
                    question=vote_data.get("question"),
                    result=vote_data.get("result"),
                )
                db.add(vote)
                total_votes += 1

        db.commit()
        return {"total_votes_added": total_votes}

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def _normalize_position(position: str | None) -> str:
    """Normalize vote position to standard values."""
    if not position:
        return "not_voting"

    position_lower = position.lower()
    if position_lower in ["yes", "yea", "aye"]:
        return "yes"
    elif position_lower in ["no", "nay"]:
        return "no"
    elif position_lower == "present":
        return "present"
    else:
        return "not_voting"
