"""Celery task to refresh politician data from ProPublica."""

import asyncio
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Politician
from app.services.propublica import ProPublicaClient, transform_member_to_politician


@celery_app.task(name="app.tasks.refresh_politicians.refresh_all_politicians")
def refresh_all_politicians():
    """Refresh all politician data from ProPublica Congress API."""
    return asyncio.run(_refresh_all_politicians_async())


async def _refresh_all_politicians_async():
    """Async implementation of politician refresh."""
    client = ProPublicaClient()
    db = SessionLocal()

    try:
        updated = 0
        created = 0

        # Current Congress (118th as of 2024)
        congress = 118

        for chamber in ["house", "senate"]:
            members = await client.get_members(congress, chamber)

            for member in members:
                data = transform_member_to_politician(member)

                # Check if politician exists
                existing = db.query(Politician).filter(
                    Politician.bioguide_id == data["bioguide_id"]
                ).first()

                if existing:
                    # Update existing
                    for key, value in data.items():
                        if value is not None:
                            setattr(existing, key, value)
                    updated += 1
                else:
                    # Create new
                    politician = Politician(**data)
                    db.add(politician)
                    created += 1

        db.commit()
        return {"updated": updated, "created": created}

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


@celery_app.task(name="app.tasks.refresh_politicians.refresh_single_politician")
def refresh_single_politician(bioguide_id: str):
    """Refresh data for a single politician."""
    return asyncio.run(_refresh_single_politician_async(bioguide_id))


async def _refresh_single_politician_async(bioguide_id: str):
    """Async implementation of single politician refresh."""
    client = ProPublicaClient()
    db = SessionLocal()

    try:
        member = await client.get_member(bioguide_id)
        if not member:
            return {"error": "Member not found"}

        data = transform_member_to_politician(member)

        existing = db.query(Politician).filter(
            Politician.bioguide_id == bioguide_id
        ).first()

        if existing:
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
            db.commit()
            return {"status": "updated", "bioguide_id": bioguide_id}
        else:
            politician = Politician(**data)
            db.add(politician)
            db.commit()
            return {"status": "created", "bioguide_id": bioguide_id}

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
