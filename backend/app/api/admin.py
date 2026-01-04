"""Admin endpoints for data population and management."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import text

from app.database import SessionLocal
from app.models import Politician
from app.services.congress_gov import CongressGovClient, transform_member_to_politician
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/populate-politicians")
async def populate_politicians(background_tasks: BackgroundTasks):
    """
    Trigger population of politician data from Congress.gov API.
    This runs in the background and may take a few minutes.
    """
    if not settings.congress_gov_api_key:
        raise HTTPException(status_code=500, detail="Congress.gov API key not configured")

    background_tasks.add_task(run_politician_population)
    return {"status": "started", "message": "Politician data population started in background"}


async def run_politician_population():
    """Background task to populate politicians from Congress.gov."""
    client = CongressGovClient()
    db = SessionLocal()

    try:
        updated = 0
        created = 0

        # Current Congress (119th as of 2025)
        congress = 119

        print(f"Fetching members from Congress {congress}...")
        members = await client.get_all_members(congress)
        print(f"Found {len(members)} members")

        for member in members:
            data = transform_member_to_politician(member)

            if not data.get("bioguide_id"):
                continue

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
        print(f"Population complete: {created} created, {updated} updated")

    except Exception as e:
        db.rollback()
        print(f"Population failed: {e}")
        raise e
    finally:
        db.close()


@router.post("/populate-politicians-sync")
async def populate_politicians_sync():
    """
    Synchronous version of politician population for debugging.
    Returns results directly instead of running in background.
    """
    if not settings.congress_gov_api_key:
        raise HTTPException(status_code=500, detail="Congress.gov API key not configured")

    client = CongressGovClient()
    db = SessionLocal()

    try:
        updated = 0
        created = 0

        # Current Congress (119th as of 2025)
        congress = 119

        members = await client.get_all_members(congress)

        for member in members:
            data = transform_member_to_politician(member)

            if not data.get("bioguide_id"):
                continue

            existing = db.query(Politician).filter(
                Politician.bioguide_id == data["bioguide_id"]
            ).first()

            if existing:
                for key, value in data.items():
                    if value is not None:
                        setattr(existing, key, value)
                updated += 1
            else:
                politician = Politician(**data)
                db.add(politician)
                created += 1

        db.commit()
        return {"status": "complete", "created": created, "updated": updated, "total_members_found": len(members)}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/test-congress-api")
async def test_congress_api():
    """Test the Congress.gov API connection."""
    if not settings.congress_gov_api_key:
        return {"error": "API key not configured", "key_length": 0}

    client = CongressGovClient()
    try:
        members = await client.get_members(congress=119, limit=5)
        return {
            "status": "ok",
            "key_configured": True,
            "key_length": len(settings.congress_gov_api_key),
            "sample_members": len(members),
            "first_member": members[0] if members else None
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "key_length": len(settings.congress_gov_api_key)}


@router.get("/stats")
async def get_stats():
    """Get database statistics."""
    db = SessionLocal()
    try:
        politician_count = db.query(Politician).count()

        # Party breakdown
        party_counts = db.execute(text("""
            SELECT party, chamber, COUNT(*) as count
            FROM politicians
            WHERE in_office = true
            GROUP BY party, chamber
        """)).fetchall()

        breakdown = {
            "total_politicians": politician_count,
            "by_party_chamber": [{"party": r[0], "chamber": r[1], "count": r[2]} for r in party_counts]
        }

        return breakdown
    finally:
        db.close()
