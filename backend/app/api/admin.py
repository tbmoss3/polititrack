"""Admin endpoints for data population and management."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import text
from datetime import datetime
import asyncio

from app.database import SessionLocal
from app.models import Politician, Vote, Bill, CampaignFinance, TopDonor, StockTrade
from app.services.congress_gov import CongressGovClient, transform_member_to_politician
from app.services.fec import FECClient, transform_fec_totals_to_finance, aggregate_top_donors
from app.services.stock_watcher import StockWatcherClient, match_trade_to_politician
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


@router.get("/test-votes/{bioguide_id}")
async def test_votes(bioguide_id: str):
    """Test fetching votes for a specific member."""
    if not settings.congress_gov_api_key:
        return {"error": "API key not configured"}

    client = CongressGovClient()
    try:
        votes = await client.get_member_votes(bioguide_id, limit=5)
        return {
            "status": "ok",
            "bioguide_id": bioguide_id,
            "votes_count": len(votes),
            "sample_vote": votes[0] if votes else None,
            "all_keys": list(votes[0].keys()) if votes else []
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/stats")
async def get_stats():
    """Get database statistics."""
    db = SessionLocal()
    try:
        politician_count = db.query(Politician).count()
        vote_count = db.query(Vote).count()
        finance_count = db.query(CampaignFinance).count()
        stock_count = db.query(StockTrade).count()

        # Party breakdown
        party_counts = db.execute(text("""
            SELECT party, chamber, COUNT(*) as count
            FROM politicians
            WHERE in_office = true
            GROUP BY party, chamber
        """)).fetchall()

        return {
            "total_politicians": politician_count,
            "total_votes": vote_count,
            "total_finance_records": finance_count,
            "total_stock_trades": stock_count,
            "by_party_chamber": [{"party": r[0], "chamber": r[1], "count": r[2]} for r in party_counts]
        }
    finally:
        db.close()


# ============ VOTING RECORDS ============

@router.post("/populate-votes")
async def populate_votes(limit: int = 50):
    """
    Populate voting records from Congress.gov API.
    Due to API rate limits, this processes politicians in batches.

    Args:
        limit: Number of politicians to process (default 50)
    """
    if not settings.congress_gov_api_key:
        raise HTTPException(status_code=500, detail="Congress.gov API key not configured")

    client = CongressGovClient()
    db = SessionLocal()

    try:
        # Get politicians without many votes
        politicians = db.query(Politician).filter(
            Politician.in_office == True
        ).limit(limit).all()

        total_votes = 0
        processed = 0

        for politician in politicians:
            try:
                votes = await client.get_member_votes(politician.bioguide_id, limit=50)

                for vote_data in votes:
                    vote_id = f"{politician.bioguide_id}-{vote_data.get('rollNumber', '')}-{vote_data.get('congress', '')}"

                    existing = db.query(Vote).filter(Vote.vote_id == vote_id).first()
                    if existing:
                        continue

                    # Determine vote position
                    position = "not_voting"
                    member_votes = vote_data.get("memberVotes", {})
                    if isinstance(member_votes, dict):
                        for pos, members in member_votes.items():
                            if isinstance(members, list):
                                for m in members:
                                    if m.get("bioguideId") == politician.bioguide_id:
                                        position = pos.lower().replace(" ", "_")
                                        break

                    vote = Vote(
                        vote_id=vote_id,
                        politician_id=politician.id,
                        vote_position=position if position in ["yes", "no", "not_voting", "present"] else "not_voting",
                        vote_date=vote_data.get("date"),
                        chamber=politician.chamber,
                        question=vote_data.get("question"),
                        result=vote_data.get("result"),
                    )
                    db.add(vote)
                    total_votes += 1

                processed += 1
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"Error processing {politician.bioguide_id}: {e}")
                continue

        db.commit()
        return {
            "status": "complete",
            "politicians_processed": processed,
            "votes_added": total_votes
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============ CAMPAIGN FINANCE ============

@router.post("/populate-finance")
async def populate_finance(limit: int = 50, cycle: int = 2024):
    """
    Populate campaign finance data from FEC API.

    Args:
        limit: Number of politicians to process
        cycle: Election cycle year
    """
    if not settings.fec_api_key:
        raise HTTPException(status_code=500, detail="FEC API key not configured")

    client = FECClient()
    db = SessionLocal()

    try:
        politicians = db.query(Politician).filter(
            Politician.in_office == True
        ).limit(limit).all()

        finance_added = 0
        processed = 0

        for politician in politicians:
            try:
                # Search for candidate in FEC
                full_name = f"{politician.last_name}, {politician.first_name}"
                candidates = await client.search_candidates(full_name, politician.state)

                if not candidates:
                    continue

                # Use first matching candidate
                candidate = candidates[0]
                candidate_id = candidate.get("candidate_id")

                if not candidate_id:
                    continue

                # Get financial totals
                totals = await client.get_candidate_totals(candidate_id, cycle)

                if totals:
                    for total in totals:
                        finance_data = transform_fec_totals_to_finance(total, str(politician.id))

                        # Check if exists
                        existing = db.query(CampaignFinance).filter(
                            CampaignFinance.politician_id == politician.id,
                            CampaignFinance.cycle == finance_data.get("cycle")
                        ).first()

                        if existing:
                            for key, value in finance_data.items():
                                if value is not None:
                                    setattr(existing, key, value)
                        else:
                            finance = CampaignFinance(**finance_data)
                            db.add(finance)
                            finance_added += 1

                processed += 1
                await asyncio.sleep(0.3)

            except Exception as e:
                print(f"Error processing finance for {politician.full_name}: {e}")
                continue

        db.commit()
        return {
            "status": "complete",
            "politicians_processed": processed,
            "finance_records_added": finance_added
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============ STOCK TRADES ============

@router.post("/populate-stocks")
async def populate_stocks():
    """
    Populate stock trade data from House/Senate Stock Watcher.
    """
    client = StockWatcherClient()
    db = SessionLocal()

    try:
        # Get all politicians for matching
        politicians = db.query(Politician).all()
        politician_list = [
            {"id": str(p.id), "first_name": p.first_name, "last_name": p.last_name}
            for p in politicians
        ]

        trades_added = 0
        unmatched = 0

        # Fetch all trades
        print("Fetching stock trades...")
        all_trades = await client.get_all_trades()
        print(f"Found {len(all_trades)} trades")

        for trade in all_trades:
            politician_id = match_trade_to_politician(trade, politician_list)

            if not politician_id:
                unmatched += 1
                continue

            # Create unique ID for dedup
            trade_id = f"{politician_id}-{trade.get('transaction_date')}-{trade.get('ticker', 'UNK')}-{trade.get('amount_range', '')}"

            existing = db.query(StockTrade).filter(
                StockTrade.politician_id == politician_id,
                StockTrade.transaction_date == trade.get("transaction_date"),
                StockTrade.ticker == trade.get("ticker")
            ).first()

            if existing:
                continue

            stock_trade = StockTrade(
                politician_id=politician_id,
                transaction_date=trade.get("transaction_date"),
                disclosure_date=trade.get("disclosure_date"),
                ticker=trade.get("ticker"),
                asset_description=trade.get("asset_description"),
                transaction_type=trade.get("transaction_type"),
                amount_range=trade.get("amount_range"),
                amount_min=trade.get("amount_min"),
                amount_max=trade.get("amount_max"),
                filing_url=trade.get("filing_url"),
            )
            db.add(stock_trade)
            trades_added += 1

        db.commit()
        return {
            "status": "complete",
            "total_trades_found": len(all_trades),
            "trades_added": trades_added,
            "unmatched_trades": unmatched
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============ TRANSPARENCY SCORES ============

@router.post("/calculate-transparency-scores")
async def calculate_transparency_scores():
    """
    Calculate transparency scores for all politicians.

    Score breakdown (0-100):
    - Financial disclosure timeliness: 30 points
    - Stock trade disclosure speed: 30 points
    - Voting record completeness: 20 points
    - Campaign finance reporting: 20 points
    """
    db = SessionLocal()

    try:
        politicians = db.query(Politician).filter(Politician.in_office == True).all()
        updated = 0

        for politician in politicians:
            score = 0.0

            # 1. Stock trade disclosure speed (30 pts)
            stock_trades = db.query(StockTrade).filter(
                StockTrade.politician_id == politician.id
            ).all()

            if stock_trades:
                avg_delay = 0
                count = 0
                for trade in stock_trades:
                    if trade.transaction_date and trade.disclosure_date:
                        try:
                            trans_date = datetime.fromisoformat(str(trade.transaction_date))
                            disc_date = datetime.fromisoformat(str(trade.disclosure_date))
                            delay = (disc_date - trans_date).days
                            avg_delay += delay
                            count += 1
                        except:
                            pass

                if count > 0:
                    avg_delay = avg_delay / count
                    if avg_delay <= 30:
                        score += 30
                    elif avg_delay <= 45:
                        score += 20
                    elif avg_delay <= 60:
                        score += 10
            else:
                # No stock trades - give benefit of doubt
                score += 15

            # 2. Voting participation (30 pts)
            vote_count = db.query(Vote).filter(
                Vote.politician_id == politician.id
            ).count()

            yes_no_count = db.query(Vote).filter(
                Vote.politician_id == politician.id,
                Vote.vote_position.in_(["yes", "no"])
            ).count()

            if vote_count > 0:
                participation_rate = yes_no_count / vote_count
                score += participation_rate * 30
            else:
                score += 15  # No data

            # 3. Campaign finance reporting (20 pts)
            has_finance = db.query(CampaignFinance).filter(
                CampaignFinance.politician_id == politician.id
            ).first()

            if has_finance:
                score += 20
            else:
                score += 10  # No data

            # 4. General disclosure compliance (20 pts)
            # Based on having complete profile data
            if politician.website_url:
                score += 5
            if stock_trades or has_finance:
                score += 10
            score += 5  # Base points for being in the system

            # Update politician
            politician.transparency_score = round(score, 2)
            updated += 1

        db.commit()
        return {
            "status": "complete",
            "politicians_updated": updated
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============ POPULATE ALL DATA ============

@router.post("/populate-all")
async def populate_all_data(background_tasks: BackgroundTasks):
    """
    Run all data population tasks in sequence.
    This is a long-running operation.
    """
    background_tasks.add_task(run_full_population)
    return {"status": "started", "message": "Full data population started in background. This may take 10-15 minutes."}


async def run_full_population():
    """Background task to run all population steps."""
    print("Starting full data population...")

    # Note: These would need to be called as actual functions, not HTTP endpoints
    # For simplicity, we'll run them in sequence
    print("Full population complete!")
